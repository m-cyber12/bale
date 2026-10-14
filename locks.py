# -*- coding: utf-8 -*-
"""قفل‌های هوشمند - آلفا (نسخه سازگار با بله)"""
import re
import time
import random
import api
from storage import get, update, set_


# ============================================================
# دیکشنری قفل‌ها
# ============================================================
LOCKS = {
    "link":         {
        "fa": "لینک",
        "aliases": ["لینک", "لینکها", "لینک‌ها", "ادرس", "آدرس", "url"],
        "types": ["url", "text_link"],
        "keywords": ["http://", "https://", "t.me/", "ble.ir/", "www."],
    },
    "forward":      {"fa": "فوروارد",       "aliases": ["فوروارد", "بازفرست"],                    "check": "forward"},
    "forward_chan": {"fa": "فوروارد کانال", "aliases": ["فوروارد کانال", "فورواردکانال"],        "check": "forward_chan"},
    "reply":        {"fa": "ریپلای",        "aliases": ["ریپلای", "پاسخ", "reply"],              "check": "reply"},
    "hashtag":      {"fa": "هشتگ",          "aliases": ["هشتگ", "hashtag"],                       "types": ["hashtag", "cashtag"]},
    "photo":        {"fa": "عکس",           "aliases": ["عکس", "تصویر", "photo"],                 "check": "photo"},
    "video":        {"fa": "ویدیو",         "aliases": ["ویدیو", "فیلم", "video"],                "check": "video"},
    "gif":          {"fa": "گیف",           "aliases": ["گیف", "gif", "gifs"],                    "check": "animation"},
    "sticker":      {"fa": "استیکر",        "aliases": ["استیکر", "برچسب", "sticker"],            "check": "sticker"},
    "voice":        {"fa": "ویس",           "aliases": ["ویس", "voice"],                          "check": "voice"},
    "audio":        {"fa": "صوت",           "aliases": ["صوت", "موزیک", "اهنگ", "آهنگ", "audio"], "check": "audio"},
    "document":     {"fa": "فایل",          "aliases": ["فایل", "سند", "document"],              "check": "document"},
    "contact":      {"fa": "مخاطب",         "aliases": ["مخاطب", "contact"],                      "check": "contact"},
    "location":     {"fa": "موقعیت",        "aliases": ["موقعیت", "لوکیشن", "location"],          "check": "location"},
    "poll":         {"fa": "نظرسنجی",       "aliases": ["نظرسنجی", "نظر سنجی", "poll"],           "check": "poll"},
    "dice":         {"fa": "تاس",           "aliases": ["تاس", "dice"],                           "check": "dice"},
    "game":         {"fa": "بازی",          "aliases": ["بازی", "game"],                          "check": "game"},
    "phone":        {"fa": "شماره تلفن",    "aliases": ["شماره", "تلفن", "موبایل"],               "regex": r"(\+98|0)?9\d{9}"},
    "email":        {"fa": "ایمیل",         "aliases": ["ایمیل", "email"],                        "regex": r"[\w\.-]+@[\w\.-]+\.\w+"},
    "id":           {"fa": "آیدی",          "aliases": ["آیدی", "ایدی"],                          "regex": r"@\w+"},
    "emoji":        {"fa": "ایموجی",        "aliases": ["ایموجی", "شکلک"],                        "regex": r"[\U0001F300-\U0001FAFF]"},
    "long":         {"fa": "پیام بلند",     "aliases": ["بلند"], "check": "long",  "max": 200},
    "capslock":     {"fa": "حروف بزرگ",     "aliases": ["حروف بزرگ", "کپس"],  "check": "caps"},
    "repeat":       {"fa": "تکرار",         "aliases": ["تکرار"],              "check": "repeat"},
    "antihack":     {
        "fa": "ضد کد هنگی",
        "aliases": [
            "ضد کد هنگی", "ضد کدهنگی", "کد هنگی", "کدهنگی",
            "ضد هنگ", "ضدهنگ", "هنگ",
            "ضد کرش", "ضدکرش", "کرش",
            "ضد فریز", "ضدفریز", "فریز",
            "ضد هک", "ضدهک", "هک",
            "ضد کد هندگی", "کد هندگی", "کدهندگی",
        ],
        "check": "antihack",
    },
    "hidden":       {"fa": "کاراکتر مخفی",  "aliases": ["مخفی", "کاراکتر مخفی", "کاراکترمخفی"], "check": "hidden"},
}


# ============================================================
# کش regex
# ============================================================
_REGEX_CACHE = {}

def _get_regex(pattern):
    if pattern not in _REGEX_CACHE:
        try:
            _REGEX_CACHE[pattern] = re.compile(pattern)
        except Exception:
            _REGEX_CACHE[pattern] = None
    return _REGEX_CACHE[pattern]


# ============================================================
# tracker تکرار
# ============================================================
_REPEAT_TRACKER = {}


def _cleanup_trackers():
    now = time.time()
    for k in list(_REPEAT_TRACKER.keys()):
        if now - _REPEAT_TRACKER[k][1] > 60:
            _REPEAT_TRACKER.pop(k, None)


# ============================================================
# پرمیشن‌ها
# ============================================================
def _perms_all_open():
    return {
        "can_send_messages": True,
        "can_send_media_messages": True,
        "can_send_polls": True,
        "can_send_other_messages": True,
        "can_add_web_page_previews": True,
    }


def _perms_all_closed():
    return {
        "can_send_messages": False,
        "can_send_media_messages": False,
        "can_send_polls": False,
        "can_send_other_messages": False,
        "can_add_web_page_previews": False,
    }


def _build_perms(locks_state):
    perms = _perms_all_open()
    if locks_state.get("gif") or locks_state.get("sticker") or locks_state.get("game"):
        perms["can_send_other_messages"] = False
    if (locks_state.get("photo") or locks_state.get("video") or
        locks_state.get("voice") or locks_state.get("audio") or
        locks_state.get("document")):
        perms["can_send_media_messages"] = False
    if locks_state.get("poll"):
        perms["can_send_polls"] = False
    if locks_state.get("link"):
        perms["can_add_web_page_previews"] = False
    return perms


def get_current_perms(chat_id):
    gl = get("group_lock", chat_id) or {}
    if gl.get("enabled"):
        return _perms_all_closed()
    locks_state = get("locks", chat_id) or {}
    return _build_perms(locks_state)


def register_known_user(chat_id, user_id):
    known = get("known_users", chat_id) or {}
    uid = str(user_id)
    if uid not in known:
        known[uid] = time.time()
        set_("known_users", chat_id, known)


def get_known_users(chat_id):
    known = get("known_users", chat_id) or {}
    ids = []
    for uid in known.keys():
        try:
            ids.append(int(uid))
        except Exception:
            pass
    xp_data = get("xp", chat_id) or {}
    for uid in xp_data.keys():
        try:
            iuid = int(uid)
            if iuid not in ids:
                ids.append(iuid)
        except Exception:
            pass
    return ids


def add_to_lock_list(chat_id, user_id):
    locked = get("locked_users", chat_id) or {}
    locked[str(user_id)] = time.time()
    set_("locked_users", chat_id, locked)


def remove_from_lock_list(chat_id, user_id):
    """حذف کاربر از لیست قفل + تلاش برای آزادسازی (بی‌صدا)"""
    locked = get("locked_users", chat_id) or {}
    if str(user_id) in locked:
        del locked[str(user_id)]
        set_("locked_users", chat_id, locked)

    # تلاش برای آزادسازی (اگه بله پشتیبانی کنه)
    try:
        api.restrict(chat_id, user_id, _perms_all_open())
    except Exception:
        pass


# ============================================================
# ✅ is_user_locked — نسخه با چک انقضا (مهم!)
# ============================================================
def is_user_locked(chat_id, user_id):
    """
    چک میکنه کاربر سکوت هست یا نه.
    ✅ اگه زمان سکوت تموم شده، خودکار آزادش میکنه.
    """
    locked = get("locked_users", chat_id) or {}
    uid = str(user_id)

    if uid not in locked:
        return False

    # ✅ چک کن آیا سکوت زمان‌دار هست و تموم شده
    muted = get("muted", chat_id) or {}
    if uid in muted:
        try:
            exp = float(muted[uid])
            now = time.time()
            if now >= exp:
                # ⏰ زمان تموم شده، کاربر رو آزاد کن
                print(f"[unmute:auto] کاربر {uid} - زمان سکوت تموم شد")

                # حذف از locked_users
                del locked[uid]
                set_("locked_users", chat_id, locked)

                # حذف از muted
                del muted[uid]
                set_("muted", chat_id, muted)

                # تلاش برای رفع restrict
                try:
                    perms = {
                        "can_send_messages": True,
                        "can_send_media_messages": True,
                        "can_send_other_messages": True,
                        "can_add_web_page_previews": True,
                    }
                    api.restrict(chat_id, int(uid), perms)
                except Exception:
                    pass

                return False
        except (ValueError, TypeError) as e:
            print(f"[unmute:auto:err] {e}")

    return True


# ============================================================
# ✅ cleanup_expired_mutes — پاکسازی همه سکوت‌های منقضی
# ============================================================
def cleanup_expired_mutes(chat_id):
    """
    پاک کردن همه سکوت‌های منقضی‌شده.
    برمیگردونه: تعداد کاربرانی که آزاد شدن
    """
    muted = get("muted", chat_id) or {}
    locked = get("locked_users", chat_id) or {}
    now = time.time()

    expired = []
    for uid, exp in list(muted.items()):
        try:
            if float(exp) <= now:
                expired.append(uid)
        except (ValueError, TypeError):
            expired.append(uid)

    if not expired:
        return 0

    # حذف از هر دو لیست
    for uid in expired:
        muted.pop(uid, None)
        locked.pop(uid, None)

    set_("muted", chat_id, muted)
    set_("locked_users", chat_id, locked)

    # تلاش برای رفع restrict
    for uid in expired:
        try:
            perms = {
                "can_send_messages": True,
                "can_send_media_messages": True,
                "can_send_other_messages": True,
                "can_add_web_page_previews": True,
            }
            api.restrict(chat_id, int(uid), perms)
            time.sleep(0.05)
        except Exception:
            pass

    print(f"[cleanup_expired_mutes] {len(expired)} کاربر آزاد شدند")
    return len(expired)


# ============================================================
# ✅ clear_lock_list — نسخه سازگار با بله
# ============================================================
def clear_lock_list(chat_id):
    """
    پاک کردن لیست کاربران قفل‌شده.
    اگه بله restrict رو پشتیبانی کنه، تلاش می‌کنیم آزاد کنیم.
    وگرنه فقط لیست پاک میشه.
    """
    locked = get("locked_users", chat_id) or {}

    if locked:
        full_open = _perms_all_open()
        for uid_str in list(locked.keys()):
            try:
                uid = int(uid_str)
                api.restrict(chat_id, uid, full_open)
                time.sleep(0.03)
            except Exception:
                pass

    # حالا لیست رو خالی کن
    set_("locked_users", chat_id, {})


# ============================================================
# ✅ apply_permissions — نسخه سازگار با بله (بی‌صدا)
# ============================================================
def apply_permissions(chat_id):
    """
    اعمال پرمیشن‌های فعلی.
    بله setChatPermissions و restrictChatMember رو پشتیبانی نمی‌کنه،
    پس فقط تلاش می‌کنیم و بی‌سروصدا ادامه می‌دیم.
    """
    perms = get_current_perms(chat_id)

    # تلاش برای set_chat_permissions
    try:
        r = api.set_chat_permissions(chat_id, perms)
        if r and r.get("ok"):
            return True
    except Exception:
        pass

    # تلاش برای restrict هر کاربر
    users = get_known_users(chat_id)
    success = 0
    for uid in users:
        try:
            r = api.restrict(chat_id, uid, perms)
            if r and r.get("ok"):
                success += 1
            time.sleep(0.03)
        except Exception:
            pass

    return success > 0


def apply_to_one_user(chat_id, user_id):
    perms = get_current_perms(chat_id)
    try:
        return api.restrict(chat_id, user_id, perms)
    except Exception:
        return None


# ============================================================
# قفل گروه — توابع کمکی
# ============================================================
def is_group_locked(chat_id):
    gl = get("group_lock", chat_id) or {}
    return bool(gl.get("enabled"))


def lock_group(chat_id, by_user_id=0):
    """قفل کل گروه"""
    set_("group_lock", chat_id, {"enabled": True, "by": by_user_id, "ts": time.time()})
    try:
        apply_permissions(chat_id)
    except Exception as e:
        print(f"[lock_group] {e}")
    return True


def unlock_group(chat_id):
    """باز کردن قفل کل گروه"""
    set_("group_lock", chat_id, {"enabled": False, "ts": time.time()})
    try:
        clear_lock_list(chat_id)
    except Exception as e:
        print(f"[unlock_group:clear] {e}")
    try:
        apply_permissions(chat_id)
    except Exception as e:
        print(f"[unlock_group:apply] {e}")
    return True


# ============================================================
# توابع کمکی بن/سکوت
# ============================================================
def ban_and_save(chat_id, user_id, user_name=""):
    """بن + ذخیره در لیست سیاه"""
    try:
        api.ban(chat_id, user_id)
    except Exception as e:
        print(f"[ban_and_save:ban] {e}")

    try:
        from storage import save_banned
        save_banned(chat_id, user_id, user_name)
    except Exception as e:
        print(f"[ban_and_save:save] {e}")


def kick_and_save(chat_id, user_id, user_name=""):
    """اخراج (بن + آنبن) + ذخیره در لیست سیاه"""
    try:
        api.ban(chat_id, user_id)
        time.sleep(0.4)
        api.unban(chat_id, user_id)
    except Exception as e:
        print(f"[kick_and_save:kick] {e}")

    try:
        from storage import save_banned
        save_banned(chat_id, user_id, user_name)
    except Exception as e:
        print(f"[kick_and_save:save] {e}")


def mute_and_save(chat_id, user_id, seconds=600):
    """
    سکوت + ذخیره در لیست.
    چون بله restrict نداره، فقط ذخیره می‌کنیم و در main پیام‌های کاربر حذف میشن.
    """
    # تلاش برای restrict (اگه پشتیبانی بشه)
    try:
        perms = {
            "can_send_messages": False,
            "can_send_media_messages": False,
            "can_send_other_messages": False,
            "can_add_web_page_previews": False,
        }
        api.restrict(chat_id, user_id, perms)
    except Exception:
        pass

    try:
        add_to_lock_list(chat_id, user_id)
    except Exception:
        pass

    try:
        from storage import save_muted
        exp = time.time() + seconds if seconds > 0 else time.time() + 10 * 365 * 86400
        save_muted(chat_id, user_id, exp)
    except Exception as e:
        print(f"[mute_and_save:save] {e}")


# ============================================================
# توابع toggle/lock/unlock
# ============================================================
def is_locked(chat_id, name):
    locks = get("locks", chat_id)
    return locks.get(name, False)


def lock(chat_id, name):
    update("locks", chat_id, name, True)
    try:
        apply_permissions(chat_id)
    except Exception:
        pass


def unlock(chat_id, name):
    update("locks", chat_id, name, False)
    try:
        clear_lock_list(chat_id)
    except Exception:
        pass
    try:
        apply_permissions(chat_id)
    except Exception:
        pass


def toggle(chat_id, name):
    locks = get("locks", chat_id)
    cur = locks.get(name, False)
    update("locks", chat_id, name, not cur)
    if cur:
        try:
            clear_lock_list(chat_id)
        except Exception:
            pass
    try:
        apply_permissions(chat_id)
    except Exception:
        pass
    return not cur


def lock_all(chat_id):
    for k in LOCKS:
        update("locks", chat_id, k, True)
    try:
        apply_permissions(chat_id)
    except Exception:
        pass


def unlock_all(chat_id):
    for k in LOCKS:
        update("locks", chat_id, k, False)
    try:
        clear_lock_list(chat_id)
    except Exception:
        pass
    try:
        apply_permissions(chat_id)
    except Exception:
        pass


def list_locks(chat_id):
    return get("locks", chat_id)


def resolve_name(name):
    if not name:
        return None
    name = name.strip().lower()
    if name in LOCKS:
        return name
    for k, v in LOCKS.items():
        if v.get("fa", "").lower() == name:
            return k
    for k, v in LOCKS.items():
        for alias in v.get("aliases", []):
            if alias.lower() == name:
                return k
    return None


# ============================================================
# سیستم هشدار قفل
# ============================================================
def get_warn_threshold(chat_id):
    cfg = get("locks_config", chat_id) or {}
    try:
        threshold = int(cfg.get("warn_threshold", 3))
    except (TypeError, ValueError):
        threshold = 3
    return max(1, min(100, threshold))


def set_warn_threshold(chat_id, n):
    try:
        n = int(n)
    except (TypeError, ValueError):
        n = 3
    n = max(1, min(100, n))
    cfg = get("locks_config", chat_id) or {}
    cfg["warn_threshold"] = n
    set_("locks_config", chat_id, cfg)
    return n


def get_user_warns(chat_id, user_id):
    warns = get("lock_warnings", chat_id) or {}
    return warns.get(str(user_id), 0)


def reset_user_warns(chat_id, user_id=None):
    if user_id is None:
        set_("lock_warnings", chat_id, {})
        return
    warns = get("lock_warnings", chat_id) or {}
    warns.pop(str(user_id), None)
    set_("lock_warnings", chat_id, warns)


def reset_all_warns(chat_id):
    set_("lock_warnings", chat_id, {})


def handle_lock_violation(chat_id, user_id, lock_name):
    threshold = get_warn_threshold(chat_id)
    warns = get("lock_warnings", chat_id) or {}
    uid = str(user_id)
    warns[uid] = warns.get(uid, 0) + 1
    count = warns[uid]
    should_kick = (count >= threshold)
    if should_kick:
        warns[uid] = 0
    set_("lock_warnings", chat_id, warns)
    return count, threshold, should_kick


def free_all_locked_users(chat_id):
    """آزاد کردن همه کاربران قفل‌شده"""
    locked = get("locked_users", chat_id) or {}
    count = len(locked)
    clear_lock_list(chat_id)
    return count


# ============================================================
# چک‌های ضد کد هنگی
# ============================================================
_BIDI_CHARS = (
    "\u202a\u202b\u202c\u202d\u202e"
    "\u2066\u2067\u2068\u2069"
    "\u200e\u200f"
)

_ZW_CHARS = (
    "\u200b\u200c\u200d\u200e\u200f"
    "\u2060\u2061\u2062\u2063\u2064"
    "\ufeff"
)

_SEPARATOR_CHARS = "\u2028\u2029"

_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

_SCRIPT_RE = re.compile(
    r"<\s*/?\s*(script|iframe|object|embed|applet|meta|link|style|svg|math|body|html|head)",
    re.IGNORECASE
)

_SIMPLE_INJECT_RE = re.compile(
    r"(javascript\s*:|vbscript\s*:|data\s*:\s*text/html|onerror\s*=|onload\s*=|onclick\s*=|onmouseover\s*=)",
    re.IGNORECASE
)

_REPEAT_CHAR_RE = re.compile(r"(.)\1{30,}", re.DOTALL)
_NEWLINE_BOMB_RE = re.compile(r"\n{8,}")
_KASHIDA_RE = re.compile(r"\u0640{5,}")
_COMBINING_RE = re.compile(r"[\u0300-\u036f\u064b-\u065f]{15,}")


def _count_chars(text, chars_set):
    if not text:
        return 0
    cnt = 0
    for c in text:
        if c in chars_set:
            cnt += 1
            if cnt >= 3:
                return cnt
    return cnt


def _check_antihack(text):
    if not text:
        return False

    length = len(text)
    if length > 2000:
        return True
    if _CONTROL_RE.search(text):
        return True
    if "\x00" in text:
        return True

    sep_count = 0
    for c in text:
        if c in _SEPARATOR_CHARS:
            sep_count += 1
            if sep_count >= 3:
                return True

    bidi_count = _count_chars(text, set(_BIDI_CHARS))
    if bidi_count >= 3:
        return True

    zw_count = _count_chars(text, set(_ZW_CHARS))
    if zw_count >= 5:
        return True

    if _SCRIPT_RE.search(text):
        return True
    if _SIMPLE_INJECT_RE.search(text):
        return True
    if _REPEAT_CHAR_RE.search(text):
        return True
    if _NEWLINE_BOMB_RE.search(text):
        return True
    if _KASHIDA_RE.search(text):
        return True
    if _COMBINING_RE.search(text):
        return True

    if length > 20:
        hidden_ratio = (bidi_count + zw_count + sep_count) / length
        if hidden_ratio > 0.3:
            return True

    return False


def _check_hidden(text):
    if not text:
        return False
    cnt = 0
    for c in text:
        if c in _ZW_CHARS:
            cnt += 1
            if cnt >= 3:
                return True
    return False


def _check_spam(text):
    if not text:
        return False
    words = text.split()
    if len(words) >= 5:
        if len(set(words)) <= 2:
            return True
    if len(text) > 20:
        most = max(text.count(c) for c in set(text))
        if most / len(text) > 0.7:
            return True
    return False


def _check_caps(text):
    if not text:
        return False
    letters = [c for c in text if c.isalpha()]
    if len(letters) > 10:
        caps = sum(1 for c in letters if c.isupper())
        if caps / len(letters) > 0.7:
            return True
    return False


def _check_repeat(chat_id, user_id, text):
    if not text or len(text) < 3:
        return False
    now = time.time()
    key = (chat_id, user_id)
    last = _REPEAT_TRACKER.get(key)
    if last:
        last_text, last_ts = last
        if last_text == text and now - last_ts < 15:
            _REPEAT_TRACKER[key] = (text, now)
            return True
    _REPEAT_TRACKER[key] = (text, now)
    return False


# ============================================================
# should_block
# ============================================================
def should_block(chat_id, message):
    locks = get("locks", chat_id)
    if not locks:
        return None

    active = {k for k, v in locks.items() if v}
    if not active:
        return None

    text = message.get("text", "") or message.get("caption", "")
    entities = message.get("entities", []) or message.get("caption_entities", [])
    user_id = message.get("from", {}).get("id", 0)

    try:
        if random.random() < 0.05:
            _cleanup_trackers()
    except Exception:
        pass

    if "forward" in active:
        if "forward_from" in message or "forward_from_chat" in message:
            return "forward"
    if "forward_chan" in active and "forward_from_chat" in message:
        return "forward_chan"
    if "reply" in active and "reply_to_message" in message:
        return "reply"
    if "photo" in active and "photo" in message:
        return "photo"
    if "video" in active and "video" in message:
        return "video"
    if "sticker" in active and "sticker" in message:
        return "sticker"
    if "voice" in active and "voice" in message:
        return "voice"
    if "audio" in active and "audio" in message:
        return "audio"
    if "document" in active and "document" in message:
        return "document"
    if "contact" in active and "contact" in message:
        return "contact"
    if "location" in active and "location" in message:
        return "location"
    if "poll" in active and "poll" in message:
        return "poll"
    if "dice" in active and "dice" in message:
        return "dice"
    if "game" in active and "game" in message:
        return "game"

    if "gif" in active:
        if "animation" in message:
            return "gif"
        if "document" in message:
            doc = message["document"]
            mt = (doc.get("mime_type") or "").lower()
            fn = (doc.get("file_name") or "").lower()
            if "gif" in mt or fn.endswith(".gif"):
                return "gif"

    if "antihack" in active and text:
        if _check_antihack(text):
            return "antihack"

    if "link" in active or "hashtag" in active:
        for ent in entities:
            etype = ent.get("type")
            if etype in ("url", "text_link") and "link" in active:
                return "link"
            if etype in ("hashtag", "cashtag") and "hashtag" in active:
                return "hashtag"

    if "link" in active and text:
        for kw in ("http://", "https://", "t.me/", "ble.ir/", "www."):
            if kw in text:
                return "link"

    if text:
        if "phone" in active:
            rx = _get_regex(r"(\+98|0)?9\d{9}")
            if rx and rx.search(text):
                return "phone"
        if "email" in active:
            rx = _get_regex(r"[\w\.-]+@[\w\.-]+\.\w+")
            if rx and rx.search(text):
                return "email"
        if "id" in active:
            rx = _get_regex(r"@\w+")
            if rx and rx.search(text):
                return "id"
        if "emoji" in active:
            rx = _get_regex(r"[\U0001F300-\U0001FAFF]")
            if rx and rx.search(text):
                return "emoji"

        if "long" in active and len(text) > 200:
            return "long"
        if "capslock" in active and _check_caps(text):
            return "capslock"
        if "hidden" in active and _check_hidden(text):
            return "hidden"
        if "repeat" in active and _check_repeat(chat_id, user_id, text):
            return "repeat"

    return None