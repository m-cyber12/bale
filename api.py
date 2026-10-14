# -*- coding: utf-8 -*-
import os
import time
import urllib.request
import urllib.parse
import urllib.error
import json
import socket
import threading
from config import BASE_URL

BOT_ID = None

_reply_ctx = threading.local()

# متدهایی که سرور 501 داده — با TTL، چون یک 501 گذرا نباید
# برای همیشه یک قابلیت (مثل getChatMember) را خاموش کند
_unsupported_methods = {}
_UNSUPPORTED_TTL = 900


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


def request(method, data=None, timeout=30):
    _uns_ts = _unsupported_methods.get(method)
    if _uns_ts and time.time() - _uns_ts < _UNSUPPORTED_TTL:
        return {"ok": False, "error_code": 501, "description": "Method not supported (cached)"}

    url = BASE_URL + method
    try:
        if data:
            body = urllib.parse.urlencode(data).encode('utf-8')
            req = urllib.request.Request(url, data=body)
        else:
            req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        if e.code == 501:
            _unsupported_methods[method] = time.time()
            return {"ok": False, "error_code": 501, "description": "Not Implemented"}

        SILENT_METHODS = (
            "getChatMember", "getChatAdministrators",
            "banChatMember", "restrictChatMember",
            "deleteMessage", "editMessageText",
            "answerCallbackQuery",
            "editMessageReplyMarkup",
            "pinChatMessage", "unpinChatMessage",
            "setChatPermissions",
        )
        if method not in SILENT_METHODS:
            print(f"[api:{method}] HTTP {e.code}")
        return {"ok": False, "error_code": e.code, "description": str(e)}
    except (urllib.error.URLError, socket.timeout) as e:
        print(f"[api:{method}] Network: {e}")
        return {"ok": False, "error_code": 0, "description": str(e)}
    except Exception as e:
        print(f"[api:{method}] {e}")
        return {"ok": False, "error_code": -1, "description": str(e)}


def get_updates(offset=None, timeout=30):
    url = BASE_URL + "getUpdates"
    params = {
        "timeout": timeout,
        "allowed_updates": json.dumps([
            "message",
            "callback_query",
            "edited_message",
            "channel_post",
            "edited_channel_post",
            "inline_query",
            "chosen_inline_result",
        ]),
    }
    if offset:
        params["offset"] = offset
    url += "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=timeout + 10) as r:
            return json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        print(f"[getUpdates] HTTP {e.code}")
        return None
    except Exception as e:
        print(f"[getUpdates] {e}")
        return None


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


def upload_file(method, files_dict, data_dict=None, timeout=120):
    boundary = "----AlfaBoundary" + str(int(time.time() * 1000))
    body = b""

    if data_dict:
        for key, value in data_dict.items():
            body += f"--{boundary}\r\n".encode("utf-8")
            body += f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode("utf-8")
            body += f"{value}\r\n".encode("utf-8")

    for key, filepath in files_dict.items():
        filename = os.path.basename(filepath)
        with open(filepath, "rb") as f:
            file_data = f.read()
        body += f"--{boundary}\r\n".encode("utf-8")
        body += f'Content-Disposition: form-data; name="{key}"; filename="{filename}"\r\n'.encode("utf-8")
        body += b"Content-Type: application/octet-stream\r\n\r\n"
        body += file_data
        body += b"\r\n"

    body += f"--{boundary}--\r\n".encode("utf-8")

    url = BASE_URL + method
    req = urllib.request.Request(url, data=body)
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    req.add_header("Content-Length", str(len(body)))

    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"[api:upload:{method}] HTTP {e.code}")
        return {"ok": False, "error_code": e.code}
    except Exception as e:
        print(f"[api:upload:{method}] {e}")
        return None


def me():
    global BOT_ID
    r = request("getMe")
    if r and r.get("ok"):
        BOT_ID = r["result"]["id"]
    return BOT_ID


def bot_id():
    if BOT_ID is None:
        me()
    return BOT_ID


def get_bot_username():
    """گرفتن یوزرنیم ربات"""
    r = request("getMe")
    if r and r.get("ok"):
        return (r["result"].get("username", "") or "").strip()
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