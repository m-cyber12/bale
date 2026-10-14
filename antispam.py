# -*- coding: utf-8 -*-
"""ضد اسپم پیشرفته - نسخه سریع با سیستم هشدار"""
import time
import threading
from collections import deque
import api
from storage import get, set_, save_banned, save_muted


# ============================================================
# Trackerها با deque
# ============================================================
_TRACKER = {}
_LAST_MSG = {}
_LOCK = threading.Lock()

DEFAULT_LIMIT = 5
DEFAULT_WINDOW = 10
DEFAULT_THRESHOLD = 3
DEFAULT_ACTION = "mute"
REPEAT_WINDOW = 20
CLEANUP_INTERVAL = 60
_last_cleanup = [0]


def _cleanup(now):
    if now - _last_cleanup[0] < CLEANUP_INTERVAL:
        return
    _last_cleanup[0] = now

    for k in list(_TRACKER.keys()):
        d = _TRACKER[k]
        while d and now - d[0] > 60:
            d.popleft()
        if not d:
            _TRACKER.pop(k, None)

    for k in list(_LAST_MSG.keys()):
        if now - _LAST_MSG[k][1] > 60:
            _LAST_MSG.pop(k, None)


def _get_cfg(chat_id):
    cfg = get("antispam", chat_id) or {}

    try:
        limit = max(2, int(cfg.get("limit", DEFAULT_LIMIT)))
    except (TypeError, ValueError):
        limit = DEFAULT_LIMIT

    try:
        window = max(2, int(cfg.get("window", DEFAULT_WINDOW)))
    except (TypeError, ValueError):
        window = DEFAULT_WINDOW

    try:
        threshold = max(1, min(100, int(cfg.get("warn_threshold", DEFAULT_THRESHOLD))))
    except (TypeError, ValueError):
        threshold = DEFAULT_THRESHOLD

    return {
        "enabled": bool(cfg.get("enabled")),
        "limit": limit,
        "window": window,
        "threshold": threshold,
        "action": cfg.get("action_key", DEFAULT_ACTION),
    }


# ============================================================
# سیستم هشدار
# ============================================================
def get_warn_threshold(chat_id):
    return _get_cfg(chat_id)["threshold"]


def set_warn_threshold(chat_id, n):
    try:
        n = max(1, min(100, int(n)))
    except (TypeError, ValueError):
        n = DEFAULT_THRESHOLD
    cfg = get("antispam", chat_id) or {}
    cfg["warn_threshold"] = n
    set_("antispam", chat_id, cfg)
    return n


def get_user_warns(chat_id, user_id):
    warns = get("antispam_warns", chat_id) or {}
    return warns.get(str(user_id), 0)


def reset_user_warns(chat_id, user_id):
    warns = get("antispam_warns", chat_id) or {}
    warns.pop(str(user_id), None)
    set_("antispam_warns", chat_id, warns)


def reset_all_warns(chat_id):
    set_("antispam_warns", chat_id, {})


def _add_warn(chat_id, user_id):
    warns = get("antispam_warns", chat_id) or {}
    uid = str(user_id)
    warns[uid] = warns.get(uid, 0) + 1
    set_("antispam_warns", chat_id, warns)
    return warns[uid]


# ============================================================
# چک اصلی
# ============================================================
def check(chat_id, user_id, text, message, is_admin_fn):
    if is_admin_fn(chat_id, user_id):
        return False

    cfg = _get_cfg(chat_id)
    if not cfg["enabled"]:
        return False

    now = time.time()
    key = (chat_id, user_id)
    limit = cfg["limit"]
    window = cfg["window"]
    threshold = cfg["threshold"]

    is_flood = False
    is_repeat = False

    with _LOCK:
        _cleanup(now)

        d = _TRACKER.get(key)
        if d is None:
            d = deque(maxlen=limit + 1)
            _TRACKER[key] = d

        while d and now - d[0] > window:
            d.popleft()

        d.append(now)
        if len(d) > limit:
            is_flood = True
            d.clear()
        elif text:
            last = _LAST_MSG.get(key)
            if last and last[0] == text and now - last[1] < REPEAT_WINDOW:
                is_repeat = True
            _LAST_MSG[key] = (text, now)

    if not (is_flood or is_repeat):
        return False

    reason = "فلاد" if is_flood else "تکرار پیام"
    count = _add_warn(chat_id, user_id)

    if count >= threshold:
        reset_user_warns(chat_id, user_id)
        _punish(chat_id, user_id, cfg["action"], reason, threshold)
    else:
        emoji = "⏱" if is_flood else "🔁"
        try:
            api.send_autodelete(
                chat_id,
                f"{emoji} **{reason}!**\n\n"
                f"🙏 لطفاً آرام‌تر پیام بده.\n"
                f"⚠️ **هشدار:** `{count}/{threshold}`",
                sec=5,
                parse_mode="Markdown"
            )
        except Exception as e:
            print(f"[antispam:warn] {e}")

    return True


# ============================================================
# ✅ مجازات — با ذخیره‌سازی خودکار
# ============================================================
def _punish(chat_id, user_id, action, reason, threshold):
    perms_mute = {
        "can_send_messages": False,
        "can_send_media_messages": False,
        "can_send_other_messages": False,
    }
    user_name = f"کاربر {user_id}"

    try:
        if action == "kick":
            # ✅ اخراج + ذخیره در لیست سیاه
            try:
                api.ban(chat_id, user_id)
                time.sleep(0.4)
                api.unban(chat_id, user_id)
            except Exception as e:
                print(f"[antispam:kick] {e}")

            try:
                save_banned(chat_id, user_id, user_name)
            except Exception as e:
                print(f"[antispam:kick:save] {e}")

            api.send_autodelete(
                chat_id,
                f"👢 کاربر به دلیل **{threshold}** بار {reason} اخراج شد.",
                sec=5, parse_mode="Markdown"
            )

        elif action == "ban":
            try:
                api.ban(chat_id, user_id)
            except Exception as e:
                print(f"[antispam:ban] {e}")

            try:
                save_banned(chat_id, user_id, user_name)
            except Exception as e:
                print(f"[antispam:ban:save] {e}")

            api.send_autodelete(
                chat_id,
                f"🚫 کاربر به دلیل **{threshold}** بار {reason} بن شد.",
                sec=5, parse_mode="Markdown"
            )

        else:  # mute
            try:
                api.restrict(chat_id, user_id, perms_mute)
            except Exception as e:
                print(f"[antispam:mute] {e}")

            try:
                exp = time.time() + 600  # ۱۰ دقیقه
                save_muted(chat_id, user_id, exp)
            except Exception as e:
                print(f"[antispam:mute:save] {e}")

            api.send_autodelete(
                chat_id,
                f"🔇 کاربر به دلیل **{threshold}** بار {reason} ۱۰ دقیقه سکوت شد.",
                sec=5, parse_mode="Markdown"
            )
    except Exception as e:
        print(f"[antispam:punish] {e}")