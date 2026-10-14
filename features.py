# -*- coding: utf-8 -*-
"""قابلیت‌های پیشرفته - آلفا"""
import time
import threading
import random
import re
from datetime import datetime, timedelta, timezone
import api
import storage
from storage import get, set_, update

# 🧠 هوش مصنوعی (اختیاری)
try:
    import ai_persona
except Exception as _e:      # pragma: no cover
    ai_persona = None
    print(f"[features] ai_persona لود نشد: {_e}")

try:
    import questions
    QUIZ_QUESTIONS = questions.QUIZ_QUESTIONS
    TRUTHS_POOL = questions.TRUTHS
    DARES_POOL = questions.DARES
except Exception as e:
    print(f"[extras:questions] {e}")
    QUIZ_QUESTIONS = []
    TRUTHS_POOL = []
    DARES_POOL = []

BOT_NAME = "مدیریت گروه آلفا"


# ============================================================
# ✅ ساعت ایران — UTC + 3:30 (بدون نیاز به کتابخانه)
# ============================================================
TEHRAN_OFFSET = timedelta(hours=3, minutes=30)


def _now_tehran():
    """زمان فعلی ایران (UTC+3:30)"""
    return datetime.now(timezone.utc) + TEHRAN_OFFSET


def _now_hhmm():
    """ساعت فعلی ایران به فرمت HH:MM"""
    return _now_tehran().strftime("%H:%M")


def _validate_time(t):
    """بررسی فرمت HH:MM"""
    if not t or ":" not in t:
        return False
    try:
        parts = t.split(":")
        h = int(parts[0])
        m = int(parts[1])
        return 0 <= h <= 23 and 0 <= m <= 59
    except Exception:
        return False


# ============================================================
# 🌙 حالت شب
# ============================================================
def get_night_mode(chat_id):
    return storage.get("night_mode", chat_id) or {}


def set_night_mode(chat_id, enabled=None, start=None, end=None):
    cfg = get_night_mode(chat_id) or {}
    if enabled is not None:
        cfg["enabled"] = bool(enabled)
    if start:
        cfg["start"] = start
    if end:
        cfg["end"] = end
    cfg.setdefault("start", "23:00")
    cfg.setdefault("end", "07:00")
    if "enabled" not in cfg:
        cfg["enabled"] = False
    set_("night_mode", chat_id, cfg)


def is_night_time(chat_id):
    """چک می‌کنه الان ساعت شب گروه هست یا نه"""
    cfg = get_night_mode(chat_id)
    if not cfg.get("enabled"):
        return False

    start = cfg.get("start", "23:00")
    end = cfg.get("end", "07:00")

    if not _validate_time(start) or not _validate_time(end):
        return False

    now = _now_hhmm()

    if start <= end:
        return start <= now <= end

    return now >= start or now <= end


def get_night_debug(chat_id):
    """اطلاعات دیباگ برای عیب‌یابی"""
    cfg = get_night_mode(chat_id)
    now = _now_hhmm()
    active = is_night_time(chat_id)
    return {
        "enabled": cfg.get("enabled", False),
        "start": cfg.get("start", "23:00"),
        "end": cfg.get("end", "07:00"),
        "now_tehran": now,
        "active_now": active,
    }


# ============================================================
# 😴 حالت خواب — چند بازه زمانی
# ============================================================
def get_sleep_mode(chat_id):
    return storage.get("sleep_mode", chat_id) or {}


def set_sleep_mode_enabled(chat_id, enabled):
    cfg = get_sleep_mode(chat_id) or {}
    cfg["enabled"] = bool(enabled)
    cfg.setdefault("ranges", [])
    set_("sleep_mode", chat_id, cfg)


def get_sleep_ranges(chat_id):
    cfg = get_sleep_mode(chat_id) or {}
    return cfg.get("ranges", [])


def add_sleep_range(chat_id, start, end):
    if not _validate_time(start) or not _validate_time(end):
        return False
    cfg = get_sleep_mode(chat_id) or {}
    ranges = cfg.get("ranges", [])
    # جلوگیری از تکرار
    for r in ranges:
        if r.get("start") == start and r.get("end") == end:
            return False
    ranges.append({"start": start, "end": end})
    cfg["ranges"] = ranges
    cfg.setdefault("enabled", False)
    set_("sleep_mode", chat_id, cfg)
    return True


def remove_sleep_range(chat_id, idx):
    cfg = get_sleep_mode(chat_id) or {}
    ranges = cfg.get("ranges", [])
    if 0 <= idx < len(ranges):
        ranges.pop(idx)
        cfg["ranges"] = ranges
        set_("sleep_mode", chat_id, cfg)
        return True
    return False


def clear_sleep_ranges(chat_id):
    cfg = get_sleep_mode(chat_id) or {}
    cfg["ranges"] = []
    set_("sleep_mode", chat_id, cfg)


def _in_range(now, start, end):
    """چک درون بازه [start, end) — با پشتیبانی از عبور از نیمه‌شب"""
    if start == end:
        return True  # 24 ساعته
    if start < end:
        return start <= now < end
    # رد شدن از نیمه‌شب (مثلاً 23:00 تا 07:00)
    return now >= start or now < end


def is_sleep_time(chat_id):
    """چک فعال بودن بازه خواب در این لحظه"""
    cfg = get_sleep_mode(chat_id) or {}
    if not cfg.get("enabled"):
        return False
    ranges = cfg.get("ranges", [])
    if not ranges:
        return False
    now = _now_hhmm()
    for r in ranges:
        s = r.get("start", "")
        e = r.get("end", "")
        if _validate_time(s) and _validate_time(e):
            if _in_range(now, s, e):
                return True
    return False


def get_sleep_debug(chat_id):
    cfg = get_sleep_mode(chat_id) or {}
    return {
        "enabled": cfg.get("enabled", False),
        "ranges": cfg.get("ranges", []),
        "now_tehran": _now_hhmm(),
        "active_now": is_sleep_time(chat_id),
    }


# ============================================================
# سفیدلیست
# ============================================================
def is_whitelisted(chat_id, user_id):
    wl = storage.get("whitelist", chat_id) or []
    return str(user_id) in wl


def add_whitelist(chat_id, user_id):
    wl = storage.get("whitelist", chat_id) or []
    if str(user_id) not in wl:
        wl.append(str(user_id))
        set_("whitelist", chat_id, wl)


def remove_whitelist(chat_id, user_id):
    wl = storage.get("whitelist", chat_id) or []
    if str(user_id) in wl:
        wl.remove(str(user_id))
        set_("whitelist", chat_id, wl)


# ============================================================
# دستورات سفارشی
# ============================================================
def add_custom_cmd(chat_id, name, reply):
    cmds = storage.get("custom_commands", chat_id) or {}
    cmds[name.lower()] = reply
    set_("custom_commands", chat_id, cmds)


def remove_custom_cmd(chat_id, name):
    cmds = storage.get("custom_commands", chat_id) or {}
    if name.lower() in cmds:
        del cmds[name.lower()]
        set_("custom_commands", chat_id, cmds)
        return True
    return False


def get_custom_cmd(chat_id, name):
    cmds = storage.get("custom_commands", chat_id) or {}
    return cmds.get(name.lower())


def list_custom_cmds(chat_id):
    return storage.get("custom_commands", chat_id) or {}


# ============================================================
# آمار پیام امروز
# ============================================================
def track_message(chat_id, user_id):
    today = _now_tehran().strftime("%Y-%m-%d")
    key = f"{chat_id}:{today}"
    stats = storage.get("msg_stats", key) or {}
    uid = str(user_id)
    stats[uid] = stats.get(uid, 0) + 1
    set_("msg_stats", key, stats)


def get_top_today(chat_id, n=10):
    today = _now_tehran().strftime("%Y-%m-%d")
    key = f"{chat_id}:{today}"
    stats = storage.get("msg_stats", key) or {}
    items = sorted(stats.items(), key=lambda x: x[1], reverse=True)
    return items[:n]


# ============================================================
# خوش‌آمد با مدیا
# ============================================================
def set_welcome_media(chat_id, media_type, file_id):
    cfg = storage.get("welcome", chat_id) or {}
    cfg["media_type"] = media_type
    cfg["media_file_id"] = file_id
    cfg["enabled"] = True
    set_("welcome", chat_id, cfg)


def set_welcome_autodelete(chat_id, seconds):
    cfg = storage.get("welcome", chat_id) or {}
    cfg["autodelete"] = seconds
    set_("welcome", chat_id, cfg)


def _welcome_autodelete(chat_id, msg_id, seconds):
    if not (msg_id and seconds and seconds > 0):
        return
    def _del():
        time.sleep(seconds)
        try:
            api.delete(chat_id, msg_id)
        except Exception:
            pass
    threading.Thread(target=_del, daemon=True).start()


def send_welcome(chat_id, member_name, group_name, member_id=None):
    """پیام خوش‌آمدگویی.

    اگر متن دلخواه ادمین تنظیم نشده باشد و AI روشن باشد، متن با AI
    ساخته می‌شود (غیرهمزمان). در آن حالت `None` برمی‌گردد چون هنوز
    شناسه‌ی پیام معلوم نیست؛ حذف خودکار داخل خودش انجام می‌شود.
    """
    cfg = storage.get("welcome", chat_id) or {}
    if not cfg.get("enabled"):
        return None

    custom_text = (cfg.get("text") or "").strip()
    text = custom_text or "🎉 {name} عزیز، به {group} خوش آمدی!"
    text = text.replace("{name}", member_name).replace("{group}", group_name)
    text = text.replace("{bot}", BOT_NAME)

    media_type = cfg.get("media_type")
    file_id = cfg.get("media_file_id")
    autodelete = int(cfg.get("autodelete", 0) or 0)

    def _send(body):
        if media_type and file_id:
            d = {"chat_id": chat_id, "caption": body}
            if media_type == "photo":
                d["photo"] = file_id
                r = api.request("sendPhoto", d)
            elif media_type == "video":
                d["video"] = file_id
                r = api.request("sendVideo", d)
            elif media_type == "animation":
                d["animation"] = file_id
                r = api.request("sendAnimation", d)
            else:
                r = api.send(chat_id, body)
        else:
            r = api.send(chat_id, body)
        if r and r.get("ok"):
            return r["result"]["message_id"]
        return None

    # ---- مسیر AI (فقط وقتی ادمین متن دلخواه نگذاشته) ----
    if ai_persona and member_id is not None and not custom_text:
        ai_on = True
        try:
            import ai_panel
            ai_on = ai_panel.feature_on(chat_id, "welcome")
        except Exception:
            pass
        if ai_on:
            import ai
            if ai.ready():
                def _deliver(body, model):
                    mid = _send(body or text)
                    _welcome_autodelete(chat_id, mid, autodelete)
                ai_persona.announce_welcome(
                    chat_id, member_id, member_name, group_name,
                    fallback_text=text, on_done=_deliver)
                return None       # پیام در نخ جداگانه فرستاده می‌شود

    mid = _send(text)
    return mid


def clear_welcome_media(chat_id):
    cfg = storage.get("welcome", chat_id) or {}
    cfg.pop("media_type", None)
    cfg.pop("media_file_id", None)
    set_("welcome", chat_id, cfg)


# ============================================================
# ثبت نام کاربر
# ============================================================
def track_user_name(chat_id, user_id, user_name):
    if not user_name:
        return
    try:
        all_xp = storage.get("xp", chat_id) or {}
        uid = str(user_id)
        if uid not in all_xp:
            all_xp[uid] = {"xp": 0, "level": 1, "name": user_name}
        else:
            if all_xp[uid].get("name") != user_name:
                all_xp[uid]["name"] = user_name
        storage.update("xp", chat_id, uid, all_xp[uid])
    except Exception as e:
        print(f"[track_user_name] {e}")


# ============================================================
# گزارش باگ
# ============================================================
def send_bug_report(chat_id, user_id, user_name, text, chat_title=""):
    from config import OWNER_ID

    owner = 0
    o = storage.get("bot_owner", "id")
    if isinstance(o, dict):
        owner = o.get("id", 0)
    if not owner:
        owner = OWNER_ID

    if not owner:
        return False, "❌ مالک ربات تنظیم نشده."

    report_id = str(int(time.time()))
    now = _now_tehran().strftime("%Y/%m/%d - %H:%M")

    msg = (
        f"🐛 **گزارش باگ جدید**\n"
        f"╔══════════════════════╗\n"
        f"🆔 کد گزارش: `#{report_id}`\n"
        f"╚══════════════════════╝\n"
        f"👤 کاربر: **{api.esc_md(user_name)}**\n"
        f"🆔 آیدی: `{user_id}`\n"
        f"👥 گروه: **{api.esc_md(chat_title or '-')}**\n"
        f"🆔 آیدی گروه: `{chat_id}`\n"
        f"📅 زمان: `{now}`\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📝 **متن گزارش:**\n\n"
        f"{text}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 پاسخ: `/پاسخ {user_id} متن`"
    )

    try:
        r = api.send(int(owner), msg, parse_mode="Markdown", reply_to=0)
        if r and r.get("ok"):
            reports = storage.get("bug_reports", "list") or {}
            reports[report_id] = {
                "user_id": user_id,
                "user_name": user_name,
                "chat_id": chat_id,
                "chat_title": chat_title,
                "text": text,
                "time": now,
                "ts": time.time(),
            }
            if len(reports) > 200:
                keys = sorted(reports.keys(), key=lambda k: reports[k].get("ts", 0))
                for k in keys[:100]:
                    del reports[k]
            storage.set_("bug_reports", "list", reports)
            return True, report_id
        else:
            err = (r or {}).get("description", "خطای نامشخص")
            print(f"[bug_report] failed: {r}")
            return False, f"❌ خطا در ارسال: {err}"
    except Exception as e:
        print(f"[bug_report] {e}")
        return False, f"❌ خطا: {e}"


# ============================================================
# آزمون
# ============================================================
_quiz_lock = {}


def start_quiz(chat_id, user_id, user_name):
    if chat_id in _quiz_lock:
        return False, "❌ یه آزمون دیگه در جریانه!"

    if not QUIZ_QUESTIONS:
        return False, "❌ بانک سوالات خالیه!"

    q = random.choice(QUIZ_QUESTIONS)
    qid = str(int(time.time())) + str(random.randint(10, 99))

    quiz = {
        "id": qid,
        "question": q["q"],
        "options": q["options"],
        "answer": q["ans"],
        "creator": user_id,
        "started": time.time(),
        "answered": {},
    }
    quizzes = get("quizzes", chat_id) or {}
    quizzes[qid] = quiz
    set_("quizzes", chat_id, quizzes)
    _quiz_lock[chat_id] = qid

    rows = []
    letters = ["🅰️", "🅱️", "©️", "🆔"]
    for i, opt in enumerate(q["options"]):
        rows.append([{"text": f"{letters[i]} {opt}", "callback_data": f"quiz:ans:{qid}:{i}"}])

    api.send(chat_id,
        f"🧠 **آزمون آلفا**\n"
        f"━━━━━━━━━━━━━━━\n"
        f"❓ {q['q']}\n\n"
        f"⏱ ۳۰ ثانیه فرصت\n"
        f"👤 شروع‌کننده: {api.esc_md(user_name)}\n"
        f"🆔 `{qid}`",
        markup={"inline_keyboard": rows},
        parse_mode="Markdown")

    def _timeout():
        time.sleep(30)
        if _quiz_lock.get(chat_id) == qid:
            end_quiz(chat_id, qid)
    threading.Thread(target=_timeout, daemon=True).start()

    return True, "✅ شروع شد!"


def answer_quiz(chat_id, user_id, user_name, qid, ans_index):
    quizzes = get("quizzes", chat_id) or {}
    quiz = quizzes.get(qid)
    if not quiz:
        return False, "❌ آزمون پیدا نشد"

    if str(user_id) in quiz["answered"]:
        return False, "❗️ قبلا جواب دادی!"

    is_correct = (ans_index == quiz["answer"])
    quiz["answered"][str(user_id)] = {
        "name": user_name,
        "ans": ans_index,
        "correct": is_correct,
    }
    set_("quizzes", chat_id, quizzes)

    if is_correct:
        try:
            from storage import add_game_win
            add_game_win(chat_id, "quiz", user_id, user_name)
        except Exception as e:
            print(f"[quiz:add_win] {e}")
        return True, "✅ آفرین! درست بود 🎉"
    else:
        return True, "❌ اشتباه بود!"


def end_quiz(chat_id, qid):
    quizzes = get("quizzes", chat_id) or {}
    quiz = quizzes.get(qid)
    if not quiz:
        return

    _quiz_lock.pop(chat_id, None)

    answered = quiz["answered"]
    correct_ans = quiz["options"][quiz["answer"]]

    txt = f"🧠 **نتیجه آزمون**\n"
    txt += f"━━━━━━━━━━━━━━━\n"
    txt += f"❓ {quiz['question']}\n"
    txt += f"✅ جواب: **{api.esc_md(correct_ans)}**\n\n"

    if not answered:
        txt += "😐 کسی جواب نداد!"
    else:
        correct_users = [(uid, d) for uid, d in answered.items() if d["correct"]]
        wrong_users = [(uid, d) for uid, d in answered.items() if not d["correct"]]

        if correct_users:
            txt += f"🎉 **درست ({len(correct_users)}):**\n"
            for uid, d in correct_users[:10]:
                txt += f"  ✅ {d['name']}\n"
        if wrong_users:
            txt += f"\n❌ **اشتباه ({len(wrong_users)}):**\n"
            for uid, d in wrong_users[:10]:
                txt += f"  ❌ {d['name']}\n"

    api.send(chat_id, txt, parse_mode="Markdown")


def get_quiz_leaderboard(chat_id):
    try:
        from storage import get_game_leaderboard
        items = get_game_leaderboard(chat_id, "quiz", 10)
    except Exception:
        items = []
    if not items:
        return "🧠 هنوز کسی توی آزمون برنده نشده!"
    txt = "🧠 **لیدربرد آزمون**\n━━━━━━━━━━━━━━━\n"
    for i, (uid, data) in enumerate(items, 1):
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")
        txt += f"{medal} {data.get('name','کاربر')} → {data.get('wins',0)} برد\n"
    return txt


# ============================================================
# قرعه‌کشی
# ============================================================
def draw_lottery(chat_id, user_id, user_name, count=1):
    today = _now_tehran()
    active_users = {}
    for i in range(7):
        d = today - timedelta(days=i)
        key = f"{chat_id}:{d.strftime('%Y-%m-%d')}"
        stats = get("msg_stats", key) or {}
        for uid, cnt in stats.items():
            active_users[uid] = active_users.get(uid, 0) + cnt

    if len(active_users) < 2:
        return None, "❌ به اندازه کافی کاربر فعال نداری!"

    uids = list(active_users.keys())
    weights = [active_users[u] for u in uids]

    if count > len(uids):
        count = len(uids)

    winners = []
    pool = uids[:]
    weights_pool = weights[:]
    for _ in range(count):
        if not pool:
            break
        w = random.choices(pool, weights=weights_pool, k=1)[0]
        idx = pool.index(w)
        pool.pop(idx)
        weights_pool.pop(idx)
        winners.append(w)

    return winners, None


# ============================================================
# رتبه‌بندی
# ============================================================
def get_weekly_ranking(chat_id):
    today = _now_tehran()
    users = {}
    for i in range(7):
        d = today - timedelta(days=i)
        key = f"{chat_id}:{d.strftime('%Y-%m-%d')}"
        stats = get("msg_stats", key) or {}
        for uid, cnt in stats.items():
            users[uid] = users.get(uid, 0) + cnt

    if not users:
        return "❌ هنوز آماری نداریم."

    bot_users = storage.get("bot_users", "list") or {}
    xp_data = get("xp", chat_id) or {}
    items = sorted(users.items(), key=lambda x: x[1], reverse=True)

    txt = "👑 **رتبه‌بندی هفتگی**\n━━━━━━━━━━━━━━━\n"
    for i, (uid, cnt) in enumerate(items[:10], 1):
        crown = {1: "👑", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")
        user_info = xp_data.get(uid, {})
        name = user_info.get("name", "") or bot_users.get(uid, {}).get("name", f"کاربر")
        level = user_info.get("level", 1)
        xp = user_info.get("xp", 0)
        txt += f"{crown} **{api.esc_md(name)}**\n"
        txt += f"   💬 {cnt} پیام | 🏅 سطح {level} | ⭐ {xp} XP\n"
    return txt


def get_monthly_ranking(chat_id):
    today = _now_tehran()
    users = {}
    for i in range(30):
        d = today - timedelta(days=i)
        key = f"{chat_id}:{d.strftime('%Y-%m-%d')}"
        stats = get("msg_stats", key) or {}
        for uid, cnt in stats.items():
            users[uid] = users.get(uid, 0) + cnt

    if not users:
        return "❌ هنوز آماری نداریم."

    bot_users = storage.get("bot_users", "list") or {}
    xp_data = get("xp", chat_id) or {}
    items = sorted(users.items(), key=lambda x: x[1], reverse=True)

    txt = "🏆 **رتبه‌بندی ماهانه**\n━━━━━━━━━━━━━━━\n"
    for i, (uid, cnt) in enumerate(items[:10], 1):
        crown = {1: "👑", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")
        user_info = xp_data.get(uid, {})
        name = user_info.get("name", "") or bot_users.get(uid, {}).get("name", f"کاربر")
        txt += f"{crown} **{api.esc_md(name)}** → {cnt} پیام\n"
    return txt


# ============================================================
# سیستم دعوت
# ============================================================
def track_invite(chat_id, inviter_id, inviter_name, new_user_id, new_user_name):
    invites = get("invites", chat_id) or {}
    inviter = invites.get(str(inviter_id), {"name": inviter_name, "count": 0, "users": []})
    inviter["count"] += 1
    inviter["users"].append({
        "id": new_user_id,
        "name": new_user_name,
        "time": time.time(),
    })
    invites[str(inviter_id)] = inviter
    set_("invites", chat_id, invites)


def get_invite_leaderboard(chat_id):
    invites = get("invites", chat_id) or {}
    if not invites:
        return "🔗 هنوز کسی کسی رو دعوت نکرده!"

    items = sorted(invites.items(), key=lambda x: x[1].get("count", 0), reverse=True)
    txt = "🔗 **لیدربرد دعوت‌کنندگان**\n━━━━━━━━━━━━━━━\n"
    for i, (uid, data) in enumerate(items[:10], 1):
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")
        txt += f"{medal} {data.get('name','کاربر')} → {data.get('count',0)} نفر\n"
    return txt


def get_user_invites(chat_id, user_id):
    invites = get("invites", chat_id) or {}
    data = invites.get(str(user_id))
    if not data:
        return "🔗 هنوز کسی رو دعوت نکردی!"
    return (
        f"🔗 **دعوت‌های شما**\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👥 تعداد: `{data.get('count', 0)}` نفر"
    )


# ============================================================
# ضد فحش (کلمات پایه)
# ============================================================
BAD_WORDS_BASE = [
    "کص", "کیر", "کون", "جنده", "فاحشه", "خارکص", "خارکوس",
    "گایید", "گاییدم", "گاییدش", "گاییدن", "گاییدین", "گاییدیم",
    "لاشی", "حرومی", "حرومزاده", "حرومزاد", "بی‌ناموس", "بیناموس",
    "مادرجنده", "مادرقحبه", "قحبه", "سگ‌مادر", "سگمادر",
    "پدرسگ", "خواهرجنده", "خواهرکص",
    "جاکش", "کسکش", "کصکش", "کوسکش",
    "تخمی", "بی‌شرف", "بیشرف",
    "کونی", "کونیم", "کونیان", "کونین",
    "کصلیس", "کصخل", "کوسخل", "خرفت",
    "دیوث", "دیوس",
    "اوبی", "اوبیا",
    "خایه", "خایمال",
]

BAD_WORDS_REGEX = [
    r"ک[صس]+[ی]?\s*[کخ]?",
    r"گ[آا]ی+",
    r"[کخ]یر",
    r"ک[وو]ن",
    r"ج[نن]د[ه]?",
    r"ل[آآ]ش[یی]",
    r"ح[رر][وو]م",
    r"خ[آا]ر[کخ]",
    r"د[یی][وو][ثص]",
]


def _normalize_for_check(text):
    if not text:
        return ""
    clean = text.lower()
    clean = clean.replace("\u200c", "")
    clean = clean.replace("آ", "ا").replace("أ", "ا")
    clean = re.sub(r"(.)\1{2,}", r"\1", clean)
    clean = re.sub(r"[\W_]+", "", clean, flags=re.UNICODE)
    return clean


def check_bad_word(text):
    if not text:
        return False, None
    clean = _normalize_for_check(text)
    for word in BAD_WORDS_BASE:
        w = word.replace("\u200c", "").replace("آ", "ا")
        w = re.sub(r"[\W_]+", "", w, flags=re.UNICODE)
        if w and w in clean:
            return True, word
    for pattern in BAD_WORDS_REGEX:
        if re.search(pattern, clean):
            return True, pattern
    return False, None


def check_bad_word_with_extra(text, chat_id):
    if not text:
        return False, None
    clean = _normalize_for_check(text)
    for word in BAD_WORDS_BASE:
        w = word.replace("\u200c", "").replace("آ", "ا")
        w = re.sub(r"[\W_]+", "", w, flags=re.UNICODE)
        if w and w in clean:
            return True, word
    for pattern in BAD_WORDS_REGEX:
        if re.search(pattern, clean):
            return True, pattern
    extra = storage.get("extra_bad_words", chat_id) or []
    for word in extra:
        if not word:
            continue
        w = word.lower().replace("\u200c", "").replace("آ", "ا")
        w = re.sub(r"[\W_]+", "", w, flags=re.UNICODE)
        if w and w in clean:
            return True, word
    return False, None


# ============================================================
# گزارش هفتگی
# ============================================================
_auto_report_started = {}


def start_auto_report(chat_id):
    if chat_id in _auto_report_started:
        return
    _auto_report_started[chat_id] = True

    def _run():
        while True:
            try:
                now = _now_tehran()
                days_until_friday = (4 - now.weekday()) % 7
                if days_until_friday == 0 and now.hour >= 20:
                    days_until_friday = 7
                next_friday = now.replace(hour=20, minute=0, second=0, microsecond=0)
                next_friday += timedelta(days=days_until_friday)
                if next_friday <= now:
                    next_friday += timedelta(days=7)
                sleep_secs = (next_friday - now).total_seconds()
                time.sleep(sleep_secs)
                cfg = get("weekly_report", chat_id) or {}
                if not cfg.get("enabled"):
                    continue
                try:
                    txt = build_weekly_report(chat_id)
                    api.send(chat_id, txt, parse_mode="Markdown")
                except Exception as e:
                    print(f"[weekly_report] {e}")
            except Exception as e:
                print(f"[weekly_loop] {e}")
                time.sleep(3600)

    threading.Thread(target=_run, daemon=True).start()


def build_weekly_report(chat_id):
    today = _now_tehran()
    users = {}
    total = 0
    for i in range(7):
        d = today - timedelta(days=i)
        key = f"{chat_id}:{d.strftime('%Y-%m-%d')}"
        stats = get("msg_stats", key) or {}
        for uid, cnt in stats.items():
            users[uid] = users.get(uid, 0) + cnt
            total += cnt

    bot_users = storage.get("bot_users", "list") or {}
    xp_data = get("xp", chat_id) or {}
    items = sorted(users.items(), key=lambda x: x[1], reverse=True)

    txt = "📊 **گزارش هفتگی گروه**\n"
    txt += "━━━━━━━━━━━━━━━\n"
    txt += f"📅 {today.strftime('%Y/%m/%d')}\n"
    txt += f"💬 کل پیام‌ها: `{total}`\n"
    txt += f"👥 کاربران فعال: `{len(users)}`\n\n"

    if items:
        txt += "👑 **برترین‌های هفته:**\n"
        for i, (uid, cnt) in enumerate(items[:5], 1):
            crown = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")
            name = xp_data.get(uid, {}).get("name", "") or bot_users.get(uid, {}).get("name", f"کاربر")
            txt += f"{crown} {api.esc_md(name)} → {cnt} پیام\n"
    else:
        txt += "😐 هفته ساکتی بود!"

    txt += "\n━━━━━━━━━━━━━━━\n"
    txt += "🏆 **مدیریت گروه آلفا**"
    return txt


def set_weekly_report(chat_id, enabled):
    cfg = get("weekly_report", chat_id) or {}
    cfg["enabled"] = enabled
    set_("weekly_report", chat_id, cfg)
    if enabled:
        start_auto_report(chat_id)


# ============================================================
# نمودار آماری
# ============================================================
def send_stats_chart(chat_id, reply_to=None):
    import urllib.parse
    import json as _json

    group_title = "گروه"
    try:
        chat_info = api.get_chat(chat_id)
        if chat_info and chat_info.get("ok"):
            group_title = api.esc_md(chat_info["result"].get("title", "گروه"))
    except Exception as e:
        print(f"[group_title] {e}")

    today = _now_tehran()
    labels = []
    data = []

    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        key = f"{chat_id}:{d.strftime('%Y-%m-%d')}"
        stats = get("msg_stats", key) or {}
        cnt = sum(stats.values())
        days_fa = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه", "یک‌شنبه"]
        day_name = days_fa[d.weekday()]
        labels.append(f"{day_name} {d.strftime('%m/%d')}")
        data.append(cnt)

    first_half = sum(data[:3])
    second_half = sum(data[-3:])
    if first_half == 0 and second_half == 0:
        trend = "➡️ **بدون فعالیت**"
        trend_emoji = "😐"
        trend_msg = "گروه ساکته، یه حرکت بزنیم!"
    elif second_half > first_half * 1.3:
        trend = "📈 **صعودی قوی**"
        trend_emoji = "🚀"
        trend_msg = "عالی داریم پیش می‌ریم!"
    elif second_half > first_half * 1.15:
        trend = "📈 **صعودی**"
        trend_emoji = "🔥"
        trend_msg = "رو به رشده، ادامه بدید!"
    elif second_half < first_half * 0.7:
        trend = "📉 **نزولی شدید**"
        trend_emoji = "💔"
        trend_msg = "گروه داره سرد میشه، تکونی بخورید!"
    elif second_half < first_half * 0.85:
        trend = "📉 **نزولی**"
        trend_emoji = "❄️"
        trend_msg = "کمی افت داشتیم، جبران کنیم!"
    else:
        trend = "➡️ **ثابت**"
        trend_emoji = "✅"
        trend_msg = "روند پایداره"

    if first_half > 0:
        change_pct = ((second_half - first_half) / first_half) * 100
        if change_pct > 0:
            change_txt = f"📈 `+{change_pct:.1f}%` رشد"
        elif change_pct < 0:
            change_txt = f"📉 `{change_pct:.1f}%` افت"
        else:
            change_txt = "➡️ `0%` بدون تغییر"
    else:
        change_txt = "🆕 داده جدید"

    all_users = {}
    last_day_users = {}
    for i in range(7):
        d = today - timedelta(days=i)
        key = f"{chat_id}:{d.strftime('%Y-%m-%d')}"
        stats = get("msg_stats", key) or {}
        for uid, cnt in stats.items():
            all_users[uid] = all_users.get(uid, 0) + cnt
            if i == 0:
                last_day_users[uid] = cnt

    top = sorted(all_users.items(), key=lambda x: x[1], reverse=True)[:5]
    bot_users = storage.get("bot_users", "list") or {}
    xp_data = get("xp", chat_id) or {}

    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    top_text = ""
    total_messages_all = sum(all_users.values()) if all_users else 0
    for i, (uid, cnt) in enumerate(top):
        name = xp_data.get(uid, {}).get("name", "") or bot_users.get(uid, {}).get("name", f"کاربر {str(uid)[-4:]}")
        pct = (cnt / total_messages_all * 100) if total_messages_all else 0
        bar_len = min(int(pct / 5), 10)
        bar = "█" * bar_len + "░" * (10 - bar_len)
        top_text += f"{medals[i]} **{api.esc_md(name)}**\n"
        top_text += f"    💬 `{cnt}` پیام | `{bar}` {pct:.0f}%\n"

    if not top_text:
        top_text = "😐 هیچ کاربری پیام نفرستاده"

    total = sum(data)
    active_count = len(all_users)
    avg_per_day = total / 7 if total else 0

    best_day_idx = data.index(max(data)) if data else 0
    best_day_name = api.esc_md(labels[best_day_idx]) if labels else "-"
    best_day_count = max(data) if data else 0

    today_top_name = ""
    today_top_count = 0
    if last_day_users:
        today_top = sorted(last_day_users.items(), key=lambda x: x[1], reverse=True)[0]
        today_top_name = xp_data.get(today_top[0], {}).get("name", "") or bot_users.get(today_top[0], {}).get("name", "")
        today_top_count = today_top[1]

    bg_colors = []
    border_colors = []
    max_val = max(data) if data else 0
    for val in data:
        if val == 0:
            bg_colors.append("rgba(200, 200, 200, 0.5)")
            border_colors.append("rgba(150, 150, 150, 1)")
        elif val == max_val:
            bg_colors.append("rgba(239, 68, 68, 0.85)")
            border_colors.append("rgba(220, 38, 38, 1)")
        elif val >= max_val * 0.7:
            bg_colors.append("rgba(34, 197, 94, 0.8)")
            border_colors.append("rgba(22, 163, 74, 1)")
        elif val >= max_val * 0.4:
            bg_colors.append("rgba(59, 130, 246, 0.8)")
            border_colors.append("rgba(37, 99, 235, 1)")
        else:
            bg_colors.append("rgba(251, 146, 60, 0.8)")
            border_colors.append("rgba(234, 88, 12, 1)")

    trend_line = []
    for i in range(len(data)):
        if i < 2:
            trend_line.append(None)
        else:
            avg = sum(data[i-2:i+1]) / 3
            trend_line.append(round(avg, 1))

    config = {
        "type": "bar",
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "label": "Payam ha",
                    "data": data,
                    "backgroundColor": bg_colors,
                    "borderColor": border_colors,
                    "borderWidth": 2,
                    "borderRadius": 10,
                    "borderSkipped": False,
                },
                {
                    "type": "line",
                    "label": "Trend",
                    "data": trend_line,
                    "borderColor": "rgba(168, 85, 247, 0.9)",
                    "borderWidth": 3,
                    "borderDash": [8, 4],
                    "pointBackgroundColor": "rgba(168, 85, 247, 1)",
                    "pointBorderColor": "#fff",
                    "pointBorderWidth": 2,
                    "pointRadius": 5,
                    "fill": False,
                    "tension": 0.4,
                }
            ]
        },
        "options": {
            "title": {
                "display": True,
                "text": ["Ammar Gozaresh - 7 Rooz", group_title],
                "fontSize": 18,
                "fontColor": "#1f2937",
                "fontStyle": "bold",
                "padding": 20,
            },
            "subtitle": {
                "display": True,
                "text": f"Majmo: {total} Payam | Ozve Faal: {active_count}",
                "fontSize": 13,
                "fontColor": "#6b7280",
            },
            "legend": {"display": False},
            "scales": {
                "yAxes": [{
                    "ticks": {"beginAtZero": True, "fontColor": "#4b5563", "fontSize": 12},
                    "gridLines": {"color": "rgba(0,0,0,0.06)", "drawBorder": False}
                }],
                "xAxes": [{
                    "ticks": {"fontColor": "#4b5563", "fontSize": 11},
                    "gridLines": {"display": False}
                }]
            },
            "animation": {"duration": 1500, "easing": "easeOutQuart"},
        }
    }

    try:
        encoded = urllib.parse.quote(_json.dumps(config, ensure_ascii=False))
        chart_url = f"https://quickchart.io/chart?c={encoded}&w=750&h=450&bkg=white&devicePixelRatio=2"
    except Exception as e:
        print(f"[chart] {e}")
        chart_url = None

    caption = (
        f"╔══════════════════════╗\n"
        f"   📊 **آمار گروه {group_title}**\n"
        f"╚══════════════════════╝\n"
        f"\n"
        f"🗓 **۷ روز اخیر**\n"
        f"💬 کل پیام‌ها: `{total}` پیام\n"
        f"👥 اعضای فعال: `{active_count}` نفر\n"
        f"📊 میانگین روزانه: `{avg_per_day:.1f}` پیام\n"
        f"\n"
        f"🔥 **روند کلی:**\n"
        f"   {trend} {trend_emoji}\n"
        f"   {change_txt}\n"
        f"   _{trend_msg}_\n"
        f"\n"
        f"🏆 **پرفعالیت‌ترین روز:**\n"
        f"   🥇 `{best_day_name}`\n"
        f"   💬 `{best_day_count}` پیام\n"
        f"\n"
    )

    if today_top_name:
        caption += (
            f"⚡ **برترین امروز:**\n"
            f"   🎯 **{api.esc_md(today_top_name)}** با `{today_top_count}` پیام\n"
            f"\n"
        )

    caption += (
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👑 **پنج نفر برتر هفته**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{top_text}"
        f"\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🏆 **مدیریت گروه آلفا** 💫\n"
        f"_{today.strftime('%A %Y/%m/%d')}_"
    )

    weekday_fa = {
        "Monday": "دوشنبه", "Tuesday": "سه‌شنبه", "Wednesday": "چهارشنبه",
        "Thursday": "پنجشنبه", "Friday": "جمعه", "Saturday": "شنبه", "Sunday": "یک‌شنبه"
    }
    for en, fa in weekday_fa.items():
        caption = caption.replace(en, fa)

    if chart_url:
        r = api.request("sendPhoto", {
            "chat_id": chat_id,
            "photo": chart_url,
            "caption": caption,
            "parse_mode": "Markdown",
        })
        if r and r.get("ok"):
            return r

    return api.send(chat_id, caption, parse_mode="Markdown", reply_to=reply_to)


def get_random_truth():
    return random.choice(TRUTHS_POOL) if TRUTHS_POOL else "رازی نداری؟ 😅"


def get_random_dare():
    return random.choice(DARES_POOL) if DARES_POOL else "یه کار باحال بکن! 🎉"