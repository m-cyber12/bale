# -*- coding: utf-8 -*-
import os
import time
import urllib.request
import urllib.parse
import urllib.error
import json
import socket
import threading
import platforms
from config import BASE_URL

BOT_ID = None

_reply_ctx = threading.local()
#: پیام‌رسانی که همین حالا در حال پردازش آپدیتش هستیم (thread-local)
_ctx = threading.local()

# متدهایی که سرور 501 داده — با TTL، چون یک 501 گذرا نباید
# برای همیشه یک قابلیت (مثل getChatMember) را خاموش کند
# کلید: (پیام‌رسان، متد)
_unsupported_methods = {}
_UNSUPPORTED_TTL = 900


# ============================================================
# 🛰 انتخاب پیام‌رسان برای هر درخواست
# ============================================================
def set_platform(key):
    """هنگام پردازش آپدیت، پیام‌رسانش را اینجا ثبت می‌کنیم."""
    try:
        _ctx.platform = platforms.resolve_key(key)
    except Exception:
        pass


def clear_platform():
    if hasattr(_ctx, "platform"):
        try:
            del _ctx.platform
        except Exception:
            pass


def current_platform_key():
    return getattr(_ctx, "platform", None)


def platform_for(data=None, platform=None):
    """۱) صریح  ۲) آپدیت در حال پردازش  ۳) نقشه‌ی چت  ۴) پیش‌فرض"""
    if platform is not None:
        return platforms.get(platform) if isinstance(platform, str) else platform

    key = current_platform_key()
    if key:
        return platforms.get(key)

    chat_id = None
    if isinstance(data, dict):
        chat_id = data.get("chat_id")
        if chat_id is None:
            chat_id = data.get("from_chat_id")
    if chat_id is not None:
        plat = platforms.platform_of_chat(chat_id)
        if plat:
            return plat

    return platforms.default()


def set_reply_context(msg_id):
    try:
        _reply_ctx.msg_id = msg_id
    except Exception:
        pass


def clear_reply_context():
    if hasattr(_reply_ctx, 'msg_id'):
        try:
            del _reply_ctx.msg_id
        except Exception:
            pass


def get_reply_context():
    return getattr(_reply_ctx, 'msg_id', None)


# ============================================================
# ✅ Escape متن کاربر برای parse_mode="Markdown"
# ============================================================
import re as _re

_MD_SPECIAL = _re.compile(r"([_*`\[\]\\])")


def esc_md(value):
    """کاراکترهای ویژه‌ی Markdown را escape می‌کند.

    نام و یوزرنیم کاربر‌ها می‌تواند `_` یا `*` یا `` ` `` داشته باشد
    (مثل @ali_reza). اگر escape نشود کل پیام با خطای
    "Can't parse entities" رد می‌شود و کاربر هیچی نمی‌بیند.
    """
    if value is None:
        return ""
    s = str(value)
    if not s:
        return s
    return _MD_SPECIAL.sub(lambda m: "\\" + m.group(1), s)


def esc_html(value):
    """همان کار esc_md ولی برای parse_mode="HTML"."""
    if value is None:
        return ""
    s = str(value)
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _is_parse_error(r):
    """آیا خطا مربوط به parse_mode است؟"""
    if not r or r.get("ok"):
        return False
    desc = (r.get("description") or "").lower()
    return ("parse entities" in desc) or ("can't find end" in desc) or \
           ("can't find start" in desc) or ("unsupported start tag" in desc)


def _pm(chat_id, mode, platform=None):
    """parse_mode را به چیزی که این پیام‌رسان قبول می‌کند ترجمه می‌کند.

    اگر پلتفرم آن حالت را نداشته باشد None برمی‌گردد (متن خام = امن‌ترین).
    """
    if not mode:
        return None
    try:
        plat = platform_for({"chat_id": chat_id}, platform)
        return plat.parse_mode(mode)
    except Exception:
        return mode


def _plain_retry(method, d):
    """تلاش دوباره بدون parse_mode تا پیام اصلاً گم نشود."""
    d2 = dict(d)
    d2.pop("parse_mode", None)
    try:
        return request(method, d2)
    except Exception:
        return None


# ✅ کش callback ها با TTL
_answered_cbs = {}


def _call(method, data=None, timeout=30, platform=None):
    """صدا زدن request با تحمل امضاهای ساده‌تر (مثل شبیه‌سازها)."""
    try:
        return request(method, data, timeout=timeout, platform=platform)
    except TypeError:
        return request(method, data, timeout=timeout)


def request(method, data=None, timeout=30, platform=None):
    """درخواست به API — پیام‌رسان از روی chat_id / context انتخاب می‌شود."""
    plat = platform_for(data, platform)
    cache_key = (getattr(plat, "key", "?"), method)
    _uns_ts = _unsupported_methods.get(cache_key)
    if _uns_ts and time.time() - _uns_ts < _UNSUPPORTED_TTL:
        return {"ok": False, "error_code": 501,
                "description": "Method not supported (cached)"}

    r = plat.request(method, data, timeout=timeout)
    if r and not r.get("ok") and r.get("error_code") == 501:
        _unsupported_methods[cache_key] = time.time()
    return r


def get_updates(offset=None, timeout=30, platform=None):
    """long-polling روی پیام‌رسان مشخص (پیش‌فرض: اصلی)."""
    plat = platform_for(None, platform)
    return plat.get_updates(offset=offset, timeout=timeout)


def _has_copy_text(markup):
    """چک می‌کنه آیا markup شامل copy_text هست"""
    if not markup:
        return False
    try:
        for row in markup.get("inline_keyboard", []):
            for b in row:
                if "copy_text" in b:
                    return True
    except Exception:
        pass
    return False


def _strip_copy_text(markup):
    """copy_text رو به callback_data تبدیل می‌کنه (fallback)"""
    if not markup:
        return markup
    new_kb = []
    for row in markup.get("inline_keyboard", []):
        new_row = []
        for b in row:
            if "copy_text" in b:
                txt = b["copy_text"].get("text", "")
                cb_data = "cp:" + txt[:60]
                new_row.append({"text": b["text"], "callback_data": cb_data})
            else:
                new_row.append(b)
        new_kb.append(new_row)
    return {"inline_keyboard": new_kb}


def send(chat_id, text, reply_to=None, markup=None, parse_mode=None):
    if reply_to is None:
        reply_to = get_reply_context()
    if reply_to == 0:
        reply_to = None

    d = {"chat_id": chat_id, "text": text}
    if reply_to:
        d["reply_to_message_id"] = reply_to
    parse_mode = _pm(chat_id, parse_mode)
    if parse_mode:
        d["parse_mode"] = parse_mode
    if markup:
        d["reply_markup"] = json.dumps(markup, ensure_ascii=False)

    r = request("sendMessage", d)

    # ✅ fallback: اگه copy_text پشتیبانی نشد
    if r and not r.get("ok") and markup and _has_copy_text(markup):
        err_desc = (r.get("description") or "").lower()
        if "copy_text" in err_desc or "unknown" in err_desc or "button" in err_desc:
            print(f"[send:fallback] copy_text not supported, retrying...")
            d["reply_markup"] = json.dumps(_strip_copy_text(markup), ensure_ascii=False)
            r = request("sendMessage", d)

    # ✅ fallback نهایی: parse_mode رد شد → بدون parse_mode بفرست (پیام گم نشه)
    if _is_parse_error(r) and d.get("parse_mode"):
        print(f"[send:fallback] parse_mode rejected, sending as plain text")
        r = _plain_retry("sendMessage", d)

    if r and not r.get("ok"):
        print(f"❌ SEND FAIL: chat={chat_id} reply={reply_to} err={r.get('error_code')} desc={r.get('description')} text={text[:60]!r}")
    return r


def send_no_reply(chat_id, text, parse_mode=None, markup=None):
    d = {"chat_id": chat_id, "text": text}
    parse_mode = _pm(chat_id, parse_mode)
    if parse_mode:
        d["parse_mode"] = parse_mode
    if markup:
        d["reply_markup"] = json.dumps(markup, ensure_ascii=False)
    r = request("sendMessage", d)

    # ✅ fallback برای copy_text
    if r and not r.get("ok") and markup and _has_copy_text(markup):
        err_desc = (r.get("description") or "").lower()
        if "copy_text" in err_desc or "unknown" in err_desc or "button" in err_desc:
            d["reply_markup"] = json.dumps(_strip_copy_text(markup), ensure_ascii=False)
            r = request("sendMessage", d)

    # ✅ fallback نهایی: parse_mode رد شد → بدون parse_mode بفرست
    if _is_parse_error(r) and d.get("parse_mode"):
        print(f"[send:fallback] parse_mode rejected, sending as plain text")
        r = _plain_retry("sendMessage", d)

    return r


def send_autodelete(chat_id, text, sec=5, parse_mode=None, markup=None):
    r = send_no_reply(chat_id, text, parse_mode=parse_mode, markup=markup)
    if r and r.get("ok"):
        try:
            mid = r["result"]["message_id"]
            def _del():
                time.sleep(sec)
                try:
                    delete(chat_id, mid)
                except: pass
            threading.Thread(target=_del, daemon=True).start()
        except Exception as e:
            print(f"[send_autodelete] {e}")
    return r


def edit_message(chat_id, msg_id, text, markup=None, parse_mode=None):
    d = {"chat_id": chat_id, "message_id": msg_id, "text": text}
    parse_mode = _pm(chat_id, parse_mode)
    if parse_mode:
        d["parse_mode"] = parse_mode
    if markup:
        d["reply_markup"] = json.dumps(markup, ensure_ascii=False)

    r = request("editMessageText", d)

    # ✅ fallback برای copy_text
    if r and not r.get("ok") and markup and _has_copy_text(markup):
        err_desc = (r.get("description") or "").lower()
        if "copy_text" in err_desc or "unknown" in err_desc or "button" in err_desc:
            print(f"[edit:fallback] copy_text not supported, retrying...")
            d["reply_markup"] = json.dumps(_strip_copy_text(markup), ensure_ascii=False)
            r = request("editMessageText", d)

    # ✅ fallback نهایی: parse_mode رد شد → بدون parse_mode ویرایش کن
    if _is_parse_error(r) and d.get("parse_mode"):
        print(f"[edit:fallback] parse_mode rejected, retrying as plain text")
        r = _plain_retry("editMessageText", d)

    return r


def answer_callback(cb_id, text="", alert=False):
    """✅ نسخه با TTL — جلوگیری از پاک شدن کل کش"""
    if not cb_id:
        return None
    now = time.time()

    if cb_id in _answered_cbs:
        if now - _answered_cbs[cb_id] < 30:
            return None

    _answered_cbs[cb_id] = now

    # ✅ پاکسازی entry های قدیمی
    if len(_answered_cbs) > 500:
        expired = [k for k, ts in _answered_cbs.items() if now - ts > 60]
        for k in expired:
            _answered_cbs.pop(k, None)

    d = {"callback_query_id": str(cb_id)}
    if text:
        d["text"] = str(text)[:200]
    if alert:
        d["show_alert"] = "true"
    try:
        return request("answerCallbackQuery", d)
    except Exception as e:
        print(f"[api:answer_callback] {e}")
        return None


def delete(chat_id, msg_id):
    for i in range(3):
        try:
            r = request("deleteMessage", {"chat_id": chat_id, "message_id": msg_id})
            if r and r.get("ok"):
                return r
            if r and r.get("error_code") == 400:
                return r
        except Exception:
            pass
        time.sleep(0.1)
    return None


def restrict(chat_id, user_id, perms):
    """تلاش برای محدود کردن کاربر."""
    try:
        r = request("restrictChatMember", {
            "chat_id": str(chat_id),
            "user_id": str(user_id),
            "permissions": json.dumps(perms)
        })
        if r and r.get("ok"):
            return r
    except Exception:
        pass

    try:
        d2 = {"chat_id": str(chat_id), "user_id": str(user_id)}
        for k, v in perms.items():
            d2[k] = "true" if v else "false"
        r = request("restrictChatMember", d2)
        if r and r.get("ok"):
            return r
    except Exception:
        pass

    return None


def ban(chat_id, user_id):
    return request("banChatMember", {"chat_id": chat_id, "user_id": user_id})


def unban(chat_id, user_id):
    return request("unbanChatMember", {"chat_id": chat_id, "user_id": user_id})


def get_member(chat_id, user_id):
    return request("getChatMember", {"chat_id": chat_id, "user_id": user_id})


def pin(chat_id, msg_id):
    return request("pinChatMessage", {"chat_id": chat_id, "message_id": msg_id})


def unpin(chat_id):
    return request("unpinChatMessage", {"chat_id": chat_id})


def get_chat(chat_id):
    return request("getChat", {"chat_id": chat_id})


def admins(chat_id):
    return request("getChatAdministrators", {"chat_id": chat_id})


def members_count(chat_id):
    return request("getChatMembersCount", {"chat_id": chat_id})


def getFile(file_id):
    return request("getFile", {"file_id": file_id})


def forward_message(to_chat_id, from_chat_id, message_id):
    return request("forwardMessage", {
        "chat_id": to_chat_id,
        "from_chat_id": from_chat_id,
        "message_id": message_id,
    })


def copy_message(to_chat_id, from_chat_id, message_id, caption=None):
    d = {"chat_id": to_chat_id, "from_chat_id": from_chat_id, "message_id": message_id}
    if caption is not None:
        d["caption"] = caption
    return request("copyMessage", d)


def set_chat_permissions(chat_id, perms):
    try:
        r = request("setChatPermissions", {
            "chat_id": chat_id,
            "permissions": json.dumps(perms)
        })
        return r
    except Exception:
        return None


def upload_file(method, files_dict, data_dict=None, timeout=120, platform=None):
    """آپلود فایل چندبخشی (عکس/ویدیو/گیف)."""
    plat = platform_for(data_dict, platform)
    return plat.request(method, data_dict, timeout=timeout, files=files_dict)


#: شناسه‌ی ربات روی هر پیام‌رسان (چون روی هر کدام یک ربات جدا هستیم)
_BOT_IDS = {}


def me(platform=None, force=False):
    """شناسه‌ی ربات روی پیام‌رسان مشخص.

    همیشه از مسیر `request` می‌رود تا تست‌ها/شبیه‌سازها هم کار کنند
    (اگر مستقیم روی پلتفرم برود، شبیه‌ساز دور زده می‌شود).
    """
    global BOT_ID
    plat = platform_for(None, platform)
    key = getattr(plat, "key", "default")
    if not force and key in _BOT_IDS:
        return _BOT_IDS[key]

    r = _call("getMe", None, platform=plat)
    if r and r.get("ok"):
        rid = (r.get("result") or {}).get("id")
        _BOT_IDS[key] = rid
        BOT_ID = rid                    # سازگاری با کدهای قدیمی
        return rid
    return None


def bot_id(chat_id=None):
    """شناسه‌ی ربات در همان پیام‌رسانی که این چت رویش است."""
    plat = platform_for({"chat_id": chat_id} if chat_id is not None else None)
    key = getattr(plat, "key", "default")
    if key in _BOT_IDS:
        return _BOT_IDS[key]
    return me(platform=plat)


def get_bot_username(platform=None):
    """گرفتن یوزرنیم ربات"""
    plat = platform_for(None, platform)
    r = _call("getMe", None, platform=plat)
    if r and r.get("ok"):
        return (r.get("result", {}).get("username", "") or "").strip()
    return ""


def promote(chat_id, user_id, perms=None):
    d = {"chat_id": chat_id, "user_id": user_id}
    if perms:
        for k, v in perms.items():
            d[k] = "true" if v else "false"
    else:
        d["can_change_info"] = "true"
        d["can_delete_messages"] = "true"
        d["can_invite_users"] = "true"
        d["can_restrict_members"] = "true"
        d["can_pin_messages"] = "true"
        d["can_promote_members"] = "false"
        d["can_manage_video_chats"] = "true"
    return request("promoteChatMember", d)


def demote(chat_id, user_id):
    d = {"chat_id": chat_id, "user_id": user_id}
    for k in ("can_change_info", "can_delete_messages", "can_invite_users",
              "can_restrict_members", "can_pin_messages", "can_promote_members",
              "can_manage_video_chats"):
        d[k] = "false"
    return request("promoteChatMember", d)