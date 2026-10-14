# -*- coding: utf-8 -*-
import html
import urllib.parse

import api
import storage
from storage import get, set_
import admin


def _chat_title(chat_id):
    try:
        r = api.get_chat(chat_id)
        if r and r.get("ok"):
            return r["result"].get("title", "گروه")
    except Exception:
        pass
    return "گروه"


def _chat_username(chat_id):
    try:
        r = api.get_chat(chat_id)
        if r and r.get("ok"):
            return r["result"].get("username", "")
    except Exception:
        pass
    return ""


def get_admins_list(chat_id):
    admins = []
    try:
        r = api.admins(chat_id)
        if r and r.get("ok"):
            for a in r.get("result", []):
                u = a.get("user", {})
                admins.append({
                    "id": u.get("id"),
                    "name": admin.u_name(u),
                    "username": u.get("username", ""),
                    "status": a.get("status", ""),
                })
    except Exception as e:
        print(f"[get_admins] {e}")
    return admins


def _admin_links(admins):
    """لیست ادمین‌ها با لینک — parse_mode این پیام‌ها HTML است، پس escape لازم است."""
    lines = []
    for a in admins:
        name = html.escape(str(a.get("name", "ادمین") or "ادمین"))
        uid = a.get("id")
        uname = a.get("username", "")
        status = a.get("status", "")
        icon = "👑" if status == "creator" else "🛡"
        if uname:
            uname_esc = html.escape(str(uname))
            uname_url = urllib.parse.quote(str(uname))
            lines.append(f"{icon} {name} — "
                         f"<a href='https://ble.ir/{uname_url}'>@{uname_esc}</a>")
        elif uid:
            lines.append(f"{icon} <a href='tg://user?id={int(uid)}'>{name}</a>")
        else:
            lines.append(f"{icon} {name}")
    return "\n".join(lines)


def notify_punishment(target_id, chat_id, action, reason="", by_name="", duration=""):
    title = _chat_title(chat_id)
    cuname = _chat_username(chat_id)
    chat_link = f"https://ble.ir/{cuname}" if cuname else ""

    if action == "ban":
        headline = "شما از گروه بن شدید"
    elif action == "mute":
        headline = "شما در گروه سکوت شدید"
    elif action == "kick":
        headline = "شما از گروه اخراج شدید"
    elif action == "warn":
        headline = "شما اخطار گرفتید"
    else:
        headline = "اطلاعیه از گروه"

    text = f"📩 {headline}\n\n"
    text += f"🏠 گروه: {title}\n"

    if action == "mute" and duration:
        text += f"⏱ مدت: {duration}\n"
    if reason:
        text += f"📝 دلیل: {reason}\n"
    if by_name:
        text += f"👮 توسط: {by_name}\n"

    text += "\n"

    admins = get_admins_list(chat_id)
    if admins:
        text += "اگه اعتراض داری، به این افراد پیام بده:\n\n"
        text += _admin_links(admins)
    else:
        text += "اگه اعتراض داری به ادمین‌های گروه پیام بده."

    rows = []
    if chat_link:
        rows.append([{"text": "🔗 برگشت به گروه", "url": chat_link}])
    for a in admins[:2]:
        if a.get("username"):
            rows.append([{"text": f"💬 {a['name']}", "url": f"https://ble.ir/{a['username']}"}])

    markup = {"inline_keyboard": rows} if rows else None

    try:
        r = api.send(int(target_id), text, parse_mode="HTML", markup=markup, reply_to=0)
        if r and r.get("ok"):
            print(f"[notify:{action}] ✅ به {target_id}")
            return True, None
        else:
            desc = (r or {}).get("description", "خطا")
            print(f"[notify:{action}] ❌ {desc}")
            return False, desc
    except Exception as e:
        print(f"[notify:{action}] ❌ {e}")
        return False, str(e)


def notify_warn(target_id, chat_id, count, max_count, by_name="", reason=""):
    title = _chat_title(chat_id)

    text = f"⚠️ اخطار {count} از {max_count}\n\n"
    text += f"🏠 گروه: {title}\n"
    if reason:
        text += f"📝 دلیل: {reason}\n"
    if by_name:
        text += f"👮 توسط: {by_name}\n"

    if count >= max_count - 1:
        text += "\n⚠️ با یه اخطار دیگه بن می‌شی."

    text += "\n\n"

    admins = get_admins_list(chat_id)
    if admins:
        text += "اگه اعتراض داری، به این افراد پیام بده:\n\n"
        text += _admin_links(admins)

    try:
        r = api.send(int(target_id), text, parse_mode="HTML", reply_to=0)
        if r and r.get("ok"):
            return True, None
        return False, (r or {}).get("description", "خطا")
    except Exception as e:
        return False, str(e)