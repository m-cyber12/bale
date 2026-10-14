# -*- coding: utf-8 -*-
"""تست موتور هوش مصنوعی + پرونده‌ی شخصیت کاربران (کاملاً آفلاین).

سناریوهایی که چک می‌شوند:
  ۱) کشف و رتبه‌بندی مدل‌های رایگان
  ۲) چرخش خودکار وقتی مدل لیمیت می‌خورد (۴۲۹ → مدل بعدی)
  ۳) کول‌داون مدل لیمیت‌خورده
  ۴) خطای کلید / نبود کلید / ۴۰۲ / ۴۰۴
  ۵) وقتی همه‌ی مدل‌ها خواب باشند → None برمی‌گردد (و لایه‌ی بالا
     پاسخ برنامه‌نویسی‌شده می‌دهد، نه پیام خطا)
  ۶) تنوع جواب‌ها
  ۷) لحن با هر تخلف سخت‌تر می‌شود + نرم‌شدن تدریجی
  ۸) درجه بر اساس تاریخ عضویت
  ۹) پیام تنبیه: با AI و بدون AI (فالبک)
 ۱۰) دستیار: با AI و بدون AI (local_answer)
 ۱۱) امنیت مارک‌داون خروجی AI
"""
import os
import re
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

TMP = tempfile.mkdtemp(prefix="bale_ai_")
import config            # noqa: E402
config.DATA_DIR = TMP

import fake_bale         # noqa: E402
import fake_openrouter   # noqa: E402
import api               # noqa: E402

FAKE_BALE = fake_bale.install(api)
OR = fake_openrouter.FakeOpenRouter()

import storage           # noqa: E402
import ai                # noqa: E402
import ai_persona        # noqa: E402
import ai_panel          # noqa: E402

OR.install(ai)

GROUP = -100777
PV = 11                      # پیوی مالک ربات (chat_id = user_id)
ADMIN = fake_bale.make_user(11, "مدیر کل", "admin")
USER = fake_bale.make_user(22, "علی_رضا", "ali_reza")
NEWBIE = fake_bale.make_user(33, "تازه‌وارد", "newbie")

FAKE_BALE.statuses[(GROUP, 11)] = "creator"

FAILS = []


def check(cond, msg):
    if not cond:
        FAILS.append(msg)
    return cond


def reset_all():
    """پاک‌کردن وضعیت بین تست‌ها."""
    ai.reset_runtime()
    OR.calls.clear()
    OR.served.clear()
    OR.behavior.clear()
    OR.default_behavior = "ok"
    OR.replies.clear()
    OR.reply = fake_openrouter.DEFAULT_REPLY
    ai.set_config(enabled=True, daily_limit=500, rpm_limit=100, blocked=[])


def sent_texts():
    return [m.get("text") or m.get("caption") or "" for m in FAKE_BALE.sent]


def wait_for(pred, timeout=20.0, step=0.05):
    """انتظار برای نتیجه‌ی نخ پس‌زمینه."""
    end = time.time() + timeout
    while time.time() < end:
        if pred():
            return True
        time.sleep(step)
    return False


# ============================================================
# ۱) کشف و رتبه‌بندی مدل‌ها
# ============================================================
def test_model_discovery():
    reset_all()
    ai.set_api_key(OR.key)
    models = ai.refresh_models(force=True)
    ids = [m["id"] for m in models]

    check(len(models) >= 4, f"تعداد مدل‌های رایگان کم است: {len(models)}")
    check(not any("deepseek-v4" in i and ":free" not in i for i in ids),
          "مدل پول‌دار در لیست رایگان آمد")
    check(ids[0].startswith("nvidia/nemotron-3-ultra"),
          f"رتبه‌بندی اشتباه — صدر جدول: {ids[0] if ids else '-'}")
    # مدل کوچک باید پایین‌تر از مدل‌های بزرگ باشد
    scores = {m["id"]: m["score"] for m in models}
    check(scores.get("liquid/lfm-2.5-2.6b:free", 0) <
          scores.get("openai/gpt-oss-120b:free", 0),
          "مدل ضعیف امتیاز بالاتری از مدل قوی گرفت")

    chain = ai.model_chain()
    check(chain and chain[0] == ids[0], "زنجیره از مدل اول شروع نمی‌شود")
    check("openrouter/free" in chain, "مسیریاب خودکار در انتهای زنجیره نیست")
    print(f"  ✓ {len(models)} مدل رایگان، صدر: {ids[0]}")


# ============================================================
# ۲) چرخش خودکار روی ۴۲۹
# ============================================================
def test_rotation_on_rate_limit():
    reset_all()
    ai.set_api_key(OR.key)
    ai.refresh_models(force=True)
    chain = ai.model_chain()

    first, second = chain[0], chain[1]
    OR.behavior[first] = 429                 # مدل اول لیمیت خورده
    OR.default_behavior = "ok"

    text, model = ai.chat([{"role": "user", "content": "سلام"}])
    check(text, "با وجود مدل دوم، پاسخ نیامد")
    check(model == second, f"به مدل بعدی نرفت (پاسخ از {model} آمد، انتظار {second})")
    check(first not in OR.served, "مدل لیمیت‌خورده باید جواب می‌داد؟")
    check(model not in [m for m, _ in OR.calls[:1]],
          "ترتیب تلاش درست نیست")
    check(ai.cooldown_report(), "مدل لیمیت‌خورده کول‌داون نگرفت")

    # درخواست بعدی نباید دوباره سراغ مدل لیمیت‌خورده برود
    before = len(OR.calls)
    ai.chat([{"role": "user", "content": "دوباره"}])
    tried = [m for m, _ in OR.calls[before:]]
    check(first not in tried, f"مدل در کول‌داون دوباره امتحان شد: {tried}")
    print(f"  ✓ چرخش ۴۲۹: {first.split('/')[-1]} → {model.split('/')[-1]} "
          f"(کول‌داون: {ai.cooldown_report()[0][1]}s)")


# ============================================================
# ۳) همه‌ی مدل‌ها خواب → None (نه خطا)
# ============================================================
def test_all_models_down():
    reset_all()
    ai.set_api_key(OR.key)
    ai.refresh_models(force=True)
    OR.default_behavior = 429

    text, why = ai.chat([{"role": "user", "content": "سلام"}])
    check(text is None, "وقتی همه لیمیت‌اند نباید متنی برگردد")
    check(why == "rate-limit", f"دلیل باید rate-limit باشد: {why}")

    # همه‌ی مدل‌های زنجیره امتحان شده باشند
    tried = {m for m, _ in OR.calls}
    check(len(tried) >= 5, f"به اندازه‌ی کافی مدل امتحان نشد: {len(tried)}")
    check(any("openrouter/free" == m for m in tried),
          "مسیریاب خودکار به‌عنوان آخرین راه امتحان نشد")
    print(f"  ✓ همه خواب: {len(tried)} مدل امتحان شد، خروجی None")


# ============================================================
# ۴) خطاهای کلید و سهمیه
# ============================================================
def test_key_errors():
    reset_all()

    # بدون کلید
    ai.set_api_key("")
    check(not ai.ready(), "بدون کلید نباید ready باشد")
    text, why = ai.chat([{"role": "user", "content": "x"}])
    check(text is None and why == "no-key", f"دلیل بدون کلید: {why}")

    # کلید غلط → ۴۰۱
    ai.set_api_key("sk-or-wrong")
    ai.refresh_models(force=True)
    text, why = ai.chat([{"role": "user", "content": "x"}])
    check(text is None and why == "bad-key", f"دلیل کلید غلط: {why}")
    check(not ai.ready(), "بعد از ۴۰۱ کلید باید موقتاً غیرفعال شود")

    # ۴۰۲ سهمیه
    reset_all()
    ai.set_api_key(OR.key)
    ai.refresh_models(force=True)
    OR.default_behavior = 402
    text, why = ai.chat([{"role": "user", "content": "x"}])
    check(text is None, "با ۴۰۲ نباید متنی بیاید")
    print(f"  ✓ خطاهای کلید/سهمیه مدیریت شد (آخرین دلیل: {why})")


# ============================================================
# ۵) ۴۰۴ → مدل حذف‌شده از زنجیره بیرون می‌رود
# ============================================================
def test_dead_model():
    reset_all()
    ai.set_api_key(OR.key)
    ai.refresh_models(force=True)
    chain = ai.model_chain()
    dead = chain[0]
    OR.behavior[dead] = 404

    text, model = ai.chat([{"role": "user", "content": "سلام"}])
    check(text, "با مدل حذف‌شده باید به مدل بعدی برود")
    check(dead not in ai.model_chain(), "مدل ۴۰۴ نباید در زنجیره بماند")
    print(f"  ✓ مدل ۴۰۴ حذف شد، پاسخ از {model.split('/')[-1]}")


# ============================================================
# ۶) تنوع پاسخ‌ها و پاک‌سازی مارک‌داون
# ============================================================
def test_variety_and_markdown():
    reset_all()
    ai.set_api_key(OR.key)
    ai.refresh_models(force=True)
    ai.set_config(temperature=1.0)
    check(ai.config()["temperature"] == 1.0, "تنظیم دما اعمال نشد")

    # خروجی نامتوازن مارک‌داون باید امن شود
    OR.reply = "سلام *دنیا ** نشکن"
    text, _ = ai.chat([{"role": "user", "content": "x"}])
    check(text is not None, "پاسخ نیامد")
    check(not any(c in text for c in ("*", "_", "`")) or "\\" in text,
          f"مارک‌داون نامتوازن پاک‌سازی نشد: {text!r}")
    check(ai.md_balanced("**بولد** متن") is True, "md_balanced روی متن سالم اشتباه کرد")
    check(ai.md_balanced("**بولد نامتوازن") is False, "md_balanced متن خراب را نگرفت")

    safe = ai.safe_md("a *b ** c")
    check(safe.count("\\") >= 2, f"safe_md escape نکرد: {safe!r}")
    print("  ✓ پاک‌سازی مارک‌داون و تنظیم دما")


# ============================================================
# ۷) پرونده و لحن کاربر
# ============================================================
def test_persona_tone():
    reset_all()
    storage.set_("ai_profiles", GROUP, {})

    p = ai_persona.get_profile(GROUP, 22, "علی")
    check(p["tone"] == 0, "لحن اولیه باید ۰ باشد")

    tones = []
    for i in range(3):
        ai_persona.note_violation(GROUP, 22, "spam")
        tones.append(ai_persona.effective_tone(GROUP, 22))
    check(tones == [1, 2, 3], f"سخت‌تر شدن تدریجی درست نیست: {tones}")

    # سقف لحن
    for _ in range(5):
        ai_persona.note_violation(GROUP, 22, "spam")
    check(ai_persona.effective_tone(GROUP, 22) == ai_persona.MAX_TONE,
          "لحن از سقف رد شد")

    # نرم‌شدن تدریجی: آخرین تخلف را ۱۵ روز عقب می‌بریم
    all_p = storage.get("ai_profiles", GROUP)
    all_p["22"]["last_decay"] = time.time() - 15 * 86400
    storage.set_("ai_profiles", GROUP, all_p)
    check(ai_persona.effective_tone(GROUP, 22) == 2,
          f"نرم‌شدن تدریجی کار نکرد: {ai_persona.effective_tone(GROUP, 22)}")

    # آمار تخلف‌ها
    info = ai_persona.rank_info(GROUP, 22)
    check(info["violations"].get("spam") == 8,
          f"شمارش تخلف درست نیست: {info['violations']}")

    # پرونده‌ی دو کاربر مستقل است
    ai_persona.get_profile(GROUP, 33, "تازه‌وارد")
    check(ai_persona.effective_tone(GROUP, 33) == 0,
          "پرونده‌ی کاربر جدید تحت تأثیر دیگری است")
    print(f"  ✓ لحن: 0→3→{ai_persona.MAX_TONE} و نرم‌شدن به 2، پرونده‌ها مستقل")


# ============================================================
# ۸) درجه بر اساس تاریخ عضویت
# ============================================================
def test_rank():
    reset_all()
    storage.set_("ai_profiles", GROUP, {})
    now = time.time()

    cases = [
        ("1", 0, "تازه‌وارد"),
        ("2", 10, "عضو جدید"),
        ("3", 45, "عضو"),
        ("4", 200, "باسابقه"),
        ("5", 400, "ریش‌سفید گروه"),
    ]
    storage.set_("members_seen", GROUP, {})
    all_p = {}
    for uid, days, want in cases:
        all_p[uid] = {"uid": uid, "name": f"کاربر {uid}",
                      "first_seen": now - days * 86400,
                      "last_seen": now, "msgs": 0, "strikes": 0, "praise": 0,
                      "tone": 0, "last_strike": 0, "last_decay": now,
                      "violations": {}, "notes": [], "last_said": []}
    storage.set_("ai_profiles", GROUP, all_p)

    for uid, days, want in cases:
        got = ai_persona.rank_info(GROUP, uid)["rank"]
        check(got == want, f"{days} روز عضویت → {got} (انتظار {want})")
    print("  ✓ درجه‌بندی: تازه‌وارد/عضو جدید/عضو/باسابقه/ریش‌سفید")


# ============================================================
# ۹) پیام تنبیه: با AI و بدون AI
# ============================================================
def test_punish_messages():
    reset_all()
    storage.set_("ai_personas", GROUP, {})
    storage.set_("ai_profiles", GROUP, {})
    storage.set_("ai_group", GROUP, {})

    # --- بدون کلید → پاسخ برنامه‌نویسی‌شده ---
    ai.set_api_key("")
    FAKE_BALE.sent.clear()
    ai_persona.announce_punish(GROUP, "warn", 33, "علی_رضا", by_name="مدیر",
                              reason="لینک", count=1)
    texts = sent_texts()
    check(len(texts) == 1, f"بدون AI باید دقیقاً یک پیام برود: {texts}")
    check("علی" in texts[0], "نام کاربر در پیام نیست")
    check("\\_" in texts[0], "نام کاربر escape نشده")
    check("اخطار" in texts[0], f"متن اخطار نیست: {texts[0]}")

    # --- با AI → متن AI می‌آید ---
    reset_all()
    ai.set_api_key(OR.key)
    ai.refresh_models(force=True)
    OR.reply = "علی جان، این بار فقط اخطار می‌گیری. قوانین رو رعایت کن."
    FAKE_BALE.sent.clear()
    ai_persona.announce_punish(GROUP, "warn", 33, "علی_رضا", by_name="مدیر",
                              reason="لینک", count=1)
    ok = wait_for(lambda: any("اخطار می" in t for t in sent_texts()))
    check(ok, f"متن AI فرستاده نشد: {sent_texts()}")

    # --- با AI خراب → فالبک برنامه‌نویسی‌شده ---
    reset_all()
    ai.set_api_key(OR.key)
    ai.refresh_models(force=True)
    OR.default_behavior = 429
    FAKE_BALE.sent.clear()
    ai_persona.announce_punish(GROUP, "mute", 33, "علی_رضا", by_name="مدیر",
                              reason="اسپم", duration="۱۰ دقیقه")
    # فالبک هم ممکن است از نخ پس‌زمینه بیاید
    wait_for(lambda: len(sent_texts()) >= 1)
    texts = sent_texts()
    check(len(texts) == 1, f"فالبک باید یک پیام بفرستد: {texts}")
    check("علی" in texts[0], f"نام کاربر در متن سکوت نیست: {texts[0]}")
    check(re.search(r"سکوت|بی\u200c?صدا|استراحت|۱۰ دقیقه", texts[0]),
          f"متن سکوت نیست: {texts[0]}")
    print("  ✓ تنبیه: بدون کلید/با AI/با لیمیت — هر سه درست")


# ============================================================
# ۱۰) دستیار مدیریت
# ============================================================
def test_assistant():
    reset_all()
    storage.set_("ai_profiles", GROUP, {})
    storage.set_("user_profiles", GROUP, {
        "11": {"first_name": "مدیر", "username": "admin"},
        "22": {"first_name": "علی_رضا", "username": "ali_reza"},
    })
    storage.set_("members_seen", GROUP, {})
    storage.set_("warnings", GROUP, {"22": 2})
    storage.set_("muted", GROUP, {"33": time.time() + 600})
    storage.set_("banned_users", GROUP, {"44": {"name": "x"}})
    storage.set_("locks", GROUP, {"link": True, "photo": True})

    # --- بدون AI → پاسخ برنامه‌نویسی‌شده از داده‌ی واقعی ---
    ai.set_api_key("")
    FAKE_BALE.sent.clear()
    ai_persona.answer_question(GROUP, 11, "مدیر", "وضعیت گروه چطوره؟")
    t = sent_texts()
    check(len(t) == 1, f"پاسخ محلی نیامد: {t}")
    check("2" in t[0] and "وضعیت" in t[0], f"آمار محلی درست نیست: {t[0]}")

    FAKE_BALE.sent.clear()
    ai_persona.answer_question(GROUP, 11, "مدیر", "اخطارها")
    t = sent_texts()
    check(t and "علی" in t[0], f"لیست اخطارها نیامد: {t}")

    FAKE_BALE.sent.clear()
    ai_persona.answer_question(GROUP, 11, "مدیر", "قفل‌ها چیه؟")
    t = sent_texts()
    check(t and "link" in t[0], f"لیست قفل‌ها نیامد: {t}")

    # --- با AI ---
    reset_all()
    ai.set_api_key(OR.key)
    ai.refresh_models(force=True)
    OR.reply = "گروه آرومه؛ دو تا اخطار فعال داریم و دو قفل روشنه."
    FAKE_BALE.sent.clear()
    ai_persona.answer_question(GROUP, 11, "مدیر", "وضعیت چطوره؟")
    ok = wait_for(lambda: any("دو تا اخطار" in x for x in sent_texts()))
    check(ok, f"پاسخ AI نیامد: {sent_texts()}")

    # --- با AI خراب → همان پاسخ محلی ---
    reset_all()
    ai.set_api_key(OR.key)
    ai.refresh_models(force=True)
    OR.default_behavior = 500
    FAKE_BALE.sent.clear()
    ai_persona.answer_question(GROUP, 11, "مدیر", "قوانین گروه چیه؟")
    ok = wait_for(lambda: len(sent_texts()) >= 1)
    check(ok and any("قانون" in x for x in sent_texts()),
          f"فالبک دستیار کار نکرد: {sent_texts()}")
    print("  ✓ دستیار: بدون AI / با AI / فالبک")


# ============================================================
# ۱۱) پرامپت‌ها اطلاعات کاربر را دارند
# ============================================================
def test_prompts_contain_context():
    reset_all()
    storage.set_("ai_profiles", GROUP, {})
    ai_persona.get_profile(GROUP, 22, "علی")
    ai_persona.note_violation(GROUP, 22, "spam")
    ai_persona.note_note(GROUP, 22, "دو بار در شب اسپم کرد")

    prompt = ai_persona.user_prompt_for_punish(
        "اخطار", "اسپم", "گروه تست", GROUP, 22, "علی", "مدیر")
    for needle in ["لحن", "تخلف", "اسپم", "دو بار در شب اسپم"]:
        check(needle in prompt, f"«{needle}» در پرامپت نیست")
    check("معمولی" in prompt, "برچسب لحن فعلی در پرامپت نیست")

    # نام آلوده نباید پرامپت را خراب کند
    p2 = ai_persona.user_prompt_for_punish(
        "اخطار", "x", "گروه", GROUP, 22, "علی_رضا", "مدیر")
    check("علی_رضا" in p2, "نام کاربر در پرامپت نیست")

    # پرامپت دستیار شامل اطلاعات واقعی گروه است
    storage.set_("warnings", GROUP, {"22": 1})
    facts = ai_persona.group_facts(GROUP)
    check("اخطارهای فعال" in facts, "اطلاعات گروه در پرامپت نیست")
    print("  ✓ پرامپت‌ها شامل تاریخ/درجه/لحن/سابقه‌اند")


# ============================================================
# ۱۲) پاسخ‌های برنامه‌نویسی‌شده متنوع‌اند
# ============================================================
def test_canned_variety():
    texts = {ai_persona.canned("warn", 0, n="کاربر", c="1") for _ in range(25)}
    check(len(texts) >= 2, f"پاسخ‌های آماده تنوع ندارند: {texts}")
    t0 = {ai_persona.canned("warn", 0, n="کاربر", c="1") for _ in range(30)}
    t4 = {ai_persona.canned("warn", 4, n="کاربر", c="1") for _ in range(30)}
    check(not (t0 & t4), "پاسخ لحن ۰ و ۴ یکسان است — لحن اثر ندارد")
    print(f"  ✓ تنوع: لحن مهربان {len(t0)} حالت، لحن بی‌گذشت {len(t4)} حالت")


# ============================================================
# ۱۳) گروه می‌تواند خاموش کند
# ============================================================
def test_group_toggle():
    reset_all()
    ai.set_api_key(OR.key)
    ai.refresh_models(force=True)
    ai_panel.set_group_setting(GROUP, "announce", False)
    check(ai_panel.feature_on(GROUP, "announce") is False, "خاموش‌کردن کار نکرد")

    from admin import _announce
    FAKE_BALE.sent.clear()
    _announce(GROUP, "warn", 33, "علی_رضا", by_name="مدیر", reason="تست",
              count=1, fallback="⚠️ اخطار ۱/۳")
    check(len(sent_texts()) == 1 and "اخطار" in sent_texts()[0],
          f"وقتی AI خاموش است باید متن آماده برود: {sent_texts()}")
    check(len(OR.calls) == 0, "با خاموش‌بودن نباید به OpenRouter درخواست برود")

    ai_panel.set_group_setting(GROUP, "announce", True)
    check(ai_panel.feature_on(GROUP, "announce") is True, "روشن‌کردن کار نکرد")
    print("  ✓ خاموش/روشن گروهی + متن آماده‌ی admin")


# ============================================================
# ۱۴) سقف مصرف (گاردها)
# ============================================================
def test_guards():
    reset_all()
    ai.set_api_key(OR.key)
    ai.refresh_models(force=True)

    ai.set_config(rpm_limit=1, daily_limit=500)
    ai.chat([{"role": "user", "content": "۱"}])
    text, why = ai.chat([{"role": "user", "content": "۲"}])
    check(text is None and why == "rpm-guard", f"گارد دقیقه‌ای کار نکرد: {why}")

    ai.reset_runtime()
    ai.set_config(rpm_limit=100, daily_limit=0)
    text, why = ai.chat([{"role": "user", "content": "۳"}])
    check(text is None and why == "daily-guard", f"گارد روزانه کار نکرد: {why}")

    # شمارنده‌ی مصرف باید درست بشمارد (ریست نمی‌شود، چون آمار واقعی است)
    reset_all()
    ai.set_config(daily_limit=500)
    before = ai.usage_today()
    ai.chat([{"role": "user", "content": "۴"}])
    check(ai.usage_today() == before + 1,
          f"شمارنده‌ی مصرف درست کار نمی‌کند: {before} → {ai.usage_today()}")
    print("  ✓ سقف دقیقه‌ای و روزانه + شمارش مصرف")


# ============================================================
# ۱۵) جریان تنظیم کلید از پنل (باگ بخش settings)
# ============================================================
def test_key_flow():
    import panels
    panels.OWNER_ID = 11            # مالک ربات در تست
    reset_all()
    ai.set_api_key("")
    storage.set_("settings", "global", {})
    storage.set_("settings", PV, {})

    # بدون پرامپت → پیام کلید نباید مصرف شود
    FAKE_BALE.sent.clear()
    check(ai_panel.handle_wait_key(PV, 11, "سلام") is False,
          "بدون پرامپت نباید پیام مصرف شود")
    check(ai.api_key() == "", "بدون پرامپت نباید کلید ست شود")

    # دکمه‌ی 🔑 در پنل مالک (در پیوی) → پرامپت باید در بخش global ثبت شود
    FAKE_BALE.sent.clear()
    ai_panel.handle_callback(
        {"id": "cbkey", "data": "ai:key", "from": ADMIN,
         "message": {"chat": {"id": PV, "type": "private"}, "message_id": 5}},
        "cbkey", "ai:key", PV, 5, ADMIN)
    g = storage.get("settings", "global") or {}
    check(g.get("wait_ai_key") == 11,
          f"پرامپت کلید در بخش global ثبت نشد: {g.get('wait_ai_key')}")

    # ارسال کلید در پیوی → ذخیره و پاک‌شدن پرامپت
    FAKE_BALE.sent.clear()
    check(ai_panel.handle_wait_key(PV, 11, "sk-or-v1-abcdef123456") is True,
          "پیام کلید مصرف نشد")
    check(ai.api_key() == "sk-or-v1-abcdef123456",
          f"کلید ذخیره نشد: {ai.api_key()!r}")
    g = storage.get("settings", "global") or {}
    check(not g.get("wait_ai_key"), "پرامپت کلید پاک نشد")

    # با کلید جدید باید مدل‌ها گرفته و engine آماده شود
    OR.key = "sk-or-v1-abcdef123456"
    ai.reset_runtime()
    ai.refresh_models(force=True)
    check(ai.ready() is True, "با کلید درست باید ready شود")

    # کلید نامعتبر (بدون sk-) نباید جایگزین شود
    storage.set_("settings", "global", {"wait_ai_key": 11})
    FAKE_BALE.sent.clear()
    check(ai_panel.handle_wait_key(PV, 11, "abcd") is True,
          "پیام نامعتبر باید مصرف شود (تا دوباره پردازش نشود)")
    check(ai.api_key() == "sk-or-v1-abcdef123456",
          f"کلید نامعتبر جایگزین شد: {ai.api_key()!r}")

    ai.set_api_key("")
    print("  ✓ جریان کلید: پرامپت → ذخیره → پاک‌شدن (بخش global)")


# ============================================================
# ۱۶) خوش‌آمدگویی: مسیر AI و مسیر متن دلخواه
# ============================================================
def test_welcome_flow():
    import features
    reset_all()
    ai.set_api_key(OR.key)
    ai.refresh_models(force=True)
    storage.set_("ai_group", GROUP, {"welcome": True})
    storage.set_("welcome", GROUP, {"enabled": True, "text": "", "autodelete": 0})
    storage.set_("ai_profiles", GROUP, {})

    # ---- AI روشن: متن ساخته‌شده‌ی AI می‌آید و None برمی‌گردد ----
    OR.reply = "علی_رضا خوش اومدی به گروه تست! 🌱"
    FAKE_BALE.sent.clear()
    r = features.send_welcome(GROUP, "علی_رضا", "گروه تست", member_id=22)
    check(r is None, f"در مسیر AI باید None برگردد: {r}")
    ok = wait_for(lambda: any("خوش اومدی" in t for t in sent_texts()))
    check(ok, f"پیام خوش‌آمد AI نیامد: {sent_texts()}")

    # ---- AI خراب → متن آماده (هیچ‌وقت پیام خطا) ----
    reset_all()
    ai.set_api_key(OR.key)
    ai.refresh_models(force=True)
    OR.default_behavior = 429
    FAKE_BALE.sent.clear()
    r = features.send_welcome(GROUP, "علی_رضا", "گروه تست", member_id=22)
    check(r is None, "در مسیر AI باید None برگردد (حتی با شکست)")
    ok = wait_for(lambda: any("خوش آمدی" in t or "خوش اومدی" in t
                              for t in sent_texts()))
    check(ok, f"فالبک خوش‌آمد نیامد: {sent_texts()}")

    # ---- متن دلخواه ادمین: AI نباید دخالت کند ----
    reset_all()
    ai.set_api_key(OR.key)
    ai.refresh_models(force=True)
    storage.set_("welcome", GROUP,
                 {"enabled": True, "text": "سلام {name}، به {group} خوش آمدی",
                  "autodelete": 0})
    keys_before = len(OR.calls)
    FAKE_BALE.sent.clear()
    r = features.send_welcome(GROUP, "علی_رضا", "گروه تست", member_id=22)
    check(r is not None, "متن دلخواه باید هم‌زمان و با شناسه‌ی پیام برود")
    check(len(OR.calls) == keys_before, "با متن دلخواه نباید به AI درخواست برود")
    check(any("علی_رضا" in t and "گروه تست" in t for t in sent_texts()),
          f"متن دلخواه درست ساخته نشد: {sent_texts()}")

    # ---- بدون member_id → مسیر AI اصلاً امتحان نمی‌شود ----
    reset_all()
    ai.set_api_key(OR.key)
    ai.refresh_models(force=True)
    storage.set_("welcome", GROUP, {"enabled": True, "text": "", "autodelete": 0})
    keys_before = len(OR.calls)
    FAKE_BALE.sent.clear()
    r = features.send_welcome(GROUP, "علی_رضا", "گروه تست")
    check(r is not None, "بدون member_id باید متن آماده برود")
    check(len(OR.calls) == keys_before, "بدون member_id نباید به AI برود")
    print("  ✓ خوش‌آمد: AI / فالبک / متن دلخواه / بدون member_id")


def main():
    tests = [
        ("کشف و رتبه‌بندی مدل‌ها", test_model_discovery),
        ("چرخش خودکار روی ۴۲۹", test_rotation_on_rate_limit),
        ("همه‌ی مدل‌ها خواب", test_all_models_down),
        ("خطاهای کلید/سهمیه", test_key_errors),
        ("مدل حذف‌شده (۴۰۴)", test_dead_model),
        ("تنوع و مارک‌داون", test_variety_and_markdown),
        ("لحن کاربر", test_persona_tone),
        ("درجه‌بندی", test_rank),
        ("پیام تنبیه", test_punish_messages),
        ("دستیار مدیریت", test_assistant),
        ("محتوای پرامپت", test_prompts_contain_context),
        ("تنوع پاسخ‌های آماده", test_canned_variety),
        ("خاموش/روشن گروهی", test_group_toggle),
        ("گاردهای مصرف", test_guards),
        ("جریان کلید OpenRouter", test_key_flow),
        ("خوش‌آمدگویی با AI", test_welcome_flow),
    ]
    print("=" * 70)
    print("تست موتور هوش مصنوعی و شخصیت کاربران")
    print(f"دیتای موقت: {TMP}")
    print("=" * 70)
    for name, fn in tests:
        before = len(FAILS)
        try:
            fn()
        except Exception:
            import traceback
            FAILS.append(f"{name}: استثنا\n{traceback.format_exc()}")
        mark = "❌" if len(FAILS) > before else "✅"
        print(f"{mark} {name}")

    print("=" * 70)
    if FAILS:
        print(f"❌ {len(FAILS)} مشکل:")
        for f in FAILS:
            print("  •", f)
        return 1
    print("🎉 همه‌ی تست‌های AI سبز")
    return 0


if __name__ == "__main__":
    sys.exit(main())
