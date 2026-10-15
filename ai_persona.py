# -*- coding: utf-8 -*-
"""شخصیت و حافظه‌ی هوش مصنوعی برای هر کاربر.

هر کاربر یک پرونده دارد: تاریخ عضویت، سطح، تعداد تخلف‌ها، «لحن» فعلی.
هر تخلف، لحن را یک پله سخت‌تر می‌کند و بی‌تخلف‌ماندن طولانی، آرام‌آرام
نرمش می‌دهد. AI با همین پرونده حرف می‌زند تا رفتارش با هر کس متفاوت باشد.

قاعده‌ی مهم: **AI فقط متن را می‌سازد، تصمیم با کد است.** مجازات‌ها همیشه
توسط منطق برنامه تعیین می‌شوند و AI هیچ‌وقت نمی‌تواند کسی را اخراج کند.

اگر AI در دسترس نبود یا لیمیت خورد، همان پاسخ‌های برنامه‌نویسی‌شده
(canned) فرستاده می‌شود — نه پیام خطا.
"""
import random
import time

import ai
import api
import storage
from storage import get, set_

SECTION = "ai_profiles"

# ============================================================
# لحن (۰ = مهربان … ۴ = بی‌گذشت)
# ============================================================
TONE_LABELS = ["مهربان", "معمولی", "جدی", "سخت‌گیر", "بی‌گذشت"]

TONE_BRIEF = {
    0: "با مهربانی و صمیمیت، تشویق‌کننده و کوتاه",
    1: "محترمانه ولی جدی؛ بدون شوخی، مستقیم",
    2: "جدی و قاطع؛ بدون تعارف، با هشدار روشن",
    3: "تیز و سرد؛ هشدار صریح بده و بگو تکرارش عواقب دارد",
    4: "خیلی خشک و بدون ارفاق؛ صریح بگو که اقدام سخت‌تری انجام می‌شود",
}

STRIKE_DECAY_DAYS = 7          # هر ۷ روز بی‌تخلف = یک پله نرم‌تر
MAX_TONE = 4

# ============================================================
# پرونده‌ی کاربر
# ============================================================
def _blank(uid, name=""):
    return {
        "uid": str(uid),
        "name": name or "",
        "first_seen": time.time(),
        "last_seen": time.time(),
        "msgs": 0,
        "strikes": 0,
        "praise": 0,
        "tone": 0,
        "last_strike": 0,
        "last_decay": time.time(),
        "violations": {},        # نوع تخلف → تعداد
        "notes": [],             # یادداشت‌های کوتاه AI
        "last_said": [],         # آخرین جمله‌هایی که AI گفته (برای تکرار نشدن)
        "chat_log": [],          # آخرین پرسش/پاسخ‌های گفتگو (حافظه‌ی کوتاه)
    }


def get_profile(chat_id, user_id, name=None):
    """پرونده‌ی کاربر را می‌گیرد یا می‌سازد."""
    try:
        all_p = get(SECTION, chat_id) or {}
    except Exception:
        all_p = {}
    uid = str(user_id)
    p = all_p.get(uid)
    if not p:
        p = _blank(uid, name or "")
        all_p[uid] = p
        try:
            set_(SECTION, chat_id, all_p)
        except Exception as e:
            print(f"[persona:create] {e}")
        return p
    if name and p.get("name") != name:
        p["name"] = name
    return p


def _save(chat_id, all_p):
    try:
        set_(SECTION, chat_id, all_p)
    except Exception as e:
        print(f"[persona:save] {e}")


def _mutate(chat_id, user_id, fn, name=None):
    all_p = get(SECTION, chat_id) or {}
    uid = str(user_id)
    p = all_p.get(uid) or _blank(uid, name or "")
    fn(p)
    all_p[uid] = p
    _save(chat_id, all_p)
    return p


# ============================================================
# رویدادها
# ============================================================
def note_message(chat_id, user_id, name=None):
    """ثبت فعالیت عادی."""
    def f(p):
        p["msgs"] = int(p.get("msgs", 0)) + 1
        p["last_seen"] = time.time()
        if name:
            p["name"] = name
    return _mutate(chat_id, user_id, f, name)


def note_violation(chat_id, user_id, kind="general", name=None, escalate=True):
    """ثبت تخلف — لحن را یک پله سخت‌تر می‌کند."""
    def f(p):
        p["strikes"] = int(p.get("strikes", 0)) + 1
        p["last_strike"] = time.time()
        if name:
            p["name"] = name
        v = p.setdefault("violations", {})
        v[kind] = int(v.get(kind, 0)) + 1
        if escalate:
            p["tone"] = min(MAX_TONE, int(p.get("tone", 0)) + 1)
            p["last_decay"] = time.time()
    return _mutate(chat_id, user_id, f, name)


def note_good(chat_id, user_id, name=None, relax=False):
    """رفتار مثبت — می‌تواند یک پله نرم‌تر کند."""
    def f(p):
        p["praise"] = int(p.get("praise", 0)) + 1
        if relax:
            p["tone"] = max(0, int(p.get("tone", 0)) - 1)
        if name:
            p["name"] = name
    return _mutate(chat_id, user_id, f, name)


def note_note(chat_id, user_id, note, keep=4):
    """یادداشت کوتاه از رفتار کاربر (برای حافظه‌ی طولانی‌مدت)."""
    note = (note or "").strip()[:160]
    if not note:
        return None

    def f(p):
        notes = p.setdefault("notes", [])
        if note not in notes:
            notes.append(note)
        p["notes"] = notes[-keep:]
    return _mutate(chat_id, user_id, f)


def remember_said(chat_id, user_id, text, keep=3):
    """آخرین جمله‌های AI را نگه می‌دارد تا تکرار نکند."""
    text = (text or "").strip()[:200]
    if not text:
        return

    def f(p):
        said = p.setdefault("last_said", [])
        said.append(text)
        p["last_said"] = said[-keep:]
    _mutate(chat_id, user_id, f)


def reset_user(chat_id, user_id, full=False):
    all_p = get(SECTION, chat_id) or {}
    uid = str(user_id)
    if uid not in all_p:
        return False
    if full:
        all_p.pop(uid, None)
    else:
        p = all_p[uid]
        p["tone"] = 0
        p["strikes"] = 0
        p["violations"] = {}
        p["last_strike"] = 0
        p["notes"] = []
        p["last_said"] = []
    _save(chat_id, all_p)
    return True


# ============================================================
# لحن مؤثر (با نرم‌شدن تدریجی)
# ============================================================
def effective_tone(chat_id, user_id):
    p = get_profile(chat_id, user_id)
    tone = int(p.get("tone", 0))
    last = float(p.get("last_decay") or p.get("last_strike") or time.time())
    days = (time.time() - last) / 86400.0
    decay = int(days // STRIKE_DECAY_DAYS)
    if decay > 0:
        new_tone = max(0, tone - decay)
        if new_tone != tone:
            def f(pp):
                pp["tone"] = new_tone
                pp["last_decay"] = time.time()
            _mutate(chat_id, user_id, f)
        tone = new_tone
    return max(0, min(MAX_TONE, tone))


def tone_label(chat_id, user_id):
    return TONE_LABELS[effective_tone(chat_id, user_id)]


# ============================================================
# درجه و سابقه
# ============================================================
RANKS = [
    (1, "تازه‌وارد"),
    (7, "عضو جدید"),
    (30, "عضو"),
    (90, "عضو قدیمی"),
    (180, "باسابقه"),
    (365, "ریش‌سفید گروه"),
]


def rank_info(chat_id, user_id):
    """تاریخ عضویت، درجه، سطح و سابقه‌ی کاربر."""
    uid = str(user_id)
    prof = get_profile(chat_id, user_id)

    seen = (get("members_seen", chat_id) or {}).get(uid) or {}
    users = (get("user_profiles", chat_id) or {}).get(uid) or {}

    first = prof.get("first_seen") or seen.get("ts") or users.get("first_seen") or time.time()
    days = max(0, int((time.time() - float(first)) / 86400))

    label = "تازه‌وارد"
    for d, r in RANKS:
        if days >= d:
            label = r

    try:
        from xp import get_user
        xp_data = get_user(chat_id, user_id) or {}
    except Exception:
        xp_data = {}

    return {
        "days": days,
        "rank": label,
        "level": int(xp_data.get("level", 1) or 1),
        "xp": int(xp_data.get("xp", 0) or 0),
        "msgs": int(prof.get("msgs", 0) or 0),
        "strikes": int(prof.get("strikes", 0) or 0),
        "praise": int(prof.get("praise", 0) or 0),
        "tone": effective_tone(chat_id, user_id),
        "violations": dict(prof.get("violations") or {}),
        "notes": list(prof.get("notes") or []),
        "last_said": list(prof.get("last_said") or []),
    }


_VIOLATION_FA = {
    "spam": "اسپم", "link": "لینک", "badword": "فحش/کلمه ممنوعه",
    "lock": "قفل‌شکنی", "flood": "پیام پشت‌سرهم", "forward": "فوروارد",
    "media": "ارسال مدیای غیرمجاز", "slowmode": "نقض حالت آهسته",
    "night": "پیام در حالت شب", "sleep": "پیام در حالت خواب",
    "warn": "اخطار", "mute": "سکوت", "ban": "بن", "kick": "اخراج",
    "general": "تخلف عمومی",
}


def violation_text(kind):
    return _VIOLATION_FA.get(kind, kind or "تخلف")


def describe_user(chat_id, user_id, name=""):
    """خلاصه‌ی فارسی از کاربر — برای تزریق در پرامپت AI."""
    info = rank_info(chat_id, user_id)
    name = name or get_profile(chat_id, user_id).get("name") or f"کاربر {user_id}"
    lines = [
        f"نام: {name}",
        f"عضویت: {info['days']} روز پیش — درجه: {info['rank']}",
        f"سطح: {info['level']} ({info['xp']} XP) | پیام‌ها: {info['msgs']}",
        f"تخلف‌ها: {info['strikes']}",
    ]
    if info["violations"]:
        parts = [f"{violation_text(k)} ×{v}" for k, v in
                 sorted(info["violations"].items(), key=lambda x: -x[1])[:4]]
        lines.append("نوع تخلف‌ها: " + "، ".join(parts))
    if info["notes"]:
        lines.append("یادداشت رفتار: " + " | ".join(info["notes"][-3:]))
    lines.append(f"لحن لازم با این کاربر: {TONE_LABELS[info['tone']]}")
    return "\n".join(lines)


# ============================================================
# پرامپت‌ها
# ============================================================
_BASE_RULES = """تو «آلفا» هستی، دستیار مدیریت گروه در پیام‌رسان بله (نه تلگرام).
وظیفه‌ی تو فقط کمک به مدیریت گروه است: اخطار، سکوت، بن، اخراج، قوانین،
ضداسپم، قفل‌ها، آمار گروه، خوش‌آمدگویی و راهنمایی مدیرها.

قواعد سخت:
- فقط فارسی بنویس. کوتاه، طبیعی و انسانی — نه ماشینی.
- درباره‌ی بازی، سرگرمی، کدنویسی، سیاست، پزشکی و موضوعات بی‌ربط حرف نزن؛
  اگر کسی چیز بی‌ربط پرسید، بگو کارت مدیریت گروه است.
- هرگز نگو «من یک هوش مصنوعی هستم» یا اسم مدل را نبر.
- از مارک‌داون فقط **بولد** استفاده کن؛ ستاره، آندرلاین و بک‌تیک تکی به‌کار نبر.
- تصمیم درباره‌ی مجازات با برنامه است؛ تو فقط متن را می‌نویسی و
  مجازات اعلام‌شده را عوض نمی‌کنی.
"""

#: قواعد حالت «گفتگو» — وقتی کاربر روی پیام ربات ریپلای می‌کند
CHAT_RULES = """تو «آلفا» هستی، دستیار گروه در پیام‌رسان بله (نه تلگرام).
کاربر روی پیام تو ریپلای کرده و دارد با تو حرف می‌زند؛ این یک گفتگوست.

قواعد:
- فقط فارسی، کوتاه و انسانی (۱ تا ۴ جمله). مثل یک آدم واقعی جواب بده.
- اگر سؤالش درباره‌ی گروه/قوانین/آمار/مدیریت بود، از «اطلاعات واقعی گروه»
  که در ادامه می‌آید استفاده کن و عدد از خودت درنیار.
- اگر چیز بی‌ربطی پرسید، کوتاه و بی‌تعارف جواب بده و یادآوری کن که
  کار اصلی‌ات مدیریت گروه است؛ بحث طولانی راه نینداز.
- هیچ‌وقت نگو «من یک هوش مصنوعی هستم» و اسم مدل را نبر.
- از مارک‌داون فقط **بولد** استفاده کن؛ ستاره/آندرلاین/بک‌تیک تکی نه.
- خودت هیچ اقدامی (بن، سکوت، اخراج) انجام نمی‌دهی؛ فقط توضیح می‌دهی.
- اگر از تو خواست کسی را بن/سکوت کنی، بگو که این کار را باید ادمین
  با دستور خودش انجام بدهد.
"""

_STYLES = [
    "کوتاه و ضربه‌ای بنویس",
    "خودمانی و رفاقتی ولی محترم",
    "با یک سؤال کوتاه تمامش کن",
    "با یک اشاره به آمار یا سابقه‌ی کاربر",
    "با یک هشدار روشن و بدون اضافه‌گویی",
    "با لحنی که کاربر حس کند جدی گرفته شده",
]


def _style(tone):
    pool = list(_STYLES)
    if tone >= 3:
        pool = [s for s in pool if "خودمانی" not in s and "سؤال" not in s]
    return random.choice(pool)


def system_prompt():
    return _BASE_RULES


def _no_repeat_note(info):
    if not info["last_said"]:
        return ""
    last = " | ".join(s[:60] for s in info["last_said"])
    return f"\nجملات قبلی‌ات که نباید تکرار شوند: {last}\n"


def user_prompt_for_punish(action_fa, reason, chat_title, chat_id, target_id,
                           target_name, by_name, extra=""):
    info = rank_info(chat_id, target_id)
    tone = info["tone"]
    body = (
        f"وضعیت گروه: {chat_title}\n"
        f"اقدام انجام‌شده: {action_fa}\n"
        f"دلیل: {reason or 'نقض قوانین'}\n"
        f"انجام‌دهنده: {by_name}\n"
        f"مخاطب پیام: {target_name}\n\n"
        f"پرونده‌ی این کاربر:\n{describe_user(chat_id, target_id, target_name)}\n"
        f"{_no_repeat_note(info)}"
    )
    if extra:
        body += f"\nنکته: {extra}\n"
    body += (
        f"\nیک پیام کوتاه (حداکثر ۲ جمله) بنویس که این اقدام را به گروه اعلام کند "
        f"و نام کاربر را داشته باشد. لحن: {TONE_LABELS[tone]} — {TONE_BRIEF[tone]}.\n"
        f"سبک نگارش: {_style(tone)}.\n"
        f"اسم کاربر را دقیقاً همان‌طور که آمده بنویس.\n"
        f"فقط متن پیام را بده، بدون توضیح اضافه."
    )
    return body


def user_prompt_for_answer(question, chat_id, chat_title, user_id, user_name,
                           group_facts=""):
    info = rank_info(chat_id, user_id)
    body = (
        f"گروه: {chat_title}\n"
        f"پرسش‌کننده: {user_name} ({info['rank']}، {info['days']} روز عضویت، "
        f"سطح {info['level']})\n"
        f"لحن با این کاربر: {TONE_LABELS[info['tone']]}\n"
    )
    if group_facts:
        body += f"\nاطلاعات واقعی گروه (فقط از همین‌ها استفاده کن):\n{group_facts}\n"
    body += (
        f"\nپرسش: {question}\n\n"
        f"در حداکثر ۵ جمله و فقط درباره‌ی مدیریت گروه پاسخ بده. "
        f"اگر جواب در اطلاعات بالا نیست، صادقانه بگو اطلاعاتش را ندارم. "
        f"سبک: {_style(info['tone'])}. فقط متن پاسخ، بدون توضیح اضافه."
    )
    return body


def user_prompt_for_welcome(chat_id, new_id, new_name, chat_title):
    info = rank_info(chat_id, new_id)
    return (
        f"یک عضو جدید وارد گروه «{chat_title}» شد.\n"
        f"نام او: {new_name}\n"
        f"اطلاعات: {info['rank']}، سطح {info['level']}\n\n"
        f"یک پیام خوش‌آمدگویی کوتاه (۱ تا ۲ جمله) با لحنی گرم بنویس و "
        f"یک نکته‌ی کوتاه یادآوری کن (مثل خواندن قوانین). "
        f"از مارک‌داون تکی استفاده نکن. فقط متن پیام."
    )


def remember_turn(chat_id, user_id, question, answer, keep=3):
    """آخرین گفتگوها را نگه می‌دارد تا AI یادش بماند چه گفتیم."""
    q = (question or "").strip()[:200]
    a = (answer or "").strip()[:200]
    if not q:
        return

    def f(p):
        log = p.setdefault("chat_log", [])
        log.append({"q": q, "a": a, "ts": time.time()})
        p["chat_log"] = log[-keep:]
    _mutate(chat_id, user_id, f)


def _chat_history(info, keep=3):
    log = (info or {}).get("chat_log") or []
    if not log:
        return ""
    lines = []
    for turn in log[-keep:]:
        lines.append(f"  کاربر: {turn.get('q','')}")
        if turn.get("a"):
            lines.append(f"  تو: {turn.get('a','')}")
    return "\nگفتگوی قبلی همین کاربر (ادامه‌اش باش، تکرار نکن):\n" + \
           "\n".join(lines) + "\n"


def reply_prompt(question, chat_id, chat_title, user_id, user_name,
                 quoted="", group_facts=""):
    """پرامپت پاسخ به ریپلای (حالت گفتگو)."""
    info = rank_info(chat_id, user_id)
    body = (
        f"گروه: {chat_title}\n"
        f"کاربر: {user_name} — {info['rank']}، {info['days']} روز عضویت، "
        f"سطح {info['level']}\n"
        f"لحن تو با او: {TONE_LABELS[info['tone']]}\n"
    )
    if quoted:
        body += f"\nپیام تو که کاربر رویش ریپلای کرده:\n{quoted[:400]}\n"
    body += _chat_history(info)
    if group_facts:
        body += f"\nاطلاعات واقعی گروه (فقط برای همین‌ها از این عددها استفاده کن):\n{group_facts}\n"
    body += (
        f"\nحرف کاربر: {question}\n\n"
        f"جواب کوتاه و طبیعی بده. سبک: {_style(info['tone'])}.\n"
        f"فقط متن پاسخ، بدون توضیح اضافه."
    )
    return body


# ============================================================
# پاسخ‌های برنامه‌نویسی‌شده (فالبک بدون AI)
# ============================================================
_CANNED = {
    "warn": {
        0: ["🙏 {n} جان، این حرکت با قوانین گروه جور نبود. اخطار {c}/3 — ممنون که رعایت می‌کنی.",
            "🌱 {n} عزیز، یه یادآوری دوستانه: قوانین گروه رو رعایت کن. اخطار {c}/3",
            "📌 {n} جان، اشتباه کوچیکی بود فکر کنم. اخطار {c}/3 — مراقب باش لطفاً."],
        2: ["⚠️ {n}، اخطار {c}/3. دیگه داره جدی می‌شه.",
            "⛔️ {n}، این بار فقط اخطار می‌گیری ({c}/3) ولی تکرارش عواقب داره.",
            "🚫 {n}، قوانین گروه شوخی نیست. اخطار {c}/3"],
        3: ["⛔️ {n}، اخطار {c}/3 — این آخرین هشدارمه.",
            "🔴 {n}، اخطار {c}/3. دفعه‌ی بعد سکوت می‌گیری.",
            "⚠️ {n}، دیگه ارفاقی در کار نیست. اخطار {c}/3"],
        4: ["🔴 {n}، اخطار {c}/3. یه قدم دیگه‌ای و از گروه خارج می‌شی.",
            "⛔️ {n}، سابقه‌ت پره. اخطار {c}/3 — تصمیم بعدی سخت‌گیرانه است.",
            "🚫 {n}، اخطار {c}/3. من صبرم تموم شده."],
    },
    "mute": {
        0: ["🤐 {n} جان، یه استراحت کوتاه بد نیست — {d} بی‌صدا. بعدش برگرد 🌱",
            "🔇 {n}، تا {d} سکوت. آروم باش و بعداً با آرامش برگرد."],
        2: ["🔇 {n} به مدت {d} سکوت شد. فرصت خوبیه برای مرور قوانین.",
            "⛔️ {n}، {d} سکوت. تکرارش سنگین‌تر می‌شه."],
        3: ["🚫 {n}، {d} سکوت گرفت. دیگه به اخطار بسنده نمی‌کنم.",
            "🔇 {n} برای {d} از ارسال پیام محروم شد."],
        4: ["⛔️ {n}، {d} سکوت. دفعه‌ی بعد بن می‌شی.",
            "🚫 {n}، {d} سکوت — و این آخرین بارمه که فقط سکوت می‌گیری."],
    },
    "ban": {
        0: ["🚫 {n} از گروه بن شد. امیدوارم دفعه‌ی بعد بهتر بشه 🙏",
            "⛔️ {n} بن شد. اگه فکر می‌کنی اشتباهی شده، به ادمین‌ها پیام بده."],
        2: ["🚫 {n} بن شد. قوانین بارها یادآوری شده بود.",
            "⛔️ {n} به‌خاطر نقض مکرر قوانین از گروه بن شد."],
        3: ["🔴 {n} بن شد. سابقه‌اش جا برای ارفاق نگذاشت.",
            "🚫 {n} بن شد — این نتیجه‌ی تخلف‌های پشت‌سرهمه."],
        4: ["⛔️ {n} برای همیشه از گروه بن شد.",
            "🔴 {n} بن شد. پرونده‌ش پر بود."],
    },
    "kick": {
        0: ["👢 {n} از گروه اخراج شد. شاید بعداً با انرژی تازه برگرده.",
            "🚪 {n} اخراج شد — نمی‌تونه تا مطمئن شدن وضعیت برگرده."],
        2: ["👢 {n} اخراج شد. دسترسی‌اش فعلاً بسته است.",
            "🚪 {n} از گروه بیرون رفت — به‌خاطر نقض قوانین."],
        3: ["👢 {n} اخراج شد و بدون اجازه‌ی ادمین نمی‌تونه برگرده.",
            "🚫 {n} اخراج شد."],
        4: ["⛔️ {n} اخراج شد. برنگشتنش بهتره.",
            "👢 {n} بیرون انداخته شد."],
    },
    "unmute": {
        0: ["🔊 {n} از سکوت آزاد شد. امیدوارم این بار بهتر پیش بریم 🌱",
            "✅ {n} می‌تونه دوباره پیام بده."],
        2: ["🔊 {n} آزاد شد — قوانین یادش باشه.",
            "✅ سکوت {n} برداشته شد."],
        3: ["🔊 {n} آزاد شد؛ ولی پرونده‌اش باز می‌مونه.",
            "✅ {n} از سکوت در اومد. حواست به رفتارش باشه."],
        4: ["🔊 {n} آزاد شد. من رفتارش رو زیر نظر دارم.",
            "✅ سکوت {n} برداشته شد — فقط همین یک بار."],
    },
    "unban": {
        0: ["✅ {n} از بن در آمد. خوش برگردی 🙏", "🤝 {n} می‌تونه برگرده به گروه."],
        2: ["✅ بن {n} برداشته شد.", "🔓 {n} آزاد شد — با شرط رعایت قوانین."],
        3: ["✅ {n} از بن در اومد. این فرصت آخرشه.",
            "🔓 {n} آزاد شد، پرونده‌اش بسته نشده."],
        4: ["🔓 {n} آزاد شد. یه قدم اشتباه دوباره بن می‌شه.",
            "✅ {n} برگشت — فقط برای یک بار."],
    },
}

_GENERIC_TONE = {
    0: ["{n} جان، همه‌چیز مرتبه 🌱", "👌 {n}، در جریانه."],
    2: ["{n}، وضعیت ثبت شد.", "📋 {n}، انجام شد."],
    4: ["{n}، ثبت شد. حواست باشه.", "⛔️ {n}، دقت کن."],
}


def _tone_bucket(tone):
    """۰-۱ → ۰ ، ۲ → ۲ ، ۳-۴ → ۳ یا ۴"""
    if tone <= 1:
        return 0
    if tone == 2:
        return 2
    return tone


def canned(action, tone, **kw):
    """پاسخ برنامه‌نویسی‌شده‌ی متناسب با لحن کاربر."""
    variants = (_CANNED.get(action) or {}).get(_tone_bucket(tone))
    if not variants:
        variants = _GENERIC_TONE.get(_tone_bucket(tone)) or _GENERIC_TONE[2]
    tpl = random.choice(variants)
    kw.setdefault("n", "کاربر")
    kw.setdefault("c", "1")
    kw.setdefault("d", "مدتی")
    try:
        return tpl.format(**kw)
    except (KeyError, IndexError):
        return tpl


# ============================================================
# اعلان اقدام مدیریتی (AI با فالبک)
# ============================================================
ACTION_FA = {
    "warn": "اخطار", "mute": "سکوت", "unmute": "رفع سکوت",
    "ban": "بن", "unban": "رفع بن", "kick": "اخراج",
}

_SHOULD_NOTIFY = {"warn", "mute", "ban", "kick", "unban", "unmute"}


def announce_punish(chat_id, action, target_id, target_name, by_name="",
                    reason="", chat_title="", extra=None, count=None,
                    duration="", reply_to=None):
    """پیام اقدام مدیریتی را می‌فرستد: AI اگر ممکن بود، وگرنه متن آماده.

    مهم: خودِ اقدام (سکوت/بن) قبلاً در کد انجام شده؛ اینجا فقط اطلاع‌رسانی است.
    """
    action = action if action in ACTION_FA else "general"
    tone = effective_tone(chat_id, target_id)
    safe_name = api.esc_md(target_name or f"کاربر {target_id}")
    fallback = canned(action, tone, n=safe_name,
                      c=str(count) if count is not None else "1",
                      d=duration or "مدتی")
    if action == "ban" and count is not None and "اخطار" in (reason or ""):
        fallback = canned("ban", tone, n=safe_name)

    def _send(text):
        api.send(chat_id, text, parse_mode="Markdown", reply_to=reply_to)

    if not ai.ready():
        _send(fallback)
        return "canned"

    def _deliver(text, model):
        text = (text or "").strip() or fallback
        if not text:
            return
        _send(ai.safe_md(text))
        if not str(model).startswith("fallback"):
            remember_said(chat_id, target_id, text)

    msgs = [
        {"role": "system", "content": system_prompt()},
        {"role": "user", "content": user_prompt_for_punish(
            ACTION_FA[action], reason, chat_title or "گروه", chat_id,
            target_id, safe_name, by_name or "ادمین", extra or "")},
    ]
    ai.chat_async(msgs, _deliver, fallback=fallback, max_tokens=220, purpose="punish")
    return "ai"


# ============================================================
# خوش‌آمدگویی
# ============================================================
def announce_welcome(chat_id, new_id, new_name, chat_title, fallback_text,
                     media=None, on_done=None):
    """پیام خوش‌آمد: AI می‌سازد، در صورت شکست متن آماده."""
    if not ai.ready():
        if on_done:
            on_done(fallback_text, "canned")
        else:
            api.send(chat_id, fallback_text, parse_mode="Markdown")
        return "canned"

    def _deliver(text, model):
        text = (text or "").strip() or fallback_text
        if on_done:
            on_done(ai.safe_md(text), model)
        else:
            api.send(chat_id, ai.safe_md(text), parse_mode="Markdown")

    msgs = [
        {"role": "system", "content": system_prompt()},
        {"role": "user", "content": user_prompt_for_welcome(
            chat_id, new_id, new_name, chat_title or "گروه")},
    ]
    ai.chat_async(msgs, _deliver, fallback=fallback_text, max_tokens=180,
                  purpose="welcome")
    return "ai"


# ============================================================
# دستیار مدیریت (پاسخ به سؤال ادمین)
# ============================================================
def group_facts(chat_id):
    """خلاصه‌ی واقعی گروه برای تزریق در پرامپت."""
    try:
        users = get("user_profiles", chat_id) or {}
        seen = get("members_seen", chat_id) or {}
        warns = get("warnings", chat_id) or {}
        muted = get("muted", chat_id) or {}
        banned = get("banned_users", chat_id) or {}
        locks = {k: v for k, v in (get("locks", chat_id) or {}).items() if v}
        rules = (get("rules", chat_id) or {})
        as_on = bool((get("antispam", chat_id) or {}).get("enabled"))
        bw = get("badword", chat_id) or {}
        slow = (get("slowmode", chat_id) or {}).get("seconds", 0)
        gl = bool((get("group_lock", chat_id) or {}).get("enabled"))
        wl = len(get("whitelist", chat_id) or [])
        lines = [
            f"تعداد اعضای شناخته‌شده: {max(len(users), len(seen))}",
            f"کاربران ثبت‌شده: {len(users)}",
            f"اخطارهای فعال: {len(warns)} کاربر",
            f"در سکوت: {len(muted)} کاربر",
            f"بن‌شده: {len(banned)} کاربر",
            f"قفل‌های فعال: {', '.join(locks.keys()) if locks else 'هیچ'}",
            f"ضداسپم: {'روشن' if as_on else 'خاموش'}",
            f"ضدفحش: {'روشن' if bw.get('enabled') else 'خاموش'}",
            f"حالت آهسته: {slow} ثانیه" if slow else "حالت آهسته: خاموش",
            f"قفل گروه: {'روشن' if gl else 'خاموش'}",
            f"سفیدلیست: {wl} نفر",
        ]
        if rules.get("text"):
            lines.append(f"قوانین گروه: {str(rules['text'])[:300]}")
        # چند نفر برتر
        try:
            from xp import top
            tops = top(chat_id, 3)
            if tops:
                lines.append("فعال‌ترین‌ها: " + "، ".join(
                    f"{u.get('name') or uid} ({u.get('xp', 0)}XP)" for uid, u in tops))
        except Exception:
            pass
        return "\n".join(lines)
    except Exception as e:
        print(f"[persona:facts] {e}")
        return ""


def _find_user(chat_id, query):
    """جستجوی کاربر با نام/یوزرنیم در پرونده‌ها."""
    q = (query or "").strip().lstrip("@").lower()
    if not q:
        return None
    if q.isdigit():
        for src, data in (("user_profiles", get("user_profiles", chat_id) or {}),
                          ("members_seen", get("members_seen", chat_id) or {})):
            if q in data:
                return q, data[q]
    for src, data in (("user_profiles", get("user_profiles", chat_id) or {}),
                      ("members_seen", get("members_seen", chat_id) or {})):
        for uid, info in (data or {}).items():
            name = f"{info.get('first_name','')} {info.get('last_name','')}".strip()
            if q and (q in name.lower() or q == (info.get("username") or "").lower()):
                return uid, info
    return None


def local_answer(question, chat_id):
    """پاسخ‌های برنامه‌نویسی‌شده وقتی AI در دسترس نیست.

    اول حالت‌های رایج مدیریتی را با داده‌ی واقعی جواب می‌دهد، وگرنه
    یک تصویر کلی از گروه می‌سازد.
    """
    q = (question or "").strip()
    ql = q.replace("‌", "")
    if not ql:
        return None

    try:
        users = get("user_profiles", chat_id) or {}
        seen = get("members_seen", chat_id) or {}
        warns = get("warnings", chat_id) or {}
        muted = get("muted", chat_id) or {}
        banned = get("banned_users", chat_id) or {}
        locks = {k: v for k, v in (get("locks", chat_id) or {}).items() if v}
        rules = (get("rules", chat_id) or {})
    except Exception as e:
        print(f"[persona:local] {e}")
        return None

    def has(*words):
        return any(w in ql for w in words)

    # ---- آمار کلی ----
    if has("آمار", "وضعیت", "خلاصه", "چخبر", "چه خبر", "گزارش"):
        return (
            "📊 **وضعیت گروه**\n"
            f"👥 اعضای شناخته‌شده: `{max(len(users), len(seen))}`\n"
            f"⚠️ اخطار فعال: `{len(warns)}` کاربر\n"
            f"🔇 در سکوت: `{len(muted)}` | 🚫 بن: `{len(banned)}`\n"
            f"🔒 قفل فعال: `{len(locks)}`"
        )

    # ---- تعداد اعضا ----
    if has("چند نفر", "چندتا", "چند تا", "تعداد اعضا", "تعداد کاربر", "اعضا"):
        return f"👥 الان `{max(len(users), len(seen))}` کاربر را می‌شناسم."

    # ---- اخطارها ----
    if has("اخطار"):
        if not warns:
            return "⚠️ هیچ کاربری اخطار فعال نداره."
        rows = []
        for uid, cnt in sorted(warns.items(), key=lambda x: -x[1])[:8]:
            info = users.get(uid) or seen.get(uid) or {}
            nm = info.get("first_name") or f"کاربر {uid}"
            rows.append(f"• {api.esc_md(nm)} — `{cnt}/3`")
        return "⚠️ **اخطارهای فعال**\n" + "\n".join(rows)

    # ---- سکوت ----
    if has("سکوت", "میوت"):
        if not muted:
            return "🔇 کاربری در سکوت نیست."
        return f"🔇 الان `{len(muted)}` کاربر در سکوت هستن."

    # ---- بن ----
    if has("بن", "بلاک", "لیست سیاه"):
        if not banned:
            return "🚫 لیست بن خالیه."
        return f"🚫 `{len(banned)}` کاربر بن هستن."

    # ---- قفل‌ها ----
    if has("قفل"):
        if not locks:
            return "🔒 هیچ قفلی فعال نیست."
        return "🔒 قفل‌های فعال: " + "، ".join(f"`{k}`" for k in list(locks)[:12])

    # ---- قوانین ----
    if has("قانون", "قوانین", "مقررات"):
        txt = (rules or {}).get("text")
        if txt:
            return f"📜 **قوانین گروه**\n{txt}"
        return "📜 هنوز قانونی تنظیم نشده. با دستور `قوانین تنظیم` می‌شه اضافه کرد."

    # ---- درباره‌ی یک شخص ----
    if has("چند تا اخطار", "سابقه", "پرونده") or has("درباره"):
        for word in ql.split():
            found = _find_user(chat_id, word)
            if found:
                uid, info = found
                nm = info.get("first_name") or f"کاربر {uid}"
                return (
                    f"👤 **{api.esc_md(nm)}**\n"
                    f"{describe_user(chat_id, uid, nm)}"
                )

    # ---- کمک ----
    if has("چیکار", "چه کار", "کمک", "راهنما", "دستور"):
        return (
            "🧠 **می‌تونم این‌کارها رو بکنم:**\n"
            "• وضعیت و آمار گروه\n"
            "• پرونده‌ی اخطار/سکوت/بن هر کاربر\n"
            "• قفل‌ها و قوانین\n"
            "• راهنمایی برای تنظیم ضداسپم و قفل‌ها\n\n"
            "مثال: `هوش مصنوعی وضعیت گروه چطوره؟`"
        )

    # ---- پیش‌فرض ----
    return (
        "🧠 الان نمی‌تونم آنلاین فکر کنم، ولی این‌ها رو از خودِ گروه می‌دونم:\n\n"
        f"👥 اعضا: `{max(len(users), len(seen))}` | "
        f"⚠️ اخطار: `{len(warns)}` | 🔇 سکوت: `{len(muted)}` | "
        f"🚫 بن: `{len(banned)}` | 🔒 قفل: `{len(locks)}`\n\n"
        "برای جزئیات بپرس: «وضعیت گروه»، «اخطارها»، «قوانین»."
    )


# ============================================================
# گفتگو: کاربر روی پیام ربات ریپلای می‌کند (حالت چت)
# ============================================================
REPLY_COOLDOWN = 3.0              # فاصله‌ی حداقلی بین دو پاسخ برای یک کاربر
_reply_ts = {}                    # (chat_id, user_id) → آخرین زمان پاسخ


def _cooldown_ok(chat_id, user_id, now=None):
    now = now or time.time()
    key = (str(chat_id), str(user_id))
    last = _reply_ts.get(key, 0)
    if now - last < REPLY_COOLDOWN:
        return False
    _reply_ts[key] = now
    if len(_reply_ts) > 2000:                 # جلوگیری از رشد نامحدود
        cut = now - 3600
        for k in [k for k, v in _reply_ts.items() if v < cut]:
            _reply_ts.pop(k, None)
    return True


#: جواب‌های آماده برای حالت گفتگو (وقتی AI در دسترس نیست) — به تفکیک لحن
_REPLY_CANNED = {
    0: [
        "🙂 {n} جان، الان نمی‌تونم درست فکر کنم — چند لحظه بعد دوباره ریپلای کن.",
        "🌱 {n} عزیز، الان مغزم در دسترس نیست. کمی بعد امتحان کن.",
        "😅 {n} جان، الان یه کم شلوغم. بعداً بپرس، حتماً جواب می‌دم.",
    ],
    1: [
        "🙂 الان نمی‌تونم جواب بدم؛ کمی بعد دوباره پرس‌وجو کن.",
        "⏳ فعلاً دستم بسته است. بعداً دوباره امتحان کن.",
    ],
    2: [
        "⏳ الان پاسخ‌دهی‌ام در دسترس نیست. بعداً بپرس.",
        "🙂 فعلاً نمی‌توانم جواب بدهم؛ بعداً امتحان کن.",
    ],
    3: [
        "⏳ در دسترس نیستم. بعداً بپرس.",
        "فعلاً جوابی ندارم. بعداً امتحان کن.",
    ],
    4: [
        "⏳ الان در دسترس نیستم.",
        "فعلاً جواب نمی‌دهم. بعداً بپرس.",
    ],
}


def reply_canned(name="", tone=0):
    """جواب آماده‌ی متنوع وقتی AI در دسترس نیست."""
    pool = _REPLY_CANNED.get(min(int(tone or 0), MAX_TONE)) or _REPLY_CANNED[0]
    return random.choice(pool).replace("{n}", name or "دوست من")


def answer_reply(chat_id, user_id, user_name, text, chat_title="",
                 quoted="", reply_to=None):
    """جواب به ریپلای روی پیام ربات — با AI، وگرنه پاسخ آماده.

    هرگز خطا/لیمیت نشان نمی‌دهد؛ در بدترین حالت یک جمله‌ی کوتاه می‌گوید.
    """
    text = (text or "").strip()
    if not text:
        return "empty"

    if not _cooldown_ok(chat_id, user_id):
        return "cooldown"

    tone = effective_tone(chat_id, user_id)
    safe_name = api.esc_md(user_name or "")

    def _send(body):
        api.send(chat_id, body, parse_mode="Markdown", reply_to=reply_to)

    def _fallback_text():
        # اگر سؤال مدیریتی بود، همان جواب برنامه‌نویسی‌شده‌ی دقیق را بده
        local = None
        try:
            local = local_answer(text, chat_id)
        except Exception as e:
            print(f"[persona:reply-local] {e}")
        return local or reply_canned(user_name, tone)

    if not ai.ready():
        _send(_fallback_text())
        return "canned"

    msgs = [
        {"role": "system", "content": CHAT_RULES},
        {"role": "user", "content": reply_prompt(
            text[:600], chat_id, chat_title or "گروه", user_id, user_name,
            quoted=(quoted or "")[:400], group_facts=group_facts(chat_id))},
    ]

    def _deliver(answer, model):
        answer = (answer or "").strip()
        if not answer or str(model).startswith("fallback"):
            _send(_fallback_text())
            return
        _send(ai.safe_md(answer))
        remember_said(chat_id, user_id, answer)
        remember_turn(chat_id, user_id, text, answer)
        note_note(chat_id, user_id, f"در گفتگو گفت: {text[:60]}")

    ai.chat_async(msgs, _deliver, fallback="", max_tokens=340, purpose="reply")
    return "ai"


def answer_question(chat_id, user_id, user_name, question, chat_title="",
                    reply_to=None):
    """پاسخ به پرسش مدیریتی ادمین — AI با فالبک برنامه‌نویسی‌شده."""
    question = (question or "").strip()
    if not question:
        api.send(chat_id, "🧠 چی می‌خوای بدونی؟ مثلاً: «وضعیت گروه چطوره؟»",
                 reply_to=reply_to)
        return "empty"

    def _send(text):
        api.send(chat_id, text, parse_mode="Markdown", reply_to=reply_to)

    if not ai.ready():
        _send(local_answer(question, chat_id) or "🧠 الان چیزی برای گفتن ندارم.")
        return "canned"

    fact = group_facts(chat_id)
    msgs = [
        {"role": "system", "content": system_prompt()},
        {"role": "user", "content": user_prompt_for_answer(
            question, chat_id, chat_title or "گروه", user_id, user_name, fact)},
    ]

    def _deliver(text, model):
        if text and not str(model).startswith("fallback"):
            _send(ai.safe_md(text))
            remember_said(chat_id, user_id, text)
            note_note(chat_id, user_id, f"پرسید: {question[:60]}")
            return
        _send(local_answer(question, chat_id) or "🧠 الان جوابی براش ندارم.")

    ai.chat_async(msgs, _deliver, fallback="", max_tokens=380, purpose="assistant")
    return "ai"
