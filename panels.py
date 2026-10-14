# -*- coding: utf-8 -*-
import time
import html
import threading
import api
import storage
from storage import get, set_, update, remove
from config import OWNER_ID
import locks as lock_mod
import features
import games
import extras


ITEMS_PER_PAGE = 15
EDIT_DELAY = 0.3


def kb(rows):
    return {"inline_keyboard": [r for r in rows if r]}


def btn(text, data=None, url=None):
    if url:
        return {"text": text, "url": url}
    return {"text": text, "callback_data": data}


def _edit(chat_id, msg_id, text, markup=None, parse_mode="Markdown"):
    try:
        time.sleep(EDIT_DELAY)
        return api.edit_message(chat_id, msg_id, text, markup=markup, parse_mode=parse_mode)
    except Exception as e:
        print(f"[edit] {e}")
        return None


def _prompt(title, body="", hint="", back="panel:main", cancel=None):
    rows = []
    if cancel:
        rows.append([btn("❌ لغو", cancel)])
    if back:
        rows.append([btn("🔙 برگشت", back)])
    text = title
    if body:
        text += "\n\n" + body
    if hint:
        text += "\n\n" + hint
    return text, kb(rows)


# ============================================================
# مدیریت پنل
# ============================================================
def register_panel_opener(chat_id, msg_id, user_id):
    owners = storage.get("panel_owners", "list") or {}
    owners[f"{chat_id}:{msg_id}"] = user_id
    if len(owners) > 1000:
        for k in list(owners.keys())[:300]:
            owners.pop(k, None)
    set_("panel_owners", "list", owners)


def get_panel_opener(chat_id, msg_id):
    owners = storage.get("panel_owners", "list") or {}
    return owners.get(f"{chat_id}:{msg_id}")


def check_panel_access(chat_id, msg_id, user_id):
    opener = get_panel_opener(chat_id, msg_id)
    if opener is None:
        return True
    return opener == user_id


# ============================================================
# ادمین ربات
# ============================================================
def get_owner_id():
    if OWNER_ID and OWNER_ID != 0:
        return OWNER_ID
    o = storage.get("bot_owner", "id")
    if isinstance(o, dict):
        return o.get("id", 0)
    return 0


def set_owner(user_id):
    set_("bot_owner", "id", {"id": user_id})


def is_bot_owner(user_id):
    return get_owner_id() == user_id


def is_bot_admin(user_id):
    if is_bot_owner(user_id):
        return True
    admins = storage.get("bot_admins", "list") or {}
    return str(user_id) in admins


def add_bot_admin(user_id, name):
    admins = storage.get("bot_admins", "list") or {}
    admins[str(user_id)] = name
    set_("bot_admins", "list", admins)


def remove_bot_admin(user_id):
    admins = storage.get("bot_admins", "list") or {}
    admins.pop(str(user_id), None)
    set_("bot_admins", "list", admins)


def register_user(user):
    uid = str(user["id"])
    users = storage.get("bot_users", "list") or {}
    if uid not in users:
        from datetime import datetime
        users[uid] = {
            "name": user.get("first_name", "کاربر"),
            "username": user.get("username", ""),
            "first_seen": datetime.now().strftime("%Y-%m-%d"),
        }
        set_("bot_users", "list", users)
    elif user.get("username") and users[uid].get("username") != user.get("username"):
        users[uid]["username"] = user["username"]
        set_("bot_users", "list", users)


# ============================================================
# عضویت اجباری
# ============================================================
def get_force_join():
    return storage.get("force_join", "global") or {}


def check_force_join(user_id):
    fj = get_force_join()
    if not fj.get("enabled"):
        return True
    ch = fj.get("channel_id") or fj.get("channel")
    if not ch:
        return True
    try:
        r = api.get_member(ch, user_id)
        if r and r.get("ok"):
            st = r.get("result", {}).get("status", "")
            return st in ("member", "administrator", "creator", "restricted")
        return False
    except Exception:
        return False


def get_group_join(chat_id):
    return storage.get("group_join", chat_id) or {}


def check_group_join(chat_id, user_id):
    gj = get_group_join(chat_id)
    if not gj.get("enabled"):
        return True
    ch = gj.get("channel_id") or gj.get("channel")
    if not ch:
        return True

    cache_key = f"jc:{chat_id}:{user_id}"
    cache = storage.get("join_cache", "list") or {}
    now = time.time()
    cached = cache.get(cache_key)
    if cached:
        try:
            val, ts = cached
            if now - ts < 300:
                return val
        except Exception:
            pass

    try:
        r = api.get_member(ch, user_id)
        if r and r.get("ok"):
            st = r.get("result", {}).get("status", "")
            result = st in ("member", "administrator", "creator", "restricted")
            cache[cache_key] = (result, now)
            if len(cache) > 1000:
                keys = sorted(cache.keys(),
                              key=lambda k: cache[k][1] if isinstance(cache[k], (list, tuple)) else 0)
                for k in keys[:500]:
                    cache.pop(k, None)
            storage.set_("join_cache", "list", cache)
            return result
        return False
    except Exception:
        return False


def invalidate_join_cache(chat_id, user_id=None):
    cache = storage.get("join_cache", "list") or {}
    if user_id:
        cache.pop(f"jc:{chat_id}:{user_id}", None)
    else:
        for k in list(cache.keys()):
            if k.startswith(f"jc:{chat_id}:"):
                cache.pop(k, None)
    storage.set_("join_cache", "list", cache)


def group_join_panel(chat_id):
    gj = get_group_join(chat_id)
    enabled = gj.get("enabled", False)
    ch = gj.get("channel_display", "تنظیم نشده")
    link = gj.get("channel_link", "")

    rows = [
        [btn(f"{'🟢 روشن' if enabled else '🔴 خاموش'}", "gj:toggle")],
        [btn("✏️ تغییر کانال", "gj:set")],
        [btn("🗑 حذف کانال", "gj:clear")],
        [btn("🔙 برگشت", "panel:main")],
    ]
    text = (
        f"📢 عضویت اجباری\n\n"
        f"وضعیت: {'روشن' if enabled else 'خاموش'}\n"
        f"کانال: {ch}\n"
        f"لینک: {link or 'نداره'}\n\n"
        f"وقتی روشن باشه، کاربرا باید اول تو کانال عضو بشن."
    )
    return text, kb(rows)


def build_group_join_message(chat_id, user_id, user_name, warn_count=0):
    gj = get_group_join(chat_id)
    ch_name = gj.get("channel_display", "کانال")
    ch_link = gj.get("channel_link", "")

    rows = []
    if ch_link:
        rows.append([btn(f"📢 عضویت در {ch_name}", url=ch_link)])
    else:
        rows.append([btn(f"📢 عضویت در {ch_name}", url="https://ble.ir")])
    rows.append([btn("✅ عضو شدم", f"gj:check:{user_id}")])

    text = (
        f"سلام {api.esc_md(user_name)} 👋\n\n"
        f"برای اینکه بتونی تو گروه پیام بذاری، "
        f"اول باید تو کانال زیر عضو بشی:\n\n"
        f"📢 {ch_name}\n\n"
        f"بعد از عضویت، دکمه زیر رو بزن."
    )
    return text, kb(rows)


# ============================================================
# پنل مالک
# ============================================================
def owner_main_panel(user_id):
    if not is_bot_admin(user_id):
        return None, None

    fj = get_force_join()
    fj_on = fj.get("enabled", False)
    fj_ch = fj.get("channel_display", "تنظیم نشده")
    admins = storage.get("bot_admins", "list") or {}
    users = storage.get("bot_users", "list") or {}
    groups = storage.get("bot_groups", "list") or {}
    role = "مالک" if is_bot_owner(user_id) else "ادمین ربات"

    rows = [
        [btn(f"📢 عضویت اجباری {'🟢' if fj_on else '🔴'}", "owner:fj")],
        [btn(f"👑 ادمین‌های ربات ({len(admins)})", "owner:admins")],
        [btn("📢 پیام همگانی", "owner:broadcast")],
        [btn("🎬 گیف ساز", "gif:start")],
        [btn("📊 آمار ربات", "owner:stats")],
        [btn("🧠 هوش مصنوعی", "ai:main")],
        [btn("📖 راهنمای دستورات", "start:help_full")],
        [btn("❌ بستن", "owner:close")],
    ]

    text = (
        f"پنل {role} ربات\n\n"
        f"📢 عضویت اجباری: {'روشن' if fj_on else 'خاموش'}\n"
        f"📺 کانال: {fj_ch}\n\n"
        f"👑 ادمین‌ها: {len(admins)}\n"
        f"👥 کاربران: {len(users)}\n"
        f"👥 گروه‌ها: {len(groups)}"
    )
    return text, kb(rows)


def owner_stats_panel(user_id):
    if not is_bot_admin(user_id):
        return None, None

    users = storage.get("bot_users", "list") or {}
    admins = storage.get("bot_admins", "list") or {}
    groups = storage.get("bot_groups", "list") or {}
    owner = get_owner_id()
    db = storage.db()
    groups_count = len(db.get("locks", {}))
    total_xp = 0
    total_warns = 0
    for _, users_xp in db.get("xp", {}).items():
        for _, d in users_xp.items():
            total_xp += d.get("xp", 0)
    for _, w in db.get("warnings", {}).items():
        total_warns += sum(w.values()) if isinstance(w, dict) else 0

    from datetime import datetime
    txt = (
        f"📊 آمار ربات\n\n"
        f"👑 مالک: {owner}\n"
        f"🛡 ادمین‌ها: {len(admins)}\n"
        f"👥 کاربران: {len(users)}\n"
        f"👥 گروه‌های فعال: {groups_count}\n"
        f"👥 گروه‌های ثبت‌شده: {len(groups)}\n\n"
        f"⭐ کل XP: {total_xp}\n"
        f"⚠️ کل اخطارها: {total_warns}\n\n"
        f"📅 {datetime.now().strftime('%Y/%m/%d - %H:%M')}"
    )
    rows = [[btn("🔄 بروزرسانی", "owner:stats"), btn("🔙 برگشت", "owner:back")]]
    return txt, kb(rows)


def force_join_admin_panel(chat_id, user_id):
    fj = get_force_join()
    enabled = fj.get("enabled", False)
    ch = fj.get("channel_display", "تنظیم نشده")
    link = fj.get("channel_link", "")
    ch_id = fj.get("channel_id", "")
    bot_admin = fj.get("bot_is_admin", False)

    rows = [
        [btn(f"{'🟢 روشن' if enabled else '🔴 خاموش'}", "owner:fj_toggle")],
        [btn("✏️ تغییر کانال", "owner:fj_set")],
        [btn("🔍 تست عضویت من", "owner:fj_test")],
        [btn("🔍 تست ادمین ربات", "owner:fj_check_admin")],
        [btn("🗑 حذف کانال", "owner:fj_clear")],
        [btn("🔙 برگشت", "owner:back")],
    ]

    text = (
        f"📢 عضویت اجباری ربات\n\n"
        f"وضعیت: {'روشن' if enabled else 'خاموش'}\n"
        f"کانال: {ch}\n"
        f"آیدی: {ch_id or '?'}\n"
        f"لینک: {link or 'نداره'}\n"
        f"ربات ادمین کانال: {'بله' if bot_admin else 'خیر'}\n"
    )
    if not bot_admin and enabled:
        text += "\n⚠️ ربات تو کانال ادمین نیست."
    return text, kb(rows)


def bot_admins_panel(chat_id, user_id):
    admins = storage.get("bot_admins", "list") or {}
    owner = get_owner_id()
    txt = f"👑 ادمین‌های ربات\n\nمالک: {owner}\n\n"
    for uid, name in admins.items():
        txt += f"• {name} — {uid}\n"
    if not admins:
        txt += "هنوز ادمین دیگه‌ای نداری."

    rows = [
        [btn("➕ افزودن", "owner:ba_add")],
        [btn("❌ حذف", "owner:ba_remove")],
        [btn("🔙 برگشت", "owner:back")],
    ]
    return txt, kb(rows)


def broadcast_panel(chat_id, user_id):
    users = storage.get("bot_users", "list") or {}
    admins = storage.get("bot_admins", "list") or {}
    groups = storage.get("bot_groups", "list") or {}

    rows = [
        [btn(f"👤 پیوی کاربران ({len(users)})", "owner:bc_private")],
        [btn(f"👥 گروه‌ها ({len(groups)})", "owner:bc_groups")],
        [btn("📢 همه", "owner:bc_both")],
        [btn(f"👑 ادمین‌های ربات ({len(admins)})", "owner:bc_admins")],
        [btn("🔙 برگشت", "owner:back")],
    ]
    return (
        f"📢 پیام همگانی\n\n"
        f"برای فوروارد، تو گروه روی پیام ریپلای کن و بزن «همگانی».\n\n"
        f"برای پیام متنی، مقصد رو انتخاب کن 👇",
        kb(rows)
    )


# ============================================================
# پنل استارت (پیوی)
# ============================================================
def start_panel(user):
    bot_username = api.get_bot_username()
    name = user.get("first_name", "دوست")

    rows = [
        [btn("🎮 پنل کاربری", "user:main")],
        [btn("➕ افزودن به گروه", "ug:panel")],
        [btn("📖 راهنما", "start:help_full")],
        [btn("👤 پروفایل من", "start:profile"),
         btn("📊 آمار", "start:stats")],
        [btn("❌ بستن", "start:close")],
    ]

    text = (
        f"سلام {name} 👋\n\n"
        f"من ربات مدیریت گروه آلفا هستم.\n"
        f"مدیریت کامل گروه + بازی + گیف ساز.\n\n"
        f"👇 یکی از گزینه‌ها رو انتخاب کن:"
    )
    return text, kb(rows)


def force_join_panel(fj):
    ch_name = fj.get("channel_display", "کانال")
    link = fj.get("channel_link", "")

    rows = []
    if link:
        rows.append([btn(f"📢 عضویت در {ch_name}", url=link)])
    rows.append([btn("✅ عضو شدم", "start:check_join")])

    text = (
        f"اول باید تو کانال زیر عضو بشی 👇\n\n"
        f"📢 {ch_name}\n\n"
        f"بعد دکمه «عضو شدم» رو بزن."
    )
    return text, kb(rows)


# ============================================================
# راهنما
# ============================================================
def help_main_panel():
    rows = [
        [btn("⚙️ پنل مدیریت", "help:panel"), btn("📢 پیام همگانی", "help:broadcast")],
        [btn("🔒 قفل‌ها", "help:locks"), btn("🛡 ضد اسپم", "help:antispam")],
        [btn("🚫 ضد فحش", "help:badword"), btn("⏱ حالت آهسته", "help:slowmode")],
        [btn("🌙 شب", "help:night"), btn("😴 خواب", "help:sleep")],
        [btn("⭐ سفیدلیست", "help:whitelist"), btn("💬 سفارشی", "help:custom")],
        [btn("📢 عضویت اجباری", "help:join"), btn("👋 خوش‌آمد", "help:welcome")],
        [btn("👤 مدیریت کاربران", "help:users"), btn("📜 اصل و لقب", "help:asl_laqab")],
        [btn("👑 ارتقا و تنزل", "help:promote"), btn("📝 مدیریت پیام", "help:messages")],
        [btn("🚫 کلمات ممنوعه", "help:words"), btn("📜 قوانین", "help:rules")],
        [btn("📌 یادداشت", "help:notes"), btn("📊 آمار", "help:stats")],
        [btn("🎮 بازی‌ها", "help:games"), btn("🎭 مافیا", "help:mafia")],
        [btn("🎯 جرئت یا حقیقت", "help:todd"), btn("🧠 آزمون", "help:quiz")],
        [btn("🎁 قرعه‌کشی", "help:lottery"), btn("⭐ امتیاز", "help:xp")],
        [btn("🏆 رنکینگ", "help:ranking"), btn("🔗 دعوت", "help:invites")],
        [btn("📅 گزارش هفتگی", "help:weekly_report"), btn("🎬 گیف ساز", "help:gif")],
        [btn("🐛 گزارش باگ", "help:bug"), btn("💾 ابزارها", "help:tools")],
        [btn("❌ بستن", "help:close")],
    ]

    text = (
        "📖 راهنمای کامل\n\n"
        "سلام! هر بخشی که می‌خوای بدونی، روی دکمه‌ش بزن 👇"
    )
    return text, kb(rows)


HELP_TEXTS = {
    "panel": """⚙️ پنل مدیریت

`پنل` → پنل کامل
`کاربران` → کاربران ثبت‌شده

بخش‌ها:
🔒 قفل‌ها، 🛡 ضداسپم، 🚫 ضدفحش
👋 خوش‌آمد، 📢 تگ، 🎬 گیف
🎮 سرگرمی، 📊 آمار""",

    "broadcast": """📢 پیام همگانی

فقط ادمین ربات دسترسی داره.

روی پیام ریپلای کن و بزن:
• `همگانی` → همه
• `همگانی پیوی` → فقط پیوی
• `همگانی گروه` → فقط گروه‌ها
• `همگانی ادمین` → ادمین‌ها""",

    "locks": """🔒 قفل‌ها

`قفل ها` → پنل قفل‌ها
`قفل همه` / `بازکردن همه`
`قفل گروه` → فقط ادمین‌ها پیام بدن

قفل‌ها: لینک، فوروارد، عکس، ویدیو، استیکر، ویس، گیف، فایل و...

بعد از N بار نقض، کاربر اخراج می‌شه.""",

    "antispam": """🛡 ضد اسپم

`ضد اسپم` → پنل تنظیمات

حد مجاز + بازه زمانی + مجازات + آستانه هشدار""",

    "badword": """🚫 ضد فحش

`ضد فحش` → پنل

روشن/خاموش + حداکثر اخطار + افزودن کلمه""",

    "slowmode": """⏱ حالت آهسته

`حالت آهسته` → پنل

`آهسته 5` → ۵ ثانیه
`آهسته 10m` → ۱۰ دقیقه
`آهسته 1h` → ۱ ساعت
`آهسته خاموش` → خاموش""",

    "night": """🌙 حالت شب

`حالت شب` → پنل

`حالت شب روشن` / `خاموش`

تو بازه تعیین شده فقط ادمین‌ها پیام می‌دن.""",

    "sleep": """😴 حالت خواب

`حالت خواب` → پنل

می‌تونی چند بازه تنظیم کنی.
مثلاً 03:00 تا 04:00.""",

    "whitelist": """⭐ سفیدلیست

`سفیدلیست` → پنل

کاربرای این لیست از ضداسپم و شب و خواب مستثنا هستن.""",

    "custom": """💬 دستورات سفارشی

`دستورات سفارشی` → پنل

مثال: دستور `سلام` → پاسخ دلخواه""",

    "join": """📢 عضویت اجباری

گروه: `عضویت`
ربات: چت خصوصی با ربات → `پنل`

کاربرا باید اول تو کانال عضو بشن.""",

    "welcome": """👋 خوش‌آمدگویی

`خوش آمد` → پنل

متغیرها: {name}، {group}، {bot}""",

    "users": """👤 مدیریت کاربران

`مدیریت` (ریپلای) → پنل
`اخطار` | `حذف اخطار` | `اخطارها`
`سکوت 10m` | `آزاد`
`بن` | `آنبن` | `اخراج`
`اطلاعات` | `لیست سیاه`

📢 تگ کردن:
`تگ` → پنل تگ
`تگ همه` | `تگ 7` | `تگ 24` | `تگ هفته`""",

    "asl_laqab": """📜 اصل و لقب

`اصل من (متن)` → درخواست ثبت اصل
`اصل` (ریپلای) → نمایش اصل
`لقب (متن)` (ریپلای) → ثبت لقب
`حذف لقب` | `لیست لقب‌ها`""",

    "promote": """👑 ارتقا و تنزل

`ارتقا` / `تنزل` (ریپلای یا @یوزرنیم)

فقط مالک گروه می‌تونه.""",

    "messages": """📝 مدیریت پیام

`حذف` (ریپلای)
`سنجاق` / `برداشتن سنجاق`
`پاکسازی 20`""",

    "words": """🚫 کلمات ممنوعه

`کلمه ممنوعه spam`
`حذف کلمه spam`
`لیست کلمات`""",

    "rules": """📜 قوانین

`قوانین تنظیم متن`
`قوانین`""",

    "notes": """📌 یادداشت‌ها

`یادداشت‌ها` → پنل

➕ افزودن، 👁 مشاهده، 🗑 حذف""",

    "stats": """📊 آمار

`آمار` → نمودار هفتگی
`ریست` | `برترین امروز`""",

    "games": """🎮 بازی‌ها

`سرگرمی` → پنل بازی‌ها""",

    "mafia": """🎭 مافیا

`مافیا` → ساخت لابی (۵ نفر به بالا)""",

    "todd": """🎯 جرئت یا حقیقت

`سرگرمی` → 🎯 جرئت یا حقیقت

با ربات، دوست یا ناشناس.""",

    "quiz": """🧠 آزمون

`آزمون` | `لیدر آزمون`""",

    "lottery": """🎁 قرعه‌کشی

`قرعه‌کشی` | `قرعه‌کشی 3`""",

    "xp": """⭐ امتیاز و سطح

هر پیام ۵ XP
هر برد ۱۵ XP
هر ۱۰۰ XP = ۱ سطح""",

    "ranking": """🏆 رنکینگ

`روزانه` | `هفتگی` | `ماهانه` | `تاپ`""",

    "invites": """🔗 دعوت

`دعوت‌ها` | `لیدر دعوت`""",

    "weekly_report": """📅 گزارش هفتگی

`گزارش هفتگی روشن` / `خاموش`
`گزارش هفتگی` → نمایش فوری""",

    "gif": """🎬 گیف ساز

روی عکس یا گیف ریپلای کن و بزن `گیف`""",

    "bug": """🐛 گزارش باگ

`گزارش باگ` یا `باگ`""",

    "tools": """💾 ابزارها

`آیدی` | `زمان` | `حساب 2+3`
`اطلاعات` | `گزارش` (ریپلای)
`لیست سیاه`""",
}


# ============================================================
# پنل اصلی گروه
# ============================================================
def _ai_on(chat_id):
    """آیا هوش مصنوعی برای این گروه فعال است؟"""
    try:
        import ai
        import ai_panel
        return bool(ai.enabled() and ai_panel.group_settings(chat_id).get("announce", True))
    except Exception:
        return False


def main_panel(chat_id):
    locks_on = sum(1 for v in (get("locks", chat_id) or {}).values() if v)
    as_on = (get("antispam", chat_id) or {}).get("enabled", False)
    bw_on = (get("badword", chat_id) or {}).get("enabled", False)
    w_on = (get("welcome", chat_id) or {}).get("enabled", False)
    banned_count = len(get("banned_users", chat_id) or {})
    muted_count = len(get("muted", chat_id) or {})
    locked_count = len(get("locked_users", chat_id) or {})
    slow = (get("slowmode", chat_id) or {}).get("seconds", 0)
    gj_on = get_group_join(chat_id).get("enabled", False)
    nm_on = features.get_night_mode(chat_id).get("enabled", False)
    sleep_on = features.get_sleep_mode(chat_id).get("enabled", False)
    wl_count = len(get("whitelist", chat_id) or [])
    cc_count = len(features.list_custom_cmds(chat_id))
    gl_on = bool((get("group_lock", chat_id) or {}).get("enabled"))

    rows = [
        [btn("🔒 قفل‌ها", "panel:locks"), btn("🛡 ضد اسپم", "panel:antispam")],
        [btn("🚫 ضد فحش", "panel:badword"), btn("👋 خوش‌آمد", "panel:welcome")],
        [btn(f"🔐 قفل گروه {'✅' if gl_on else '❌'}", "panel:group_lock_toggle"),
         btn(f"🔓 آزاد ({locked_count})", "panel:free_locked")],
        [btn("📢 تگ کاربران", "panel:tag_menu"),
         btn("👥 کاربران", "panel:registered_users")],
        [btn(f"⏱ آهسته {slow}s" if slow else "⏱ آهسته", "panel:slowmode"),
         btn(f"🌙 شب {'✅' if nm_on else '❌'}", "panel:night_mode")],
        [btn(f"😴 خواب {'✅' if sleep_on else '❌'}", "panel:sleep"),
         btn(f"⭐ سفیدلیست ({wl_count})", "panel:whitelist")],
        [btn("🚫 کلمات ممنوعه", "panel:words"), btn("📜 قوانین", "panel:rules")],
        [btn("📌 یادداشت", "panel:notes"),
         btn(f"💬 سفارشی ({cc_count})", "panel:custom_cmds")],
        [btn(f"📢 عضویت {'✅' if gj_on else '❌'}", "panel:group_join")],
        [btn("🎬 گیف", "gif:start"), btn("🎮 سرگرمی", "panel:entertainment")],
        [btn("🏆 لیدربرد", "panel:leaderboards"), btn("📊 آمار", "panel:stats")],
        [btn(f"🚫 بن ({banned_count})", "panel:banned"),
         btn(f"🔇 سکوت ({muted_count})", "panel:muted")],
        [btn("⚠️ اخطارها", "panel:warns"), btn("📋 لیست سیاه", "panel:blacklist")],
        [btn("🧠 هوش مصنوعی", "ai:group"), btn("🧹 پاک‌سازی", "panel:clean")],
        [btn("💬 پنل پیوی", "panel:pv_open")],
    ]

    text = (
        "🏆 پنل مدیریت گروه\n\n"
        f"🔒 {locks_on} قفل فعال\n"
        f"🛡 ضداسپم {'روشن' if as_on else 'خاموش'}\n"
        f"🚫 ضدفحش {'روشن' if bw_on else 'خاموش'}\n"
        f"👋 خوش‌آمد {'روشن' if w_on else 'خاموش'}\n"
        f"🌙 شب {'روشن' if nm_on else 'خاموش'} | "
        f"😴 خواب {'روشن' if sleep_on else 'خاموش'}\n"
        f"📢 عضویت اجباری {'روشن' if gj_on else 'خاموش'}\n"
        f"🧠 هوش مصنوعی {'روشن' if _ai_on(chat_id) else 'خاموش'}\n\n"
        f"🚫 {banned_count} بن | 🔇 {muted_count} سکوت\n\n"
        f"از دکمه‌های زیر استفاده کن 👇"
    )
    return text, kb(rows)


# ============================================================
# تگ
# ============================================================
def tag_menu_panel(chat_id):
    profiles = get("user_profiles", chat_id) or {}
    members_seen = get("members_seen", chat_id) or {}

    all_users = {}
    now = time.time()

    for uid, info in profiles.items():
        all_users[uid] = {
            "username": info.get("username", ""),
            "last_seen": info.get("last_seen", info.get("ts", 0)),
        }
    for uid, info in members_seen.items():
        if uid in all_users:
            if info.get("ts", 0) > all_users[uid]["last_seen"]:
                all_users[uid]["last_seen"] = info["ts"]
            if info.get("username") and not all_users[uid]["username"]:
                all_users[uid]["username"] = info["username"]
        else:
            all_users[uid] = {
                "username": info.get("username", ""),
                "last_seen": info.get("ts", now),
            }

    all_count = len(all_users)
    with_uname = sum(1 for u in all_users.values() if u.get("username"))
    c7 = sum(1 for u in all_users.values() if u["last_seen"] >= now - 7 * 3600)
    c24 = sum(1 for u in all_users.values() if u["last_seen"] >= now - 24 * 3600)
    cw = sum(1 for u in all_users.values() if u["last_seen"] >= now - 7 * 24 * 3600)

    rows = [
        [btn(f"👥 همه ({all_count})", "tag:all")],
        [btn(f"⏰ ۷ ساعت اخیر ({c7})", "tag:7h")],
        [btn(f"📅 ۲۴ ساعت اخیر ({c24})", "tag:24h")],
        [btn(f"📆 یه هفته اخیر ({cw})", "tag:week")],
        [btn("🔙 برگشت", "panel:main")],
    ]

    text = (
        "📢 تگ کردن کاربران\n\n"
        f"👥 کل کاربران: {all_count}\n"
        f"🔔 قابل تگ: {with_uname}\n"
        f"⏰ ۷ ساعت اخیر: {c7}\n"
        f"📅 ۲۴ ساعت اخیر: {c24}\n"
        f"📆 یه هفته اخیر: {cw}\n\n"
        "بله فقط @یوزرنیم رو پشتیبانی می‌کنه."
    )
    return text, kb(rows)


def registered_users_panel(chat_id, page=0):
    profiles = get("user_profiles", chat_id) or {}
    items = [(uid, info) for uid, info in profiles.items() if info.get("username")]
    per_page = 10

    if not items:
        return (
            "👥 کاربران ثبت‌شده\n\n"
            "هنوز کسی ثبت نشده.\n\n"
            "کاربرا وقتی ثبت می‌شن که پیام بدن یا ربات رو تو پیوی استارت کنن.",
            kb([[btn("🔙 برگشت", "panel:main")]])
        )

    total = max(1, (len(items) + per_page - 1) // per_page)
    page = max(0, min(page, total - 1))
    chunk = items[page * per_page:(page + 1) * per_page]

    txt = f"👥 کاربران ({len(items)} نفر)\n\n"
    for uid, info in chunk:
        fname = info.get("first_name", "کاربر")
        uname = info.get("username", "")
        txt += f"• {api.esc_md(fname)} — @{api.esc_md(uname)}\n"

    if len(items) > per_page:
        txt += f"\nصفحه {page+1} از {total}"

    rows = []
    nav = []
    if page > 0:
        nav.append(btn("⬅️", f"users:page:{page-1}"))
    nav.append(btn(f"{page+1}/{total}", "noop"))
    if page < total - 1:
        nav.append(btn("➡️", f"users:page:{page+1}"))
    if nav:
        rows.append(nav)

    rows.append([btn("🔄 بروزرسانی", "panel:registered_users"),
                 btn("🔙 برگشت", "panel:main")])
    return txt, kb(rows)


# ============================================================
# اطلاعات کاربر — فقط آیدی عددی قابل کپی
# ============================================================
def _get_user_status_fa(chat_id, uid):
    """وضعیت کاربر: کاربر ساده / ادمین / مالک"""
    try:
        r = api.get_member(chat_id, uid)
        if r and r.get("ok"):
            status = r["result"].get("status", "")
            if status == "creator":
                return "مالک 👑"
            elif status == "administrator":
                return "ادمین 🛡"
            else:
                return "کاربر ساده 👤"
    except Exception:
        pass
    return "کاربر ساده 👤"


def user_info_panel(chat_id, target, xp_data=None, warns=0, is_banned=False, is_muted=False):
    uid = target["id"]
    first = target.get("first_name", "کاربر")
    last = target.get("last_name", "")
    full_name = f"{first} {last}".strip() if last else first

    status_fa = _get_user_status_fa(chat_id, uid)

    text = f"👤 <b>پروفایل {html.escape(full_name)}</b>\n\n"
    text += f"🎭 وضعیت: {status_fa}\n"
    text += f"\n💡 <i>برای کپی، روی دکمه زیر بزن</i>"

    rows = [[{
        "text": f"🆔 آیدی: {uid}",
        "copy_text": {"text": str(uid)}
    }]]

    return text, kb(rows)


# ============================================================
# ضد فحش
# ============================================================
def badword_panel(chat_id):
    cfg = get("badword", chat_id) or {}
    enabled = cfg.get("enabled", False)
    max_warns = cfg.get("max_warns", 3)
    extra = get("extra_bad_words", chat_id) or []

    rows = [
        [btn(f"{'🟢 فعال' if enabled else '🔴 غیرفعال'}", "bw:toggle")],
        [btn(f"⚠️ حداکثر اخطار: {max_warns}", "bw:setmax")],
        [btn(f"📝 کلمات اضافی ({len(extra)})", "bw:extra_list")],
        [btn("➕ افزودن", "bw:add"), btn("🗑 حذف", "bw:remove_panel")],
        [btn("🗑 پاک کردن همه", "bw:clear_extra")],
        [btn("🔙 برگشت", "panel:main")],
    ]

    text = (
        f"🚫 ضد فحش\n\n"
        f"وضعیت: {'فعال' if enabled else 'غیرفعال'}\n"
        f"حداکثر اخطار: {max_warns}\n"
        f"کلمات اضافی: {len(extra)}\n\n"
        f"ادمین‌ها مستثنا هستن."
    )
    return text, kb(rows)


def badword_max_panel(chat_id):
    rows = [
        [btn("1", "bw:max:1"), btn("2", "bw:max:2"), btn("3", "bw:max:3")],
        [btn("4", "bw:max:4"), btn("5", "bw:max:5"), btn("10", "bw:max:10")],
        [btn("🔙 برگشت", "panel:badword")],
    ]
    return "⚠️ حداکثر اخطار قبل از بن:", kb(rows)


def badword_extra_list_panel(chat_id):
    extra = get("extra_bad_words", chat_id) or []
    txt = "📝 کلمات اضافی\n\n"
    if extra:
        for i, w in enumerate(extra, 1):
            txt += f"{i}. {w}\n"
    else:
        txt += "خالیه."

    rows = [
        [btn("➕ افزودن", "bw:add"), btn("🗑 حذف تکی", "bw:remove_panel")],
        [btn("🗑 پاک کردن همه", "bw:clear_extra")],
        [btn("🔙 برگشت", "panel:badword")],
    ]
    return txt, kb(rows)


def badword_remove_panel(chat_id):
    extra = get("extra_bad_words", chat_id) or []
    if not extra:
        return "لیست خالیه.", kb([[btn("🔙 برگشت", "panel:badword")]])

    rows = []
    for i, w in enumerate(extra[:ITEMS_PER_PAGE]):
        rows.append([btn(f"❌ {w}", f"bw:rm:{i}")])
    rows.append([btn("🔙 برگشت", "panel:badword")])
    return "روی کلمه بزن تا حذف بشه:", kb(rows)


# ============================================================
# سرگرمی
# ============================================================
def entertainment_panel(chat_id):
    rows = [
        [btn("🎯 حدس عدد", "ent:guess"), btn("💭 حدس کلمه", "ent:word")],
        [btn("🔤 حروف بهم ریخته", "ent:scramble"), btn("🪨 سنگ کاغذ قیچی", "ent:rps")],
        [btn("🎮 دوز", "ent:doss"), btn("🎯 جرئت یا حقیقت", "ent:tod")],
        [btn("😂 جوک", "ent:joke"), btn("🎭 مافیا", "ent:mafia")],
        [btn("🎲 تاس", "ent:dice"), btn("🪙 شیر یا خط", "ent:coin")],
        [btn("📖 راهنما", "ent:help"), btn("🏆 لیدربرد", "panel:leaderboards")],
        [btn("🔙 برگشت", "panel:main")],
    ]

    text = (
        "🎮 سرگرمی\n\n"
        "هر بازی سه حالت داره:\n"
        "🤖 با ربات\n"
        "👤 با یه دوست\n"
        "🎭 ناشناس\n\n"
        "کدوم رو می‌خوای؟ 👇"
    )
    return text, kb(rows)


def entertainment_help(chat_id):
    text = (
        "📖 راهنمای بازی‌ها\n\n"
        "🤖 با ربات — مستقیم شروع می‌شه\n"
        "👤 با دوست — روی پیامش ریپلای کن\n"
        "🎭 ناشناس — می‌ری تو صف\n\n"
        "🏆 هر برد ۱۵ امتیاز داره."
    )
    return text, kb([[btn("🔙 برگشت", "panel:entertainment")]])


def leaderboards_panel(chat_id):
    rows = [
        [btn("🎯 حدس عدد", "lb:guess"), btn("💭 حدس کلمه", "lb:word")],
        [btn("🔤 حروف بهم ریخته", "lb:scramble"), btn("🪨 سنگ کاغذ قیچی", "lb:rps")],
        [btn("🎮 دوز", "lb:doss"), btn("🧠 آزمون", "lb:quiz")],
        [btn("😂 جوک", "lb:joke"), btn("❓ حقیقت", "lb:truth")],
        [btn("🔥 جرئت", "lb:dare")],
        [btn("🏆 همه بازی‌ها", "lb:all")],
        [btn("📅 روزانه", "rank:daily"), btn("📆 هفتگی", "rank:weekly")],
        [btn("🗓 ماهانه", "rank:monthly"), btn("🏆 تاپ ۱۰", "panel:top10")],
        [btn("🔙 برگشت", "panel:main")],
    ]
    return "🏆 لیدربردها\n\nکدوم رو ببینی؟", kb(rows)


def show_leaderboard(chat_id, game_key=None):
    from storage import get_game_leaderboard, get as _get

    game_names = {
        "guess": "🎯 حدس عدد",
        "word": "💭 حدس کلمه",
        "scramble": "🔤 حروف بهم ریخته",
        "rps": "🪨 سنگ کاغذ قیچی",
        "doss": "🎮 دوز",
        "joke": "😂 جوک",
        "truth": "❓ حقیقت",
        "dare": "🔥 جرئت",
        "quiz": "🧠 آزمون",
    }
    xp_data = _get("xp", chat_id) or {}

    if game_key and game_key != "all":
        items = get_game_leaderboard(chat_id, game_key, 10)
        name = game_names.get(game_key, game_key)
        if not items:
            return f"🏆 لیدربرد {name}\n\nهنوز کسی برنده نشده.", kb([[btn("🔙 برگشت", "panel:leaderboards")]])

        txt = f"🏆 لیدربرد {name}\n\n"
        for i, (uid, data) in enumerate(items, 1):
            medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")
            name = (xp_data.get(uid, {}).get("name")
                    or data.get("name", "")
                    or f"کاربر {str(uid)[-4:]}")
            txt += f"{medal} {name} — {data.get('wins', 0)} برد\n"
    else:
        txt = "🏆 لیدربرد همه بازی‌ها\n\n"
        found = False
        for gk, gname in game_names.items():
            items = get_game_leaderboard(chat_id, gk, 1)
            if items:
                uid, data = items[0]
                name = (xp_data.get(uid, {}).get("name")
                        or data.get("name", "")
                        or f"کاربر {str(uid)[-4:]}")
                txt += f"{gname}: {name} ({data.get('wins', 0)})\n"
                found = True
        if not found:
            txt += "هنوز کسی برنده نشده."

    return txt, kb([[btn("🔙 برگشت", "panel:leaderboards")]])


# ============================================================
# قفل‌ها
# ============================================================
def locks_panel(chat_id, page=0):
    locks = get("locks", chat_id) or {}
    items = list(lock_mod.LOCKS.items())
    per_page = 10
    total = (len(items) + per_page - 1) // per_page
    page = max(0, min(page, total - 1))
    chunk = items[page * per_page:(page + 1) * per_page]

    rows = []
    for i in range(0, len(chunk), 2):
        row = []
        for name, cfg in chunk[i:i + 2]:
            icon = "✅" if locks.get(name) else "⬜️"
            row.append(btn(f"{icon} {cfg['fa']}", f"lock:toggle:{name}:{page}"))
        rows.append(row)

    nav = []
    if page > 0:
        nav.append(btn("⬅️", f"lock:page:{page-1}"))
    nav.append(btn(f"{page+1}/{total}", "noop"))
    if page < total - 1:
        nav.append(btn("➡️", f"lock:page:{page+1}"))
    rows.append(nav)
    rows.append([btn("🔒 همه روشن", "lock:all:on"), btn("🔓 همه خاموش", "lock:all:off")])

    threshold = lock_mod.get_warn_threshold(chat_id)
    rows.append([btn(f"⚙️ آستانه هشدار: {threshold}", "lock:warn_panel")])
    rows.append([btn("🔙 برگشت", "panel:main")])

    on_count = sum(1 for v in locks.values() if v)
    text = (
        f"🔒 قفل‌ها\n\n"
        f"فعال: {on_count} از {len(items)}\n"
        f"آستانه اخراج: {threshold} هشدار\n\n"
        f"روی هر قفل بزن تا روشن/خاموش بشه."
    )
    return text, kb(rows)


def locks_warn_panel(chat_id):
    threshold = lock_mod.get_warn_threshold(chat_id)
    warns = get("lock_warnings", chat_id) or {}
    active = {uid: n for uid, n in warns.items() if n > 0}

    rows = []
    row1 = []
    for n in (1, 2, 3, 4):
        mark = "✅ " if threshold == n else ""
        row1.append(btn(f"{mark}{n}", f"lock:set_threshold:{n}"))
    rows.append(row1)

    row2 = []
    for n in (5, 7, 10, 15):
        mark = "✅ " if threshold == n else ""
        row2.append(btn(f"{mark}{n}", f"lock:set_threshold:{n}"))
    rows.append(row2)

    if active:
        rows.append([btn(f"🔄 صفر کردن هشدارها ({len(active)})", "lock:reset_warns")])

    rows.append([btn("🔙 برگشت", "panel:locks")])

    text = f"⚙️ تنظیمات هشدار قفل‌ها\n\nآستانه فعلی: {threshold} هشدار\n"
    if active:
        text += "\nکاربرای با هشدار فعال:\n"
        for uid, cnt in list(active.items())[:10]:
            text += f"• {uid} — {cnt}\n"
    else:
        text += "\nهنوز کسی هشدار نگرفته."
    return text, kb(rows)


# ============================================================
# ضد اسپم
# ============================================================
def antispam_panel(chat_id):
    cfg = get("antispam", chat_id) or {}
    enabled = cfg.get("enabled", False)
    limit = cfg.get("limit", 5)
    window = cfg.get("window", 10)
    action = cfg.get("action", "سکوت")
    try:
        threshold = int(cfg.get("warn_threshold", 3))
    except (TypeError, ValueError):
        threshold = 3

    warns = get("antispam_warns", chat_id) or {}
    active = {uid: n for uid, n in warns.items() if n > 0}

    rows = [
        [btn(f"{'🟢 روشن' if enabled else '🔴 خاموش'}", "as:toggle")],
        [btn(f"📊 حد: {limit}", "as:limit"), btn(f"⏱ زمان: {window}s", "as:window")],
        [btn(f"⚖️ مجازات: {action}", "as:action")],
        [btn(f"⚠️ آستانه اخراج: {threshold}", "as:warn_panel")],
        [btn("🔙 برگشت", "panel:main")],
    ]

    text = (
        f"🛡 ضد اسپم\n\n"
        f"وضعیت: {'روشن' if enabled else 'خاموش'}\n"
        f"حد: {limit} پیام در {window} ثانیه\n"
        f"مجازات: {action}\n"
        f"آستانه اخراج: {threshold} هشدار"
    )
    if active:
        text += f"\n\nکاربرای با هشدار: {len(active)}"
    return text, kb(rows)


def antispam_warn_panel(chat_id):
    cfg = get("antispam", chat_id) or {}
    try:
        threshold = int(cfg.get("warn_threshold", 3))
    except (TypeError, ValueError):
        threshold = 3

    warns = get("antispam_warns", chat_id) or {}
    active = {uid: n for uid, n in warns.items() if n > 0}

    rows = []
    row1 = []
    for n in (1, 2, 3, 4):
        mark = "✅ " if threshold == n else ""
        row1.append(btn(f"{mark}{n}", f"as:set_warn:{n}"))
    rows.append(row1)

    row2 = []
    for n in (5, 7, 10, 15):
        mark = "✅ " if threshold == n else ""
        row2.append(btn(f"{mark}{n}", f"as:set_warn:{n}"))
    rows.append(row2)

    if active:
        rows.append([btn(f"🔄 صفر کردن هشدارها ({len(active)})", "as:reset_warns")])

    rows.append([btn("🔙 برگشت", "panel:antispam")])

    text = f"⚙️ تنظیمات هشدار ضد اسپم\n\nآستانه فعلی: {threshold} هشدار\n"
    if active:
        text += "\nکاربرای با هشدار:\n"
        for uid, cnt in list(active.items())[:10]:
            text += f"• {uid} — {cnt}\n"
    return text, kb(rows)


def antispam_limit_panel(chat_id):
    rows = [
        [btn("3", "as:setlimit:3"), btn("5", "as:setlimit:5"), btn("10", "as:setlimit:10")],
        [btn("15", "as:setlimit:15"), btn("20", "as:setlimit:20"), btn("30", "as:setlimit:30")],
        [btn("🔙 برگشت", "panel:antispam")],
    ]
    return "📊 حد مجاز:", kb(rows)


def antispam_window_panel(chat_id):
    rows = [
        [btn("5s", "as:setwindow:5"), btn("10s", "as:setwindow:10")],
        [btn("20s", "as:setwindow:20"), btn("30s", "as:setwindow:30")],
        [btn("60s", "as:setwindow:60"), btn("120s", "as:setwindow:120")],
        [btn("🔙 برگشت", "panel:antispam")],
    ]
    return "⏱ بازه زمانی:", kb(rows)


def antispam_action_panel(chat_id):
    rows = [
        [btn("🔇 سکوت", "as:setaction:mute")],
        [btn("👢 اخراج", "as:setaction:kick")],
        [btn("🚫 بن", "as:setaction:ban")],
        [btn("🔙 برگشت", "panel:antispam")],
    ]
    return "⚖️ مجازات:", kb(rows)


# ============================================================
# خوش‌آمد
# ============================================================
def welcome_panel(chat_id):
    cfg = get("welcome", chat_id) or {}
    enabled = cfg.get("enabled", False)
    t = cfg.get("text", "")
    preview = t if t else "تنظیم نشده"
    autodel = cfg.get("autodelete", 0)
    has_media = bool(cfg.get("media_type"))
    media_type = cfg.get("media_type", "")
    media_icon = {"photo": "🖼", "video": "🎥", "animation": "🎞"}.get(media_type, "❌")

    rows = [
        [btn(f"{'🟢 روشن' if enabled else '🔴 خاموش'}", "w:toggle")],
        [btn("✏️ تغییر متن", "w:edit"), btn("📋 قالب‌ها", "w:templates")],
        [btn(f"{media_icon} مدیا {'✅' if has_media else '❌'}", "w:setmedia"),
         btn("🗑 حذف مدیا", "w:clearmedia")],
        [btn(f"⏱ حذف خودکار: {autodel}s" if autodel else "⏱ حذف خودکار: خاموش", "w:autodel")],
        [btn("👁 پیش‌نمایش", "w:preview"), btn("🗑 حذف متن", "w:clear")],
        [btn("🔙 برگشت", "panel:main")],
    ]

    return (
        f"👋 خوش‌آمدگویی\n\n"
        f"وضعیت: {'روشن' if enabled else 'خاموش'}\n"
        f"متن: {api.esc_md(str(preview)[:120])}\n"
        f"مدیا: {media_icon}\n"
        f"حذف خودکار: {autodel}s\n\n"
        f"متغیرها: {{name}}، {{group}}، {{bot}}",
        kb(rows)
    )


def welcome_templates(chat_id):
    rows = [
        [btn("سلام {name}، به {group} خوش اومدی 🎉", "w:use:1")],
        [btn("{name} عزیز، خوش اومدی 💐", "w:use:2")],
        [btn("به گروه ما خوش اومدی {name} 🌹", "w:use:3")],
        [btn("{name} جان، خوش اومدی ❤️", "w:use:4")],
        [btn("🎊 {name} به {group} پیوست!", "w:use:5")],
        [btn("🔙 برگشت", "panel:welcome")],
    ]
    return "📋 قالب‌های آماده:", kb(rows)


TEMPLATES = {
    "1": "سلام {name}، به {group} خوش اومدی 🎉",
    "2": "{name} عزیز، خوش اومدی 💐",
    "3": "به گروه ما خوش اومدی {name} 🌹",
    "4": "{name} جان، خوش اومدی ❤️",
    "5": "🎊 {name} به {group} پیوست!",
}


# ============================================================
# کلمات ممنوعه
# ============================================================
def words_panel(chat_id):
    words = get("banned_words", chat_id) or []
    cfg = get("banned_words_config", chat_id) or {}
    try:
        threshold = int(cfg.get("warn_threshold", 3))
    except (TypeError, ValueError):
        threshold = 3
    action = cfg.get("action", "mute_10m")
    action_fa = {
        "mute_10m": "سکوت ۱۰ دقیقه",
        "mute_1h": "سکوت ۱ ساعت",
        "kick": "اخراج",
        "ban": "بن",
    }.get(action, "سکوت ۱۰ دقیقه")

    bw_warns = get("bw_warnings", chat_id) or {}
    active = {uid: n for uid, n in bw_warns.items() if n > 0}

    txt = f"🚫 کلمات ممنوعه\n\n"
    txt += f"آستانه اخطار: {threshold}\n"
    txt += f"مجازات: {action_fa}\n\n"

    if words:
        txt += "لیست کلمات:\n"
        for i, w in enumerate(words[:ITEMS_PER_PAGE], 1):
            txt += f"{i}. {w}\n"
        if len(words) > ITEMS_PER_PAGE:
            txt += f"و {len(words) - ITEMS_PER_PAGE} تای دیگه...\n"
    else:
        txt += "لیست خالیه."

    if active:
        txt += f"\nکاربرای با هشدار: {len(active)}"

    rows = [
        [btn("➕ افزودن", "word:add"), btn("🗑 حذف همه", "word:clearall")],
        [btn("❌ حذف تکی", "word:remove_panel")],
        [btn(f"⚠️ آستانه: {threshold}", "word:set_threshold")],
        [btn(f"⚖️ مجازات: {action_fa}", "word:set_action")],
        [btn("🔄 صفر کردن هشدارها", "word:reset_warns")],
        [btn("🔙 برگشت", "panel:main")],
    ]
    return txt, kb(rows)


def words_threshold_panel(chat_id):
    cfg = get("banned_words_config", chat_id) or {}
    try:
        cur = int(cfg.get("warn_threshold", 3))
    except (TypeError, ValueError):
        cur = 3

    rows = []
    row1 = []
    for n in (1, 2, 3, 4):
        mark = "✅ " if cur == n else ""
        row1.append(btn(f"{mark}{n}", f"word:threshold:{n}"))
    rows.append(row1)

    row2 = []
    for n in (5, 7, 10, 15):
        mark = "✅ " if cur == n else ""
        row2.append(btn(f"{mark}{n}", f"word:threshold:{n}"))
    rows.append(row2)

    rows.append([btn("🔙 برگشت", "panel:words")])
    return f"⚠️ آستانه هشدار\n\nالان روی {cur} هشداره.", kb(rows)


def words_action_panel(chat_id):
    cfg = get("banned_words_config", chat_id) or {}
    cur = cfg.get("action", "mute_10m")

    def mark(k):
        return "✅ " if cur == k else ""

    rows = [
        [btn(f"{mark('mute_10m')}🔇 سکوت ۱۰ دقیقه", "word:action:mute_10m")],
        [btn(f"{mark('mute_1h')}🔇 سکوت ۱ ساعت", "word:action:mute_1h")],
        [btn(f"{mark('kick')}👢 اخراج", "word:action:kick")],
        [btn(f"{mark('ban')}🚫 بن", "word:action:ban")],
        [btn("🔙 برگشت", "panel:words")],
    ]
    return "⚖️ مجازات بعد از آستانه:", kb(rows)


def word_remove_panel(chat_id):
    words = get("banned_words", chat_id) or []
    if not words:
        return "لیست خالیه.", kb([[btn("🔙 برگشت", "panel:words")]])
    rows = []
    for i, w in enumerate(words[:ITEMS_PER_PAGE]):
        rows.append([btn(f"❌ {w}", f"word:rm:{i}")])
    rows.append([btn("🔙 برگشت", "panel:words")])
    return "روی کلمه بزن:", kb(rows)


# ============================================================
# قوانین / اخطارها
# ============================================================
def rules_panel(chat_id):
    r = get("rules", chat_id) or {}
    txt = r.get("text") or "تنظیم نشده"
    rows = [
        [btn("✏️ تغییر", "r:edit"), btn("🗑 حذف", "r:clear")],
        [btn("🔙 برگشت", "panel:main")],
    ]
    return f"📜 قوانین\n\n{txt}", kb(rows)


def warns_panel(chat_id):
    warns = get("warnings", chat_id) or {}
    txt = "⚠️ اخطارها\n\n"
    if warns:
        for uid, c in list(warns.items())[:ITEMS_PER_PAGE]:
            if c > 0:
                txt += f"{uid} — {c} اخطار\n"
    else:
        txt += "خالیه."
    rows = [
        [btn("🔄 ریست همه", "warn:clearall")],
        [btn("🔙 برگشت", "panel:main")],
    ]
    return txt, kb(rows)


# ============================================================
# لیست سیاه
# ============================================================
def blacklist_panel(chat_id):
    banned = get("banned_users", chat_id) or {}
    muted = get("muted", chat_id) or {}
    now = time.time()

    active_muted = {uid: exp for uid, exp in muted.items() if exp > now}
    if active_muted != muted:
        set_("muted", chat_id, active_muted)

    txt = "📋 لیست سیاه\n\n"
    rows = []

    if banned:
        txt += f"🚫 بن‌شده‌ها ({len(banned)}):\n"
        for uid, info in list(banned.items())[:ITEMS_PER_PAGE]:
            name = info.get("name", "کاربر") if isinstance(info, dict) else "کاربر"
            txt += f"• {name} — {uid}\n"
            rows.append([btn(f"❌ آنبن {name}", f"bl:unban:{uid}")])
        txt += "\n"
    else:
        txt += "🚫 بن‌شده‌ها: خالی\n\n"

    if active_muted:
        txt += f"🔇 سکوت‌شده‌ها ({len(active_muted)}):\n"
        for uid, exp in list(active_muted.items())[:ITEMS_PER_PAGE]:
            rem = int(exp - now)
            if rem >= 3600:
                t = f"{rem // 3600} ساعت"
            elif rem >= 60:
                t = f"{rem // 60} دقیقه"
            else:
                t = f"{rem} ثانیه"
            txt += f"• {uid} — {t}\n"
            rows.append([btn(f"🔊 آزاد {str(uid)[-6:]}", f"bl:unmute:{uid}")])
    else:
        txt += "🔇 سکوت‌شده‌ها: خالی"

    rows.append([btn("🔄 بروزرسانی", "panel:blacklist"), btn("🔙 برگشت", "panel:main")])
    return txt, kb(rows)


def banned_panel(chat_id, page=0):
    banned = get("banned_users", chat_id) or {}
    items = list(banned.items())
    per_page = 8
    total = max(1, (len(items) + per_page - 1) // per_page)
    page = max(0, min(page, total - 1))
    chunk = items[page * per_page:(page + 1) * per_page]

    rows = []
    for uid, info in chunk:
        name = info.get("name", "کاربر") if isinstance(info, dict) else "کاربر"
        rows.append([btn(f"🔓 {name}", f"ban:unban:{uid}:{page}")])

    nav = []
    if page > 0:
        nav.append(btn("⬅️", f"ban:page:{page-1}"))
    nav.append(btn(f"{page+1}/{total}", "noop"))
    if page < total - 1:
        nav.append(btn("➡️", f"ban:page:{page+1}"))
    if nav:
        rows.append(nav)
    rows.append([btn("🔙 برگشت", "panel:main")])

    txt = f"🚫 بن‌شده‌ها ({len(items)})\n\n" + ("روی اسم بزن:" if items else "خالیه.")
    return txt, kb(rows)


def muted_panel(chat_id, page=0):
    muted = get("muted", chat_id) or {}
    now = time.time()
    active = {uid: exp for uid, exp in muted.items() if exp > now}
    if active != muted:
        set_("muted", chat_id, active)

    items = list(active.items())
    per_page = 8
    total = max(1, (len(items) + per_page - 1) // per_page)
    page = max(0, min(page, total - 1))
    chunk = items[page * per_page:(page + 1) * per_page]

    rows = []
    for uid, exp in chunk:
        rem = int(exp - now)
        if rem > 3600:
            t = f"{rem // 3600}h"
        elif rem > 60:
            t = f"{rem // 60}m"
        else:
            t = f"{rem}s"
        rows.append([btn(f"🔊 آزاد ({t})", f"mute:unmute:{uid}:{page}")])

    nav = []
    if page > 0:
        nav.append(btn("⬅️", f"mute:page:{page-1}"))
    nav.append(btn(f"{page+1}/{total}", "noop"))
    if page < total - 1:
        nav.append(btn("➡️", f"mute:page:{page+1}"))
    if nav:
        rows.append(nav)
    rows.append([btn("🔊 آزاد کردن همه", "mute:unmuteall")])
    rows.append([btn("🔙 برگشت", "panel:main")])

    txt = f"🔇 سکوت‌شده‌ها ({len(items)})\n\n" + ("روی اسم بزن:" if items else "خالیه.")
    return txt, kb(rows)


# ============================================================
# آمار
# ============================================================
def stats_panel(chat_id):
    w = sum((get("warnings", chat_id) or {}).values())
    m = len(get("muted", chat_id) or {})
    b = len(get("banned_users", chat_id) or {})
    locks_on = sum(1 for v in (get("locks", chat_id) or {}).values() if v)
    locks_total = len(lock_mod.LOCKS)
    as_on = (get("antispam", chat_id) or {}).get("enabled", False)
    bw_on = (get("badword", chat_id) or {}).get("enabled", False)
    w_on = (get("welcome", chat_id) or {}).get("enabled", False)
    slow = (get("slowmode", chat_id) or {}).get("seconds", 0)
    gj_on = get_group_join(chat_id).get("enabled", False)
    nm_on = features.get_night_mode(chat_id).get("enabled", False)
    sleep_on = features.get_sleep_mode(chat_id).get("enabled", False)
    wl_count = len(get("whitelist", chat_id) or [])
    cc_count = len(features.list_custom_cmds(chat_id))
    gl_on = bool((get("group_lock", chat_id) or {}).get("enabled"))
    xp_data = get("xp", chat_id) or {}
    notes = get("notes", chat_id) or {}
    c = api.members_count(chat_id)
    cnt = c["result"] if c and c.get("ok") else "?"

    txt = (
        f"📊 آمار گروه\n\n"
        f"👥 اعضا: {cnt}\n"
        f"🔒 قفل‌ها: {locks_on} از {locks_total}\n"
        f"🔐 قفل کل گروه: {'روشن' if gl_on else 'خاموش'}\n"
        f"🛡 ضد اسپم: {'روشن' if as_on else 'خاموش'}\n"
        f"🚫 ضد فحش: {'روشن' if bw_on else 'خاموش'}\n"
        f"⏱ حالت آهسته: {slow}s\n"
        f"🌙 شب: {'روشن' if nm_on else 'خاموش'}\n"
        f"😴 خواب: {'روشن' if sleep_on else 'خاموش'}\n"
        f"📢 عضویت اجباری: {'روشن' if gj_on else 'خاموش'}\n"
        f"👋 خوش‌آمد: {'روشن' if w_on else 'خاموش'}\n\n"
        f"⚠️ اخطارها: {w}\n"
        f"🔇 سکوت: {m}\n"
        f"🚫 بن: {b}\n"
        f"⭐ سفیدلیست: {wl_count}\n"
        f"💬 سفارشی: {cc_count}\n"
        f"📌 یادداشت: {len(notes)}\n"
        f"⭐ XP: {len(xp_data)} کاربر"
    )
    rows = [[btn("🔄 بروزرسانی", "panel:stats"), btn("🔙 برگشت", "panel:main")]]
    return txt, kb(rows)


# ============================================================
# پاکسازی
# ============================================================
def clean_panel(chat_id):
    rows = [
        [btn("⚠️ پاک اخطارها", "clean:warns"), btn("🔊 آزاد سکوت‌ها", "clean:mutes")],
        [btn("🚫 پاک لیست بن", "clean:bans"), btn("🚫 پاک کلمات", "clean:words")],
        [btn("⚠️ پاک هشدار کلمات", "clean:bwwarns")],
        [btn("📌 پاک یادداشت", "clean:notes")],
        [btn("⭐ پاک سفیدلیست", "clean:whitelist"), btn("💬 پاک سفارشی", "clean:cc")],
        [btn("🚫 پاک ضدفحش اضافی", "clean:extrabw")],
        [btn("⚠️ پاک هشدار قفل", "clean:lockwarns")],
        [btn("⚠️ پاک هشدار ضد اسپم", "clean:aswarns")],
        [btn("😴 پاک خواب", "clean:sleep")],
        [btn("📢 پاک کش عضویت", "clean:joincache")],
        [btn("🔓 آزادسازی کاربران قفل", "clean:freelocked")],
        [btn("🔄 ریست کامل", "clean:all")],
        [btn("🔙 برگشت", "panel:main")],
    ]
    return "🧹 پاکسازی\n\nچی رو پاک کنم؟", kb(rows)


# ============================================================
# دستورات سریع
# ============================================================
def quick_panel(chat_id):
    rows = [
        [btn("📜 قوانین", "quick:rules"), btn("📊 آمار", "panel:stats")],
        [btn("🔗 لینک گروه", "quick:link"), btn("🏆 برترین‌ها", "quick:top")],
        [btn("📋 لیست سیاه", "panel:blacklist")],
        [btn("👑 تاپ ۱۰", "panel:top10")],
        [btn("📅 روزانه", "rank:daily"), btn("📆 هفتگی", "rank:weekly")],
        [btn("🗓 ماهانه", "rank:monthly")],
        [btn("🏆 برترین امروز", "panel:top_today")],
        [btn("🎮 سرگرمی", "panel:entertainment"), btn("🏆 لیدربرد", "panel:leaderboards")],
        [btn("🎬 گیف", "gif:start")],
        [btn("💬 پنل پیوی", "panel:pv_open")],
        [btn("🔙 برگشت", "panel:main")],
    ]
    return "⚡ دستورات سریع", kb(rows)


# ============================================================
# مدیریت کاربر
# ============================================================
def user_manage_panel(chat_id, target_id, target_name):
    rows = [
        [btn("⚠️ اخطار", f"um:warn:{target_id}"), btn("✅ حذف اخطار", f"um:unwarn:{target_id}")],
        [btn("🔇 سکوت", f"um:mute:{target_id}"), btn("🔊 آزاد", f"um:unmute:{target_id}")],
        [btn("🚫 بن", f"um:ban:{target_id}"), btn("👢 اخراج", f"um:kick:{target_id}")],
        [btn("👑 ارتقا", f"um:promote:{target_id}"), btn("⬇️ تنزل", f"um:demote:{target_id}")],
        [btn("🏷 لقب", f"um:title:{target_id}"), btn("👤 پروفایل", f"um:profile:{target_id}")],
        [btn("⭐ سفیدلیست", f"um:wladd:{target_id}")],
        [btn("❌ بستن", "um:close")],
    ]
    return f"👤 مدیریت {target_name}\nآیدی: {target_id}", kb(rows)


def mute_duration_panel(chat_id, target_id):
    rows = [
        [btn("۱ دقیقه", f"md:{target_id}:60"), btn("۵ دقیقه", f"md:{target_id}:300")],
        [btn("۱۰ دقیقه", f"md:{target_id}:600"), btn("۳۰ دقیقه", f"md:{target_id}:1800")],
        [btn("۱ ساعت", f"md:{target_id}:3600"), btn("۶ ساعت", f"md:{target_id}:21600")],
        [btn("۱ روز", f"md:{target_id}:86400"), btn("۱ هفته", f"md:{target_id}:604800")],
        [btn("♾ دائمی", f"md:{target_id}:0")],
        [btn("🔙 برگشت", f"um:back:{target_id}")],
    ]
    return "🔇 مدت سکوت:", kb(rows)


# ============================================================
# حالت آهسته
# ============================================================
def slowmode_panel(chat_id):
    cur = (get("slowmode", chat_id) or {}).get("seconds", 0)

    if cur == 0:
        status = "خاموش"
        toggle_btn = btn("🟢 روشن کردن (۵ ثانیه)", "sm:toggle_on")
    else:
        if cur < 60:
            status = f"{cur} ثانیه"
        elif cur < 3600:
            status = f"{cur // 60} دقیقه"
        else:
            status = f"{cur // 3600} ساعت"
        toggle_btn = btn("🔴 خاموش کردن", "sm:set:0")

    rows = [
        [toggle_btn],
        [btn("5s", "sm:set:5"), btn("10s", "sm:set:10"), btn("30s", "sm:set:30")],
        [btn("1m", "sm:set:60"), btn("5m", "sm:set:300"), btn("10m", "sm:set:600")],
        [btn("🔙 برگشت", "panel:main")],
    ]

    text = (
        f"⏱ حالت آهسته\n\n"
        f"وضعیت: {status}\n\n"
        f"کاربرا بین پیام‌هاشون باید صبر کنن.\n"
        f"ادمین‌ها محدودیتی ندارن."
    )
    return text, kb(rows)


# ============================================================
# حالت شب
# ============================================================
def night_mode_panel(chat_id):
    cfg = features.get_night_mode(chat_id)
    enabled = cfg.get("enabled", False)
    start = cfg.get("start", "23:00")
    end = cfg.get("end", "07:00")
    now = features._now_hhmm()
    active_now = features.is_night_time(chat_id)

    status = "خاموش"
    if enabled:
        status = "روشن (الان فعاله)" if active_now else "روشن"

    rows = [
        [btn(f"{status}", "nm:toggle")],
        [btn(f"⏰ شروع: {start}", "nm:set_start"), btn(f"⏰ پایان: {end}", "nm:set_end")],
        [btn("🔙 برگشت", "panel:main")],
    ]

    return (
        f"🌙 حالت شب\n\n"
        f"ساعت الان: {now} (ایران)\n"
        f"وضعیت: {status}\n"
        f"از {start} تا {end}\n\n"
        f"تو این بازه فقط ادمین‌ها پیام می‌دن.",
        kb(rows)
    )


# ============================================================
# حالت خواب
# ============================================================
def sleep_mode_panel(chat_id):
    cfg = features.get_sleep_mode(chat_id)
    enabled = cfg.get("enabled", False)
    ranges = cfg.get("ranges", [])
    now = features._now_hhmm()
    active_now = features.is_sleep_time(chat_id)

    rows = []
    status = "روشن" if enabled else "خاموش"
    if enabled and active_now:
        status = "روشن (الان فعاله)"
    rows.append([btn(status, "sleep:toggle")])

    for i, r in enumerate(ranges[:ITEMS_PER_PAGE]):
        rows.append([btn(f"❌ {r['start']} تا {r['end']}", f"sleep:rm:{i}")])

    if len(ranges) < ITEMS_PER_PAGE:
        rows.append([btn("➕ افزودن بازه", "sleep:add")])
    if ranges:
        rows.append([btn("🗑 پاک کردن همه", "sleep:clear")])

    rows.append([btn("🔙 برگشت", "panel:main")])

    txt = (
        f"😴 حالت خواب\n\n"
        f"ساعت الان: {now}\n"
        f"وضعیت: {status}\n\n"
    )
    if ranges:
        txt += "بازه‌های خاموشی:\n"
        for i, r in enumerate(ranges, 1):
            is_this = features._in_range(now, r["start"], r["end"]) if enabled else False
            mark = " ✅" if is_this else ""
            txt += f"{i}. {r['start']} تا {r['end']}{mark}\n"
    else:
        txt += "هنوز بازه‌ای تنظیم نشده.\nمثال: 03:00 تا 04:00"
    return txt, kb(rows)


def sleep_confirm_panel(chat_id, start, end):
    safe_start = start.replace(":", "_")
    safe_end = end.replace(":", "_")
    rows = [
        [btn("✅ تایید", f"sleep:confirm:{safe_start}:{safe_end}")],
        [btn("❌ لغو", "sleep:add_cancel")],
    ]
    return f"😴 تایید بازه خواب\n\nاز {start} تا {end}\n\nتایید می‌کنی؟", kb(rows)


# ============================================================
# سفیدلیست
# ============================================================
def whitelist_panel(chat_id, page=0):
    wl = get("whitelist", chat_id) or []
    items = list(wl)
    per_page = 10
    total = max(1, (len(items) + per_page - 1) // per_page)
    page = max(0, min(page, total - 1))
    chunk = items[page * per_page:(page + 1) * per_page]

    rows = []
    for uid in chunk:
        rows.append([btn(f"❌ {uid}", f"wl:rm:{uid}:{page}")])

    nav = []
    if page > 0:
        nav.append(btn("⬅️", f"wl:page:{page-1}"))
    nav.append(btn(f"{page+1}/{total}", "noop"))
    if page < total - 1:
        nav.append(btn("➡️", f"wl:page:{page+1}"))
    if nav:
        rows.append(nav)
    rows.append([btn("➕ افزودن", "wl:add")])
    rows.append([btn("🔙 برگشت", "panel:main")])

    txt = (
        f"⭐ سفیدلیست ({len(items)})\n\n"
        "این کاربرا از ضداسپم، شب و خواب مستثنا هستن.\n\n"
        + ("روی هر کدوم بزن:" if items else "خالیه.")
    )
    return txt, kb(rows)


# ============================================================
# دستورات سفارشی
# ============================================================
def custom_cmds_panel(chat_id, page=0):
    cmds = features.list_custom_cmds(chat_id)
    items = list(cmds.items())
    per_page = 8
    total = max(1, (len(items) + per_page - 1) // per_page)
    page = max(0, min(page, total - 1))
    chunk = items[page * per_page:(page + 1) * per_page]

    rows = []
    for name, reply in chunk:
        preview = reply[:15] + "..." if len(reply) > 15 else reply
        rows.append([btn(f"❌ /{name} → {preview}", f"cc:rm:{name}:{page}")])

    nav = []
    if page > 0:
        nav.append(btn("⬅️", f"cc:page:{page-1}"))
    nav.append(btn(f"{page+1}/{total}", "noop"))
    if page < total - 1:
        nav.append(btn("➡️", f"cc:page:{page+1}"))
    if nav:
        rows.append(nav)
    rows.append([btn("➕ افزودن", "cc:add")])
    rows.append([btn("🔙 برگشت", "panel:main")])

    txt = f"💬 دستورات سفارشی ({len(items)})\n" + ("هر کاربر بزنه، پاسخ می‌گیره." if items else "خالیه.")
    return txt, kb(rows)


# ============================================================
# یادداشت‌ها
# ============================================================
def notes_panel(chat_id):
    notes = get("notes", chat_id) or {}

    rows = []
    if notes:
        for name in list(notes.keys())[:ITEMS_PER_PAGE]:
            display = name[:25] + "..." if len(name) > 25 else name
            rows.append([btn(f"📝 {display}", f"note:view:{name}")])

    rows.append([btn("➕ افزودن", "note:add"), btn("🗑 حذف", "note:remove_panel")])
    rows.append([btn("🔙 برگشت", "panel:main")])

    txt = f"📌 یادداشت‌ها ({len(notes)})\n\n"
    if notes:
        txt += "روی هر یادداشت بزن تا متنش رو ببینی."
    else:
        txt += "هنوز یادداشتی ثبت نشده."
    return txt, kb(rows)


def note_view_panel(chat_id, name):
    notes = get("notes", chat_id) or {}
    if name not in notes:
        return "یادداشت پیدا نشد.", kb([[btn("🔙 برگشت", "panel:notes")]])

    content = notes.get(name, "") or "(خالی)"
    safe_name = html.escape(name)
    safe_content = html.escape(content)

    txt = f"📝 {safe_name}\n\n{safe_content}"
    rows = [
        [btn("🔙 برگشت به لیست", "panel:notes")],
        [btn("🗑 حذف این یادداشت", f"note:rm:{name}")],
    ]
    return txt, kb(rows)


def notes_remove_panel(chat_id):
    notes = get("notes", chat_id) or {}
    rows = []
    for name in list(notes.keys())[:ITEMS_PER_PAGE]:
        display = name[:25] + "..." if len(name) > 25 else name
        rows.append([btn(f"❌ {display}", f"note:rm:{name}")])
    rows.append([btn("🔙 برگشت", "panel:notes")])
    if not notes:
        return "لیست خالی.", kb([[btn("🔙 برگشت", "panel:notes")]])
    return "روی یادداشت بزن تا حذف بشه:", kb(rows)


# ============================================================
# قابلیت‌های پیشرفته
# ============================================================
def extras_panel(chat_id):
    invites = get("invites", chat_id) or {}
    wr = (get("weekly_report", chat_id) or {}).get("enabled", False)

    rows = [
        [btn("🧠 آزمون", "ext:quiz"), btn("🎁 قرعه‌کشی", "ext:lottery")],
        [btn("👑 رتبه هفتگی", "ext:rank"), btn("🔗 دعوت‌ها", "ext:invites")],
        [btn(f"📅 گزارش هفتگی {'🟢' if wr else '🔴'}", "ext:weekly_report")],
        [btn("🎬 گیف", "gif:start"), btn("🐛 گزارش باگ", "bug:report")],
        [btn("🔙 برگشت", "panel:main")],
    ]
    text = (
        f"قابلیت‌های پیشرفته\n\n"
        f"🔗 دعوت: {len(invites)}\n"
        f"📅 گزارش هفتگی: {'روشن' if wr else 'خاموش'}\n\n"
        f"از دکمه‌ها استفاده کن 👇"
    )
    return text, kb(rows)


def invites_panel(chat_id):
    txt = extras.get_invite_leaderboard(chat_id)
    return txt, kb([[btn("🔙 برگشت", "panel:extras")]])


def weekly_report_panel(chat_id):
    wr = (get("weekly_report", chat_id) or {}).get("enabled", False)
    rows = [
        [btn(f"{'🔴 خاموش کن' if wr else '🟢 روشن کن'}", "ext:wr_toggle")],
        [btn("📅 نمایش فوری", "ext:wr_show")],
        [btn("🔙 برگشت", "panel:extras")],
    ]
    return (
        f"📅 گزارش هفتگی خودکار\n\n"
        f"وضعیت: {'روشن' if wr else 'خاموش'}\n\n"
        f"وقتی روشن باشه، هر جمعه ساعت ۲۰ گزارش میاد.",
        kb(rows)
    )


# ============================================================
# گروه‌های کاربر (تو پیوی)
# ============================================================
def user_groups_panel(user_id):
    bot_username = api.get_bot_username()

    groups = storage.get("bot_groups", "list") or {}
    user_groups = []

    for gid, info in list(groups.items())[:50]:
        try:
            r = api.get_member(int(gid), user_id)
            if r and r.get("ok"):
                st = r["result"].get("status", "")
                if st in ("creator", "administrator"):
                    user_groups.append({
                        "id": gid,
                        "title": info.get("title", f"گروه {gid}"),
                        "status": st,
                    })
        except Exception:
            pass

    rows = []
    if user_groups:
        for g in user_groups[:8]:
            icon = "👑" if g["status"] == "creator" else "🛡"
            title = g["title"]
            if len(title) > 25:
                title = title[:25] + "..."
            rows.append([btn(f"{icon} {title}", f"ug:info:{g['id']}")])

    if bot_username:
        add_url = f"https://ble.ir/{bot_username}?startgroup=true"
        rows.append([btn("➕ افزودن به گروه جدید", url=add_url)])
    else:
        rows.append([btn("➕ افزودن به گروه جدید", "ug:how")])

    rows.append([btn("🔙 برگشت", "user:main")])

    text = f"👥 گروه‌های شما\n\n📊 تعداد: {len(user_groups)}\n\n"

    if user_groups:
        text += "این گروه‌هایی هستن که شما مدیرشون هستید و ربات توش حضور داره:\n\n"
        for g in user_groups[:8]:
            icon = "👑" if g["status"] == "creator" else "🛡"
            text += f"{icon} {g['title']}\n"
        text += "\n💡 برای افزودن به گروه جدید، دکمه زیر رو بزن:"
    else:
        text += ("شما هنوز مدیر هیچ گروهی که ربات توش باشه نیستید.\n\n"
                 "👇 برای افزودن ربات به گروه جدید، دکمه زیر رو بزن:")

    return text, kb(rows)


def user_group_info_panel(chat_id, group_id):
    try:
        c = api.get_chat(int(group_id))
        if not c or not c.get("ok"):
            return "گروه پیدا نشد.", kb([[btn("🔙 برگشت", "ug:panel")]])
        info = c["result"]
        title = info.get("title", "گروه")
        uname = info.get("username", "")
        link = info.get("invite_link", "")
        if not link and uname:
            link = f"https://ble.ir/{uname}"

        text = f"👥 {title}\n\n🆔 آیدی: {group_id}\n"
        if uname:
            text += f"🔗 یوزرنیم: @{api.esc_md(uname)}\n"
        if link:
            text += f"🔗 لینک: {link}\n"

        rows = []
        if link:
            rows.append([btn("🔗 ورود به گروه", url=link)])
        rows.append([btn("🔙 برگشت", "ug:panel")])
        return text, kb(rows)
    except Exception as e:
        return f"خطا: {e}", kb([[btn("🔙 برگشت", "ug:panel")]])


# ============================================================
# پردازش callback گروه
# ============================================================
def handle_callback(cb):
    cb_id = cb["id"]
    data = cb.get("data", "")
    msg = cb.get("message", {})
    chat = msg.get("chat") or {}
    chat_id = chat.get("id")
    if chat_id is None:
        return
    chat_type = chat.get("type") or "supergroup"
    msg_id = msg.get("message_id")
    user = cb.get("from") or {}
    user_id = user.get("id")
    if user_id is None:
        return
    first_name = user.get("first_name", "کاربر")

    if chat_type == "private":
        handle_private_callback(cb, cb_id, data, chat_id, msg_id, user)
        return

    # ✅ fallback دکمه‌های copy_text
    if data.startswith("cp:"):
        val = data[3:]
        api.answer_callback(cb_id, f"📋 کپی کن:\n{val}", alert=True)
        return

    # ✅ callbackهای کاربر — تو گروه و پیوی هر دو کار کنن
    if (data.startswith("user:") or data.startswith("ug:") or
        data.startswith("game:") or data.startswith("mode:") or
        data.startswith("lb:") or data.startswith("rank:") or
        data.startswith("anon_cancel:") or data.startswith("todd:setrounds:")):
        try:
            import user_panels
            user_panels.handle_user_callback(cb, cb_id, data, chat_id, msg_id, user)
            return
        except Exception as e:
            print(f"[group:user] {e}")
            import traceback
            traceback.print_exc()
            api.answer_callback(cb_id, "خطا", alert=True)
            return

    # ✅ gif تو گروه هم کار می‌کنه
    if data.startswith("gif:"):
        try:
            import gifmaker
            gifmaker.handle_callback(cb, cb_id, data, chat_id, msg_id, user)
            return
        except Exception as e:
            print(f"[group:gif] {e}")
            api.answer_callback(cb_id, "خطا", alert=True)
            return

    PUBLIC_CALLBACKS = (
        data == "noop"
        or data.startswith("poll:vote:")
        or data.startswith("quiz:ans:")
        or data.startswith("gj:check:")
        or data == "panel:top10"
        or data == "panel:help"
        or data == "panel:pv_open"
        or data == "panel:group_lock_toggle"
        or data == "panel:free_locked"
        or data == "panel:registered_users"
        or data == "panel:tag_menu"
        or data.startswith("tag:")
        or data.startswith("users:page:")
        or data.startswith("ai:")
        or data.startswith("asl:")
    )

    if not PUBLIC_CALLBACKS:
        if not check_panel_access(chat_id, msg_id, user_id):
            api.answer_callback(cb_id, "این پنل مخصوص شما نیست.", alert=True)
            return
        from admin import is_admin
        if not is_admin(chat_id, user_id):
            api.answer_callback(cb_id, "فقط ادمین‌های گروه.", alert=True)
            return

    text, markup = None, None
    answer = ""
    parse_mode = "Markdown"

    if data == "noop":
        api.answer_callback(cb_id, "")
        return

    if data.startswith("gj:check:"):
        try:
            target_uid = int(data.split(":")[2])
        except Exception:
            target_uid = user_id
        if target_uid != user_id:
            api.answer_callback(cb_id, "این دکمه مخصوص شما نیست.", alert=True)
            return

        try:
            invalidate_join_cache(chat_id, user_id)
        except Exception:
            pass

        if check_group_join(chat_id, user_id):
            api.answer_callback(cb_id, "تایید شد")
            try:
                api.edit_message(chat_id, msg_id,
                    f"✅ {first_name}، عضویتت تایید شد!\n\n"
                    f"حالا می‌تونی تو گروه پیام بذاری.",
                    parse_mode="Markdown")
            except Exception:
                pass
            try:
                def _del():
                    time.sleep(5)
                    try:
                        api.delete(chat_id, msg_id)
                    except Exception:
                        pass
                threading.Thread(target=_del, daemon=True).start()
            except Exception:
                pass
        else:
            api.answer_callback(cb_id, "هنوز عضو نشدی!", alert=True)
        return

    # ==================== پنل‌ها ====================
    if data == "panel:main":
        text, markup = main_panel(chat_id)
    elif data == "panel:locks":
        text, markup = locks_panel(chat_id)
    elif data == "panel:antispam":
        text, markup = antispam_panel(chat_id)
    elif data == "panel:badword":
        text, markup = badword_panel(chat_id)
    elif data == "panel:welcome":
        text, markup = welcome_panel(chat_id)
    elif data == "panel:words":
        text, markup = words_panel(chat_id)
    elif data == "panel:rules":
        text, markup = rules_panel(chat_id)
    elif data == "panel:warns":
        text, markup = warns_panel(chat_id)
    elif data == "panel:blacklist":
        text, markup = blacklist_panel(chat_id)
    elif data == "panel:banned":
        text, markup = banned_panel(chat_id)
    elif data == "panel:muted":
        text, markup = muted_panel(chat_id)
    elif data == "panel:registered_users":
        text, markup = registered_users_panel(chat_id)
    elif data == "panel:tag_menu":
        text, markup = tag_menu_panel(chat_id)
    elif data.startswith("users:page:"):
        try:
            page = int(data.split(":")[2])
        except Exception:
            page = 0
        text, markup = registered_users_panel(chat_id, page)
    elif data == "tag:all":
        api.answer_callback(cb_id, "دارم تگ می‌کنم...")
        api.delete(chat_id, msg_id)
        from admin import tag_users_smart
        tag_users_smart(chat_id, user_id, first_name, "all")
        return
    elif data == "tag:7h":
        api.answer_callback(cb_id, "دارم تگ می‌کنم...")
        api.delete(chat_id, msg_id)
        from admin import tag_users_smart
        tag_users_smart(chat_id, user_id, first_name, "7")
        return
    elif data == "tag:24h":
        api.answer_callback(cb_id, "دارم تگ می‌کنم...")
        api.delete(chat_id, msg_id)
        from admin import tag_users_smart
        tag_users_smart(chat_id, user_id, first_name, "24")
        return
    elif data == "tag:week":
        api.answer_callback(cb_id, "دارم تگ می‌کنم...")
        api.delete(chat_id, msg_id)
        from admin import tag_users_smart
        tag_users_smart(chat_id, user_id, first_name, "week")
        return
    elif data == "panel:stats":
        text, markup = stats_panel(chat_id)
    elif data == "panel:clean":
        text, markup = clean_panel(chat_id)
    elif data == "panel:quick":
        text, markup = quick_panel(chat_id)
    elif data == "panel:slowmode":
        text, markup = slowmode_panel(chat_id)
    elif data == "panel:notes":
        st = get("settings", chat_id) or {}
        st["notes_panel_msg"] = msg_id
        set_("settings", chat_id, st)
        text, markup = notes_panel(chat_id)
    elif data == "panel:group_join":
        text, markup = group_join_panel(chat_id)
    elif data == "panel:night_mode":
        text, markup = night_mode_panel(chat_id)
    elif data == "panel:sleep":
        text, markup = sleep_mode_panel(chat_id)
    elif data == "panel:whitelist":
        text, markup = whitelist_panel(chat_id)
    elif data == "panel:custom_cmds":
        text, markup = custom_cmds_panel(chat_id)
    elif data == "panel:entertainment":
        text, markup = entertainment_panel(chat_id)
    elif data == "panel:leaderboards":
        text, markup = leaderboards_panel(chat_id)
    elif data == "panel:extras":
        text, markup = extras_panel(chat_id)
    elif data == "panel:top10":
        games.cmd_ranking_period(chat_id, "all")
        api.answer_callback(cb_id, "🏆")
        return

    elif data == "panel:group_lock_toggle":
        gl = get("group_lock", chat_id) or {}
        new_state = not gl.get("enabled")
        set_("group_lock", chat_id, {"enabled": new_state, "by": user_id})
        try:
            lock_mod.apply_permissions(chat_id)
        except Exception:
            pass
        answer = "قفل شد" if new_state else "باز شد"
        text, markup = main_panel(chat_id)

    elif data == "panel:free_locked":
        locked = get("locked_users", chat_id) or {}
        count = len(locked)
        if count == 0:
            api.answer_callback(cb_id, "کسی قفل نیست")
            return
        try:
            lock_mod.clear_lock_list(chat_id)
        except Exception:
            pass
        answer = f"{count} کاربر آزاد شد"
        text, markup = main_panel(chat_id)

    elif data == "panel:help":
        text, markup = help_main_panel()

    elif data == "panel:pv_open":
        try:
            username = api.get_bot_username()
            if username:
                url = f"https://ble.ir/{username}"
                rows = [[btn("🚀 باز کردن پنل در پیوی", url=url)]]
                try:
                    api.edit_message(chat_id, msg_id,
                        "💬 پنل در پیوی\n\n"
                        "با کلیک روی دکمه زیر، ربات تو پیوی باز می‌شه.\n\n"
                        "👇",
                        markup={"inline_keyboard": rows})
                    api.answer_callback(cb_id, "🚀")
                except Exception:
                    api.send(chat_id, f"پنل در پیوی:\n{url}", reply_to=0)
                    api.answer_callback(cb_id, "🚀")
            else:
                bid = api.bot_id()
                api.answer_callback(cb_id, f"یوزرنیم نداره. آیدی: {bid}", alert=True)
        except Exception as e:
            print(f"[pv_open] {e}")
            api.answer_callback(cb_id, "خطا", alert=True)
        return

    elif data == "w:back_to_panel":
        text, markup = welcome_panel(chat_id)

    elif data.startswith("bl:unban:"):
        uid = data.split(":")[2]
        try:
            api.unban(chat_id, int(uid))
        except Exception:
            pass
        banned = get("banned_users", chat_id) or {}
        banned.pop(uid, None)
        set_("banned_users", chat_id, banned)
        answer = "آنبن شد"
        text, markup = blacklist_panel(chat_id)
    elif data.startswith("bl:unmute:"):
        uid = data.split(":")[2]
        perms = {"can_send_messages": True, "can_send_media_messages": True,
                 "can_send_other_messages": True, "can_add_web_page_previews": True}
        try:
            api.restrict(chat_id, int(uid), perms)
        except Exception:
            pass
        muted = get("muted", chat_id) or {}
        muted.pop(uid, None)
        set_("muted", chat_id, muted)
        try:
            lock_mod.remove_from_lock_list(chat_id, int(uid))
        except Exception:
            pass
        answer = "آزاد شد"
        text, markup = blacklist_panel(chat_id)

    elif data == "bw:toggle":
        cfg = get("badword", chat_id) or {}
        cfg["enabled"] = not cfg.get("enabled", False)
        cfg.setdefault("max_warns", 3)
        set_("badword", chat_id, cfg)
        answer = "فعال" if cfg["enabled"] else "غیرفعال"
        text, markup = badword_panel(chat_id)
    elif data == "bw:setmax":
        text, markup = badword_max_panel(chat_id)
    elif data.startswith("bw:max:"):
        n = int(data.split(":")[2])
        cfg = get("badword", chat_id) or {}
        cfg["max_warns"] = n
        set_("badword", chat_id, cfg)
        answer = str(n)
        text, markup = badword_panel(chat_id)
    elif data == "bw:extra_list":
        text, markup = badword_extra_list_panel(chat_id)
    elif data == "bw:add":
        api.answer_callback(cb_id, "")
        st = get("settings", chat_id) or {}
        st["wait_badword"] = user_id
        st["prompt_msg_id"] = msg_id
        st["prompt_back"] = "panel:badword"
        set_("settings", chat_id, st)
        text, markup = _prompt(
            "🚫 افزودن کلمه به ضدفحش",
            "کلمه یا کلمات رو بفرست (با فاصله).",
            "برای لغو بنویس: لغو",
            "panel:badword", "bw:cancel")
    elif data == "bw:cancel":
        st = get("settings", chat_id) or {}
        st.pop("wait_badword", None)
        st.pop("prompt_msg_id", None)
        st.pop("prompt_back", None)
        set_("settings", chat_id, st)
        api.answer_callback(cb_id, "لغو شد")
        text, markup = badword_panel(chat_id)
    elif data == "bw:remove_panel":
        text, markup = badword_remove_panel(chat_id)
    elif data.startswith("bw:rm:"):
        i = int(data.split(":")[2])
        extra = get("extra_bad_words", chat_id) or []
        if 0 <= i < len(extra):
            extra.pop(i)
            set_("extra_bad_words", chat_id, extra)
        text, markup = badword_extra_list_panel(chat_id)
    elif data == "bw:clear_extra":
        set_("extra_bad_words", chat_id, [])
        text, markup = badword_extra_list_panel(chat_id)

    elif data == "ent:help":
        text, markup = entertainment_help(chat_id)
    elif data == "ent:guess":
        games.cmd_guess(chat_id)
        api.answer_callback(cb_id, "🎯")
        return
    elif data == "ent:word":
        games.cmd_word(chat_id)
        api.answer_callback(cb_id, "💭")
        return
    elif data == "ent:scramble":
        games.cmd_scramble(chat_id)
        api.answer_callback(cb_id, "🔤")
        return
    elif data == "ent:rps":
        games.cmd_rps(chat_id)
        api.answer_callback(cb_id, "🪨")
        return
    elif data == "ent:doss":
        games.cmd_doss(chat_id, user_id, first_name)
        api.answer_callback(cb_id, "🎮")
        return
    elif data == "ent:joke":
        games.cmd_joke(chat_id, user_id, first_name, msg_id)
        api.answer_callback(cb_id, "😂")
        return
    elif data == "ent:tod":
        games.cmd_tod_panel(chat_id, user_id, first_name, "bot")
        api.answer_callback(cb_id, "🎯")
        return
    elif data == "ent:mafia":
        games.cmd_mafia_start(chat_id, user_id, first_name)
        api.answer_callback(cb_id, "🎭")
        return
    elif data == "ent:dice":
        games.cmd_dice(chat_id, msg_id, first_name)
        api.answer_callback(cb_id, "🎲")
        return
    elif data == "ent:coin":
        games.cmd_coin(chat_id, msg_id, first_name)
        api.answer_callback(cb_id, "🪙")
        return
    elif data.startswith("lb:"):
        key = data.split(":", 1)[1]
        text, markup = show_leaderboard(chat_id, key)

    elif data == "bug:report":
        api.answer_callback(cb_id, "")
        st = get("settings", chat_id) or {}
        st["wait_bug_report"] = user_id
        st["prompt_msg_id"] = msg_id
        st["prompt_back"] = "panel:main"
        set_("settings", chat_id, st)
        text, markup = _prompt(
            "🐛 گزارش باگ",
            "مشکل یا باگ رو کامل توضیح بده.",
            "برای لغو بنویس: لغو",
            "panel:main")

    elif data == "ext:quiz":
        ok, msg_txt = extras.start_quiz(chat_id, user_id, first_name)
        if not ok:
            api.answer_callback(cb_id, msg_txt, alert=True)
        else:
            api.answer_callback(cb_id, "شروع شد")
        return
    elif data == "ext:lottery":
        winners, err = extras.draw_lottery(chat_id, user_id, first_name, 1)
        if err:
            api.answer_callback(cb_id, err, alert=True)
            return
        bot_users = storage.get("bot_users", "list") or {}
        xp_data = get("xp", chat_id) or {}
        name = xp_data.get(winners[0], {}).get("name", "") or bot_users.get(winners[0], {}).get("name", "کاربر")
        api.send(chat_id, f"🎁 برنده: {name}", parse_mode="Markdown", reply_to=0)
        api.answer_callback(cb_id, "🎁")
        return
    elif data == "ext:rank":
        txt = extras.get_weekly_ranking(chat_id)
        api.send(chat_id, txt, parse_mode="Markdown", reply_to=0)
        api.answer_callback(cb_id, "")
        return
    elif data == "ext:invites":
        text, markup = invites_panel(chat_id)
    elif data == "ext:weekly_report":
        text, markup = weekly_report_panel(chat_id)
    elif data == "ext:wr_toggle":
        wr = (get("weekly_report", chat_id) or {}).get("enabled", False)
        extras.set_weekly_report(chat_id, not wr)
        answer = "روشن" if not wr else "خاموش"
        text, markup = weekly_report_panel(chat_id)
    elif data == "ext:wr_show":
        txt = extras.build_weekly_report(chat_id)
        api.send(chat_id, txt, parse_mode="Markdown", reply_to=0)
        api.answer_callback(cb_id, "")
        return

    elif data.startswith("quiz:ans:"):
        parts = data.split(":")
        qid = parts[2]
        ans_idx = int(parts[3])
        ok, msg_txt = extras.answer_quiz(chat_id, user_id, first_name, qid, ans_idx)
        api.answer_callback(cb_id, msg_txt, alert=True)
        return

    elif data.startswith("lock:page:"):
        text, markup = locks_panel(chat_id, int(data.split(":")[2]))
    elif data.startswith("lock:toggle:"):
        parts = data.split(":")
        name = parts[2]
        page = int(parts[3])
        new = lock_mod.toggle(chat_id, name)
        answer = f"{'🔒' if new else '🔓'} {lock_mod.LOCKS[name]['fa']}"
        text, markup = locks_panel(chat_id, page)
    elif data == "lock:all:on":
        lock_mod.lock_all(chat_id)
        answer = "همه روشن"
        text, markup = locks_panel(chat_id)
    elif data == "lock:all:off":
        lock_mod.unlock_all(chat_id)
        answer = "همه خاموش"
        text, markup = locks_panel(chat_id)
    elif data == "lock:warn_panel":
        text, markup = locks_warn_panel(chat_id)
    elif data.startswith("lock:set_threshold:"):
        try:
            n = int(data.split(":")[2])
        except Exception:
            n = 3
        lock_mod.set_warn_threshold(chat_id, n)
        answer = f"آستانه: {n}"
        text, markup = locks_warn_panel(chat_id)
    elif data == "lock:reset_warns":
        lock_mod.reset_all_warns(chat_id)
        answer = "صفر شد"
        text, markup = locks_warn_panel(chat_id)

    elif data == "as:toggle":
        cfg = get("antispam", chat_id) or {}
        cfg["enabled"] = not cfg.get("enabled", False)
        cfg.setdefault("limit", 5)
        cfg.setdefault("window", 10)
        cfg.setdefault("action", "سکوت")
        cfg.setdefault("action_key", "mute")
        cfg.setdefault("warn_threshold", 3)
        set_("antispam", chat_id, cfg)
        answer = "روشن" if cfg["enabled"] else "خاموش"
        text, markup = antispam_panel(chat_id)
    elif data == "as:limit":
        text, markup = antispam_limit_panel(chat_id)
    elif data == "as:window":
        text, markup = antispam_window_panel(chat_id)
    elif data == "as:action":
        text, markup = antispam_action_panel(chat_id)
    elif data == "as:warn_panel":
        text, markup = antispam_warn_panel(chat_id)
    elif data.startswith("as:set_warn:"):
        try:
            n = int(data.split(":")[2])
        except Exception:
            n = 3
        cfg = get("antispam", chat_id) or {}
        cfg["warn_threshold"] = n
        set_("antispam", chat_id, cfg)
        answer = f"آستانه: {n}"
        text, markup = antispam_warn_panel(chat_id)
    elif data == "as:reset_warns":
        set_("antispam_warns", chat_id, {})
        answer = "صفر شد"
        text, markup = antispam_warn_panel(chat_id)
    elif data.startswith("as:setlimit:"):
        v = int(data.split(":")[2])
        cfg = get("antispam", chat_id) or {}
        cfg["limit"] = v
        set_("antispam", chat_id, cfg)
        answer = str(v)
        text, markup = antispam_panel(chat_id)
    elif data.startswith("as:setwindow:"):
        v = int(data.split(":")[2])
        cfg = get("antispam", chat_id) or {}
        cfg["window"] = v
        set_("antispam", chat_id, cfg)
        answer = f"{v}s"
        text, markup = antispam_panel(chat_id)
    elif data.startswith("as:setaction:"):
        v = data.split(":")[2]
        fa = {"mute": "سکوت", "kick": "اخراج", "ban": "بن"}.get(v, v)
        cfg = get("antispam", chat_id) or {}
        cfg["action"] = fa
        cfg["action_key"] = v
        set_("antispam", chat_id, cfg)
        answer = fa
        text, markup = antispam_panel(chat_id)

    elif data == "w:toggle":
        cfg = get("welcome", chat_id) or {}
        cfg["enabled"] = not cfg.get("enabled", False)
        cfg.setdefault("text", "🎉 {name} عزیز، به {group} خوش آمدی!")
        set_("welcome", chat_id, cfg)
        answer = "روشن" if cfg["enabled"] else "خاموش"
        text, markup = welcome_panel(chat_id)
    elif data == "w:templates":
        text, markup = welcome_templates(chat_id)
    elif data.startswith("w:use:"):
        tpl = data.split(":")[2]
        cfg = get("welcome", chat_id) or {}
        cfg["text"] = TEMPLATES.get(tpl, "")
        cfg["enabled"] = True
        set_("welcome", chat_id, cfg)
        answer = "✅"
        text, markup = welcome_panel(chat_id)
    elif data == "w:preview":
        cfg = get("welcome", chat_id) or {}
        t = cfg.get("text", "")
        if not t:
            answer = "متنی نیست"
        else:
            p = t.replace("{name}", "علی").replace("{group}", "گروه نمونه").replace("{bot}", "آلفا")
            api.send(chat_id, f"پیش‌نمایش:\n\n{p}", reply_to=0)
            api.answer_callback(cb_id, "فرستادم")
            return
        text, markup = welcome_panel(chat_id)
    elif data == "w:clear":
        cfg = get("welcome", chat_id) or {}
        cfg["text"] = ""
        set_("welcome", chat_id, cfg)
        answer = "🗑"
        text, markup = welcome_panel(chat_id)
    elif data == "w:edit":
        api.answer_callback(cb_id, "")
        st = get("settings", chat_id) or {}
        st["wait_welcome"] = user_id
        st["prompt_msg_id"] = msg_id
        st["prompt_back"] = "panel:welcome"
        set_("settings", chat_id, st)
        text, markup = _prompt(
            "📝 متن خوش‌آمد",
            "متن رو بفرست.",
            "متغیرها: {name}، {group}، {bot}\nبرای لغو بنویس: لغو",
            "panel:welcome", "w:canceltext")
    elif data == "w:canceltext":
        st = get("settings", chat_id) or {}
        st.pop("wait_welcome", None)
        st.pop("prompt_msg_id", None)
        st.pop("prompt_back", None)
        set_("settings", chat_id, st)
        api.answer_callback(cb_id, "لغو شد")
        text, markup = welcome_panel(chat_id)
    elif data == "w:setmedia":
        api.answer_callback(cb_id, "")
        st = get("settings", chat_id) or {}
        st["wait_welcome_media"] = user_id
        st["prompt_msg_id"] = msg_id
        st["prompt_back"] = "panel:welcome"
        set_("settings", chat_id, st)
        text, markup = _prompt(
            "🖼 تنظیم مدیا",
            "عکس، ویدیو یا گیف بفرست.",
            "برای لغو بنویس: لغو",
            "panel:welcome", "w:cancelmedia")
    elif data == "w:cancelmedia":
        st = get("settings", chat_id) or {}
        st.pop("wait_welcome_media", None)
        st.pop("prompt_msg_id", None)
        st.pop("prompt_back", None)
        set_("settings", chat_id, st)
        api.answer_callback(cb_id, "لغو شد")
        text, markup = welcome_panel(chat_id)
    elif data == "w:clearmedia":
        features.clear_welcome_media(chat_id)
        answer = "🗑"
        text, markup = welcome_panel(chat_id)
    elif data == "w:autodel":
        rows = [
            [btn("خاموش", "w:ad:0"), btn("5s", "w:ad:5")],
            [btn("10s", "w:ad:10"), btn("30s", "w:ad:30")],
            [btn("60s", "w:ad:60"), btn("5m", "w:ad:300")],
            [btn("🔙 برگشت", "panel:welcome")],
        ]
        text = "⏱ حذف خودکار"
        markup = kb(rows)
    elif data.startswith("w:ad:"):
        sec = int(data.split(":")[2])
        features.set_welcome_autodelete(chat_id, sec)
        answer = f"{sec}s" if sec else "خاموش"
        text, markup = welcome_panel(chat_id)

    elif data == "gj:toggle":
        gj = get_group_join(chat_id)
        gj["enabled"] = not gj.get("enabled", False)
        set_("group_join", chat_id, gj)
        try:
            invalidate_join_cache(chat_id)
        except Exception:
            pass
        answer = "روشن" if gj["enabled"] else "خاموش"
        text, markup = group_join_panel(chat_id)
    elif data == "gj:set":
        api.answer_callback(cb_id, "")
        st = get("settings", chat_id) or {}
        st["wait_group_channel"] = user_id
        st["prompt_msg_id"] = msg_id
        st["prompt_back"] = "panel:group_join"
        set_("settings", chat_id, st)
        text, markup = _prompt(
            "📢 تنظیم کانال عضویت اجباری",
            "آیدی، یوزرنیم یا لینک کانال رو بفرست.",
            "برای لغو بنویس: لغو",
            "panel:group_join", "gj:cancel")
    elif data == "gj:cancel":
        st = get("settings", chat_id) or {}
        st.pop("wait_group_channel", None)
        st.pop("prompt_msg_id", None)
        st.pop("prompt_back", None)
        set_("settings", chat_id, st)
        api.answer_callback(cb_id, "لغو شد")
        text, markup = group_join_panel(chat_id)
    elif data == "gj:clear":
        set_("group_join", chat_id, {"enabled": False})
        try:
            invalidate_join_cache(chat_id)
        except Exception:
            pass
        answer = "🗑"
        text, markup = group_join_panel(chat_id)

    elif data == "nm:toggle":
        cfg = features.get_night_mode(chat_id)
        new_state = not cfg.get("enabled", False)
        features.set_night_mode(chat_id, enabled=new_state)
        answer = "روشن" if new_state else "خاموش"
        text, markup = night_mode_panel(chat_id)
    elif data == "nm:set_start":
        api.answer_callback(cb_id, "")
        st = get("settings", chat_id) or {}
        st["wait_nm_start"] = user_id
        st["prompt_msg_id"] = msg_id
        st["prompt_back"] = "panel:night_mode"
        set_("settings", chat_id, st)
        text, markup = _prompt(
            "⏰ ساعت شروع شب",
            "فرمت: HH:MM — مثال: 23:00",
            "برای لغو بنویس: لغو",
            "panel:night_mode", "nm:cancel")
    elif data == "nm:set_end":
        api.answer_callback(cb_id, "")
        st = get("settings", chat_id) or {}
        st["wait_nm_end"] = user_id
        st["prompt_msg_id"] = msg_id
        st["prompt_back"] = "panel:night_mode"
        set_("settings", chat_id, st)
        text, markup = _prompt(
            "⏰ ساعت پایان شب",
            "فرمت: HH:MM — مثال: 07:00",
            "برای لغو بنویس: لغو",
            "panel:night_mode", "nm:cancel")
    elif data == "nm:cancel":
        st = get("settings", chat_id) or {}
        st.pop("wait_nm_start", None)
        st.pop("wait_nm_end", None)
        st.pop("prompt_msg_id", None)
        st.pop("prompt_back", None)
        set_("settings", chat_id, st)
        api.answer_callback(cb_id, "لغو شد")
        text, markup = night_mode_panel(chat_id)

    elif data == "sleep:toggle":
        cfg = features.get_sleep_mode(chat_id)
        new = not cfg.get("enabled", False)
        features.set_sleep_mode_enabled(chat_id, new)
        answer = "روشن" if new else "خاموش"
        text, markup = sleep_mode_panel(chat_id)
    elif data == "sleep:add":
        api.answer_callback(cb_id, "")
        st = get("settings", chat_id) or {}
        st["wait_sleep_start"] = user_id
        st["prompt_msg_id"] = msg_id
        st["prompt_back"] = "panel:sleep"
        set_("settings", chat_id, st)
        text, markup = _prompt(
            "😴 افزودن بازه خواب (۱/۲)",
            "ساعت شروع رو بفرست.",
            "فرمت: HH:MM — مثال: 03:00\nبرای لغو بنویس: لغو",
            "panel:sleep", "sleep:add_cancel")
    elif data == "sleep:add_cancel":
        st = get("settings", chat_id) or {}
        st.pop("wait_sleep_start", None)
        st.pop("wait_sleep_end", None)
        st.pop("sleep_pending_start", None)
        st.pop("prompt_msg_id", None)
        st.pop("prompt_back", None)
        set_("settings", chat_id, st)
        api.answer_callback(cb_id, "لغو شد")
        text, markup = sleep_mode_panel(chat_id)
    elif data.startswith("sleep:confirm:"):
        parts = data.split(":")
        start = parts[2].replace("_", ":")
        end = parts[3].replace("_", ":")
        ok = features.add_sleep_range(chat_id, start, end)
        answer = "اضافه شد" if ok else "تکراری"
        text, markup = sleep_mode_panel(chat_id)
    elif data.startswith("sleep:rm:"):
        try:
            idx = int(data.split(":")[2])
        except Exception:
            idx = -1
        features.remove_sleep_range(chat_id, idx)
        answer = "🗑"
        text, markup = sleep_mode_panel(chat_id)
    elif data == "sleep:clear":
        features.clear_sleep_ranges(chat_id)
        answer = "🗑"
        text, markup = sleep_mode_panel(chat_id)

    elif data.startswith("wl:page:"):
        text, markup = whitelist_panel(chat_id, int(data.split(":")[2]))
    elif data == "wl:add":
        api.answer_callback(cb_id, "")
        st = get("settings", chat_id) or {}
        st["wait_wl"] = user_id
        st["prompt_msg_id"] = msg_id
        st["prompt_back"] = "panel:whitelist"
        set_("settings", chat_id, st)
        text, markup = _prompt(
            "⭐ افزودن به سفیدلیست",
            "آیدی عددی کاربر رو بفرست.",
            "برای لغو بنویس: لغو",
            "panel:whitelist", "wl:cancel")
    elif data == "wl:cancel":
        st = get("settings", chat_id) or {}
        st.pop("wait_wl", None)
        st.pop("prompt_msg_id", None)
        st.pop("prompt_back", None)
        set_("settings", chat_id, st)
        api.answer_callback(cb_id, "لغو شد")
        text, markup = whitelist_panel(chat_id)
    elif data.startswith("wl:rm:"):
        parts = data.split(":")
        uid = parts[2]
        page = int(parts[3])
        features.remove_whitelist(chat_id, uid)
        answer = "🗑"
        text, markup = whitelist_panel(chat_id, page)

    elif data.startswith("cc:page:"):
        text, markup = custom_cmds_panel(chat_id, int(data.split(":")[2]))
    elif data == "cc:add":
        api.answer_callback(cb_id, "")
        st = get("settings", chat_id) or {}
        st["wait_cc_name"] = user_id
        st["prompt_msg_id"] = msg_id
        st["prompt_back"] = "panel:custom_cmds"
        set_("settings", chat_id, st)
        text, markup = _prompt(
            "💬 دستور سفارشی جدید",
            "اسم دستور رو بفرست (بدون /).",
            "مثال: سلام\nبرای لغو بنویس: لغو",
            "panel:custom_cmds", "cc:cancel")
    elif data == "cc:cancel":
        st = get("settings", chat_id) or {}
        st.pop("wait_cc_name", None)
        st.pop("wait_cc_reply", None)
        st.pop("cc_pending_name", None)
        st.pop("prompt_msg_id", None)
        st.pop("prompt_back", None)
        set_("settings", chat_id, st)
        api.answer_callback(cb_id, "لغو شد")
        text, markup = custom_cmds_panel(chat_id)
    elif data.startswith("cc:rm:"):
        parts = data.split(":")
        if len(parts) >= 4:
            name = parts[2]
            page = parts[3]
            features.remove_custom_cmd(chat_id, name)
            answer = "🗑"
            try:
                text, markup = custom_cmds_panel(chat_id, int(page))
            except Exception:
                text, markup = custom_cmds_panel(chat_id)

    elif data == "note:add":
        api.answer_callback(cb_id, "")
        st = get("settings", chat_id) or {}
        st["wait_note_step"] = "name"
        st["wait_note_user"] = user_id
        st["notes_panel_msg"] = msg_id
        st["prompt_msg_id"] = msg_id
        st["prompt_back"] = "panel:notes"
        set_("settings", chat_id, st)
        text = (
            "📌 افزودن یادداشت (۱/۲)\n\n"
            "اسم یادداشت رو بفرست:\n\n"
            "بدون فاصله، حداکثر ۳۰ حرف.\n"
            "مثال: قوانین"
        )
        markup = kb([[btn("❌ لغو", "note:cancel")]])
    elif data == "note:cancel":
        st = get("settings", chat_id) or {}
        st.pop("wait_note_step", None)
        st.pop("wait_note_user", None)
        st.pop("note_pending_name", None)
        st.pop("prompt_msg_id", None)
        st.pop("prompt_back", None)
        set_("settings", chat_id, st)
        api.answer_callback(cb_id, "لغو شد")
        text, markup = notes_panel(chat_id)
    elif data == "note:remove_panel":
        text, markup = notes_remove_panel(chat_id)
    elif data.startswith("note:view:"):
        name = data[10:]
        text, markup = note_view_panel(chat_id, name)
    elif data.startswith("note:rm:"):
        name = data[8:]
        notes = get("notes", chat_id) or {}
        notes.pop(name, None)
        set_("notes", chat_id, notes)
        answer = "🗑"
        text, markup = notes_panel(chat_id)

    elif data == "panel:top_today":
        items = features.get_top_today(chat_id, 10)
        if not items:
            api.answer_callback(cb_id, "امروز کسی پیام نداده")
            return
        xp_data = get("xp", chat_id) or {}
        txt = "🏆 برترین‌های امروز\n\n"
        for i, (uid, cnt) in enumerate(items, 1):
            m = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")
            name = xp_data.get(uid, {}).get("name", "") or f"کاربر {str(uid)[-4:]}"
            txt += f"{m} {api.esc_md(name)} — {cnt} پیام\n"
        api.send(chat_id, txt, parse_mode="Markdown", reply_to=0)
        api.answer_callback(cb_id, "")
        return

    elif data == "word:add":
        api.answer_callback(cb_id, "")
        st = get("settings", chat_id) or {}
        st["wait_word"] = user_id
        st["prompt_msg_id"] = msg_id
        st["prompt_back"] = "panel:words"
        set_("settings", chat_id, st)
        text, markup = _prompt(
            "🚫 افزودن کلمات ممنوعه",
            "کلمات رو با فاصله بفرست.",
            "برای لغو بنویس: لغو",
            "panel:words", "word:cancel")
    elif data == "word:cancel":
        st = get("settings", chat_id) or {}
        st.pop("wait_word", None)
        st.pop("prompt_msg_id", None)
        st.pop("prompt_back", None)
        set_("settings", chat_id, st)
        api.answer_callback(cb_id, "لغو شد")
        text, markup = words_panel(chat_id)
    elif data == "word:clearall":
        set_("banned_words", chat_id, [])
        answer = "🗑"
        text, markup = words_panel(chat_id)
    elif data == "word:remove_panel":
        text, markup = word_remove_panel(chat_id)
    elif data.startswith("word:rm:"):
        i = int(data.split(":")[2])
        words = get("banned_words", chat_id) or []
        if 0 <= i < len(words):
            words.pop(i)
            set_("banned_words", chat_id, words)
        text, markup = words_panel(chat_id)
    elif data == "word:set_threshold":
        text, markup = words_threshold_panel(chat_id)
    elif data.startswith("word:threshold:"):
        try:
            n = int(data.split(":")[2])
        except Exception:
            n = 3
        cfg = get("banned_words_config", chat_id) or {}
        cfg["warn_threshold"] = max(1, min(100, n))
        set_("banned_words_config", chat_id, cfg)
        text, markup = words_panel(chat_id)
    elif data == "word:set_action":
        text, markup = words_action_panel(chat_id)
    elif data.startswith("word:action:"):
        action = data.split(":")[2]
        if action not in ("mute_10m", "mute_1h", "kick", "ban"):
            action = "mute_10m"
        cfg = get("banned_words_config", chat_id) or {}
        cfg["action"] = action
        set_("banned_words_config", chat_id, cfg)
        text, markup = words_panel(chat_id)
    elif data == "word:reset_warns":
        set_("bw_warnings", chat_id, {})
        answer = "صفر شد"
        text, markup = words_panel(chat_id)

    elif data == "r:edit":
        api.answer_callback(cb_id, "")
        st = get("settings", chat_id) or {}
        st["wait_rules"] = user_id
        st["prompt_msg_id"] = msg_id
        st["prompt_back"] = "panel:rules"
        set_("settings", chat_id, st)
        text, markup = _prompt(
            "📜 متن قوانین",
            "متن قوانین رو بفرست.",
            "برای لغو بنویس: لغو",
            "panel:rules", "r:cancel")
    elif data == "r:cancel":
        st = get("settings", chat_id) or {}
        st.pop("wait_rules", None)
        st.pop("prompt_msg_id", None)
        st.pop("prompt_back", None)
        set_("settings", chat_id, st)
        api.answer_callback(cb_id, "لغو شد")
        text, markup = rules_panel(chat_id)
    elif data == "r:clear":
        remove("rules", chat_id)
        answer = "🗑"
        text, markup = rules_panel(chat_id)

    elif data == "sm:toggle_on":
        storage.set_("slowmode", chat_id, {"seconds": 5})
        try:
            import main as _main
            _main.reset_slowmode_cache(chat_id)
        except Exception:
            pass
        answer = "روشن (۵ ثانیه)"
        text, markup = slowmode_panel(chat_id)
    elif data.startswith("sm:set:"):
        try:
            sec = int(data.split(":")[2])
        except Exception:
            sec = 0
        storage.set_("slowmode", chat_id, {"seconds": sec})
        try:
            import main as _main
            _main.reset_slowmode_cache(chat_id)
        except Exception:
            pass

        if sec == 0:
            answer = "خاموش"
        elif sec < 60:
            answer = f"{sec} ثانیه"
        elif sec < 3600:
            answer = f"{sec // 60} دقیقه"
        else:
            answer = f"{sec // 3600} ساعت"
        text, markup = slowmode_panel(chat_id)

    elif data == "warn:clearall":
        set_("warnings", chat_id, {})
        answer = "🔄"
        text, markup = warns_panel(chat_id)

    elif data.startswith("ban:page:"):
        text, markup = banned_panel(chat_id, int(data.split(":")[2]))
    elif data.startswith("ban:unban:"):
        parts = data.split(":")
        tid = parts[2]
        page = int(parts[3])
        try:
            api.unban(chat_id, int(tid))
        except Exception:
            pass
        banned = get("banned_users", chat_id) or {}
        banned.pop(tid, None)
        set_("banned_users", chat_id, banned)
        answer = "✅"
        text, markup = banned_panel(chat_id, page)

    elif data.startswith("mute:page:"):
        text, markup = muted_panel(chat_id, int(data.split(":")[2]))
    elif data.startswith("mute:unmute:"):
        parts = data.split(":")
        tid = parts[2]
        page = int(parts[3])
        perms = {"can_send_messages": True, "can_send_media_messages": True,
                 "can_send_other_messages": True, "can_add_web_page_previews": True}
        try:
            api.restrict(chat_id, int(tid), perms)
        except Exception:
            pass
        muted = get("muted", chat_id) or {}
        muted.pop(tid, None)
        set_("muted", chat_id, muted)
        answer = "🔊"
        text, markup = muted_panel(chat_id, page)
    elif data == "mute:unmuteall":
        muted = get("muted", chat_id) or {}
        perms = {"can_send_messages": True, "can_send_media_messages": True,
                 "can_send_other_messages": True}
        for uid in list(muted.keys()):
            try:
                api.restrict(chat_id, int(uid), perms)
            except Exception:
                pass
        set_("muted", chat_id, {})
        answer = "همه آزاد"
        text, markup = muted_panel(chat_id)

    elif data == "clean:warns":
        set_("warnings", chat_id, {})
        answer = "✅"
        text, markup = clean_panel(chat_id)
    elif data == "clean:mutes":
        muted = get("muted", chat_id) or {}
        perms = {"can_send_messages": True, "can_send_media_messages": True,
                 "can_send_other_messages": True}
        for uid in list(muted.keys()):
            try:
                api.restrict(chat_id, int(uid), perms)
            except Exception:
                pass
        set_("muted", chat_id, {})
        answer = "✅"
        text, markup = clean_panel(chat_id)
    elif data == "clean:bans":
        set_("banned_users", chat_id, {})
        answer = "✅"
        text, markup = clean_panel(chat_id)
    elif data == "clean:words":
        set_("banned_words", chat_id, [])
        answer = "✅"
        text, markup = clean_panel(chat_id)
    elif data == "clean:bwwarns":
        set_("bw_warnings", chat_id, {})
        answer = "✅"
        text, markup = clean_panel(chat_id)
    elif data == "clean:notes":
        set_("notes", chat_id, {})
        answer = "✅"
        text, markup = clean_panel(chat_id)
    elif data == "clean:whitelist":
        set_("whitelist", chat_id, [])
        answer = "✅"
        text, markup = clean_panel(chat_id)
    elif data == "clean:cc":
        set_("custom_commands", chat_id, {})
        answer = "✅"
        text, markup = clean_panel(chat_id)
    elif data == "clean:extrabw":
        set_("extra_bad_words", chat_id, [])
        answer = "✅"
        text, markup = clean_panel(chat_id)
    elif data == "clean:lockwarns":
        lock_mod.reset_all_warns(chat_id)
        answer = "✅"
        text, markup = clean_panel(chat_id)
    elif data == "clean:aswarns":
        set_("antispam_warns", chat_id, {})
        answer = "✅"
        text, markup = clean_panel(chat_id)
    elif data == "clean:sleep":
        features.clear_sleep_ranges(chat_id)
        features.set_sleep_mode_enabled(chat_id, False)
        answer = "✅"
        text, markup = clean_panel(chat_id)
    elif data == "clean:joincache":
        set_("join_cache", "list", {})
        answer = "✅"
        text, markup = clean_panel(chat_id)
    elif data == "clean:freelocked":
        try:
            lock_mod.clear_lock_list(chat_id)
        except Exception:
            pass
        answer = "✅"
        text, markup = clean_panel(chat_id)
    elif data == "clean:all":
        try:
            lock_mod.clear_lock_list(chat_id)
        except Exception:
            pass
        set_("warnings", chat_id, {})
        set_("muted", chat_id, {})
        set_("banned_words", chat_id, [])
        set_("locks", chat_id, {})
        set_("antispam", chat_id, {"enabled": False})
        set_("badword", chat_id, {"enabled": False, "max_warns": 3})
        set_("extra_bad_words", chat_id, [])
        set_("slowmode", chat_id, {"seconds": 0})
        set_("night_mode", chat_id, {"enabled": False})
        set_("sleep_mode", chat_id, {"enabled": False, "ranges": []})
        set_("whitelist", chat_id, [])
        set_("custom_commands", chat_id, {})
        set_("locked_users", chat_id, {})
        set_("lock_warnings", chat_id, {})
        set_("antispam_warns", chat_id, {})
        set_("bw_warnings", chat_id, {})
        set_("join_cache", "list", {})
        try:
            lock_mod.apply_permissions(chat_id)
        except Exception:
            pass
        answer = "🔄"
        text, markup = clean_panel(chat_id)

    elif data == "quick:rules":
        r = get("rules", chat_id) or {}
        api.send(chat_id, f"📜 {r.get('text') or 'قوانینی تنظیم نشده.'}", reply_to=0)
        api.answer_callback(cb_id, "")
        return
    elif data == "quick:link":
        c = api.get_chat(chat_id)
        if c and c.get("ok"):
            link = c["result"].get("invite_link")
            api.answer_callback(cb_id, link or "لینکی نیست", alert=True)
        return
    elif data == "quick:top":
        games.cmd_ranking_period(chat_id, "all")
        api.answer_callback(cb_id, "🏆")
        return

    elif data.startswith("um:warn:"):
        tid = int(data.split(":")[2])
        from admin import is_admin as _is_admin
        if _is_admin(chat_id, tid):
            api.answer_callback(cb_id, "این کاربر ادمینه.", alert=True)
            return
        warns = get("warnings", chat_id) or {}
        warns[str(tid)] = warns.get(str(tid), 0) + 1
        set_("warnings", chat_id, warns)
        c = warns[str(tid)]
        if c >= 3:
            try:
                api.ban(chat_id, tid)
            except Exception:
                pass
            try:
                from storage import save_banned
                save_banned(chat_id, tid, f"کاربر {tid}")
            except Exception:
                pass
            warns.pop(str(tid), None)
            set_("warnings", chat_id, warns)
            api.send(chat_id, "کاربر با ۳ اخطار بن شد.", reply_to=0)
            try:
                import notify
                notify.notify_punishment(tid, chat_id, "ban", reason="۳ اخطار")
            except Exception:
                pass
        else:
            api.send(chat_id, f"اخطار ({c}/3)", reply_to=0)
        api.answer_callback(cb_id, f"⚠️ {c}/3")
        return
    elif data.startswith("um:unwarn:"):
        tid = int(data.split(":")[2])
        warns = get("warnings", chat_id) or {}
        if warns.get(str(tid), 0) > 0:
            warns[str(tid)] -= 1
            set_("warnings", chat_id, warns)
            api.answer_callback(cb_id, f"✅ {warns[str(tid)]}/3")
        else:
            api.answer_callback(cb_id, "اخطاری نیست")
        return
    elif data.startswith("um:mute:"):
        tid = int(data.split(":")[2])
        text, markup = mute_duration_panel(chat_id, tid)
    elif data.startswith("um:unmute:"):
        tid = int(data.split(":")[2])
        perms = {"can_send_messages": True, "can_send_media_messages": True,
                 "can_send_other_messages": True, "can_add_web_page_previews": True}
        try:
            api.restrict(chat_id, tid, perms)
        except Exception:
            pass
        muted = get("muted", chat_id) or {}
        muted.pop(str(tid), None)
        set_("muted", chat_id, muted)
        try:
            lock_mod.remove_from_lock_list(chat_id, tid)
        except Exception:
            pass
        api.answer_callback(cb_id, "🔊")
        return
    elif data.startswith("um:ban:"):
        tid = int(data.split(":")[2])
        try:
            api.ban(chat_id, tid)
        except Exception:
            pass
        try:
            from storage import save_banned
            save_banned(chat_id, tid, f"کاربر {tid}")
        except Exception:
            pass
        api.answer_callback(cb_id, "🚫")
        try:
            import notify
            notify.notify_punishment(tid, chat_id, "ban")
        except Exception:
            pass
        return
    elif data.startswith("um:kick:"):
        tid = int(data.split(":")[2])
        try:
            api.ban(chat_id, tid)
            time.sleep(0.4)
            api.unban(chat_id, tid)
        except Exception:
            pass
        try:
            from storage import save_banned
            save_banned(chat_id, tid, f"کاربر {tid}")
        except Exception:
            pass
        api.answer_callback(cb_id, "👢")
        try:
            import notify
            notify.notify_punishment(tid, chat_id, "kick")
        except Exception:
            pass
        return
    elif data.startswith("um:promote:"):
        tid = int(data.split(":")[2])
        from admin import is_admin as _is_admin, _make_admin
        if _is_admin(chat_id, tid):
            api.answer_callback(cb_id, "این کاربر ادمینه.", alert=True)
            return
        me_r = api.get_member(chat_id, user_id)
        is_creator_now = me_r and me_r.get("ok") and me_r["result"].get("status") == "creator"
        if not is_creator_now:
            api.answer_callback(cb_id, "فقط مالک گروه.", alert=True)
            return
        if _make_admin(chat_id, tid):
            api.answer_callback(cb_id, "ارتقا یافت", alert=True)
            api.send(chat_id, f"کاربر {tid} ادمین شد.", reply_to=0)
        else:
            api.answer_callback(cb_id, "خطا", alert=True)
        return
    elif data.startswith("um:demote:"):
        tid = int(data.split(":")[2])
        from admin import _demote_admin
        me_r = api.get_member(chat_id, user_id)
        is_creator_now = me_r and me_r.get("ok") and me_r["result"].get("status") == "creator"
        if not is_creator_now:
            api.answer_callback(cb_id, "فقط مالک گروه.", alert=True)
            return
        if _demote_admin(chat_id, tid):
            api.answer_callback(cb_id, "تنزل یافت", alert=True)
            api.send(chat_id, f"کاربر {tid} از ادمینی حذف شد.", reply_to=0)
        else:
            api.answer_callback(cb_id, "خطا", alert=True)
        return
    elif data.startswith("um:title:"):
        tid = int(data.split(":")[2])
        api.answer_callback(cb_id, "")
        st = get("settings", chat_id) or {}
        st["wait_title"] = tid
        st["prompt_msg_id"] = msg_id
        st["prompt_back"] = "panel:main"
        set_("settings", chat_id, st)
        text, markup = _prompt(
            "🏷 ثبت لقب",
            "لقب رو بفرست.",
            "برای لغو بنویس: لغو",
            "panel:main", "um:canceltitle")
    elif data == "um:canceltitle":
        st = get("settings", chat_id) or {}
        st.pop("wait_title", None)
        st.pop("prompt_msg_id", None)
        st.pop("prompt_back", None)
        set_("settings", chat_id, st)
        api.answer_callback(cb_id, "لغو شد")
        return
    elif data.startswith("um:wladd:"):
        tid = int(data.split(":")[2])
        features.add_whitelist(chat_id, tid)
        api.answer_callback(cb_id, "⭐", alert=True)
        return
    elif data.startswith("um:profile:"):
        tid = int(data.split(":")[2])
        warns = (get("warnings", chat_id) or {}).get(str(tid), 0)
        muted = str(tid) in (get("muted", chat_id) or {})
        api.answer_callback(cb_id, f"آیدی: {tid}\nاخطار: {warns}\nسکوت: {'بله' if muted else 'خیر'}", alert=True)
        return
    elif data.startswith("um:back:"):
        tid = int(data.split(":")[2])
        text, markup = user_manage_panel(chat_id, tid, f"کاربر {tid}")
    elif data == "um:close":
        api.delete(chat_id, msg_id)
        api.answer_callback(cb_id, "")
        return

    elif data.startswith("md:"):
        parts = data.split(":")
        tid = int(parts[1])
        sec = int(parts[2])
        perms = {"can_send_messages": False,
                 "can_send_media_messages": False,
                 "can_send_other_messages": False}
        try:
            api.restrict(chat_id, tid, perms)
        except Exception:
            pass
        muted = get("muted", chat_id) or {}
        exp = time.time() + sec if sec > 0 else time.time() + 10 * 365 * 86400
        muted[str(tid)] = exp
        set_("muted", chat_id, muted)
        try:
            lock_mod.add_to_lock_list(chat_id, tid)
        except Exception:
            pass
        if sec == 0:
            t = "دائمی"
        elif sec < 3600:
            t = f"{sec // 60} دقیقه"
        elif sec < 86400:
            t = f"{sec // 3600} ساعت"
        else:
            t = f"{sec // 86400} روز"
        api.send_autodelete(
            chat_id,
            f"کاربر برای {t} سکوت شد.",
            sec=5, parse_mode="Markdown")
        api.answer_callback(cb_id, f"🔇 {t}")
        api.delete(chat_id, msg_id)
        try:
            import notify
            notify.notify_punishment(tid, chat_id, "mute",
                                     duration=t, by_name=first_name)
        except Exception:
            pass
        return

    else:
        api.answer_callback(cb_id, "❓")
        return

    if text and markup is not None:
        _edit(chat_id, msg_id, text, markup)
    if answer:
        api.answer_callback(cb_id, answer)
    else:
        api.answer_callback(cb_id, "")


def handle_private_callback(cb, cb_id, data, chat_id, msg_id, user):
    user_id = user["id"]

    # ✅ delegate به user_panels برای callbackهای کاربر تو پیوی
    if (data.startswith("user:") or data.startswith("ug:") or
        data.startswith("game:") or data.startswith("mode:") or
        data.startswith("todd:setrounds:") or data.startswith("anon_cancel:") or
        data.startswith("lb:") or data.startswith("rank:")):
        try:
            import user_panels
            user_panels.handle_user_callback(cb, cb_id, data, chat_id, msg_id, user)
            return
        except Exception as e:
            print(f"[private:user] {e}")
            import traceback
            traceback.print_exc()
            api.answer_callback(cb_id, "خطا", alert=True)
            return

    if data.startswith("gif:"):
        try:
            import gifmaker
            gifmaker.handle_callback(cb, cb_id, data, chat_id, msg_id, user)
            return
        except Exception as e:
            print(f"[private:gif] {e}")
            api.answer_callback(cb_id, "خطا", alert=True)
            return

    if data == "start:close":
        api.delete(chat_id, msg_id)
        api.answer_callback(cb_id, "بسته شد")
        return

    if data == "start:check_join":
        if check_force_join(user_id):
            text, markup = start_panel(user)
            _edit(chat_id, msg_id, text, markup)
            api.answer_callback(cb_id, "تایید شد")
        else:
            api.answer_callback(cb_id, "هنوز عضو نشدی!", alert=True)
        return

    if data in ("start:help", "start:help_full", "help:back"):
        text, markup = help_main_panel()
        _edit(chat_id, msg_id, text, markup)
        api.answer_callback(cb_id, "")
        return

    if data == "help:close":
        api.delete(chat_id, msg_id)
        api.answer_callback(cb_id, "بسته شد")
        return

    if data.startswith("help:"):
        key = data.split(":", 1)[1]
        if key in HELP_TEXTS:
            text = HELP_TEXTS[key]
            markup = kb([[btn("🔙 برگشت به راهنما", "help:back"), btn("❌ بستن", "help:close")]])
            _edit(chat_id, msg_id, text, markup)
            api.answer_callback(cb_id, "")
            return
        api.answer_callback(cb_id, "❓")
        return

    if data == "start:profile":
        users = storage.get("bot_users", "list") or {}
        u = users.get(str(user_id), {})
        first = u.get("first_seen", "?")
        uname = u.get("username", "")
        is_admin_txt = "بله" if is_bot_admin(user_id) else "خیر"
        txt = f"👤 پروفایل تو\n\nنام: {user.get('first_name', 'کاربر')}\n"
        if uname:
            txt += f"یوزرنیم: @{api.esc_md(uname)}\n"
        txt += f"آیدی: {user_id}\nتاریخ عضویت: {first}\nادمین ربات: {is_admin_txt}"
        api.send(chat_id, txt, parse_mode="Markdown", reply_to=0)
        api.answer_callback(cb_id, "")
        return

    if data == "start:stats":
        users = storage.get("bot_users", "list") or {}
        admins = storage.get("bot_admins", "list") or {}
        groups = storage.get("bot_groups", "list") or {}
        txt = (
            f"📊 آمار ربات\n\n"
            f"👥 کاربران: {len(users)}\n"
            f"👥 گروه‌ها: {len(groups)}\n"
            f"👑 ادمین‌ها: {len(admins)}"
        )
        api.send(chat_id, txt, parse_mode="Markdown", reply_to=0)
        api.answer_callback(cb_id, "")
        return

    if data == "owner:back":
        if not is_bot_admin(user_id):
            api.answer_callback(cb_id, "❌", alert=True)
            return
        text, markup = owner_main_panel(user_id)
        if text:
            _edit(chat_id, msg_id, text, markup)
        api.answer_callback(cb_id, "")
        return
    if data == "owner:close":
        api.delete(chat_id, msg_id)
        api.answer_callback(cb_id, "بسته شد")
        return
    if data == "owner:stats":
        if not is_bot_admin(user_id):
            api.answer_callback(cb_id, "❌", alert=True)
            return
        t, m = owner_stats_panel(user_id)
        if t:
            _edit(chat_id, msg_id, t, m)
        api.answer_callback(cb_id, "")
        return
    if data == "owner:fj":
        if not is_bot_admin(user_id):
            api.answer_callback(cb_id, "❌", alert=True)
            return
        text, markup = force_join_admin_panel(chat_id, user_id)
        _edit(chat_id, msg_id, text, markup)
        api.answer_callback(cb_id, "")
        return
    if data == "owner:fj_toggle":
        if not is_bot_admin(user_id):
            api.answer_callback(cb_id, "❌", alert=True)
            return
        fj = get_force_join()
        fj["enabled"] = not fj.get("enabled", False)
        set_("force_join", "global", fj)
        answer = "روشن" if fj["enabled"] else "خاموش"
        text, markup = force_join_admin_panel(chat_id, user_id)
        _edit(chat_id, msg_id, text, markup)
        api.answer_callback(cb_id, answer)
        return
    if data == "owner:fj_set":
        if not is_bot_admin(user_id):
            api.answer_callback(cb_id, "❌", alert=True)
            return
        api.answer_callback(cb_id, "")
        set_("settings", "global", {"wait_channel": user_id, "prompt_msg_id": msg_id, "prompt_back": "owner:back"})
        text, markup = _prompt(
            "📢 تنظیم کانال عضویت اجباری",
            "آیدی، یوزرنیم یا لینک کانال رو بفرست.",
            "برای لغو بنویس: لغو",
            "owner:back", "owner:fj_cancel")
        _edit(chat_id, msg_id, text, markup)
        return
    if data == "owner:fj_cancel":
        st = get("settings", "global") or {}
        st.pop("wait_channel", None)
        st.pop("prompt_msg_id", None)
        st.pop("prompt_back", None)
        set_("settings", "global", st)
        api.answer_callback(cb_id, "لغو شد")
        text, markup = force_join_admin_panel(chat_id, user_id)
        _edit(chat_id, msg_id, text, markup)
        return
    if data == "owner:fj_clear":
        if not is_bot_admin(user_id):
            api.answer_callback(cb_id, "❌", alert=True)
            return
        set_("force_join", "global", {"enabled": False})
        text, markup = force_join_admin_panel(chat_id, user_id)
        _edit(chat_id, msg_id, text, markup)
        api.answer_callback(cb_id, "حذف شد")
        return
    if data == "owner:fj_test":
        if not is_bot_admin(user_id):
            api.answer_callback(cb_id, "❌", alert=True)
            return
        fj = get_force_join()
        if not fj.get("channel_id"):
            api.answer_callback(cb_id, "اول کانال رو تنظیم کن", alert=True)
            return
        try:
            r = api.get_member(fj["channel_id"], user_id)
            if r and r.get("ok"):
                st = r["result"].get("status", "?")
                api.answer_callback(cb_id, f"وضعیت تو: {st}", alert=True)
            else:
                api.answer_callback(cb_id, "خطا", alert=True)
        except Exception as e:
            api.answer_callback(cb_id, f"خطا: {e}", alert=True)
        return
    if data == "owner:fj_check_admin":
        if not is_bot_admin(user_id):
            api.answer_callback(cb_id, "❌", alert=True)
            return
        fj = get_force_join()
        if not fj.get("channel_id"):
            api.answer_callback(cb_id, "اول کانال رو تنظیم کن", alert=True)
            return
        try:
            bot_id = api.bot_id()
            r = api.get_member(fj["channel_id"], bot_id)
            if r and r.get("ok"):
                st = r["result"].get("status", "?")
                if st in ("administrator", "creator"):
                    fj["bot_is_admin"] = True
                    set_("force_join", "global", fj)
                    api.answer_callback(cb_id, f"بله ({st})", alert=True)
                else:
                    fj["bot_is_admin"] = False
                    set_("force_join", "global", fj)
                    api.answer_callback(cb_id, f"خیر ({st})", alert=True)
            else:
                api.answer_callback(cb_id, "خطا", alert=True)
        except Exception as e:
            api.answer_callback(cb_id, f"خطا: {e}", alert=True)
        return
    if data == "owner:admins":
        if not is_bot_admin(user_id):
            api.answer_callback(cb_id, "❌", alert=True)
            return
        text, markup = bot_admins_panel(chat_id, user_id)
        _edit(chat_id, msg_id, text, markup)
        api.answer_callback(cb_id, "")
        return
    if data == "owner:ba_add":
        if not is_bot_admin(user_id):
            api.answer_callback(cb_id, "❌", alert=True)
            return
        api.answer_callback(cb_id, "")
        set_("settings", "global", {"wait_admin_add": user_id, "prompt_msg_id": msg_id, "prompt_back": "owner:back"})
        text, markup = _prompt(
            "👑 افزودن ادمین ربات",
            "آیدی عددی کاربر رو بفرست.",
            "برای لغو بنویس: لغو",
            "owner:back", "owner:ba_cancel")
        _edit(chat_id, msg_id, text, markup)
        return
    if data == "owner:ba_cancel":
        st = get("settings", "global") or {}
        st.pop("wait_admin_add", None)
        st.pop("prompt_msg_id", None)
        st.pop("prompt_back", None)
        set_("settings", "global", st)
        api.answer_callback(cb_id, "لغو شد")
        text, markup = bot_admins_panel(chat_id, user_id)
        _edit(chat_id, msg_id, text, markup)
        return
    if data == "owner:ba_remove":
        if not is_bot_admin(user_id):
            api.answer_callback(cb_id, "❌", alert=True)
            return
        admins = storage.get("bot_admins", "list") or {}
        rows = []
        for uid, name in admins.items():
            rows.append([btn(f"❌ {name}", f"owner:ba_rm:{uid}")])
        rows.append([btn("🔙 برگشت", "owner:admins")])
        if admins:
            text = "روی ادمین بزن تا حذف بشه:"
            markup = kb(rows)
        else:
            text = "لیست خالی."
            markup = kb([[btn("🔙 برگشت", "owner:admins")]])
        _edit(chat_id, msg_id, text, markup)
        api.answer_callback(cb_id, "")
        return
    if data.startswith("owner:ba_rm:"):
        if not is_bot_admin(user_id):
            api.answer_callback(cb_id, "❌", alert=True)
            return
        uid = data.split(":")[2]
        remove_bot_admin(uid)
        text, markup = bot_admins_panel(chat_id, user_id)
        _edit(chat_id, msg_id, text, markup)
        api.answer_callback(cb_id, "حذف شد")
        return
    if data == "owner:broadcast":
        if not is_bot_admin(user_id):
            api.answer_callback(cb_id, "❌", alert=True)
            return
        text, markup = broadcast_panel(chat_id, user_id)
        _edit(chat_id, msg_id, text, markup)
        api.answer_callback(cb_id, "")
        return
    if data in ("owner:bc_private", "owner:bc_groups", "owner:bc_both", "owner:bc_admins"):
        if not is_bot_admin(user_id):
            api.answer_callback(cb_id, "❌", alert=True)
            return
        target_map = {
            "owner:bc_private": ("private", "پیوی کاربران"),
            "owner:bc_groups": ("groups", "گروه‌ها"),
            "owner:bc_both": ("both", "پیوی + گروه‌ها"),
            "owner:bc_admins": ("admins", "ادمین‌های ربات"),
        }
        target, label = target_map[data]
        api.answer_callback(cb_id, "")
        set_("settings", "global", {"wait_broadcast": user_id, "target": target,
                                     "prompt_msg_id": msg_id, "prompt_back": "owner:back"})
        text, markup = _prompt(
            f"📢 پیام همگانی — {label}",
            "متن پیام رو بفرست.",
            "برای لغو بنویس: لغو",
            "owner:back", "owner:bc_cancel")
        _edit(chat_id, msg_id, text, markup)
        return
    if data == "owner:bc_cancel":
        st = get("settings", "global") or {}
        st.pop("wait_broadcast", None)
        st.pop("target", None)
        st.pop("prompt_msg_id", None)
        st.pop("prompt_back", None)
        set_("settings", "global", st)
        api.answer_callback(cb_id, "لغو شد")
        text, markup = broadcast_panel(chat_id, user_id)
        _edit(chat_id, msg_id, text, markup)
        return

    if data == "w:back_to_panel":
        text, markup = welcome_panel(chat_id)
        _edit(chat_id, msg_id, text, markup)
        api.answer_callback(cb_id, "")
        return

    # ✅ fallback دکمه‌های copy_text
    if data.startswith("cp:"):
        val = data[3:]
        api.answer_callback(cb_id, f"📋 کپی کن:\n{val}", alert=True)
        return

    api.answer_callback(cb_id, "❓")