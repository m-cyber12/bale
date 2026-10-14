# -*- coding: utf-8 -*-
"""سیستم تجربه و سطح + ریست روز/هفته/ماه"""
import time
from datetime import datetime
from storage import get, update, set_

XP_PER_MSG = 5
XP_COOLDOWN = 30
LEVEL_UP = 100

_last_msg = {}


def _today():
    return datetime.now().strftime("%Y-%m-%d")


def _week_key():
    d = datetime.now()
    return f"{d.year}-W{d.isocalendar()[1]}"


def _month_key():
    return datetime.now().strftime("%Y-%m")


def _check_reset(chat_id):
    meta = get("xp_meta", chat_id) or {}
    changed = False

    today = _today()
    if meta.get("daily_key") != today:
        set_("xp_daily", chat_id, {})
        meta["daily_key"] = today
        changed = True

    wk = _week_key()
    if meta.get("weekly_key") != wk:
        set_("xp_weekly", chat_id, {})
        meta["weekly_key"] = wk
        changed = True

    mk = _month_key()
    if meta.get("monthly_key") != mk:
        set_("xp_monthly", chat_id, {})
        meta["monthly_key"] = mk
        changed = True

    if changed:
        update("xp_meta", chat_id, "daily_key", meta.get("daily_key"))
        update("xp_meta", chat_id, "weekly_key", meta.get("weekly_key"))
        update("xp_meta", chat_id, "monthly_key", meta.get("monthly_key"))


def _add_period(chat_id, section, user_id, user_name, amount):
    data = get(section, chat_id) or {}
    uid = str(user_id)
    if uid not in data:
        data[uid] = {"xp": 0, "name": user_name or "کاربر"}
    data[uid]["xp"] = data[uid].get("xp", 0) + amount
    if user_name:
        data[uid]["name"] = user_name
    set_(section, chat_id, data)


def add_xp(chat_id, user_id, user_name=None, amount=None):
    _check_reset(chat_id)

    key = (chat_id, user_id)
    now = time.time()
    if now - _last_msg.get(key, 0) < XP_COOLDOWN:
        return None
    _last_msg[key] = now

    gain = amount if amount else XP_PER_MSG

    all_xp = get("xp", chat_id) or {}
    uid = str(user_id)
    user = all_xp.get(uid, {"xp": 0, "level": 1, "name": ""})
    user["xp"] += gain
    if user_name:
        user["name"] = user_name
    new_level = 1 + user["xp"] // LEVEL_UP
    leveled = new_level > user["level"]
    user["level"] = new_level
    all_xp[uid] = user
    update("xp", chat_id, uid, user)

    _add_period(chat_id, "xp_daily", user_id, user_name, gain)
    _add_period(chat_id, "xp_weekly", user_id, user_name, gain)
    _add_period(chat_id, "xp_monthly", user_id, user_name, gain)

    return new_level if leveled else None


def add_game_xp(chat_id, user_id, user_name, game_key=None, amount=15):
    _last_msg.pop((chat_id, user_id), None)
    return add_xp(chat_id, user_id, user_name, amount)


def track_user_name(chat_id, user_id, user_name):
    if not user_name:
        return
    all_xp = get("xp", chat_id) or {}
    uid = str(user_id)
    if uid not in all_xp:
        all_xp[uid] = {"xp": 0, "level": 1, "name": user_name}
    else:
        if all_xp[uid].get("name") != user_name:
            all_xp[uid]["name"] = user_name
    update("xp", chat_id, uid, all_xp[uid])


def get_user(chat_id, user_id):
    all_xp = get("xp", chat_id) or {}
    return all_xp.get(str(user_id), {"xp": 0, "level": 1, "name": ""})


def top(chat_id, n=10):
    all_xp = get("xp", chat_id) or {}
    items = sorted(all_xp.items(), key=lambda x: x[1].get("xp", 0), reverse=True)
    return items[:n]


def top_daily(chat_id, n=10):
    _check_reset(chat_id)
    data = get("xp_daily", chat_id) or {}
    items = sorted(data.items(), key=lambda x: x[1].get("xp", 0), reverse=True)
    return [(uid, u) for uid, u in items if u.get("xp", 0) > 0][:n]


def top_weekly(chat_id, n=10):
    _check_reset(chat_id)
    data = get("xp_weekly", chat_id) or {}
    items = sorted(data.items(), key=lambda x: x[1].get("xp", 0), reverse=True)
    return [(uid, u) for uid, u in items if u.get("xp", 0) > 0][:n]


def top_monthly(chat_id, n=10):
    _check_reset(chat_id)
    data = get("xp_monthly", chat_id) or {}
    items = sorted(data.items(), key=lambda x: x[1].get("xp", 0), reverse=True)
    return [(uid, u) for uid, u in items if u.get("xp", 0) > 0][:n]


def reset(chat_id):
    set_("xp", chat_id, {})
    set_("xp_daily", chat_id, {})
    set_("xp_weekly", chat_id, {})
    set_("xp_monthly", chat_id, {})