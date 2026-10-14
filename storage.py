# -*- coding: utf-8 -*-
import json
import os
import threading
from config import DATA_DIR

FILE = os.path.join(DATA_DIR, "groups.json")
_save_lock = threading.Lock()

_DB = {
    "locks": {},
    "warnings": {},
    "muted": {},
    "titles": {},
    "welcome": {},
    "banned_words": {},
    "rules": {},
    "antispam": {},
    "xp": {},
    "xp_daily": {},
    "xp_weekly": {},
    "xp_monthly": {},
    "xp_meta": {},
    "notes": {},
    "settings": {},
    "banned_users": {},
    "force_join": {},
    "group_join": {},
    "bot_users": {},
    "bot_groups": {},
    "bot_owner": {},
    "bot_admins": {},
    "punish_log": {},
    "slowmode": {},
    "night_mode": {},
    "whitelist": {},
    "custom_commands": {},
    "msg_stats": {},
    "game_stats": {},
    "active_games": {},
    "polls": {},
    "admin_logs": {},
    "afk": {},
    "quizzes": {},
    "invites": {},
    "weekly_report": {},
    "panel_owners": {},
    "badword": {},
    "extra_bad_words": {},
    "gif_flows": {},
    "bug_reports": {},
    "asl": {},
    "group_lock": {},
    "known_users": {},
    "locks_config": {},
    "lock_warnings": {},
    "banned_words_config": {},
    "bw_warnings": {},
    "sleep_mode": {},
    "antispam_warns": {},
    "join_cache": {},
    "user_profiles": {},
    "members_seen": {},
}


def load():
    global _DB
    if not os.path.isdir(DATA_DIR):
        os.makedirs(DATA_DIR)
    if os.path.isfile(FILE):
        try:
            with open(FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for k in data.keys():
                _DB[k] = data[k]
            for k in list(_DB.keys()):
                if k not in data:
                    _DB[k] = _DB[k] if isinstance(_DB[k], dict) else {}
        except Exception as e:
            print(f"[storage] load error: {e}")


def save():
    with _save_lock:
        try:
            if not os.path.isdir(DATA_DIR):
                os.makedirs(DATA_DIR)
            tmp = FILE + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(_DB, f, ensure_ascii=False, indent=2)
            os.replace(tmp, FILE)
        except Exception as e:
            print(f"[storage] save error: {e}")


def db():
    return _DB


def get(section, chat_id, default=None):
    try:
        return _DB.get(section, {}).get(str(chat_id), default if default is not None else {})
    except Exception:
        return default if default is not None else {}


def set_(section, chat_id, value):
    _DB.setdefault(section, {})[str(chat_id)] = value
    save()


def update(section, chat_id, key, value):
    s = _DB.setdefault(section, {}).setdefault(str(chat_id), {})
    s[str(key)] = value
    save()


def remove(section, chat_id, key=None):
    if str(chat_id) in _DB.get(section, {}):
        if key is None:
            del _DB[section][str(chat_id)]
        else:
            _DB[section][str(chat_id)].pop(str(key), None)
        save()


def log_punish(chat_id, user_id, action, by_id, reason=""):
    from datetime import datetime
    logs = _DB.setdefault("punish_log", {}).setdefault(str(chat_id), [])
    logs.append({
        "user_id": user_id,
        "action": action,
        "by": by_id,
        "reason": reason,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
    })
    logs[:] = logs[-100:]
    save()


def add_game_win(chat_id, game, user_id, user_name=""):
    stats = _DB.setdefault("game_stats", {}).setdefault(str(chat_id), {})
    g = stats.setdefault(game, {})
    uid = str(user_id)
    if uid not in g:
        g[uid] = {"wins": 0, "name": user_name}
    g[uid]["wins"] += 1
    if user_name:
        g[uid]["name"] = user_name
    try:
        from xp import add_game_xp
        add_game_xp(chat_id, user_id, user_name, game_key=game, amount=15)
    except Exception as e:
        print(f"[add_game_xp] {e}")
    save()


def get_game_leaderboard(chat_id, game, n=10):
    stats = _DB.get("game_stats", {}).get(str(chat_id), {}).get(game, {})
    items = sorted(stats.items(), key=lambda x: x[1].get("wins", 0), reverse=True)
    return items[:n]


def save_banned(chat_id, user_id, name=""):
    banned = _DB.setdefault("banned_users", {}).setdefault(str(chat_id), {})
    banned[str(user_id)] = {"name": name or f"کاربر {user_id}"}
    save()


def remove_banned(chat_id, user_id):
    banned = _DB.setdefault("banned_users", {}).setdefault(str(chat_id), {})
    banned.pop(str(user_id), None)
    save()


def save_muted(chat_id, user_id, exp_time):
    muted = _DB.setdefault("muted", {}).setdefault(str(chat_id), {})
    muted[str(user_id)] = exp_time
    save()


def remove_muted(chat_id, user_id):
    muted = _DB.setdefault("muted", {}).setdefault(str(chat_id), {})
    muted.pop(str(user_id), None)
    save()