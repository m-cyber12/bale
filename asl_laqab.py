# -*- coding: utf-8 -*-
"""اصل و لقب - آلفا"""
import time
import api
import storage
from storage import get, set_
import admin


def kb(rows):
    return {"inline_keyboard": [r for r in rows if r]}


def btn(text, data=None):
    return {"text": text, "callback_data": data}


# ============================================================
# درخواست ثبت اصل
# ============================================================
def cmd_asl_request(chat_id, user_id, message, args):
    """کاربر درخواست ثبت اصل میده - ادمین تأیید می‌کنه"""
    if not args:
        api.send(chat_id,
            "╔══════════════════════════╗\n"
            "║      📜  ثـبـت اصـل         ║\n"
            "╚══════════════════════════╝\n\n"
            "🙏 برای ثبت اصلت بنویس:\n"
            "`اصل من (متن)`\n\n"
            "📝 مثال:\n"
            "• `اصل من تهرانی`\n"
            "• `اصل من اصفهانی`\n"
            "• `اصل من شیرازی`\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "⚠️ **فقط ادمین‌های محترم گروه** می‌تونن تأیید کنن",
            parse_mode="Markdown",
            reply_to=message["message_id"])
        return

    text = " ".join(args).strip()
    if not text:
        return

    if len(text) > 50:
        text = text[:50]

    user_name = admin.u_name(message["from"])

    asl = get("asl", chat_id) or {}
    asl[str(user_id)] = {
        "text": text,
        "status": "pending",
        "ts": time.time(),
        "name": user_name,
        "user_id": user_id,
    }
    set_("asl", chat_id, asl)

    rows = [
        [btn("✅ تأیید", f"asl:approve:{user_id}"),
         btn("❌ رد", f"asl:reject:{user_id}")],
    ]

    api.send(chat_id,
        f"╔══════════════════════════╗\n"
        f"║    📩  درخـواسـت ثـبـت اصل     ║\n"
        f"╚══════════════════════════╝\n\n"
        f"👤 کاربر: **{api.esc_md(user_name)}**\n"
        f"🆔 `{user_id}`\n"
        f"📝 اصل درخواستی: _{text}_\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👮 **ادمین‌های محترم، تأیید کنید:**\n\n"
        f"👇",
        markup=kb(rows),
        parse_mode="Markdown")


def cmd_asl_show(chat_id, user_id, message, args):
    """نمایش اصل کاربر"""
    t = admin.get_target(message)
    if not t:
        t = message["from"]

    asl = get("asl", chat_id) or {}
    data = asl.get(str(t["id"]))

    if not data:
        api.send(chat_id,
            f"ℹ️ **{api.esc_md(admin.u_name(t))}** اصل ثبت شده‌ای نداره.",
            parse_mode="Markdown",
            reply_to=message["message_id"])
        return

    status_fa = {
        "approved": "✅ تأیید شده",
        "pending": "⏳ در انتظار تأیید",
        "rejected": "❌ رد شده",
    }.get(data.get("status", "pending"), "?")

    api.send(chat_id,
        f"╔══════════════════════════╗\n"
        f"║      📜  اصـل کـاربـر        ║\n"
        f"╚══════════════════════════╝\n\n"
        f"👤 **{api.esc_md(admin.u_name(t))}**\n"
        f"📝 **اصل:** _{data.get('text', '-')}_\n"
        f"📊 **وضعیت:** {status_fa}",
        parse_mode="Markdown",
        reply_to=message["message_id"])


# ============================================================
# لقب - ادمین‌ها برای عادی، مالک برای همه
# ============================================================
def cmd_laqab(chat_id, user_id, message, args):
    """ادمین به کاربر لقب میده"""
    t = admin.get_target(message)
    if not t:
        api.send(chat_id,
            "🙏 روی پیام کاربر **ریپلای** کن و بعد لقب رو بنویس\n\n"
            "📝 **مثال:** `لقب مدیر نمونه`",
            reply_to=message["message_id"])
        return

    tid = t["id"]
    tname = admin.u_name(t)
    sender = message["from"]
    sender_name = admin.u_name(sender)

    # چک: کاربر فرستنده ادمینه (تو main چک شده)
    # چک: اگه هدف ادمینه، فقط مالک می‌تونه
    if admin.is_admin(chat_id, tid):
        if not admin.is_creator(chat_id, user_id):
            api.send(chat_id,
                "╔══════════════════════════╗\n"
                "║    👑  فـقـط مـالـک         ║\n"
                "╚══════════════════════════╝\n\n"
                "🙏 **فقط مالک گروه** می‌تونه برای ادمین‌ها لقب بذاره.",
                parse_mode="Markdown",
                reply_to=message["message_id"])
            return

    if not args:
        titles = get("titles", chat_id) or {}
        cur = titles.get(str(tid), "—")
        api.send(chat_id,
            f"🏷 **لقب {api.esc_md(tname)}:** _{cur}_\n\n"
            f"برای تغییر: `لقب (متن جدید)`",
            parse_mode="Markdown",
            reply_to=message["message_id"])
        return

    title = " ".join(args).strip()
    if len(title) > 30:
        title = title[:30]

    titles = get("titles", chat_id) or {}
    titles[str(tid)] = title
    set_("titles", chat_id, titles)

    api.send(chat_id,
        f"╔══════════════════════════╗\n"
        f"║     🏷  لقـب ثـبـت شـد       ║\n"
        f"╚══════════════════════════╝\n\n"
        f"👤 **کاربر:** {api.esc_md(tname)}\n"
        f"🏷 **لقب:** _{title}_\n\n"
        f"👮 توسط: {sender_name}",
        parse_mode="Markdown",
        reply_to=message["message_id"])


def cmd_laqab_remove(chat_id, user_id, message):
    """حذف لقب"""
    t = admin.get_target(message)
    if not t:
        api.send(chat_id, "🙏 ریپلای کن!", reply_to=message["message_id"])
        return

    tid = t["id"]
    tname = admin.u_name(t)

    if admin.is_admin(chat_id, tid):
        if not admin.is_creator(chat_id, user_id):
            api.send(chat_id,
                "👑 **فقط مالک** می‌تونه لقب ادمین‌ها رو حذف کنه.",
                parse_mode="Markdown",
                reply_to=message["message_id"])
            return

    titles = get("titles", chat_id) or {}
    titles.pop(str(tid), None)
    set_("titles", chat_id, titles)

    api.send(chat_id,
        f"🗑 لقب **{api.esc_md(tname)}** حذف شد.",
        parse_mode="Markdown",
        reply_to=message["message_id"])


def cmd_laqab_list(chat_id, user_id, message):
    """لیست همه لقب‌ها"""
    titles = get("titles", chat_id) or {}
    if not titles:
        api.send(chat_id, "ℹ️ هنوز کسی لقب نداره.",
                 reply_to=message["message_id"])
        return

    txt = (
        "╔══════════════════════════╗\n"
        "║    🏷  لـیـسـت لـقـب‌هـا     ║\n"
        "╚══════════════════════════╝\n\n"
    )
    for uid, title in list(titles.items())[:30]:
        txt += f"👤 `{uid}` → _{api.esc_md(title)}_\n"

    api.send(chat_id, txt, parse_mode="Markdown", reply_to=message["message_id"])


# ============================================================
# Callback
# ============================================================
def handle_asl_callback(cb, cb_id, data, chat_id, msg_id, user):
    user_id = user["id"]

    if not admin.is_admin(chat_id, user_id):
        api.answer_callback(cb_id, "🙏 فقط ادمین‌ها!", alert=True)
        return

    parts = data.split(":")
    action = parts[1]
    target_id = int(parts[2])

    asl = get("asl", chat_id) or {}
    entry = asl.get(str(target_id))

    if not entry:
        api.answer_callback(cb_id, "❌ درخواست پیدا نشد", alert=True)
        return

    approver = admin.u_name(user)

    if action == "approve":
        entry["status"] = "approved"
        entry["approved_by"] = user_id
        entry["approved_at"] = time.time()
        asl[str(target_id)] = entry
        set_("asl", chat_id, asl)

        api.answer_callback(cb_id, "✅ تأیید شد")

        try:
            api.edit_message(chat_id, msg_id,
                f"╔══════════════════════════╗\n"
                f"║    ✅  اصـل تـأیـیـد شـد       ║\n"
                f"╚══════════════════════════╝\n\n"
                f"👤 **کاربر:** {entry.get('name', 'کاربر')}\n"
                f"📝 **اصل:** _{entry.get('text', '-')}_\n\n"
                f"👮 توسط: {approver}",
                parse_mode="Markdown")
        except: pass

    elif action == "reject":
        entry["status"] = "rejected"
        entry["rejected_by"] = user_id
        entry["rejected_at"] = time.time()
        asl[str(target_id)] = entry
        set_("asl", chat_id, asl)

        api.answer_callback(cb_id, "❌ رد شد")

        try:
            api.edit_message(chat_id, msg_id,
                f"╔══════════════════════════╗\n"
                f"║    ❌  اصـل رد شـد          ║\n"
                f"╚══════════════════════════╝\n\n"
                f"👤 **کاربر:** {entry.get('name', 'کاربر')}\n"
                f"📝 **اصل:** _{entry.get('text', '-')}_\n\n"
                f"👮 توسط: {approver}",
                parse_mode="Markdown")
        except: pass


def get_asl(chat_id, user_id):
    """گرفتن اصل تأیید شده کاربر"""
    asl = get("asl", chat_id) or {}
    entry = asl.get(str(user_id))
    if entry and entry.get("status") == "approved":
        return entry.get("text")
    return None


def get_laqab(chat_id, user_id):
    """گرفتن لقب کاربر"""
    titles = get("titles", chat_id) or {}
    return titles.get(str(user_id))