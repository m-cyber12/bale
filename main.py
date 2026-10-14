# -*- coding: utf-8 -*-
import os
import sys
sys.path.insert(0, ".")

import time
import random
import threading
import api
import storage
import locks
import games
import xp
import antispam
import admin
import user as user_module
import panels
import user_panels
import features
import extras
import mafia
import multiplayer
import doss
import gifmaker
import asl_laqab
import notify
import ai
import ai_persona
import ai_panel
import config
import platforms
from config import OWNER_ID


# ✅ تابع کمکی ساخت دکمه
def _btn(text, data=None, url=None):
    if url:
        return {"text": text, "url": url}
    return {"text": text, "callback_data": data}


def normalize(text):
    if not text:
        return text
    text = text.replace("\u200c", "").replace("\u200d", "").replace("\ufeff", "")
    text = text.replace("ي", "ی").replace("ك", "ک")
    text = text.replace("ۀ", "ه").replace("ة", "ه")
    text = text.replace("أ", "ا").replace("إ", "ا")
    text = text.replace("ؤ", "و").replace("ئ", "ی")
    return text


_bot_admin_cache = {}
_bot_admin_cache_last_cleanup = [0]


def _cleanup_bot_admin_cache():
    now = time.time()
    if now - _bot_admin_cache_last_cleanup[0] < 300:
        return
    _bot_admin_cache_last_cleanup[0] = now

    expired = []
    for k, (val, ts) in _bot_admin_cache.items():
        if now - ts > 600:
            expired.append(k)
    for k in expired:
        _bot_admin_cache.pop(k, None)


def _save_user_profile(chat_id, user):
    if not user or user.get("is_bot"):
        return
    uid = user.get("id")
    if not uid:
        return

    now = time.time()
    profiles = storage.get("user_profiles", chat_id) or {}
    uid_str = str(uid)

    existing = profiles.get(uid_str, {})
    profiles[uid_str] = {
        "username": (user.get("username") or "").strip(),
        "first_name": user.get("first_name", "") or existing.get("first_name", ""),
        "last_name": user.get("last_name", "") or existing.get("last_name", ""),
        "ts": existing.get("ts", now),
        "last_seen": now,
        "msg_count": existing.get("msg_count", 0) + 1,
    }

    if len(profiles) > 5000:
        keys = sorted(profiles.keys(),
                      key=lambda k: profiles[k].get("last_seen", 0))
        for k in keys[:1000]:
            profiles.pop(k, None)
    storage.set_("user_profiles", chat_id, profiles)


def is_bot_admin_in_group(chat_id):
    now = time.time()
    if chat_id in _bot_admin_cache:
        val, ts = _bot_admin_cache[chat_id]
        if now - ts < 120:
            return val
    try:
        r = api.get_member(chat_id, api.bot_id(chat_id))
        if r and r.get("ok"):
            st = r["result"].get("status", "")
            result = st in ("administrator", "creator")
            _bot_admin_cache[chat_id] = (result, now)
            try:
                _cleanup_bot_admin_cache()
            except Exception:
                pass
            return result
        if r and r.get("error_code") == 403:
            _bot_admin_cache[chat_id] = (False, now)
            return False
    except Exception as e:
        print(f"[bot_admin_check] {e}")
    return False


ALIASES = {
    "start": "شروع", "شروع": "شروع",
    "help": "راهنما", "راهنما": "راهنما",
    "panel": "پنل", "settings": "پنل", "تنظیمات": "پنل", "پنل": "پنل",
    "notes": "یادداشتها", "یادداشت": "یادداشتها", "یادداشتها": "یادداشتها",
    "locks": "قفلها", "قفلها": "قفلها", "قفل": "قفل",
    "lockgroup": "قفلگروه", "قفلگروه": "قفلگروه",
    "قفلگپ": "قفلگروه", "قفلگیری": "قفلگروه", "قفلگروهی": "قفلگروه",
    "unlockgroup": "بازکردنگروه", "بازکردنگروه": "بازکردنگروه",
    "بازگپ": "بازکردنگروه", "بازکردنگپ": "بازکردنگروه",
    "آزادگروه": "بازکردنگروه", "آزادگپ": "بازکردنگروه",
    "unlockall": "بازکردنهمه", "بازکردنهمه": "بازکردنهمه",
    "lockall": "قفلهمه", "قفلهمه": "قفلهمه",
    "welcome": "خوشآمد", "setwelcome": "خوشآمد", "خوشآمد": "خوشآمد", "خوشامد": "خوشآمد",
    "words": "لیستکلمات", "لیستکلمات": "لیستکلمات", "لیستکلمهها": "لیستکلمات",
    "addword": "کلمهممنوعه", "کلمهممنوعه": "کلمهممنوعه",
    "delword": "حذفکلمه", "حذفکلمه": "حذفکلمه",
    "setrules": "قوانینتنظیم", "قوانینتنظیم": "قوانینتنظیم",
    "stopgame": "پایانبازی", "پایانبازی": "پایانبازی",
    "unwarn": "حذفاخطار", "حذفاخطار": "حذفاخطار",
    "unpin": "برداشتنسنجاق", "برداشتنسنجاق": "برداشتنسنجاق",
    "coin": "شیرخط", "شیرخط": "شیرخط", "شیروخط": "شیرخط", "شیریا": "شیرخط",
    "slowmode": "آهسته", "آهسته": "آهسته", "حالتآهسته": "آهسته", "حالت آهسته": "آهسته",
    "broadcast": "همگانی", "پیامهمگانی": "همگانی", "همگانی": "همگانی",
    "broadcastall": "همگانی", "فوروارد": "همگانی", "ارسالهمه": "همگانی",
    "unlock": "بازکردن", "بازکردن": "بازکردن",
    "antispam": "ضداسپم", "ضداسپم": "ضداسپم",
    "badword": "ضدفحش", "ضدفحش": "ضدفحش", "antiflash": "ضدفحش", "فحش": "ضدفحش",
    "blacklist": "لیستسیاه", "لیستسیاه": "لیستسیاه", "لیست سیاه": "لیستسیاه",
    "blist": "لیستسیاه", "سیاه": "لیستسیاه",
    "cancel": "لغو", "لغو": "لغو", "کنسل": "لغو", "انصراف": "لغو",
    "reset": "ریست", "ریست": "ریست",
    "stats": "آمار", "آمار": "آمار",
    "warn": "اخطار", "اخطار": "اخطار",
    "warns": "اخطارها", "اخطارها": "اخطارها",
    "mute": "سکوت", "سکوت": "سکوت",
    "unmute": "آزاد", "آزاد": "آزاد",
    "ban": "بن", "بن": "بن",
    "unban": "آنبن", "آنبن": "آنبن",
    "kick": "اخراج", "اخراج": "اخراج",
    "promote": "ارتقا", "ارتقا": "ارتقا",
    "demote": "تنزل", "تنزل": "تنزل",
    "title": "لقب", "لقب": "لقب",
    "laqab": "لقب", "حذفلقب": "حذفلقب",
    "laqab_list": "لیستلقبها", "لیستلقبها": "لیستلقبها", "لقبها": "لیستلقبها",
    "asl": "اصل", "اصل": "اصل",
    "del": "حذف", "حذف": "حذف",
    "pin": "سنجاق", "سنجاق": "سنجاق",
    "manage": "مدیریت", "مدیریت": "مدیریت",
    "game": "بازی", "بازی": "بازی",
    "dice": "تاس", "تاس": "تاس",
    "دوز": "دوز", "doss": "دوز", "xo": "دوز",
    "گیف": "گیف", "gif": "گیف", "گیفساز": "گیف", "gifsaz": "گیف",
    "توقف": "توقف",
    "rules": "قوانین", "قوانین": "قوانین",
    "report": "گزارش", "گزارش": "گزارش",
    "info": "اطلاعات", "اطلاعات": "اطلاعات",
    "id": "آیدی", "آیدی": "آیدی",
    "time": "زمان", "زمان": "زمان",
    "calc": "حساب", "حساب": "حساب",
    "save": "ذخیره", "ذخیره": "ذخیره",
    "get": "بگیر", "بگیر": "بگیر",
    "myxp": "امتیازمن", "امتیازمن": "امتیازمن", "امتیاز": "امتیازمن",
    "top": "تاپ", "taps": "تاپ", "تاپ": "تاپ", "top10": "تاپ",
    "برترینها": "برترینها", "برترین": "تاپ",
    "rank": "رنک", "رنک": "رنک",
    "ranking": "رنکینگ", "رنکینگ": "رنکینگ",
    "level": "لول", "لول": "لول",
    "daily": "روزانه", "روزانه": "روزانه", "today": "روزانه", "امروز": "روزانه",
    "weekly": "هفتگی", "هفتگی": "هفتگی", "week": "هفتگی",
    "monthly": "ماهانه", "ماهانه": "ماهانه", "month": "ماهانه",
    "join": "عضویت", "عضویت": "عضویت", "forcejoin": "عضویت",
    "nightmode": "حالتشب", "حالتشب": "حالتشب",
    "sleepmode": "حالتخواب", "حالتخواب": "حالتخواب", "sleep": "حالتخواب",
    "خواب": "حالتخواب", "حالتخوابگروه": "حالتخواب",
    "whitelist": "سفیدلیست", "سفیدلیست": "سفیدلیست",
    "customcmds": "دستوراتسفارشی", "دستوراتسفارشی": "دستوراتسفارشی",
    "todaytop": "برترینامروز", "برترینامروز": "برترینامروز",
    "purge": "پاکسازی", "پاکسازی": "پاکسازی",
    "joke": "جوک", "جوک": "جوک",
    "tod": "جرئتحقیقت", "جرئتحقیقت": "جرئتحقیقت", "جرئت": "جرئتحقیقت", "حقیقت": "جرئتحقیقت",
    "mafia": "مافیا", "مافیا": "مافیا",
    "rps": "سنگکاغذقیچی", "سنگکاغذقیچی": "سنگکاغذقیچی",
    "leaderboard": "لیدربرد", "لیدربرد": "لیدربرد", "لیدر": "لیدربرد",
    "entertainment": "سرگرمی", "سرگرمی": "سرگرمی",
    "quiz": "آزمون", "آزمون": "آزمون", "کوییز": "آزمون",
    "quizlb": "لیدرآزمون", "لیدرآزمون": "لیدرآزمون",
    "lottery": "قرعهکشی", "قرعهکشی": "قرعهکشی",
    "rankweek": "رتبه", "رتبه": "رتبه", "رتبههفتگی": "رتبه",
    "rankmonth": "رتبهماهانه", "رتبهماهانه": "رتبهماهانه",
    "invites": "دعوتها", "دعوتها": "دعوتها",
    "invitelb": "لیدردعوت", "لیدردعوت": "لیدردعوت",
    "weeklyreport": "گزارشهفتگی", "گزارشهفتگی": "گزارشهفتگی",
    "onreport": "گزارشهفتگیروشن", "گزارشهفتگیروشن": "گزارشهفتگیروشن",
    "offreport": "گزارشهفتگیخاموش", "گزارشهفتگیخاموش": "گزارشهفتگیخاموش",
    "bug": "گزارشباگ", "گزارشباگ": "گزارشباگ", "باگ": "گزارشباگ",
    "bugreport": "گزارشباگ",
    "users": "کاربران", "کاربران": "کاربران", "لیستکاربران": "کاربران",
    "لیست کاربران": "کاربران", "کاربرهایثبتشده": "کاربران",
    "tag": "تگ", "تگ": "تگ", "منشن": "تگ", "mention": "تگ",
    "تگهمه": "تگ", "تگکردن": "تگ",
    "tagall": "تگ", "tag_all": "تگ",
    "ai": "هوش‌مصنوعی", "هوش": "هوش‌مصنوعی", "هوش‌مصنوعی": "هوش‌مصنوعی",
    "دستیار": "هوش‌مصنوعی", "دستیارai": "هوش‌مصنوعی",
    "aikey": "کلیدai", "کلیدai": "کلیدai",
    "openrouter": "کلیدai", "کلید ai": "کلیدai",
}

NO_SLASH_CMDS = set(ALIASES.values())


def split_cmd(text):
    text = normalize(text)
    parts = text.split()
    if not parts:
        return "", []

    first = parts[0]
    has_slash = first.startswith("/")
    if has_slash:
        first = first[1:]
    first_low = first.lower()
    args = parts[1:]

    if args:
        two = first_low + args[0].lower()
        if two in ALIASES:
            canonical = ALIASES[two]
            if has_slash or len(parts) == 2 or canonical in NO_SLASH_CMDS:
                return "/" + canonical, args[1:]

    if first_low in ALIASES:
        canonical = ALIASES[first_low]
        return "/" + canonical, args

    return "", []


HELP = """📖 راهنمای ربات آلفا

سلام 👋
من یه ربات مدیریت گروه هستم.

━━━━━━━━━━━━━━━
⚙️ پنل مدیریت
━━━━━━━━━━━━━━━
`پنل` → پنل مدیریت
`کاربران` → کاربران ثبت‌شده
`لیست سیاه` → بن و سکوت

━━━━━━━━━━━━━━━
📢 تگ کاربران
━━━━━━━━━━━━━━━
`تگ` → منوی تگ
`تگ همه` | `تگ 7` | `تگ 24` | `تگ هفته`

━━━━━━━━━━━━━━━
📢 پیام همگانی
━━━━━━━━━━━━━━━
فقط ادمین ربات. روی پیام ریپلای کن و بزن:
`همگانی` | `همگانی پیوی` | `همگانی گروه` | `همگانی ادمین`

━━━━━━━━━━━━━━━
🔒 قفل‌ها
━━━━━━━━━━━━━━━
`قفل ها` | `قفل همه` | `بازکردن همه`
`قفل گروه` | `باز کردن`

━━━━━━━━━━━━━━━
🛡 ضد اسپم و ضد فحش
━━━━━━━━━━━━━━━
`ضد اسپم` | `ضد فحش`

━━━━━━━━━━━━━━━
⏱ آهسته، شب، خواب
━━━━━━━━━━━━━━━
`حالت آهسته` → پنل
`آهسته 5` | `آهسته 10m` | `آهسته خاموش`
`حالت شب` | `حالت خواب`

━━━━━━━━━━━━━━━
👤 مدیریت کاربران
━━━━━━━━━━━━━━━
`مدیریت` (ریپلای یا @یوزرنیم)
`اخطار` | `حذف اخطار` | `اخطارها`
`سکوت 10m` | `آزاد`
`بن` | `آنبن` | `اخراج`
`اطلاعات` | `لیست سیاه`

━━━━━━━━━━━━━━━
📌 یادداشت
━━━━━━━━━━━━━━━
`یادداشت‌ها` | `ذخیره اسم متن` | `بگیر اسم`

━━━━━━━━━━━━━━━
🎬 گیف ساز
━━━━━━━━━━━━━━━
روی عکس یا گیف ریپلای کن و بزن `گیف`

━━━━━━━━━━━━━━━
🎮 بازی‌ها
━━━━━━━━━━━━━━━
`سرگرمی` → پنل بازی‌ها
`لیدربرد` | `مافیا` | `جرئت حقیقت`

━━━━━━━━━━━━━━━
⭐ رتبه و امتیاز
━━━━━━━━━━━━━━━
`تاپ` | `رنک` | `امتیازمن`
`روزانه` | `هفتگی` | `ماهانه`

━━━━━━━━━━━━━━━
🏆 تیم آلفا
━━━━━━━━━━━━━━━
"""

_last_msg_time = {}
_group_join_warn = {}
_night_warn_cache = {}
_sleep_warn_cache = {}
_last_mute_cleanup = {}


ADMIN_COMMANDS_NEED_BOT_ADMIN = {
    "/قفل", "/بازکردن", "/قفلها",
    "/قفلگروه", "/بازکردنگروه", "/قفلهمه", "/بازکردنهمه",
    "/ضداسپم", "/ضدفحش",
    "/خوشآمد", "/قوانینتنظیم",
    "/کلمهممنوعه", "/حذفکلمه", "/لیستکلمات",
    "/ریست", "/آمار",
    "/اخطار", "/حذفاخطار", "/اخطارها",
    "/سکوت", "/آزاد", "/بن", "/آنبن", "/اخراج",
    "/لقب", "/حذفلقب", "/لیستلقبها",
    "/حذف", "/سنجاق", "/برداشتنسنجاق",
    "/آهسته", "/عضویت", "/حالتشب", "/حالتخواب",
    "/سفیدلیست", "/دستوراتسفارشی", "/برترینامروز",
    "/پاکسازی", "/ارتقا", "/تنزل", "/مدیریت",
    "/گزارشهفتگیروشن", "/گزارشهفتگیخاموش", "/گزارشهفتگی",
    "/یادداشتها", "/لیستسیاه",
    "/روزانه", "/هفتگی", "/ماهانه",
    "/کاربران",
    "/تگ",
}


# ============================================================
# حالت آهسته
# ============================================================
def check_slowmode(chat_id, user_id):
    cfg = storage.get("slowmode", chat_id) or {}
    try:
        sec = int(cfg.get("seconds", 0) or 0)
    except (TypeError, ValueError):
        sec = 0

    if sec <= 0:
        _last_msg_time.pop((chat_id, user_id), None)
        return True, 0, 0

    key = (chat_id, user_id)
    now = time.time()
    last = _last_msg_time.get(key, 0)
    diff = now - last

    if last > 0 and diff < sec:
        remaining = max(1, int(sec - diff) + 1)
        return False, remaining, sec

    _last_msg_time[key] = now
    return True, 0, sec


def reset_slowmode_cache(chat_id=None):
    if chat_id is None:
        _last_msg_time.clear()
        return
    cid = str(chat_id)
    for k in list(_last_msg_time.keys()):
        if str(k[0]) == cid:
            _last_msg_time.pop(k, None)


def auto_delete_later(chat_id, mid, sec):
    def _run():
        time.sleep(sec)
        try:
            api.delete(chat_id, mid)
        except Exception:
            pass
    threading.Thread(target=_run, daemon=True).start()


def send_not_admin_warning(chat_id, reply_to=None):
    api.send(chat_id,
        "سلام مدیر عزیز 👋\n\n"
        "برای اینکه بتونم گروه رو مدیریت کنم، "
        "لطفاً اول من رو ادمین کن.\n\n"
        "1️⃣ تنظیمات گروه → ادمین‌ها\n"
        "2️⃣ افزودن ادمین → ربات آلفا\n"
        "3️⃣ همه دسترسی‌ها رو ✅ کن\n\n"
        "ممنون از همراهی‌ات 🌟",
        parse_mode="Markdown",
        reply_to=reply_to)


def send_bot_welcome(chat_id):
    api.send(chat_id,
        "سلام به همه 👋\n\n"
        "من ربات مدیریت گروه آلفا هستم.\n\n"
        "• `پنل` → پنل مدیریت\n"
        "• `سرگرمی` → بازی‌ها\n"
        "• `راهنما` → راهنمای کامل",
        parse_mode="Markdown",
        reply_to=0)


MAFIA_REAL_ACTIONS = (
    "mafia:join", "mafia:leave", "mafia:start", "mafia:cancel",
    "mafia:kill:", "mafia:save:", "mafia:check:", "mafia:vote:",
)


def _handle_doss_callback(cb, cb_id, data, chat_id, msg_id, user):
    user_id = user["id"]

    if data == "doss:noop":
        api.answer_callback(cb_id, "")
        return

    if data == "doss:cancel":
        ok, msg = doss.cancel_game(chat_id, user_id)
        api.answer_callback(cb_id, msg, alert=True)
        if ok:
            try:
                api.delete(chat_id, msg_id)
            except Exception:
                pass
        return

    if data.startswith("doss:play:"):
        parts = data.split(":")
        gid = int(parts[2])
        idx = int(parts[3])
        if gid != chat_id:
            api.answer_callback(cb_id, "❌", alert=True)
            return
        ok, msg = doss.handle_play(chat_id, user_id, idx)
        api.answer_callback(cb_id, msg if not ok else "✅", alert=not ok)
        return

    if data.startswith("doss:anon:"):
        parts = data.split(":")
        pair_id = parts[2]
        idx = int(parts[3])
        ok, msg = doss.handle_anon_play(user_id, pair_id, idx)
        api.answer_callback(cb_id, msg if not ok else "✅", alert=not ok)
        return

    api.answer_callback(cb_id, "❓")


def _handle_todd_callback(cb, cb_id, data, chat_id, msg_id, user):
    import questions
    user_id = user["id"]
    first_name = user.get("first_name", "کاربر")

    if data == "todd:cancel":
        try:
            api.delete(chat_id, msg_id)
        except Exception:
            pass
        api.answer_callback(cb_id, "لغو شد")
        return

    if data.startswith("todd:pick:"):
        parts = data.split(":")
        mode = parts[2]
        kind = parts[3]

        settings = storage.get("settings", chat_id) or {}
        rounds = settings.get("todd_rounds", 3)
        settings["pending_rounds"] = rounds
        storage.set_("settings", chat_id, settings)

        if kind == "truth":
            q = random.choice(questions.TRUTHS)
            emoji = "🎯"
            title = "حقیقت"
        else:
            q = random.choice(questions.DARES)
            emoji = "🔥"
            title = "جرئت"

        api.answer_callback(cb_id, f"{emoji} {title}")

        try:
            api.delete(chat_id, msg_id)
        except Exception:
            pass

        if mode == "bot":
            if kind == "truth":
                api.send(chat_id,
                    f"🎯 حقیقت برای {api.esc_md(first_name)}\n\n"
                    f"❓ {q}\n\n"
                    f"باید جواب بدی 💬",
                    parse_mode="Markdown")
            else:
                api.send(chat_id,
                    f"🔥 جرئت برای {api.esc_md(first_name)}\n\n"
                    f"⚡ {q}\n\n"
                    f"باید انجامش بدی 💪",
                    parse_mode="Markdown")
        return

    if data.startswith("todd:friend:"):
        parts = data.split(":")
        kind = parts[2]
        target_id = int(parts[3])
        target_name = parts[4] if len(parts) > 4 else "کاربر"

        if kind == "truth":
            q = random.choice(questions.TRUTHS)
            api.answer_callback(cb_id, "🎯 حقیقت")
            try:
                api.delete(chat_id, msg_id)
            except Exception:
                pass
            api.send(chat_id,
                f"🎯 حقیقت برای <a href='tg://user?id={target_id}'>{api.esc_html(target_name)}</a>\n\n"
                f"❓ {q}\n\n"
                f"باید جواب بدی 💬",
                parse_mode="HTML")
        else:
            d = random.choice(questions.DARES)
            api.answer_callback(cb_id, "🔥 جرئت")
            try:
                api.delete(chat_id, msg_id)
            except Exception:
                pass
            api.send(chat_id,
                f"🔥 جرئت برای <a href='tg://user?id={target_id}'>{api.esc_html(target_name)}</a>\n\n"
                f"⚡ {d}\n\n"
                f"باید انجامش بدی 💪",
                parse_mode="HTML")
        return

    if data.startswith("todd:anon:"):
        parts = data.split(":")
        kind = parts[2]
        pair_id = parts[3]
        target_id = int(parts[4])
        target_name = parts[5] if len(parts) > 5 else "کاربر"

        if kind == "truth":
            q = random.choice(questions.TRUTHS)
            api.answer_callback(cb_id, "🎯 حقیقت")
            try:
                api.delete(chat_id, msg_id)
            except Exception:
                pass
            api.send(target_id,
                f"🎯 حقیقت برای تو\n\n"
                f"❓ {q}\n\n"
                f"باید جواب بدی 💬",
                parse_mode="Markdown")
        else:
            d = random.choice(questions.DARES)
            api.answer_callback(cb_id, "🔥 جرئت")
            try:
                api.delete(chat_id, msg_id)
            except Exception:
                pass
            api.send(target_id,
                f"🔥 جرئت برای تو\n\n"
                f"⚡ {d}\n\n"
                f"باید انجامش بدی 💪",
                parse_mode="Markdown")
        return

    api.answer_callback(cb_id, "❓")


def handle(update, platform_key=None):
    """پردازش یک آپدیت.

    `platform_key` می‌گوید این آپدیت از کدام پیام‌رسان آمده؛ همه‌ی
    ارسال‌های این آپدیت (و تایمرهایش) به همان جا برمی‌گردند.
    """
    if platform_key:
        api.set_platform(platform_key)
    try:
        _handle_inner(update)
    finally:
        api.clear_platform()


def _handle_inner(update):
    if update.get("chat_member") or update.get("my_chat_member"):
        try:
            cm = update.get("chat_member") or update.get("my_chat_member")
            chat_id = cm.get("chat", {}).get("id")
            if not chat_id:
                return
            new_member = cm.get("new_chat_member", {})
            user_info = new_member.get("user", {})
            uid = user_info.get("id")
            if not uid or user_info.get("is_bot"):
                return

            members_seen = storage.get("members_seen", chat_id) or {}
            members_seen[str(uid)] = {
                "first_name": user_info.get("first_name", ""),
                "last_name": user_info.get("last_name", ""),
                "username": user_info.get("username", ""),
                "ts": time.time(),
            }
            if len(members_seen) > 10000:
                keys = sorted(members_seen.keys(),
                              key=lambda k: members_seen[k].get("ts", 0))
                for k in keys[:2000]:
                    members_seen.pop(k, None)
            storage.set_("members_seen", chat_id, members_seen)

            try:
                _save_user_profile(chat_id, user_info)
            except Exception:
                pass
        except Exception as e:
            print(f"[chat_member] {e}")
        return

    if update.get("callback_query"):
        try:
            cb = update["callback_query"]
            data = cb.get("data", "")
            msg = cb.get("message", {}) or {}
            chat_id = (msg.get("chat") or {}).get("id")
            msg_id = msg.get("message_id")
            user_id = (cb.get("from") or {}).get("id")
            if not chat_id or not user_id:
                print("[callback] skip: chat_id/user_id ندارد")
                return

            reply_msg = msg.get("reply_to_message")
            if reply_msg:
                api.set_reply_context(reply_msg.get("message_id"))
            else:
                api.clear_reply_context()

            if data.startswith("ai:"):
                ai_panel.handle_callback(cb, cb["id"], data, chat_id, msg_id,
                                         user)
                return

            if data.startswith("cp:"):
                val = data[3:]
                api.answer_callback(cb["id"], f"📋 کپی کن:\n{val}", alert=True)
                return

            if data.startswith("asl:"):
                asl_laqab.handle_asl_callback(cb, cb["id"], data, chat_id, msg_id, cb["from"])
                return

            if data.startswith("todd:vote:"):
                vote = data.split(":")[2]
                ok, msg_txt = multiplayer.handle_todd_vote(chat_id, user_id, vote)
                api.answer_callback(cb["id"], msg_txt, alert=not ok)
                return
            elif data.startswith("todd:grace_ok"):
                ok, msg_txt = multiplayer.handle_todd_grace(chat_id, user_id, "ok")
                api.answer_callback(cb["id"], msg_txt, alert=not ok)
                return
            elif data.startswith("todd:grace_no"):
                ok, msg_txt = multiplayer.handle_todd_grace(chat_id, user_id, "no")
                api.answer_callback(cb["id"], msg_txt, alert=not ok)
                return
            elif data.startswith("todd:setrounds:"):
                user_panels.handle_user_callback(cb, cb["id"], data, chat_id, msg_id, cb["from"])
                return

            if data.startswith("anon_todd:vote:"):
                parts = data.split(":")
                pair_id = parts[2]
                vote = parts[3]
                ok, msg_txt = multiplayer.handle_anon_todd_vote(user_id, pair_id, vote)
                api.answer_callback(cb["id"], msg_txt, alert=not ok)
                return

            is_mafia_real = any(data.startswith(x) for x in MAFIA_REAL_ACTIONS)
            is_doss = data.startswith("doss:")
            is_todd = data.startswith("todd:")
            is_gif = data.startswith("gif:")

            is_user_panel = (
                data.startswith("user:")
                or data.startswith("ug:")
                or data.startswith("game:")
                or data.startswith("mode:")
                or data.startswith("lb:")
                or data.startswith("rank:")
                or data.startswith("anon_cancel:")
            )

            PUBLIC_DATA = (
                data == "noop"
                or is_mafia_real
                or is_doss
                or is_todd
                or is_gif
                or is_user_panel
                or data.startswith("anon:")
                or data.startswith("anon_cancel:")
                or data.startswith("anon_todd:")
                or data.startswith("mp:")
                or data.startswith("quiz:ans:")
                or data.startswith("poll:vote:")
                or data.startswith("asl:")
                or data.startswith("gj:check:")
                or data == "ext:quiz"
                or data == "ext:lottery"
                or data == "ext:rank"
                or data == "user:quiz"
                or data == "user:lottery"
                or data == "user:rank"
                or data == "user:rank_daily"
                or data == "user:rank_weekly"
                or data == "user:rank_monthly"
                or data == "user:top"
                or data == "user:top10"
                or data == "user:myxp"
                or data == "user:id"
                or data == "user:rules"
                or data == "user:help"
                or data == "user:ent_help"
                or data == "user:invites"
                or data == "panel:top10"
                or data == "panel:help"
                or data == "panel:pv_open"
                or data == "panel:group_lock_toggle"
                or data == "panel:free_locked"
                or data == "panel:registered_users"
                or data == "panel:tag_menu"
                or data.startswith("tag:")
                or data.startswith("users:page:")
                or data == "rank:daily"
                or data == "rank:weekly"
                or data == "rank:monthly"
            )

            if not PUBLIC_DATA and data != "owner:close":
                opener = panels.get_panel_opener(chat_id, msg_id)
                if opener is not None and opener != user_id:
                    api.answer_callback(cb["id"],
                        "این پنل مخصوص شما نیست.", alert=True)
                    return

            if is_gif:
                gifmaker.handle_callback(cb, cb["id"], data, chat_id, msg_id, cb["from"])
                return

            if is_mafia_real:
                mafia.handle_callback(cb, cb["id"], data, chat_id, msg_id, cb["from"])
            elif is_doss:
                _handle_doss_callback(cb, cb["id"], data, chat_id, msg_id, cb["from"])
            elif is_todd:
                _handle_todd_callback(cb, cb["id"], data, chat_id, msg_id, cb["from"])
            elif data.startswith("anon:rps:") or data.startswith("anon:dice:") or data.startswith("anon:coin:"):
                ok, m = multiplayer.handle_anon_callback(user_id, data)
                api.answer_callback(cb["id"], m, alert=not ok)
            elif data.startswith("rpsg:"):
                choice = data.split(":")[1]
                ok, msg_txt = multiplayer.rps_choice(chat_id, user_id, choice)
                api.answer_callback(cb["id"], msg_txt, alert=not ok)
            elif data.startswith("anon_cancel:"):
                user_panels.handle_user_callback(cb, cb["id"], data, chat_id, msg_id, cb["from"])
            elif data.startswith("mode:") or data.startswith("game:"):
                user_panels.handle_user_callback(cb, cb["id"], data, chat_id, msg_id, cb["from"])
            elif data.startswith("mafia:"):
                user_panels.handle_user_callback(cb, cb["id"], data, chat_id, msg_id, cb["from"])
            elif data.startswith("mp:"):
                user_panels.handle_user_callback(cb, cb["id"], data, chat_id, msg_id, cb["from"])
            elif (data.startswith("user:") or data.startswith("ug:") or
                  data.startswith("lb:") or data.startswith("rank:")):
                user_panels.handle_user_callback(cb, cb["id"], data, chat_id, msg_id, cb["from"])
            else:
                panels.handle_callback(cb)
        except Exception as e:
            print(f"[callback] {e}")
            import traceback
            traceback.print_exc()
        finally:
            api.clear_reply_context()
        return

    m = update.get("message")
    if not m:
        return

    if "from" not in m:
        return

    chat = m.get("chat")
    if not chat:
        return

    chat_id = chat["id"]
    chat_type = chat.get("type", "private")
    user = m["from"]
    user_id = user.get("id")
    if not user_id:
        return

    _remember_platform(m)
    user_name = admin.u_name(user)
    raw_text = (m.get("text") or "").strip()
    text = normalize(raw_text)
    msg_id = m.get("message_id")
    if msg_id is None:
        print("[handle] skip: message_id ندارد")
        return

    api.set_reply_context(msg_id)

    try:
        features.track_user_name(chat_id, user_id, user_name)
    except Exception as e:
        print(f"[track_name] {e}")

    try:
        _save_user_profile(chat_id, user)
    except Exception as e:
        print(f"[save_profile] {e}")

    try:
        _process_message(m, chat, chat_id, chat_type, user, user_id, user_name,
                         raw_text, text, msg_id)
    except Exception as e:
        print(f"[handle] {e}")
        import traceback
        traceback.print_exc()
    finally:
        api.clear_reply_context()


def _remember_platform(m):
    """چت → پیام‌رسان را ذخیره می‌کند تا تایمرها/پیام‌های بعدی درست بروند."""
    try:
        cid = (m.get("chat") or {}).get("id")
        if cid is None:
            return
        key = api.current_platform_key()
        if key:
            platforms.remember_chat(key, cid)
    except Exception as e:
        print(f"[platforms:remember] {e}")


def _process_message(m, chat, chat_id, chat_type, user, user_id, user_name,
                     raw_text, text, msg_id):
    is_bot_msg = user.get("is_bot", False)
    settings = storage.get("settings", chat_id) or {}

    # ============================================
    # چت خصوصی
    # ============================================
    if chat_type == "private":
        panels.register_user(user)

        try:
            _save_user_profile("global", user)
        except Exception as e:
            print(f"[save_profile:pv] {e}")

        if not panels.get_owner_id():
            panels.set_owner(user_id)
            api.send(chat_id, f"👑 شما به عنوان مالک ربات ثبت شدید.\nآیدی: `{user_id}`", parse_mode="Markdown")

        g_settings = storage.get("settings", "global") or {}

        if raw_text and raw_text.strip() in ("لغو", "/لغو", "کنسل", "/کنسل", "انصراف", "/انصراف"):
            cleared = False
            for k in list(g_settings.keys()):
                if k.startswith("wait_"):
                    g_settings.pop(k, None)
                    cleared = True
            g_settings.pop("prompt_msg_id", None)
            g_settings.pop("prompt_back", None)
            storage.set_("settings", "global", g_settings)
            if cleared:
                api.send(chat_id, "✅ لغو شد.", parse_mode="Markdown", reply_to=0)
            return

        # 🔑 انتظار کلید OpenRouter
        if g_settings.get("wait_ai_key") == user_id:
            if ai_panel.handle_wait_key(chat_id, user_id, raw_text):
                try:
                    api.delete(chat_id, msg_id)
                except Exception as e:
                    print(f"[ai:del-key-msg] {e}")
                return

        if g_settings.get("wait_bug_reply") == user_id:
            target_id = g_settings.get("bug_reply_target", 0)
            g_settings.pop("wait_bug_reply", None)
            g_settings.pop("bug_reply_target", None)
            storage.set_("settings", "global", g_settings)
            try:
                api.send(int(target_id), f"📩 پاسخ مدیریت:\n\n{api.esc_md(raw_text)}", parse_mode="Markdown")
                api.send(chat_id, "✅ ارسال شد.", reply_to=0)
            except Exception as e:
                api.send(chat_id, f"❌ خطا: {e}", reply_to=0)
            return

        if g_settings.get("wait_broadcast") == user_id:
            target = g_settings.get("target", "all")
            prompt_msg_id = g_settings.pop("prompt_msg_id", None)
            prompt_back = g_settings.pop("prompt_back", "owner:back")
            g_settings.pop("wait_broadcast", None)
            g_settings.pop("target", None)
            storage.set_("settings", "global", g_settings)
            api.clear_reply_context()
            send_broadcast(chat_id, user_id, raw_text, target)
            if prompt_msg_id:
                try:
                    api.edit_message(chat_id, prompt_msg_id,
                        "✅ پیام همگانی ارسال شد.",
                        markup={"inline_keyboard": [[
                            {"text": "🔙 بازگشت به پنل", "callback_data": prompt_back}
                        ]]},
                        parse_mode="Markdown")
                except Exception:
                    pass
            return

        if g_settings.get("wait_channel") == user_id:
            prompt_msg_id = g_settings.pop("prompt_msg_id", None)
            prompt_back = g_settings.pop("prompt_back", "owner:back")
            g_settings.pop("wait_channel", None)
            storage.set_("settings", "global", g_settings)
            setup_channel(chat_id, raw_text)
            if prompt_msg_id:
                try:
                    api.edit_message(chat_id, prompt_msg_id,
                        "✅ کانال تنظیم شد.",
                        markup={"inline_keyboard": [[
                            {"text": "🔙 بازگشت به پنل", "callback_data": prompt_back}
                        ]]},
                        parse_mode="Markdown")
                except Exception:
                    pass
            return

        if g_settings.get("wait_admin_add") == user_id:
            prompt_msg_id = g_settings.pop("prompt_msg_id", None)
            prompt_back = g_settings.pop("prompt_back", "owner:back")
            g_settings.pop("wait_admin_add", None)
            storage.set_("settings", "global", g_settings)
            try:
                uid = int(raw_text.strip())
                panels.add_bot_admin(uid, f"ادمین {uid}")
                msg_txt = "✅ ادمین اضافه شد."
            except Exception:
                msg_txt = "❌ آیدی نامعتبر."
            if prompt_msg_id:
                try:
                    api.edit_message(chat_id, prompt_msg_id, msg_txt,
                        markup={"inline_keyboard": [[
                            {"text": "🔙 بازگشت به پنل", "callback_data": prompt_back}
                        ]]},
                        parse_mode="Markdown")
                except Exception:
                    pass
            else:
                api.send(chat_id, msg_txt, parse_mode="Markdown", reply_to=0)
            return

        try:
            if gifmaker.handle_text(chat_id, user_id, raw_text, msg_id):
                return
        except Exception as e:
            print(f"[gif:text:private] {e}")

        ccmd, cargs = split_cmd(text)
        if ccmd == "/پاسخ":
            if not panels.is_bot_admin(user_id):
                api.send(chat_id, "فقط ادمین‌های ربات.", reply_to=0)
                return
            if len(cargs) < 2:
                api.send(chat_id, "فرمت: /پاسخ user_id متن", reply_to=0)
                return
            try:
                target_uid = int(cargs[0])
                reply_text = " ".join(cargs[1:])
                api.send(target_uid,
                    f"📩 پاسخ مدیریت:\n\n{api.esc_md(reply_text)}",
                    parse_mode="Markdown", reply_to=0)
                api.send(chat_id, "✅ ارسال شد.", reply_to=0)
            except Exception as e:
                api.send(chat_id, f"❌ خطا: {e}", reply_to=0)
            return

        # ✅ /start تو پیوی → پنل کاربری مستقیم
        if ccmd == "/شروع" or text in ("/start", "start", "شروع") or text.startswith("/start "):
            if panels.is_bot_admin(user_id):
                t, markup = panels.owner_main_panel(user_id)
                if t:
                    r = api.send(chat_id, t, parse_mode="Markdown", markup=markup, reply_to=0)
                    if r and r.get("ok"):
                        panels.register_panel_opener(chat_id, r["result"]["message_id"], user_id)
                return
            t, markup = user_panels.user_main_panel(chat_id, user_id)
            api.send(chat_id, t, parse_mode="Markdown", markup=markup, reply_to=0)
            return

        if ccmd == "/راهنما":
            text_help, markup = panels.help_main_panel()
            api.send(chat_id, text_help, parse_mode="Markdown", markup=markup, reply_to=0)
            return

        # ✅ /پنل تو پیوی → پنل کاربری مستقیم
        if ccmd == "/پنل":
            if panels.is_bot_admin(user_id):
                t, markup = panels.owner_main_panel(user_id)
                if t:
                    r = api.send(chat_id, t, parse_mode="Markdown", markup=markup, reply_to=0)
                    if r and r.get("ok"):
                        panels.register_panel_opener(chat_id, r["result"]["message_id"], user_id)
                return
            t, markup = user_panels.user_main_panel(chat_id, user_id)
            api.send(chat_id, t, parse_mode="Markdown", markup=markup, reply_to=0)
            return

        return

    if chat_type not in ("group", "supergroup"):
        return

    # ثبت خودکار گروه
    try:
        groups = storage.get("bot_groups", "list") or {}
        gid = str(chat_id)
        new_title = chat.get("title", "")
        if gid not in groups or groups[gid].get("title") != new_title:
            groups[gid] = {
                "title": new_title,
                "added": time.strftime("%Y-%m-%d"),
                "last_seen": time.time(),
            }
            storage.set_("bot_groups", "list", groups)
    except Exception as e:
        print(f"[track_group] {e}")

    # ============================================
    # بازی دو نفره
    # ============================================
    if not is_bot_msg and text:
        pick = settings.get("pick_target")
        if pick and pick.get("user_id") == user_id:
            game_type = pick.get("game_type")
            if m.get("reply_to_message") and game_type in ("doss", "todd"):
                reply_user = m["reply_to_message"]["from"]
                if reply_user.get("id") == user_id:
                    api.send(chat_id, "نمی‌تونی با خودت بازی کنی.", reply_to=0)
                    settings.pop("pick_target", None)
                    storage.set_("settings", chat_id, settings)
                    return
                if reply_user.get("is_bot"):
                    api.send(chat_id, "ربات نمی‌تونه حریف باشه.", reply_to=0)
                    settings.pop("pick_target", None)
                    storage.set_("settings", chat_id, settings)
                    return

                tid = reply_user["id"]
                tname = reply_user.get("first_name", "کاربر")
                rounds = pick.get("rounds", 3)
                settings.pop("pick_target", None)
                settings["pending_rounds"] = rounds
                storage.set_("settings", chat_id, settings)

                if game_type == "doss":
                    doss.start_with_friend(chat_id, user_id, user_name, tid, tname)
                elif game_type == "todd":
                    multiplayer.start_between(chat_id, "todd", user_id, tid, tname)
                return

        try:
            if multiplayer.handle_message(chat_id, user_id, text, m):
                return
        except Exception as e:
            print(f"[multiplayer:handle] {e}")

        try:
            if multiplayer.check_pick_target(chat_id, user_id, m):
                return
        except Exception as e:
            print(f"[multiplayer:pick] {e}")

    # ============================================
    # لغو
    # ============================================
    if not is_bot_msg and raw_text and raw_text.strip() in ("لغو", "/لغو", "کنسل", "/کنسل", "انصراف", "/انصراف"):
        cleared = False
        for k in list(settings.keys()):
            if k.startswith("wait_") or k in (
                "note_pending_name", "cc_pending_name",
                "sleep_pending_start",
            ):
                settings.pop(k, None)
                cleared = True
        settings.pop("prompt_msg_id", None)
        settings.pop("prompt_back", None)
        storage.set_("settings", chat_id, settings)
        if cleared:
            api.send(chat_id, "✅ لغو شد.", parse_mode="Markdown", reply_to=0)
            return

    # ============================================
    # حالت انتظار یادداشت
    # ============================================
    if not is_bot_msg:
        step = settings.get("wait_note_step")
        if step and settings.get("wait_note_user") == user_id:
            if step == "name":
                name = (raw_text or "").strip().lstrip("/").strip()
                if not name:
                    api.send(chat_id, "اسم بنویس.", reply_to=0)
                    try:
                        api.delete(chat_id, msg_id)
                    except Exception:
                        pass
                    return
                if " " in name:
                    api.send(chat_id, "اسم نباید فاصله داشته باشه.", reply_to=0)
                    try:
                        api.delete(chat_id, msg_id)
                    except Exception:
                        pass
                    return
                if ":" in name:
                    api.send(chat_id, "اسم نباید `:` داشته باشه.", reply_to=0)
                    try:
                        api.delete(chat_id, msg_id)
                    except Exception:
                        pass
                    return
                if len(name) > 30:
                    api.send(chat_id, "اسم طولانیه (حداکثر ۳۰ حرف).", reply_to=0)
                    try:
                        api.delete(chat_id, msg_id)
                    except Exception:
                        pass
                    return
                notes = storage.get("notes", chat_id) or {}
                if name in notes:
                    api.send(chat_id, "این اسم قبلاً ثبت شده.", reply_to=0)
                    try:
                        api.delete(chat_id, msg_id)
                    except Exception:
                        pass
                    return

                settings["note_pending_name"] = name
                settings["wait_note_step"] = "text"
                storage.set_("settings", chat_id, settings)

                try:
                    api.delete(chat_id, msg_id)
                except Exception:
                    pass

                pmsg = settings.get("notes_panel_msg")
                if pmsg:
                    try:
                        api.edit_message(chat_id, pmsg,
                            f"📌 افزودن یادداشت (مرحله ۲/۲)\n\n"
                            f"اسم: {api.esc_md(name)}\n\n"
                            f"حالا متن یادداشت رو بفرست.",
                            parse_mode="Markdown",
                            markup={"inline_keyboard": [[{"text": "❌ لغو", "callback_data": "note:cancel"}]]})
                    except Exception as e:
                        print(f"[note:edit_name] {e}")
                return

            elif step == "text":
                name = settings.get("note_pending_name", "")
                if not name:
                    settings.pop("wait_note_step", None)
                    settings.pop("wait_note_user", None)
                    storage.set_("settings", chat_id, settings)
                    return

                content = raw_text or ""

                notes = storage.get("notes", chat_id) or {}
                notes[name] = content
                storage.set_("notes", chat_id, notes)

                settings.pop("wait_note_step", None)
                settings.pop("wait_note_user", None)
                settings.pop("note_pending_name", None)
                prompt_msg_id = settings.pop("prompt_msg_id", None)
                prompt_back = settings.pop("prompt_back", "panel:notes")
                storage.set_("settings", chat_id, settings)

                try:
                    api.delete(chat_id, msg_id)
                except Exception:
                    pass

                pmsg = settings.get("notes_panel_msg")
                if pmsg:
                    try:
                        t, mm = panels.notes_panel(chat_id)
                        api.edit_message(chat_id, pmsg, t, markup=mm, parse_mode="Markdown")
                    except Exception as e:
                        print(f"[note:edit_text] {e}")

                if prompt_msg_id:
                    try:
                        api.edit_message(chat_id, prompt_msg_id,
                            f"✅ یادداشت «{api.esc_md(name)}» ذخیره شد.",
                            markup={"inline_keyboard": [[
                                {"text": "🔙 بازگشت به پنل", "callback_data": prompt_back}
                            ]]},
                            parse_mode="Markdown")
                    except Exception:
                        pass
                else:
                    try:
                        api.send_autodelete(chat_id,
                            f"✅ یادداشت {api.esc_md(name)} ذخیره شد.",
                            sec=3, parse_mode="Markdown")
                    except Exception:
                        pass
                return

    # ============================================
    # حالت انتظار مدیا
    # ============================================
    if not is_bot_msg:
        if settings.get("wait_welcome_media") == user_id:
            is_photo = bool(m.get("photo"))
            is_video = bool(m.get("video"))
            is_anim = bool(m.get("animation"))
            is_gif_doc = False
            is_video_doc = False

            if m.get("document"):
                doc = m["document"]
                mt = (doc.get("mime_type") or "").lower()
                fn = (doc.get("file_name") or "").lower()
                if "gif" in mt or fn.endswith(".gif"):
                    is_gif_doc = True
                elif "video" in mt or fn.endswith(".mp4") or fn.endswith(".webm"):
                    is_video_doc = True

            is_sticker = bool(m.get("sticker"))

            prompt_msg_id = settings.get("prompt_msg_id")
            prompt_back = settings.get("prompt_back", "panel:welcome")

            if is_photo:
                features.set_welcome_media(chat_id, "photo", m["photo"][-1]["file_id"])
                settings.pop("wait_welcome_media", None)
                settings.pop("prompt_msg_id", None)
                settings.pop("prompt_back", None)
                storage.set_("settings", chat_id, settings)
                try:
                    api.delete(chat_id, msg_id)
                except Exception:
                    pass
                if prompt_msg_id:
                    try:
                        api.edit_message(chat_id, prompt_msg_id,
                            "✅ عکس ذخیره شد.",
                            markup={"inline_keyboard": [[
                                {"text": "🔙 بازگشت به پنل", "callback_data": prompt_back}
                            ]]},
                            parse_mode="Markdown")
                    except Exception:
                        pass
                else:
                    api.send(chat_id, "✅ عکس ذخیره شد.", reply_to=0)
                return

            elif is_video:
                features.set_welcome_media(chat_id, "video", m["video"]["file_id"])
                settings.pop("wait_welcome_media", None)
                settings.pop("prompt_msg_id", None)
                settings.pop("prompt_back", None)
                storage.set_("settings", chat_id, settings)
                try:
                    api.delete(chat_id, msg_id)
                except Exception:
                    pass
                if prompt_msg_id:
                    try:
                        api.edit_message(chat_id, prompt_msg_id,
                            "✅ ویدیو ذخیره شد.",
                            markup={"inline_keyboard": [[
                                {"text": "🔙 بازگشت به پنل", "callback_data": prompt_back}
                            ]]},
                            parse_mode="Markdown")
                    except Exception:
                        pass
                else:
                    api.send(chat_id, "✅ ویدیو ذخیره شد.", reply_to=0)
                return

            elif is_anim:
                features.set_welcome_media(chat_id, "animation", m["animation"]["file_id"])
                settings.pop("wait_welcome_media", None)
                settings.pop("prompt_msg_id", None)
                settings.pop("prompt_back", None)
                storage.set_("settings", chat_id, settings)
                try:
                    api.delete(chat_id, msg_id)
                except Exception:
                    pass
                if prompt_msg_id:
                    try:
                        api.edit_message(chat_id, prompt_msg_id,
                            "✅ گیف ذخیره شد.",
                            markup={"inline_keyboard": [[
                                {"text": "🔙 بازگشت به پنل", "callback_data": prompt_back}
                            ]]},
                            parse_mode="Markdown")
                    except Exception:
                        pass
                else:
                    api.send(chat_id, "✅ گیف ذخیره شد.", reply_to=0)
                return

            elif is_gif_doc:
                features.set_welcome_media(chat_id, "animation", m["document"]["file_id"])
                settings.pop("wait_welcome_media", None)
                settings.pop("prompt_msg_id", None)
                settings.pop("prompt_back", None)
                storage.set_("settings", chat_id, settings)
                try:
                    api.delete(chat_id, msg_id)
                except Exception:
                    pass
                if prompt_msg_id:
                    try:
                        api.edit_message(chat_id, prompt_msg_id,
                            "✅ گیف ذخیره شد.",
                            markup={"inline_keyboard": [[
                                {"text": "🔙 بازگشت به پنل", "callback_data": prompt_back}
                            ]]},
                            parse_mode="Markdown")
                    except Exception:
                        pass
                else:
                    api.send(chat_id, "✅ گیف ذخیره شد.", reply_to=0)
                return

            elif is_video_doc:
                features.set_welcome_media(chat_id, "video", m["document"]["file_id"])
                settings.pop("wait_welcome_media", None)
                settings.pop("prompt_msg_id", None)
                settings.pop("prompt_back", None)
                storage.set_("settings", chat_id, settings)
                try:
                    api.delete(chat_id, msg_id)
                except Exception:
                    pass
                if prompt_msg_id:
                    try:
                        api.edit_message(chat_id, prompt_msg_id,
                            "✅ ویدیو ذخیره شد.",
                            markup={"inline_keyboard": [[
                                {"text": "🔙 بازگشت به پنل", "callback_data": prompt_back}
                            ]]},
                            parse_mode="Markdown")
                    except Exception:
                        pass
                else:
                    api.send(chat_id, "✅ ویدیو ذخیره شد.", reply_to=0)
                return

            elif is_sticker:
                api.send(chat_id, "استیکر پشتیبانی نمیشه.\nعکس، ویدیو یا گیف بفرست.",
                         reply_to=0)
                return

            else:
                api.send(chat_id, "لطفاً عکس، ویدیو یا گیف بفرست.", reply_to=0)
                return

    # ============================================
    # حالت انتظار متن
    # ============================================
    if not is_bot_msg and raw_text and not raw_text.startswith("/"):
        try:
            if gifmaker.handle_text(chat_id, user_id, raw_text, msg_id):
                return
        except Exception as e:
            print(f"[gif:text] {e}")

        if settings.get("wait_badword") == user_id:
            prompt_msg_id = settings.pop("prompt_msg_id", None)
            prompt_back = settings.pop("prompt_back", "panel:badword")
            settings.pop("wait_badword", None)
            storage.set_("settings", chat_id, settings)
            words = raw_text.split()
            extra = storage.get("extra_bad_words", chat_id) or []
            added = 0
            for w in words:
                w = w.strip()
                if w and w not in extra:
                    extra.append(w)
                    added += 1
            storage.set_("extra_bad_words", chat_id, extra)
            try:
                api.delete(chat_id, msg_id)
            except Exception:
                pass
            if prompt_msg_id:
                try:
                    api.edit_message(chat_id, prompt_msg_id,
                        f"✅ {added} کلمه اضافه شد.\nمجموع: {len(extra)}",
                        markup={"inline_keyboard": [[
                            {"text": "🔙 بازگشت به پنل", "callback_data": prompt_back}
                        ]]},
                        parse_mode="Markdown")
                except Exception:
                    pass
            else:
                api.send(chat_id, f"✅ {added} کلمه اضافه شد.", reply_to=0)
            return

        if settings.get("wait_bug_report") == user_id:
            prompt_msg_id = settings.pop("prompt_msg_id", None)
            prompt_back = settings.pop("prompt_back", "panel:main")
            settings.pop("wait_bug_report", None)
            storage.set_("settings", chat_id, settings)
            ok, result = extras.send_bug_report(chat_id, user_id, user_name, raw_text, chat.get("title", ""))
            try:
                api.delete(chat_id, msg_id)
            except Exception:
                pass
            if ok:
                msg_txt = f"✅ گزارش ثبت شد.\nکد پیگیری: #{result}"
            else:
                msg_txt = result
            if prompt_msg_id:
                try:
                    api.edit_message(chat_id, prompt_msg_id, msg_txt,
                        markup={"inline_keyboard": [[
                            {"text": "🔙 بازگشت به پنل", "callback_data": prompt_back}
                        ]]},
                        parse_mode="Markdown")
                except Exception:
                    pass
            else:
                api.send(chat_id, msg_txt, reply_to=0)
            return

        if settings.get("wait_welcome") == user_id:
            cfg = storage.get("welcome", chat_id) or {}
            cfg["text"] = raw_text
            cfg["enabled"] = True
            storage.set_("welcome", chat_id, cfg)
            prompt_msg_id = settings.pop("prompt_msg_id", None)
            prompt_back = settings.pop("prompt_back", "panel:welcome")
            settings.pop("wait_welcome", None)
            storage.set_("settings", chat_id, settings)
            try:
                api.delete(chat_id, msg_id)
            except Exception:
                pass
            if prompt_msg_id:
                try:
                    api.edit_message(chat_id, prompt_msg_id,
                        "✅ متن خوش‌آمد ذخیره شد.",
                        markup={"inline_keyboard": [[
                            {"text": "🔙 بازگشت به پنل", "callback_data": prompt_back}
                        ]]},
                        parse_mode="Markdown")
                except Exception:
                    pass
            else:
                api.send(chat_id, "✅ ذخیره شد.", reply_to=0)
            return

        if settings.get("wait_rules") == user_id:
            storage.set_("rules", chat_id, {"text": raw_text})
            prompt_msg_id = settings.pop("prompt_msg_id", None)
            prompt_back = settings.pop("prompt_back", "panel:rules")
            settings.pop("wait_rules", None)
            storage.set_("settings", chat_id, settings)
            try:
                api.delete(chat_id, msg_id)
            except Exception:
                pass
            if prompt_msg_id:
                try:
                    api.edit_message(chat_id, prompt_msg_id,
                        "✅ قوانین ذخیره شد.",
                        markup={"inline_keyboard": [[
                            {"text": "🔙 بازگشت به پنل", "callback_data": prompt_back}
                        ]]},
                        parse_mode="Markdown")
                except Exception:
                    pass
            else:
                api.send(chat_id, "✅ قوانین ذخیره شد.", reply_to=0)
            return

        if settings.get("wait_word") == user_id:
            words = storage.get("banned_words", chat_id) or []
            added = 0
            for w in raw_text.split():
                if w not in words:
                    words.append(w)
                    added += 1
            storage.set_("banned_words", chat_id, words)
            prompt_msg_id = settings.pop("prompt_msg_id", None)
            prompt_back = settings.pop("prompt_back", "panel:words")
            settings.pop("wait_word", None)
            storage.set_("settings", chat_id, settings)
            try:
                api.delete(chat_id, msg_id)
            except Exception:
                pass
            if prompt_msg_id:
                try:
                    api.edit_message(chat_id, prompt_msg_id,
                        f"✅ {added} کلمه اضافه شد.",
                        markup={"inline_keyboard": [[
                            {"text": "🔙 بازگشت به پنل", "callback_data": prompt_back}
                        ]]},
                        parse_mode="Markdown")
                except Exception:
                    pass
            else:
                api.send(chat_id, "✅ اضافه شد.", reply_to=0)
            return

        if "wait_title" in settings:
            tid = settings["wait_title"]
            titles = storage.get("titles", chat_id) or {}
            titles[str(tid)] = raw_text
            storage.set_("titles", chat_id, titles)
            prompt_msg_id = settings.pop("prompt_msg_id", None)
            prompt_back = settings.pop("prompt_back", "panel:main")
            settings.pop("wait_title", None)
            storage.set_("settings", chat_id, settings)
            try:
                api.delete(chat_id, msg_id)
            except Exception:
                pass
            if prompt_msg_id:
                try:
                    api.edit_message(chat_id, prompt_msg_id,
                        f"🏷 لقب ثبت شد: {api.esc_md(raw_text)}",
                        markup={"inline_keyboard": [[
                            {"text": "🔙 بازگشت به پنل", "callback_data": prompt_back}
                        ]]},
                        parse_mode="Markdown")
                except Exception:
                    pass
            else:
                api.send(chat_id, f"🏷 لقب ثبت شد: {raw_text}", reply_to=0)
            return

        if settings.get("wait_group_channel") == user_id:
            prompt_msg_id = settings.pop("prompt_msg_id", None)
            prompt_back = settings.pop("prompt_back", "panel:group_join")
            settings.pop("wait_group_channel", None)
            storage.set_("settings", chat_id, settings)
            setup_group_channel(chat_id, raw_text)
            try:
                api.delete(chat_id, msg_id)
            except Exception:
                pass
            if prompt_msg_id:
                try:
                    api.edit_message(chat_id, prompt_msg_id,
                        "✅ کانال تنظیم شد.",
                        markup={"inline_keyboard": [[
                            {"text": "🔙 بازگشت به پنل", "callback_data": prompt_back}
                        ]]},
                        parse_mode="Markdown")
                except Exception:
                    pass
            return

        if settings.get("wait_nm_start") == user_id:
            prompt_msg_id = settings.pop("prompt_msg_id", None)
            prompt_back = settings.pop("prompt_back", "panel:night_mode")
            settings.pop("wait_nm_start", None)
            storage.set_("settings", chat_id, settings)
            t = raw_text.strip()
            try:
                api.delete(chat_id, msg_id)
            except Exception:
                pass
            if features._validate_time(t):
                features.set_night_mode(chat_id, start=t)
                msg_txt = f"✅ ساعت شروع: {t}"
            else:
                msg_txt = "❌ فرمت اشتباه. مثال: 23:00"
            if prompt_msg_id:
                try:
                    api.edit_message(chat_id, prompt_msg_id, msg_txt,
                        markup={"inline_keyboard": [[
                            {"text": "🔙 بازگشت به پنل", "callback_data": prompt_back}
                        ]]},
                        parse_mode="Markdown")
                except Exception:
                    pass
            return

        if settings.get("wait_nm_end") == user_id:
            prompt_msg_id = settings.pop("prompt_msg_id", None)
            prompt_back = settings.pop("prompt_back", "panel:night_mode")
            settings.pop("wait_nm_end", None)
            storage.set_("settings", chat_id, settings)
            t = raw_text.strip()
            try:
                api.delete(chat_id, msg_id)
            except Exception:
                pass
            if features._validate_time(t):
                features.set_night_mode(chat_id, end=t)
                msg_txt = f"✅ ساعت پایان: {t}"
            else:
                msg_txt = "❌ فرمت اشتباه. مثال: 07:00"
            if prompt_msg_id:
                try:
                    api.edit_message(chat_id, prompt_msg_id, msg_txt,
                        markup={"inline_keyboard": [[
                            {"text": "🔙 بازگشت به پنل", "callback_data": prompt_back}
                        ]]},
                        parse_mode="Markdown")
                except Exception:
                    pass
            return

        if settings.get("wait_sleep_start") == user_id:
            t = raw_text.strip()
            if not features._validate_time(t):
                try:
                    api.delete(chat_id, msg_id)
                except Exception:
                    pass
                prompt_msg_id = settings.get("prompt_msg_id")
                if prompt_msg_id:
                    try:
                        api.edit_message(chat_id, prompt_msg_id,
                            "❌ فرمت اشتباه\n\n"
                            "فرمت درست: HH:MM — مثال: 03:00\n\n"
                            "دوباره بفرست یا بنویس لغو",
                            markup={"inline_keyboard": [[
                                {"text": "🔙 بازگشت به پنل", "callback_data": "panel:sleep"}
                            ]]},
                            parse_mode="Markdown")
                    except Exception:
                        pass
                return

            settings.pop("wait_sleep_start", None)
            settings["sleep_pending_start"] = t
            settings["wait_sleep_end"] = user_id
            storage.set_("settings", chat_id, settings)
            try:
                api.delete(chat_id, msg_id)
            except Exception:
                pass

            prompt_msg_id = settings.get("prompt_msg_id")
            if prompt_msg_id:
                try:
                    api.edit_message(chat_id, prompt_msg_id,
                        f"😴 افزودن بازه خواب (۲/۲)\n\n"
                        f"شروع: {t}\n\n"
                        f"حالا ساعت پایان رو بفرست.\n\n"
                        f"مثال: 04:00",
                        markup={"inline_keyboard": [[
                            {"text": "🔙 بازگشت به پنل", "callback_data": "panel:sleep"}
                        ]]},
                        parse_mode="Markdown")
                except Exception:
                    pass
            else:
                api.send(chat_id, f"شروع: {t}\nحالا پایان رو بفرست.", reply_to=0)
            return

        if settings.get("wait_sleep_end") == user_id:
            t = raw_text.strip()
            if not features._validate_time(t):
                try:
                    api.delete(chat_id, msg_id)
                except Exception:
                    pass
                api.send(chat_id, "❌ فرمت اشتباه. مثال: 04:00", reply_to=0)
                return

            start = settings.get("sleep_pending_start", "")
            settings.pop("wait_sleep_end", None)
            settings.pop("sleep_pending_start", None)
            storage.set_("settings", chat_id, settings)
            try:
                api.delete(chat_id, msg_id)
            except Exception:
                pass

            if not start:
                api.send(chat_id, "خطا. دوباره تلاش کن.", reply_to=0)
                return

            prompt_msg_id = settings.get("prompt_msg_id")
            txt, markup = panels.sleep_confirm_panel(chat_id, start, t)
            if prompt_msg_id:
                try:
                    api.edit_message(chat_id, prompt_msg_id, txt, markup=markup, parse_mode="Markdown")
                except Exception:
                    pass
            else:
                api.send(chat_id, txt, parse_mode="Markdown", markup=markup, reply_to=0)
            return

        if settings.get("wait_wl") == user_id:
            prompt_msg_id = settings.pop("prompt_msg_id", None)
            prompt_back = settings.pop("prompt_back", "panel:whitelist")
            settings.pop("wait_wl", None)
            storage.set_("settings", chat_id, settings)
            try:
                api.delete(chat_id, msg_id)
            except Exception:
                pass
            try:
                uid = int(raw_text.strip())
                features.add_whitelist(chat_id, uid)
                msg_txt = f"✅ کاربر {uid} به سفیدلیست اضافه شد."
            except Exception:
                msg_txt = "❌ آیدی نامعتبر."
            if prompt_msg_id:
                try:
                    api.edit_message(chat_id, prompt_msg_id, msg_txt,
                        markup={"inline_keyboard": [[
                            {"text": "🔙 بازگشت به پنل", "callback_data": prompt_back}
                        ]]},
                        parse_mode="Markdown")
                except Exception:
                    pass
            return

        if settings.get("wait_cc_name") == user_id:
            name = raw_text.strip().lstrip("/")
            try:
                api.delete(chat_id, msg_id)
            except Exception:
                pass
            if not name or " " in name:
                prompt_msg_id = settings.get("prompt_msg_id")
                if prompt_msg_id:
                    try:
                        api.edit_message(chat_id, prompt_msg_id,
                            "بدون فاصله بنویس.",
                            markup={"inline_keyboard": [[
                                {"text": "🔙 بازگشت به پنل", "callback_data": "panel:custom_cmds"}
                            ]]},
                            parse_mode="Markdown")
                    except Exception:
                        pass
                return
            settings.pop("wait_cc_name", None)
            settings["cc_pending_name"] = name
            settings["wait_cc_reply"] = user_id
            storage.set_("settings", chat_id, settings)
            prompt_msg_id = settings.get("prompt_msg_id")
            if prompt_msg_id:
                try:
                    api.edit_message(chat_id, prompt_msg_id,
                        f"✅ اسم: {api.esc_md(name)}\n\nحالا متن پاسخ رو بفرست.",
                        markup={"inline_keyboard": [[
                            {"text": "🔙 بازگشت به پنل", "callback_data": "panel:custom_cmds"}
                        ]]},
                        parse_mode="Markdown")
                except Exception:
                    pass
            return

        if settings.get("wait_cc_reply") == user_id:
            name = settings.get("cc_pending_name", "")
            prompt_msg_id = settings.pop("prompt_msg_id", None)
            prompt_back = settings.pop("prompt_back", "panel:custom_cmds")
            settings.pop("wait_cc_reply", None)
            settings.pop("cc_pending_name", None)
            storage.set_("settings", chat_id, settings)
            try:
                api.delete(chat_id, msg_id)
            except Exception:
                pass
            if not name:
                return
            features.add_custom_cmd(chat_id, name, raw_text)
            if prompt_msg_id:
                try:
                    api.edit_message(chat_id, prompt_msg_id,
                        f"✅ دستور /{api.esc_md(name)} ثبت شد.",
                        markup={"inline_keyboard": [[
                            {"text": "🔙 بازگشت به پنل", "callback_data": prompt_back}
                        ]]},
                        parse_mode="Markdown")
                except Exception:
                    pass
            return

    # ============================================
    # ورود/خروج
    # ============================================
    if m.get("new_chat_members"):
        api.clear_reply_context()
        for member in m["new_chat_members"]:
            if member.get("id") == api.bot_id(chat_id):
                time.sleep(1.5)
                _bot_admin_cache.pop(chat_id, None)
                try:
                    locks.apply_permissions(chat_id)
                except Exception as e:
                    print(f"[apply_perms:new_bot] {e}")
                if is_bot_admin_in_group(chat_id):
                    send_bot_welcome(chat_id)
                else:
                    send_not_admin_warning(chat_id)
            else:
                try:
                    locks.register_known_user(chat_id, member["id"])
                except Exception as e:
                    print(f"[register_new] {e}")

                try:
                    _save_user_profile(chat_id, member)
                except Exception as e:
                    print(f"[save_profile:new_member] {e}")

                try:
                    members_seen = storage.get("members_seen", chat_id) or {}
                    members_seen[str(member["id"])] = {
                        "first_name": member.get("first_name", ""),
                        "last_name": member.get("last_name", ""),
                        "username": member.get("username", ""),
                        "ts": time.time(),
                    }
                    storage.set_("members_seen", chat_id, members_seen)
                except Exception as e:
                    print(f"[members_seen:new] {e}")

                msg_id_w = features.send_welcome(chat_id, admin.u_name(member),
                                                 chat.get("title", ""),
                                                 member_id=member.get("id"))
                cfg = storage.get("welcome", chat_id) or {}
                ad = cfg.get("autodelete", 0)
                if msg_id_w and ad > 0:
                    auto_delete_later(chat_id, msg_id_w, ad)
                try:
                    inviter = m.get("from")
                    if inviter and inviter.get("id") != member.get("id"):
                        extras.track_invite(chat_id, inviter["id"], admin.u_name(inviter), member["id"], admin.u_name(member))
                except Exception as e:
                    print(f"[invite] {e}")
        return

    if m.get("left_chat_member"):
        if not m["left_chat_member"].get("is_bot"):
            name = admin.u_name(m['left_chat_member'])
            api.send(chat_id,
                f"👋 {name} از گروه رفت.\nموفق باشه 💐",
                reply_to=0)
        return

    if is_bot_msg:
        return

    if not user:
        return

    is_user_admin = admin.is_admin(chat_id, user_id)
    bot_is_admin = is_bot_admin_in_group(chat_id)

    try:
        now_cleanup = time.time()
        if now_cleanup - _last_mute_cleanup.get(chat_id, 0) > 60:
            _last_mute_cleanup[chat_id] = now_cleanup
            locks.cleanup_expired_mutes(chat_id)
    except Exception as e:
        print(f"[cleanup_mutes] {e}")

    # ============================================
    # چک قفل‌ها
    # ============================================
    if not is_user_admin and bot_is_admin:
        try:
            locks.register_known_user(chat_id, user_id)
        except Exception as e:
            print(f"[register_user] {e}")

        if locks.is_user_locked(chat_id, user_id):
            try:
                api.delete(chat_id, msg_id)
            except Exception as e:
                print(f"[lock:delete_locked] {e}")
            return

        if locks.is_group_locked(chat_id):
            try:
                api.delete(chat_id, msg_id)
            except Exception as e:
                print(f"[lock:delete_grp] {e}")
            try:
                locks.apply_to_one_user(chat_id, user_id)
            except Exception:
                pass
            try:
                locks.add_to_lock_list(chat_id, user_id)
            except Exception:
                pass
            try:
                api.send_autodelete(
                    chat_id,
                    f"گروه قفل است.\n{api.esc_md(user_name)} جان، فقط ادمین‌ها پیام می‌دن.",
                    sec=5, parse_mode="Markdown")
            except Exception as e:
                print(f"[lock:warn_grp] {e}")
            return

        try:
            blocked = locks.should_block(chat_id, m)
            if blocked:
                try:
                    api.delete(chat_id, msg_id)
                except Exception as e:
                    print(f"[lock:delete] {e}")

                try:
                    count, threshold, should_kick = locks.handle_lock_violation(
                        chat_id, user_id, blocked
                    )
                    fa = locks.LOCKS.get(blocked, {}).get("fa", blocked)
                    try:
                        ai_persona.note_violation(chat_id, user_id, "lock",
                                                  user_name)
                    except Exception as e:
                        print(f"[persona:lock] {e}")

                    if should_kick:
                        try:
                            api.ban(chat_id, user_id)
                            time.sleep(0.4)
                            api.unban(chat_id, user_id)
                        except Exception as e:
                            print(f"[lock:kick] {e}")
                        try:
                            from storage import save_banned
                            save_banned(chat_id, user_id, user_name)
                        except Exception as e:
                            print(f"[lock:kick:save] {e}")
                        try:
                            api.send_autodelete(
                                chat_id,
                                f"👢 {api.esc_md(user_name)} به دلیل {threshold} بار نقض قوانین ({fa}) اخراج شد.",
                                sec=5, parse_mode="Markdown")
                        except Exception as e:
                            print(f"[lock:kick_msg] {e}")

                        try:
                            notify.notify_punishment(user_id, chat_id, "kick",
                                                     reason=f"نقض قوانین ({fa})")
                        except Exception as e:
                            print(f"[lock:kick:notify] {e}")
                    else:
                        try:
                            api.send_autodelete(
                                chat_id,
                                f"«{fa}» قفل است.\n"
                                f"{api.esc_md(user_name)} جان، این پیام ممنوعه.\n"
                                f"هشدار: {count}/{threshold}",
                                sec=5, parse_mode="Markdown")
                        except Exception as e:
                            print(f"[lock:warn] {e}")
                except Exception as e:
                    print(f"[lock:handle_violation] {e}")
                return
        except Exception as e:
            print(f"[locks] {e}")

    # ============================================================
    # قفل گروه
    # ============================================================
    text_clean = text.strip().lstrip("/").strip() if text else ""
    text_clean = (text_clean
                  .replace(" ", "")
                  .replace("\u200c", "")
                  .replace("\u200e", "")
                  .replace("\u200f", "")
                  .replace("\t", "")
    )

    group_lock_triggers = (
        "قفلگروه", "قفلگپ", "قفلگیری", "قفلگروهی",
        "قفلکل", "قفلجمع", "گروهقفل", "گپقفل",
        "lockgroup", "قفلگروهکامل",
    )
    group_unlock_triggers = (
        "بازکردنگروه", "بازکردنگپ", "بازگپ", "بازگروه",
        "آزادگروه", "آزادگپ", "بازکردنگروهی",
        "رفعقفلگروه", "رفعقفلگپ",
        "بازکردنهمه", "بازکردنکل",
        "unlockgroup",
        "گروهباز", "گپباز",
    )

    if text_clean in group_lock_triggers:
        if not bot_is_admin:
            send_not_admin_warning(chat_id, reply_to=msg_id)
            return
        if not is_user_admin:
            api.send(chat_id, "فقط ادمین‌ها.", reply_to=msg_id)
            return
        admin.cmd_lock_group(chat_id, user_id, user_name)
        return

    if text_clean in group_unlock_triggers:
        if not bot_is_admin:
            send_not_admin_warning(chat_id, reply_to=msg_id)
            return
        if not is_user_admin:
            api.send(chat_id, "فقط ادمین‌ها.", reply_to=msg_id)
            return
        admin.cmd_unlock_group(chat_id, user_id, user_name)
        return

    # ============================================================
    # حالت شب
    # ============================================================
    if not is_user_admin:
        is_cmd_nm = bool(text) and text.strip().startswith("/")
        is_whitelisted_nm = features.is_whitelisted(chat_id, user_id)
        if not is_cmd_nm and not is_whitelisted_nm:
            if features.is_night_time(chat_id):
                try:
                    api.delete(chat_id, msg_id)
                except Exception as e:
                    print(f"[night:delete] {e}")
                try:
                    now = time.time()
                    key = (chat_id, user_id, "night")
                    if now - _night_warn_cache.get(key, 0) > 60:
                        _night_warn_cache[key] = now
                        cfg = features.get_night_mode(chat_id)
                        api.send_autodelete(
                            chat_id,
                            f"🌙 حالت شب فعاله\n\n"
                            f"{api.esc_md(user_name)} جان، از {cfg.get('start','23:00')} "
                            f"تا {cfg.get('end','07:00')} نمی‌تونیم پیام بذاریم.",
                            sec=6, parse_mode="Markdown")
                except Exception as e:
                    print(f"[night:warn] {e}")
                return

    # ============================================================
    # حالت خواب
    # ============================================================
    if not is_user_admin:
        is_cmd_sp = bool(text) and text.strip().startswith("/")
        is_whitelisted_sp = features.is_whitelisted(chat_id, user_id)
        if not is_cmd_sp and not is_whitelisted_sp:
            if features.is_sleep_time(chat_id):
                try:
                    api.delete(chat_id, msg_id)
                except Exception as e:
                    print(f"[sleep:delete] {e}")
                try:
                    now = time.time()
                    key = (chat_id, user_id, "sleep")
                    if now - _sleep_warn_cache.get(key, 0) > 60:
                        _sleep_warn_cache[key] = now
                        api.send_autodelete(
                            chat_id,
                            f"😴 حالت خواب فعاله\n\n"
                            f"{api.esc_md(user_name)} جان، الان گروه خوابه.",
                            sec=6, parse_mode="Markdown")
                except Exception as e:
                    print(f"[sleep:warn] {e}")
                return

    # ============================================================
    # عضویت اجباری
    # ============================================================
    if not is_user_admin:
        is_cmd_gj = bool(text) and text.strip().startswith("/")
        if not is_cmd_gj:
            gj = panels.get_group_join(chat_id)
            if gj.get("enabled"):
                if not panels.check_group_join(chat_id, user_id):
                    try:
                        api.delete(chat_id, msg_id)
                    except Exception as e:
                        print(f"[gj:delete] {e}")

                    try:
                        txt, markup = panels.build_group_join_message(
                            chat_id, user_id, user_name
                        )
                        r = api.send(chat_id, txt, parse_mode="Markdown", markup=markup, reply_to=0)
                        if r and r.get("ok"):
                            mid = r["result"]["message_id"]
                            def _auto_del(c_id=chat_id, m_id=mid):
                                time.sleep(180)
                                try:
                                    api.delete(c_id, m_id)
                                except Exception:
                                    pass
                            threading.Thread(target=_auto_del, daemon=True).start()
                    except Exception as e:
                        print(f"[gj:send] {e}")
                    return

    # ============================================================
    # حالت آهسته
    # ============================================================
    if not is_user_admin:
        is_cmd_check = bool(text) and text.strip().startswith("/")
        if not is_cmd_check:
            allowed, wait_sec, total_sec = check_slowmode(chat_id, user_id)
            if not allowed:
                try:
                    api.delete(chat_id, msg_id)
                except Exception as e:
                    print(f"[slowmode:delete] {e}")
                try:
                    api.send_autodelete(
                        chat_id,
                        f"⏱ حالت آهسته فعاله\n\n"
                        f"{api.esc_md(user_name)} جان، {total_sec} ثانیه صبر کن.\n"
                        f"باقی‌مونده: {wait_sec} ثانیه",
                        sec=5, parse_mode="Markdown")
                except Exception as e:
                    print(f"[slowmode:warn] {e}")
                return

    if not text:
        return

    cmd, args = split_cmd(text)

    if cmd == "/همگانی":
        if not panels.is_bot_admin(user_id):
            api.send(chat_id, "این دستور فقط برای ادمین‌های رباته.",
                     reply_to=msg_id)
            return

        if not m.get("reply_to_message"):
            api.send(chat_id,
                "📢 پیام همگانی\n\n"
                "روی پیام ریپلای کن و بفرست:\n\n"
                "• همگانی → به همه\n"
                "• همگانی پیوی → فقط پیوی\n"
                "• همگانی گروه → فقط گروه‌ها\n"
                "• همگانی ادمین → فقط ادمین‌ها",
                parse_mode="Markdown", reply_to=msg_id)
            return

        target = "both"
        if args:
            a = args[0].lower()
            if a in ("پیوی", "private", "user", "کاربران"):
                target = "private"
            elif a in ("گروه", "groups", "group", "گروهها"):
                target = "groups"
            elif a in ("ادمین", "admins", "admin"):
                target = "admins"
            elif a in ("همه", "both", "all"):
                target = "both"

        replied = m["reply_to_message"]

        if replied.get("forward_from_chat") and replied.get("forward_from_message_id"):
            src_chat_id = replied["forward_from_chat"]["id"]
            src_msg_id = replied["forward_from_message_id"]
            src_title = replied["forward_from_chat"].get("title", "کانال")
            api.send(chat_id,
                f"⏳ دارم فوروارد می‌کنم...\n\n"
                f"مقصد: {target}\n"
                f"مبدأ: {src_title}",
                reply_to=msg_id)
        else:
            src_chat_id = chat_id
            src_msg_id = replied["message_id"]
            api.send(chat_id,
                f"⏳ دارم فوروارد می‌کنم...\n\n"
                f"مقصد: {target}",
                reply_to=msg_id)

        send_broadcast_forward(chat_id, user_id, src_chat_id, src_msg_id, target)
        return

    if cmd in ("/تاپ", "/رنک", "/رنکینگ", "/لول", "/برترینها"):
        games.cmd_ranking_period(chat_id, "all")
        return
    if cmd == "/روزانه":
        games.cmd_ranking_period(chat_id, "daily")
        return
    if cmd == "/هفتگی":
        games.cmd_ranking_period(chat_id, "weekly")
        return
    if cmd == "/ماهانه":
        games.cmd_ranking_period(chat_id, "monthly")
        return

    if cmd in ADMIN_COMMANDS_NEED_BOT_ADMIN:
        if is_user_admin:
            if not bot_is_admin:
                send_not_admin_warning(chat_id, reply_to=msg_id)
                return
        else:
            api.send(chat_id,
                "این دستور مخصوص ادمین‌های گروهه.",
                reply_to=msg_id)
            return

    if not cmd:
        norm_text = normalize(raw_text).strip()
        if norm_text.startswith("/"):
            parts = norm_text[1:].split()
            if parts:
                cname = parts[0].lower()
                custom = features.get_custom_cmd(chat_id, cname)
                if custom:
                    api.send(chat_id, custom, reply_to=msg_id)
                    return
        else:
            custom = features.get_custom_cmd(chat_id, norm_text.lower())
            if custom:
                api.send(chat_id, custom, reply_to=msg_id)
                return
            first_word = norm_text.split()[0].lower()
            custom = features.get_custom_cmd(chat_id, first_word)
            if custom:
                api.send(chat_id, custom, reply_to=msg_id)
                return

    if not text.startswith("/") and not cmd:
        try:
            features.track_message(chat_id, user_id)
        except Exception as e:
            print(f"[track] {e}")

    # ============================================================
    # ضد فحش
    # ============================================================
    if text and not is_user_admin and not text.startswith("/") and not cmd:
        bw_cfg = storage.get("badword", chat_id) or {}
        if bw_cfg.get("enabled"):
            try:
                is_bad, matched = extras.check_bad_word_with_extra(text, chat_id)
                if is_bad:
                    max_warns = bw_cfg.get("max_warns", 3)
                    try:
                        api.delete(chat_id, msg_id)
                    except Exception:
                        pass
                    warns = storage.get("warnings", chat_id) or {}
                    cur = warns.get(str(user_id), 0) + 1
                    warns[str(user_id)] = cur
                    storage.set_("warnings", chat_id, warns)
                    try:
                        ai_persona.note_violation(chat_id, user_id, "badword",
                                                  user_name)
                    except Exception as e:
                        print(f"[persona:badword] {e}")
                    if cur >= max_warns:
                        _fb_bad = (f"🚫 {api.esc_md(user_name)} به دلیل فحش "
                                   f"مکرر بن شد.")
                        try:
                            if ai_panel.feature_on(chat_id, "announce"):
                                ai_persona.announce_punish(
                                    chat_id, "ban", user_id, user_name,
                                    by_name="سیستم ضدفحش", reason="فحش مکرر",
                                    chat_title=chat.get("title", ""),
                                    count=max_warns)
                            else:
                                api.send(chat_id, _fb_bad,
                                         parse_mode="Markdown", reply_to=0)
                        except Exception as e:
                            print(f"[persona:announce-ban] {e}")
                            api.send(chat_id, _fb_bad,
                                     parse_mode="Markdown", reply_to=0)
                        try:
                            from storage import save_banned
                            api.ban(chat_id, user_id)
                            save_banned(chat_id, user_id, user_name)
                        except Exception as e:
                            print(f"[badword:ban] {e}")
                        warns.pop(str(user_id), None)
                        storage.set_("warnings", chat_id, warns)

                        try:
                            notify.notify_punishment(user_id, chat_id, "ban",
                                                     reason="فحش مکرر")
                        except Exception as e:
                            print(f"[badword:notify] {e}")
                    else:
                        api.send_autodelete(chat_id,
                            f"⚠️ {api.esc_md(user_name)} فحش نده. ({cur}/{max_warns})",
                            sec=5, parse_mode="Markdown")
                    return
            except Exception as e:
                print(f"[badword] {e}")

    if not is_bot_msg:
        if not features.is_whitelisted(chat_id, user_id):
            try:
                if antispam.check(chat_id, user_id, text, m, admin.is_admin):
                    return
            except Exception as e:
                print(f"[antispam] {e}")

    if not cmd:
        try:
            if games.handle(chat_id, text, user_name, user_id, msg_id):
                return
        except Exception as e:
            print(f"[game] {e}")

    # ============================================================
    # کلمات ممنوعه
    # ============================================================
    bw = storage.get("banned_words", chat_id) or []
    if bw and not is_user_admin:
        bw_cfg = storage.get("banned_words_config", chat_id) or {}
        try:
            bw_threshold = int(bw_cfg.get("warn_threshold", 3))
        except (TypeError, ValueError):
            bw_threshold = 3
        bw_action = bw_cfg.get("action", "mute_10m")

        for word in bw:
            if word.lower() in text.lower():
                try:
                    api.delete(chat_id, msg_id)
                except Exception:
                    pass

                bw_warns = storage.get("bw_warnings", chat_id) or {}
                uid = str(user_id)
                bw_warns[uid] = bw_warns.get(uid, 0) + 1
                count = bw_warns[uid]
                try:
                    ai_persona.note_violation(chat_id, user_id, "banned_word",
                                              user_name)
                except Exception as e:
                    print(f"[persona:bw] {e}")

                if count >= bw_threshold:
                    bw_warns[uid] = 0
                    storage.set_("bw_warnings", chat_id, bw_warns)

                    perms_mute = {
                        "can_send_messages": False,
                        "can_send_media_messages": False,
                        "can_send_other_messages": False,
                    }

                    if bw_action == "kick":
                        try:
                            api.ban(chat_id, user_id)
                            time.sleep(0.4)
                            api.unban(chat_id, user_id)
                        except Exception:
                            pass
                        try:
                            from storage import save_banned
                            save_banned(chat_id, user_id, user_name)
                        except Exception as e:
                            print(f"[bw:kick:save] {e}")
                        api.send_autodelete(
                            chat_id,
                            f"👢 {api.esc_md(user_name)} به دلیل {bw_threshold} بار کلمات ممنوعه اخراج شد.",
                            sec=6, parse_mode="Markdown")
                        try:
                            notify.notify_punishment(user_id, chat_id, "kick",
                                                     reason="کلمات ممنوعه")
                        except Exception:
                            pass
                    elif bw_action == "ban":
                        try:
                            api.ban(chat_id, user_id)
                        except Exception:
                            pass
                        try:
                            from storage import save_banned
                            save_banned(chat_id, user_id, user_name)
                        except Exception as e:
                            print(f"[bw:ban:save] {e}")
                        api.send_autodelete(
                            chat_id,
                            f"🚫 {api.esc_md(user_name)} به دلیل {bw_threshold} بار کلمات ممنوعه بن شد.",
                            sec=6, parse_mode="Markdown")
                        try:
                            notify.notify_punishment(user_id, chat_id, "ban",
                                                     reason="کلمات ممنوعه")
                        except Exception:
                            pass
                    elif bw_action == "mute_1h":
                        try:
                            api.restrict(chat_id, user_id, perms_mute)
                        except Exception:
                            pass
                        try:
                            locks.add_to_lock_list(chat_id, user_id)
                        except Exception:
                            pass
                        muted = storage.get("muted", chat_id) or {}
                        muted[str(user_id)] = time.time() + 3600
                        storage.set_("muted", chat_id, muted)
                        api.send_autodelete(
                            chat_id,
                            f"🔇 {api.esc_md(user_name)} به دلیل {bw_threshold} بار کلمات ممنوعه یک ساعت سکوت شد.",
                            sec=6, parse_mode="Markdown")
                        try:
                            notify.notify_punishment(user_id, chat_id, "mute",
                                                     duration="۱ ساعت",
                                                     reason="کلمات ممنوعه")
                        except Exception:
                            pass
                    else:
                        try:
                            api.restrict(chat_id, user_id, perms_mute)
                        except Exception:
                            pass
                        try:
                            locks.add_to_lock_list(chat_id, user_id)
                        except Exception:
                            pass
                        muted = storage.get("muted", chat_id) or {}
                        muted[str(user_id)] = time.time() + 600
                        storage.set_("muted", chat_id, muted)
                        api.send_autodelete(
                            chat_id,
                            f"🔇 {api.esc_md(user_name)} به دلیل {bw_threshold} بار کلمات ممنوعه ۱۰ دقیقه سکوت شد.",
                            sec=6, parse_mode="Markdown")
                        try:
                            notify.notify_punishment(user_id, chat_id, "mute",
                                                     duration="۱۰ دقیقه",
                                                     reason="کلمات ممنوعه")
                        except Exception:
                            pass
                else:
                    storage.set_("bw_warnings", chat_id, bw_warns)
                    api.send_autodelete(
                        chat_id,
                        f"🚫 کلمه ممنوعه!\n"
                        f"{api.esc_md(user_name)} جان، این کلمه در گروه ممنوعه.\n"
                        f"هشدار: {count}/{bw_threshold}",
                        sec=5, parse_mode="Markdown")
                return

    try:
        leveled = xp.add_xp(chat_id, user_id, user_name)
        if leveled:
            api.send(chat_id, f"🎉 تبریک {api.esc_md(user_name)}!\nسطح {leveled}",
                     parse_mode="Markdown", reply_to=0)
    except Exception as e:
        print(f"[xp] {e}")

    # 🧠 ثبت فعالیت در پرونده‌ی شخصیت (تاریخ عضویت/درجه/لحن)
    try:
        ai_persona.note_message(chat_id, user_id, user_name)
    except Exception as e:
        print(f"[persona:msg] {e}")

    if not cmd:
        return

    if cmd == "/راهنما":
        api.send(chat_id, HELP, parse_mode="Markdown")
        return

    # ============================================
    # 🧠 هوش مصنوعی — دستیار مدیریت گروه
    # ============================================
    if cmd == "/هوش‌مصنوعی":
        if not is_user_admin:
            api.send(chat_id, "🧠 این بخش فقط برای ادمین‌های گروهه.", reply_to=0)
            return
        ai_panel.cmd_ai_command(chat_id, user_id, user_name, m, args,
                                chat.get("title", ""))
        return

    if cmd == "/کلیدai":
        if user_id != OWNER_ID:
            api.send(chat_id, "👑 فقط مالک ربات.", reply_to=0)
            return
        if not args or not args[0].startswith("sk-"):
            api.send(chat_id,
                     "🔑 فرمت درست: `/کلیدai sk-or-v1-...`\n\n"
                     "کلید را از openrouter.ai/keys بگیر.\n"
                     "می‌تونی از پنل هم بفرستی: `هوش مصنوعی` → 🔑",
                     parse_mode="Markdown", reply_to=0)
            return
        key = args[0]
        ai.set_api_key(key)
        ai.reset_runtime()
        st = ai.status()
        try:
            api.delete(chat_id, msg_id)
        except Exception:
            pass
        api.send(chat_id,
                 f"✅ کلید ذخیره شد.\n🧠 مدل‌های رایگان: `{st['models_total']}`\n"
                 f"برای تست بزن: `/هوش‌مصنوعی تست`",
                 parse_mode="Markdown", reply_to=0)
        return

    if cmd == "/اصل":
        asl_laqab.cmd_asl_request(chat_id, user_id, m, args)
        return

    if cmd == "/لقب":
        if not is_user_admin:
            api.send(chat_id, "فقط ادمین‌ها.", reply_to=0)
            return
        asl_laqab.cmd_laqab(chat_id, user_id, m, args)
        return

    if cmd == "/حذفلقب":
        if not is_user_admin:
            api.send(chat_id, "فقط ادمین‌ها.", reply_to=0)
            return
        asl_laqab.cmd_laqab_remove(chat_id, user_id, m)
        return

    if cmd == "/لیستلقبها":
        if not is_user_admin:
            api.send(chat_id, "فقط ادمین‌ها.", reply_to=0)
            return
        asl_laqab.cmd_laqab_list(chat_id, user_id, m)
        return

    if cmd == "/لیستسیاه":
        t, markup = panels.blacklist_panel(chat_id)
        api.send(chat_id, t, parse_mode="Markdown", markup=markup)
        return

    if cmd == "/کاربران":
        profiles = storage.get("user_profiles", chat_id) or {}

        if not profiles:
            api.send(chat_id,
                "هنوز کسی ثبت نشده.\n\n"
                "کاربرا وقتی ثبت می‌شن که پیام بدن یا ربات رو تو پیوی استارت کنن.",
                parse_mode="Markdown")
            return

        txt = f"👥 کاربران ثبت‌شده ({len(profiles)} نفر)\n\n"
        count = 0
        for uid, info in profiles.items():
            uname = info.get("username", "")
            fname = info.get("first_name", "کاربر")
            if uname:
                txt += (f"• {api.esc_md(fname)} — "
                        f"@{api.esc_md(uname)}\n")
                count += 1
                if count >= 30:
                    txt += f"\nو {len(profiles) - 30} نفر دیگه...\n"
                    break

        if count == 0:
            txt += "هیچ کاربری یوزرنیم نداره."

        api.send(chat_id, txt, parse_mode="Markdown")
        return

    if cmd == "/تگ":
        if args:
            arg_low = args[0].lower().strip()
            mode = "all"
            if arg_low in ("7", "7h", "7ساعت", "هفتساعت"):
                mode = "7"
            elif arg_low in ("24", "24h", "24ساعت", "یکروز", "1d"):
                mode = "24"
            elif arg_low in ("هفته", "week", "7d", "7روز", "یکهفته"):
                mode = "week"
            elif arg_low in ("همه", "all", "allusers"):
                mode = "all"
            admin.tag_users_smart(chat_id, user_id, user_name, mode)
            return

        txt, markup = panels.tag_menu_panel(chat_id)
        r = api.send(chat_id, txt, parse_mode="Markdown", markup=markup)
        if r and r.get("ok"):
            panels.register_panel_opener(chat_id, r["result"]["message_id"], user_id)
        return

    # ✅ /پنل تو گروه → کاربر ساده: پنل کاربری، ادمین: پنل مدیریت
    if cmd == "/پنل":
        try:
            if is_user_admin and bot_is_admin:
                t, markup = panels.main_panel(chat_id)
            else:
                t, markup = user_panels.user_main_panel(chat_id, user_id)
            r = api.send(chat_id, t, parse_mode="Markdown", markup=markup, reply_to=msg_id)
            if r and r.get("ok"):
                panels.register_panel_opener(chat_id, r["result"]["message_id"], user_id)
        except Exception as e:
            print(f"[panel] {e}")
        return

    # ✅ /سرگرمی تو گروه → کاربر ساده: بازی‌های کاربر، ادمین: پنل ادمین
    if cmd == "/سرگرمی":
        try:
            if is_user_admin and bot_is_admin:
                t, markup = panels.entertainment_panel(chat_id)
            else:
                t, markup = user_panels.user_entertainment_panel(chat_id)
            r = api.send(chat_id, t, parse_mode="Markdown", markup=markup, reply_to=msg_id)
            if r and r.get("ok"):
                panels.register_panel_opener(chat_id, r["result"]["message_id"], user_id)
        except Exception as e:
            print(f"[ent_panel] {e}")
        return

    if cmd == "/گیف":
        if not m.get("reply_to_message"):
            api.send(chat_id, "روی عکس یا گیف ریپلای کن و بعد گیف بفرست.",
                     reply_to=0)
            return
        gifmaker.start_flow(chat_id, user_id, m["reply_to_message"], msg_id)
        return

    if cmd == "/ضدفحش":
        t, markup = panels.badword_panel(chat_id)
        api.send(chat_id, t, parse_mode="Markdown", markup=markup)
        return

    if cmd == "/بازی":
        if not args:
            try:
                if is_user_admin and bot_is_admin:
                    t, markup = panels.entertainment_panel(chat_id)
                else:
                    t, markup = user_panels.user_entertainment_panel(chat_id)
                r = api.send(chat_id, t, parse_mode="Markdown", markup=markup, reply_to=msg_id)
                if r and r.get("ok"):
                    panels.register_panel_opener(chat_id, r["result"]["message_id"], user_id)
            except Exception as e:
                print(f"[ent_panel] {e}")
            return
        gt = args[0].lower()
        if gt in ("guess", "عدد"):
            games.cmd_guess(chat_id)
        elif gt in ("word", "کلمه"):
            games.cmd_word(chat_id)
        elif gt in ("scramble", "حروف"):
            games.cmd_scramble(chat_id)
        elif gt in ("doss", "دوز"):
            games.cmd_doss(chat_id, user_id, user_name)
        else:
            api.send(chat_id, "❌")
        return

    if cmd == "/دوز":
        games.cmd_doss(chat_id, user_id, user_name)
        return

    if cmd == "/پایانبازی" or cmd == "/توقف":
        games.stop(chat_id)
        multiplayer.BETWEEN_GAMES.pop(chat_id, None)
        doss.DOSS_GAMES.pop(chat_id, None)
        api.send(chat_id, "متوقف شد.")
        return
    if cmd == "/تاس":
        games.cmd_dice(chat_id, msg_id, user_name)
        return
    if cmd == "/شیرخط":
        games.cmd_coin(chat_id, msg_id, user_name)
        return
    if cmd == "/جوک":
        games.cmd_joke(chat_id, user_id, user_name, msg_id)
        return
    if cmd == "/جرئتحقیقت":
        games.cmd_tod_panel(chat_id, user_id, user_name, "bot")
        return
    if cmd == "/مافیا":
        games.cmd_mafia_start(chat_id, user_id, user_name)
        return
    if cmd == "/سنگکاغذقیچی":
        games.cmd_rps(chat_id)
        return

    if cmd == "/گزارشباگ":
        settings["wait_bug_report"] = user_id
        settings["prompt_msg_id"] = msg_id
        settings["prompt_back"] = "panel:main"
        storage.set_("settings", chat_id, settings)
        api.send(chat_id,
            "🐛 گزارش باگ\nمتن گزارش رو بفرست:\n\nبرای لغو بنویس: لغو",
            parse_mode="Markdown", reply_to=msg_id)
        return

    if cmd == "/آیدی":
        t = admin.get_target(m, chat_id)
        if not t:
            t = user
        tid = t["id"]
        from xp import get_user
        udata = get_user(chat_id, tid)
        warns = (storage.get("warnings", chat_id) or {}).get(str(tid), 0)
        is_banned = str(tid) in (storage.get("banned_users", chat_id) or {})
        is_muted = str(tid) in (storage.get("muted", chat_id) or {})
        txt, markup = panels.user_info_panel(
            chat_id, t, udata, warns, is_banned, is_muted
        )
        api.send(chat_id, txt, parse_mode="HTML", reply_to=0, markup=markup)
        return

    if cmd == "/زمان":
        user_module.cmd_time(chat_id, user_id, m)
        return
    if cmd == "/حساب":
        user_module.cmd_calc(chat_id, user_id, m, args)
        return
    if cmd == "/ذخیره":
        user_module.cmd_save(chat_id, user_id, m, args)
        return
    if cmd == "/بگیر":
        user_module.cmd_get(chat_id, user_id, m, args)
        return
    if cmd == "/امتیازمن":
        user_module.cmd_myxp(chat_id, user_id, m)
        return
    if cmd == "/گزارش":
        user_module.cmd_report(chat_id, user_id, m, user_name)
        return

    if cmd == "/اطلاعات":
        t = admin.get_target(m, chat_id)
        if not t:
            t = user
        tid = t["id"]
        from xp import get_user
        udata = get_user(chat_id, tid)
        warns = (storage.get("warnings", chat_id) or {}).get(str(tid), 0)
        is_banned = str(tid) in (storage.get("banned_users", chat_id) or {})
        is_muted = str(tid) in (storage.get("muted", chat_id) or {})
        txt, markup = panels.user_info_panel(
            chat_id, t, udata, warns, is_banned, is_muted
        )
        api.send(chat_id, txt, parse_mode="HTML", reply_to=0, markup=markup)
        return

    if cmd == "/لیدربرد":
        if args:
            arg_text = " ".join(args).lower()
            game_key = None
            if "حدس" in arg_text and "عدد" in arg_text:
                game_key = "guess"
            elif "حدس" in arg_text and "کلمه" in arg_text:
                game_key = "word"
            elif "حروف" in arg_text or "بهم" in arg_text:
                game_key = "scramble"
            elif "سنگ" in arg_text or "کاغذ" in arg_text or "قیچی" in arg_text:
                game_key = "rps"
            elif "جوک" in arg_text:
                game_key = "joke"
            elif "حقیقت" in arg_text:
                game_key = "truth"
            elif "جرئت" in arg_text:
                game_key = "dare"
            elif "آزمون" in arg_text:
                game_key = "quiz"
            elif "دوز" in arg_text:
                game_key = "doss"
            games.cmd_leaderboard(chat_id, game_key)
        else:
            games.cmd_leaderboard(chat_id, None)
        return

    if cmd == "/آزمون":
        ok, msg_txt = extras.start_quiz(chat_id, user_id, user_name)
        if not ok:
            api.send(chat_id, msg_txt)
        return
    if cmd == "/لیدرآزمون":
        txt = extras.get_quiz_leaderboard(chat_id)
        api.send(chat_id, txt, parse_mode="Markdown")
        return

    if cmd == "/قرعهکشی":
        count = 1
        if args:
            try:
                count = int(args[0])
                if count < 1:
                    count = 1
                if count > 10:
                    count = 10
            except Exception:
                count = 1
        winners, err = extras.draw_lottery(chat_id, user_id, user_name, count)
        if err:
            api.send(chat_id, err)
            return
        bot_users = storage.get("bot_users", "list") or {}
        xp_data = storage.get("xp", chat_id) or {}
        txt = f"🎁 قرعه‌کشی\n{len(winners)} برنده:\n\n"
        for i, uid in enumerate(winners, 1):
            name = xp_data.get(uid, {}).get("name", "") or bot_users.get(uid, {}).get("name", f"کاربر")
            crown = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, "🎯")
            txt += f"{crown} {name}\n"
        api.send(chat_id, txt, parse_mode="Markdown")
        return

    if cmd == "/رتبه":
        txt = extras.get_weekly_ranking(chat_id)
        api.send(chat_id, txt, parse_mode="Markdown")
        return
    if cmd == "/رتبهماهانه":
        txt = extras.get_monthly_ranking(chat_id)
        api.send(chat_id, txt, parse_mode="Markdown")
        return
    if cmd == "/دعوتها":
        txt = extras.get_user_invites(chat_id, user_id)
        api.send(chat_id, txt, parse_mode="Markdown")
        return
    if cmd == "/لیدردعوت":
        txt = extras.get_invite_leaderboard(chat_id)
        api.send(chat_id, txt, parse_mode="Markdown")
        return

    if cmd == "/قوانین":
        r = storage.get("rules", chat_id) or {}
        api.send(chat_id,
                 f"📜 قوانین:\n\n{api.esc_md(r.get('text') or 'تنظیم نشده')}",
                 parse_mode="Markdown")
        return

    if cmd == "/یادداشتها":
        t, markup = panels.notes_panel(chat_id)
        r = api.send(chat_id, t, parse_mode="Markdown", markup=markup)
        if r and r.get("ok"):
            st = storage.get("settings", chat_id) or {}
            st["notes_panel_msg"] = r["result"]["message_id"]
            storage.set_("settings", chat_id, st)
        return

    if cmd == "/آهسته":
        if not args:
            t, markup = panels.slowmode_panel(chat_id)
            api.send(chat_id, t, parse_mode="Markdown", markup=markup)
            return

        a = args[0].lower()
        if a in ("خاموش", "off", "0", "صفر"):
            storage.set_("slowmode", chat_id, {"seconds": 0})
            reset_slowmode_cache(chat_id)
            api.send(chat_id, "حالت آهسته خاموش شد.", reply_to=0)
            return

        sec = None
        try:
            if a.endswith("s"):
                sec = int(a[:-1])
            elif a.endswith("m"):
                sec = int(a[:-1]) * 60
            elif a.endswith("h"):
                sec = int(a[:-1]) * 3600
            else:
                sec = int(a) * 60
        except Exception:
            sec = None

        if sec is None or sec < 0:
            api.send(chat_id,
                "❌ فرمت اشتباه\n\n"
                "مثال:\n"
                "• آهسته 5 → ۵ ثانیه\n"
                "• آهسته 10m → ۱۰ دقیقه\n"
                "• آهسته 1h → ۱ ساعت\n"
                "• آهسته خاموش",
                reply_to=0)
            return

        storage.set_("slowmode", chat_id, {"seconds": sec})
        reset_slowmode_cache(chat_id)

        if sec < 60:
            t = f"{sec} ثانیه"
        elif sec < 3600:
            t = f"{sec // 60} دقیقه"
        else:
            t = f"{sec // 3600} ساعت"

        api.send(chat_id, f"⏱ حالت آهسته {t} فعال شد.\nتوسط: {user_name}",
                 reply_to=0)
        return

    if cmd == "/عضویت":
        t, markup = panels.group_join_panel(chat_id)
        api.send(chat_id, t, parse_mode="Markdown", markup=markup)
        return

    if cmd == "/حالتشب":
        if args:
            a = args[0].lower()
            if a in ("روشن", "on", "فعال", "true", "1"):
                features.set_night_mode(chat_id, enabled=True)
                api.send(chat_id, f"🌙 حالت شب روشن شد.\nتوسط: {user_name}")
                return
            elif a in ("خاموش", "off", "غیرفعال", "false", "0"):
                features.set_night_mode(chat_id, enabled=False)
                api.send(chat_id, f"🌙 حالت شب خاموش شد.\nتوسط: {user_name}")
                return
        t, markup = panels.night_mode_panel(chat_id)
        api.send(chat_id, t, parse_mode="Markdown", markup=markup)
        return

    if cmd == "/حالتخواب":
        if args:
            a = args[0].lower()
            if a in ("روشن", "on", "فعال", "true", "1"):
                features.set_sleep_mode_enabled(chat_id, True)
                api.send(chat_id, f"😴 حالت خواب روشن شد.\nتوسط: {user_name}")
                return
            elif a in ("خاموش", "off", "غیرفعال", "false", "0"):
                features.set_sleep_mode_enabled(chat_id, False)
                api.send(chat_id, f"😴 حالت خواب خاموش شد.\nتوسط: {user_name}")
                return
        t, markup = panels.sleep_mode_panel(chat_id)
        api.send(chat_id, t, parse_mode="Markdown", markup=markup)
        return

    if cmd == "/سفیدلیست":
        t, markup = panels.whitelist_panel(chat_id)
        api.send(chat_id, t, parse_mode="Markdown", markup=markup)
        return

    if cmd == "/دستوراتسفارشی":
        t, markup = panels.custom_cmds_panel(chat_id)
        api.send(chat_id, t, parse_mode="Markdown", markup=markup)
        return

    if cmd == "/برترینامروز":
        items = features.get_top_today(chat_id, 10)
        if not items:
            api.send(chat_id, "امروز کسی پیام نداده.")
            return
        xp_data = storage.get("xp", chat_id) or {}
        txt = "🏆 برترین‌های امروز:\n\n"
        for i, (uid, cnt) in enumerate(items, 1):
            medals = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")
            display_name = xp_data.get(uid, {}).get("name", "") or f"کاربر {str(uid)[-4:]}"
            txt += f"{medals} {api.esc_md(display_name)} — {cnt} پیام\n"
        api.send(chat_id, txt, parse_mode="Markdown")
        return

    if cmd == "/پاکسازی":
        if not args:
            api.send(chat_id, "مثال: پاکسازی 20")
            return
        try:
            n = int(args[0])
            if n > 100:
                n = 100
            count = 0
            for i in range(msg_id, msg_id - n - 1, -1):
                if i <= 0:
                    break
                r = api.delete(chat_id, i)
                if r and r.get("ok"):
                    count += 1
            api.send(chat_id, f"🧹 {count} پیام پاک شد.")
        except Exception:
            api.send(chat_id, "❌")
        return

    if cmd == "/گزارشهفتگیروشن":
        extras.set_weekly_report(chat_id, True)
        api.send(chat_id, "روشن شد.")
        return
    if cmd == "/گزارشهفتگیخاموش":
        extras.set_weekly_report(chat_id, False)
        api.send(chat_id, "خاموش شد.")
        return
    if cmd == "/گزارشهفتگی":
        txt = extras.build_weekly_report(chat_id)
        api.send(chat_id, txt, parse_mode="Markdown")
        return

    if cmd == "/ارتقا":
        if not admin.is_creator(chat_id, user_id):
            api.send(chat_id, "فقط مالک.", reply_to=msg_id)
            return
        admin.cmd_promote(chat_id, user_id, m, args)
        return

    if cmd == "/تنزل":
        if not admin.is_creator(chat_id, user_id):
            api.send(chat_id, "فقط مالک.", reply_to=msg_id)
            return
        admin.cmd_demote(chat_id, user_id, m)
        return

    if cmd == "/مدیریت":
        t = admin.get_target(m, chat_id)
        if not t:
            api.send(chat_id, "ریپلای کن یا با @یوزرنیم تگ کن.\nمثال: مدیریت @ali",
                     reply_to=msg_id)
            return
        if admin.is_admin(chat_id, t["id"]):
            api.send(chat_id, "ادمینه.", reply_to=msg_id)
            return
        tmsg, markup = panels.user_manage_panel(chat_id, t["id"], admin.u_name(t))
        api.send(chat_id, tmsg, parse_mode="Markdown", markup=markup)
        return

    ADMIN_CMDS = {
        "/قفل", "/بازکردن", "/قفلها",
        "/ضداسپم", "/خوشآمد", "/قوانینتنظیم",
        "/کلمهممنوعه", "/حذفکلمه", "/لیستکلمات",
        "/ریست", "/آمار",
        "/اخطار", "/حذفاخطار", "/اخطارها",
        "/سکوت", "/آزاد",
        "/بن", "/آنبن", "/اخراج",
        "/حذف", "/سنجاق", "/برداشتنسنجاق",
        "/لیستسیاه",
    }

    if cmd in ADMIN_CMDS:
        if cmd == "/قفل":
            admin.cmd_lock(chat_id, user_id, args)
            return
        if cmd == "/بازکردن":
            admin.cmd_unlock(chat_id, user_id, args)
            return
        if cmd == "/قفلها":
            t, markup = panels.locks_panel(chat_id)
            api.send(chat_id, t, parse_mode="Markdown", markup=markup)
            return
        if cmd == "/ضداسپم":
            if not args:
                t, markup = panels.antispam_panel(chat_id)
                api.send(chat_id, t, parse_mode="Markdown", markup=markup)
                return
            admin.cmd_antispam(chat_id, user_id, args)
            return
        if cmd == "/خوشآمد":
            t, markup = panels.welcome_panel(chat_id)
            api.send(chat_id, t, parse_mode="Markdown", markup=markup)
            return
        if cmd == "/قوانینتنظیم":
            if not args:
                api.send(chat_id, "مثال: قوانین تنظیم متن")
                return
            admin.cmd_setrules(chat_id, user_id, m, args)
            return
        if cmd == "/کلمهممنوعه":
            if not args:
                t, markup = panels.words_panel(chat_id)
                api.send(chat_id, t, parse_mode="Markdown", markup=markup)
                return
            admin.cmd_addword(chat_id, user_id, args)
            return
        if cmd == "/حذفکلمه":
            admin.cmd_delword(chat_id, user_id, args)
            return
        if cmd == "/لیستکلمات":
            t, markup = panels.words_panel(chat_id)
            api.send(chat_id, t, parse_mode="Markdown", markup=markup)
            return
        if cmd == "/ریست":
            admin.cmd_reset(chat_id, user_id, args)
            return
        if cmd == "/آمار":
            try:
                extras.send_stats_chart(chat_id)
            except Exception as e:
                print(f"[stats_chart] {e}")
            return
        if cmd == "/اخطار":
            if not admin.get_target(m, chat_id):
                api.send(chat_id, "ریپلای یا @یوزرنیم.", reply_to=msg_id)
                return
            admin.cmd_warn(chat_id, user_id, m)
            return
        if cmd == "/حذفاخطار":
            admin.cmd_unwarn(chat_id, user_id, m)
            return
        if cmd == "/اخطارها":
            admin.cmd_warns(chat_id, user_id, m)
            return
        if cmd == "/سکوت":
            t = admin.get_target(m, chat_id)
            if not t:
                admin._send_user_not_found(chat_id, m,
                                            action_verb="سکوت",
                                            action_hint="سکوت @ali 10m")
                return

            duration_args = [a for a in args if not a.startswith("@")]

            if duration_args:
                admin.cmd_mute(chat_id, user_id, m, duration_args)
            else:
                txt, markup = panels.mute_duration_panel(chat_id, t["id"])
                r = api.send(chat_id, txt, parse_mode="Markdown", markup=markup)
                if r and r.get("ok"):
                    panels.register_panel_opener(chat_id, r["result"]["message_id"], user_id)
            return
        if cmd == "/آزاد":
            admin.cmd_unmute(chat_id, user_id, m)
            return
        if cmd == "/بن":
            admin.cmd_ban(chat_id, user_id, m)
            return
        if cmd == "/آنبن":
            admin.cmd_unban(chat_id, user_id, m)
            return
        if cmd == "/اخراج":
            admin.cmd_kick(chat_id, user_id, m)
            return
        if cmd == "/حذف":
            admin.cmd_del(chat_id, user_id, m)
            return
        if cmd == "/سنجاق":
            admin.cmd_pin(chat_id, user_id, m)
            return
        if cmd == "/برداشتنسنجاق":
            admin.cmd_unpin(chat_id, user_id, m)
            return
        if cmd == "/لیستسیاه":
            t, markup = panels.blacklist_panel(chat_id)
            api.send(chat_id, t, parse_mode="Markdown", markup=markup)
            return


def setup_channel(chat_id, channel_input):
    channel_input = channel_input.strip()
    username = channel_input
    if "ble.ir/" in channel_input or "t.me/" in channel_input:
        parts = channel_input.rstrip("/").split("/")
        username = "@" + parts[-1] if parts[-1] else channel_input
    elif channel_input.startswith("-") or channel_input.lstrip("-").isdigit():
        username = channel_input
    elif not channel_input.startswith("@"):
        username = "@" + channel_input

    r = api.get_chat(username)
    if not r or not r.get("ok"):
        api.send(chat_id, "کانال پیدا نشد.")
        return

    info = r["result"]
    display = info.get("title", username)
    ch_id = info.get("id", username)
    link = info.get("invite_link", "")
    if not link and info.get("username"):
        link = f"https://ble.ir/{info['username']}"

    bot_id = api.bot_id()
    is_bot_admin_in_channel = False
    try:
        ac = api.get_member(ch_id, bot_id)
        if ac and ac.get("ok"):
            st = ac["result"].get("status", "")
            is_bot_admin_in_channel = st in ("administrator", "creator")
    except Exception:
        pass

    fj = {"enabled": True, "channel": username, "channel_id": ch_id,
          "channel_display": display, "channel_link": link or "",
          "bot_is_admin": is_bot_admin_in_channel}
    storage.set_("force_join", "global", fj)
    api.send(chat_id, f"✅ تنظیم شد.\n📢 {display}")


def setup_group_channel(chat_id, channel_input):
    channel_input = channel_input.strip()
    username = channel_input
    if "ble.ir/" in channel_input or "t.me/" in channel_input:
        parts = channel_input.rstrip("/").split("/")
        username = "@" + parts[-1] if parts[-1] else channel_input
    elif channel_input.startswith("-") or channel_input.lstrip("-").isdigit():
        username = channel_input
    elif not channel_input.startswith("@"):
        username = "@" + channel_input

    r = api.get_chat(username)
    if not r or not r.get("ok"):
        api.send(chat_id, "کانال پیدا نشد.")
        return

    info = r["result"]
    display = info.get("title", username)
    ch_id = info.get("id", username)
    link = info.get("invite_link", "")
    if not link and info.get("username"):
        link = f"https://ble.ir/{info['username']}"

    gj = {"enabled": True, "channel": username, "channel_id": ch_id,
          "channel_display": display, "channel_link": link or ""}
    storage.set_("group_join", chat_id, gj)
    api.send(chat_id, "✅ تنظیم شد.")


def _get_broadcast_targets(target):
    users = storage.get("bot_users", "list") or {}
    admins = storage.get("bot_admins", "list") or {}
    groups = storage.get("bot_groups", "list") or {}
    owner = panels.get_owner_id()

    private_targets = []
    group_targets = []

    if target == "admins":
        ids = list(admins.keys())
        if str(owner) not in ids:
            ids.append(str(owner))
        private_targets = ids
    elif target == "private":
        private_targets = list(users.keys())
    elif target == "groups":
        group_targets = list(groups.keys())
    elif target == "both":
        private_targets = list(users.keys())
        group_targets = list(groups.keys())
    else:
        private_targets = list(users.keys())

    return private_targets, group_targets


def send_broadcast(chat_id, user_id, text, target):
    api.clear_reply_context()
    private_targets, group_targets = _get_broadcast_targets(target)

    sent = 0
    failed = 0

    for uid in private_targets:
        try:
            r = api.send(int(uid), text, parse_mode="Markdown", reply_to=0)
            if r and r.get("ok"):
                sent += 1
            else:
                failed += 1
            time.sleep(0.05)
        except Exception:
            failed += 1

    for gid in group_targets:
        try:
            r = api.send(int(gid), text, parse_mode="Markdown", reply_to=0)
            if r and r.get("ok"):
                sent += 1
            else:
                failed += 1
            time.sleep(0.05)
        except Exception:
            failed += 1

    api.send(chat_id,
        f"✅ موفق: {sent}\n❌ ناموفق: {failed}",
        parse_mode="Markdown")


def send_broadcast_forward(chat_id, user_id, from_chat_id, message_id, target):
    api.clear_reply_context()
    private_targets, group_targets = _get_broadcast_targets(target)

    sent = 0
    failed = 0
    errors = []

    for uid in private_targets:
        try:
            r = api.forward_message(int(uid), from_chat_id, message_id)
            if r and r.get("ok"):
                sent += 1
            else:
                failed += 1
                if len(errors) < 5:
                    errors.append(f"پیوی {uid}: [{(r or {}).get('error_code','?')}] {(r or {}).get('description','?')}")
            time.sleep(0.05)
        except Exception as e:
            failed += 1
            if len(errors) < 5:
                errors.append(f"پیوی {uid}: {e}")

    for gid in group_targets:
        try:
            r = api.forward_message(int(gid), from_chat_id, message_id)
            if r and r.get("ok"):
                sent += 1
            else:
                failed += 1
                if len(errors) < 5:
                    errors.append(f"گروه {gid}: [{(r or {}).get('error_code','?')}] {(r or {}).get('description','?')}")
            time.sleep(0.05)
        except Exception as e:
            failed += 1
            if len(errors) < 5:
                errors.append(f"گروه {gid}: {e}")

    result_txt = (
        f"📨 نتیجه فوروارد:\n"
        f"✅ موفق: {sent}\n"
        f"❌ ناموفق: {failed}"
    )

    if errors:
        result_txt += "\n\n🔍 نمونه خطاها:\n"
        for e in errors[:5]:
            result_txt += f"• {api.esc_md(str(e))}\n"

    api.send(chat_id, result_txt, parse_mode="Markdown")


def _poll_loop(plat):
    """حلقه‌ی long-polling یک پیام‌رسان (هر پلتفرم نخ خودش)."""
    name = plat.key
    offset = 0
    err = 0
    while True:
        try:
            r = plat.get_updates(offset=offset + 1, timeout=30)
            if r and r.get("ok") and r.get("result"):
                for raw in r["result"]:
                    try:
                        uid = raw.get("update_id")
                        if isinstance(uid, int) and uid > offset:
                            offset = uid
                        upd = plat.normalize(raw)
                        if not upd:
                            continue
                        handle(upd, name)
                    except Exception as e:
                        print(f"[handle:{name}] {e}")
                err = 0
            elif r and not r.get("ok"):
                err += 1
                time.sleep(min(err * 2, 20))
            time.sleep(0.3)
        except KeyboardInterrupt:
            raise
        except Exception as e:
            err += 1
            print(f"[poll:{name}] {e}")
            time.sleep(min(err * 5, 30))


def main():
    print("=" * 50)
    print("🏆 مدیریت گروه آلفا روشن شد!")
    print("=" * 50)

    plats = platforms.enabled()

    # ------------------------------------------------------------
    # وب‌سرور (Render / health-check / webhook) — همیشه اول بالا بیاید
    # تا اگر تنظیمات ناقص بود، بتوانی از /healthz علت را ببینی
    # ------------------------------------------------------------
    import server
    server.set_handler(handle)
    if config.web_server_enabled():
        server.start(config.port())
    else:
        print("ℹ️  وب‌سرور خاموش است (برای روشن‌کردن: متغیر PORT را ست کن)")

    if not plats:
        print(config.token_hint())
        if config.web_server_enabled():
            print("⏳ سرور بالا است ولی هیچ پیام‌رسانی وصل نشد — "
                  "وضعیت: /healthz")
            while True:
                time.sleep(3600)
        return

    for plat in plats:
        hint = ", ".join(plat.token_envs) or "—"
        print(f"📡 پیام‌رسان فعال: {plat.title} ({plat.key}) — توکن از {hint}")
    if len(plats) > 1:
        print(f"🔀 حالت چند-پیام‌رسانی: {', '.join(p.key for p in plats)}")

    if ai.enabled():
        if ai.api_key():
            print("🧠 موتور هوش مصنوعی: روشن (OpenRouter)"
                  + (" — کلید از env" if os.environ.get("OPENROUTER_API_KEY")
                     else " — کلید از پنل"))
        else:
            print("🧠 هوش مصنوعی روشن است ولی کلید OpenRouter تنظیم نشده.")
            print("   کلید را در Environment بگذار: OPENROUTER_API_KEY")
            print("   یا در پیوی ربات: پنل → 🧠 هوش مصنوعی → 🔑")

    storage.load()

    # ------------------------------------------------------------
    # اتصال و polling
    # ------------------------------------------------------------
    pollers = []
    for plat in plats:
        if plat.webhook_based:
            print(f"🔗 {plat.title}: از راه وب‌هوک (/webhook/{plat.key})")
            continue
        who = plat.me()
        if not who:
            print(f"❌ اتصال به {plat.title} برقرار نشد (توکن یا شبکه).")
            continue
        uname = f" (@{who.get('username')})" if who.get("username") else ""
        print(f"✅ متصل به {plat.title}{uname} — شناسه: {who.get('id')}")
        pollers.append(plat)

    if not pollers:
        print("❌ هیچ پیام‌رسان قابل pollingی وصل نشد.")
        if config.web_server_enabled():
            print("⏳ سرور بالا می‌ماند تا از /healthz علت را ببینی "
                  "(توکن/شبکه را چک کن).")
            while True:
                time.sleep(3600)
        return

    threads = []
    for plat in pollers[1:]:
        t = threading.Thread(target=_poll_loop, args=(plat,), daemon=True,
                             name=f"poll-{plat.key}")
        t.start()
        threads.append(t)

    try:
        _poll_loop(pollers[0])          # نخ اصلی
    except KeyboardInterrupt:
        print("\n⛔️ متوقف شد.")
        storage.save()


if __name__ == "__main__":
    main()