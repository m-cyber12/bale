# -*- coding: utf-8 -*-
"""دستورات کاربر عادی"""
import time
from datetime import datetime
import api
import games
import xp as xp_mod
from storage import get, set_
import admin


def cmd_id(chat_id, user_id, message):
    api.send(chat_id, f"🆔 آیدی شما: `{user_id}`\nآیدی گروه: `{chat_id}`",
             parse_mode="Markdown", reply_to=message["message_id"])


def cmd_time(chat_id, user_id, message):
    now = datetime.now().strftime("%Y/%m/%d - %H:%M:%S")
    api.send(chat_id, f"🕐 {now}")


def cmd_calc(chat_id, user_id, message, args):
    if not args:
        api.send(chat_id, "مثال: /حساب 2+3*4")
        return
    expr = " ".join(args)
    allowed = set("0123456789+-*/(). ")
    if not all(c in allowed for c in expr):
        api.send(chat_id, "❌ فقط اعداد و عملگرها.")
        return
    try:
        result = eval(expr)
        api.send(chat_id, f"🧮 `{expr} = {result}`", parse_mode="Markdown", reply_to=message["message_id"])
    except:
        api.send(chat_id, "❌ خطا.")


def cmd_save(chat_id, user_id, message, args):
    if len(args) < 2:
        api.send(chat_id, "مثال: /ذخیره اسم متن")
        return
    name = args[0]
    content = " ".join(args[1:])
    notes = get("notes", chat_id) or {}
    notes[name] = content
    set_("notes", chat_id, notes)
    api.send(chat_id, f"✅ ذخیره شد: {name}")


def cmd_get(chat_id, user_id, message, args):
    if not args:
        return
    name = args[0]
    notes = get("notes", chat_id) or {}
    if name in notes:
        api.send(chat_id, notes[name], reply_to=message["message_id"])
    else:
        api.send(chat_id, "❌ پیدا نشد.")


def cmd_myxp(chat_id, user_id, message):
    u = xp_mod.get_user(chat_id, user_id)
    api.send(chat_id, f"⭐ XP: {u['xp']}\n🏅 سطح: {u['level']}", reply_to=message["message_id"])


def cmd_top(chat_id, user_id, message):
    top = xp_mod.top(chat_id, 10)
    if not top:
        api.send(chat_id, "هنوز کسی XP نگرفته.")
        return
    lines = ["🏆 **جدول برترین‌ها:**"]
    for i, (uid, u) in enumerate(top, 1):
        lines.append(f"{i}. `{uid}` → {u.get('xp',0)} XP (سطح {u.get('level',1)})")
    api.send(chat_id, "\n".join(lines), parse_mode="Markdown")


def cmd_report(chat_id, user_id, message, user_name):
    if not message.get("reply_to_message"):
        api.send(chat_id, "⚠️ روی پیام متخلف ریپلای کن!", reply_to=message["message_id"])
        return
    t = message["reply_to_message"]["from"]
    api.send(chat_id, f"📢 {api.esc_md(user_name)} از {admin.u_name(t)} گزارش داد!")