# -*- coding: utf-8 -*-
"""پیام‌رسان عمومی «هرچیزی که وب‌هوک دارد».

با این آداپتور هر پیام‌رسانی که بتواند JSON بفرستد/بگیرد به ربات وصل می‌شود:

**ورودی (پیام‌رسان → ربات):**
    POST  https://<your-app>/webhook/webhook
    Header: `X-Webhook-Token: <WEBHOOK_TOKEN>`   (اگر تنظیم شده باشد)

سه شکل بدنه پذیرفته می‌شود:

1. شکل ساده (توصیه‌شده):
```json
{"chat_id": "-100123", "chat_type": "group", "chat_title": "گروه من",
 "user_id": 555, "user_name": "علی", "text": "سلام"}
```
2. شکل «رویداد»:
```json
{"event": "message", "chat": {...}, "from": {...}, "text": "سلام"}
```
3. شکل خام بله/تلگرام:
```json
{"message": {"message_id": 1, "chat": {...}, "from": {...}, "text": "سلام"}}
```

**خروجی (ربات → پیام‌رسان):** ربات به `WEBHOOK_SEND_URL` یک JSON می‌فرستد:
```json
{"method": "sendMessage", "chat_id": "-100123", "text": "متن پیام",
 "parse_mode": "Markdown", "reply_to_message_id": 12}
```
پل (bridge) تو فقط باید همین را به API پیام‌رسان خودش ترجمه کند و
`{"ok": true, "result": {"message_id": 1}}` برگرداند.

تنظیمات:
    WEBHOOK_SEND_URL = https://my-bridge.example.com/send
    WEBHOOK_TOKEN    = یک رمز دلخواه برای اعتبارسنجی ورودی (اختیاری)
"""
import json
import os
import time
import urllib.error
import urllib.request

from .base import Platform

_MSG_ID = [0]


def _next_msg_id():
    _MSG_ID[0] += 1
    return _MSG_ID[0]


class WebhookPlatform(Platform):
    key = "webhook"
    title = "وب‌هوک (پیام‌رسان دلخواه)"
    token_envs = ("WEBHOOK_TOKEN",)
    base_url = ""
    body_format = "json"
    webhook_based = True
    supported_parse_modes = ("Markdown", "HTML")

    # ------------------------------------------------------------
    def configured(self):
        """اگر فقط آدرس ارسال تنظیم باشد کافی است (توکن اختیاری است)."""
        return bool(self.send_url())

    def send_url(self):
        return (os.environ.get("WEBHOOK_SEND_URL") or "").strip()

    def api_url(self):
        return self.send_url()

    def health(self):
        h = super().health()
        h["send_url_set"] = bool(self.send_url())
        return h

    # ------------------------------------------------------------
    # خروجی
    # ------------------------------------------------------------
    def request(self, method, data=None, timeout=30, files=None):
        url = self.send_url()
        if not url:
            return {"ok": False, "error_code": 401,
                    "description": "WEBHOOK_SEND_URL is not set"}
        body = {"method": method}
        for k, v in (data or {}).items():
            if v is None:
                continue
            body[k] = v
        try:
            req = urllib.request.Request(
                url, data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                headers={"Content-Type": "application/json; charset=utf-8"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read().decode("utf-8", "replace")
            try:
                parsed = json.loads(raw) if raw.strip() else {}
            except Exception:
                parsed = {}
            if not isinstance(parsed, dict):
                parsed = {}
            if "ok" not in parsed:
                # پل جواب استاندارد نداد → خودمان شناسه‌ی پیام می‌سازیم
                parsed = {"ok": True, "result": parsed or {
                    "message_id": _next_msg_id()}}
                parsed["result"].setdefault("message_id", _next_msg_id())
            return parsed
        except urllib.error.HTTPError as e:
            print(f"[webhook:{method}] HTTP {e.code}")
            return {"ok": False, "error_code": e.code, "description": str(e)}
        except Exception as e:
            print(f"[webhook:{method}] {e}")
            return {"ok": False, "error_code": 0, "description": str(e)}

    # ------------------------------------------------------------
    # ورودی
    # ------------------------------------------------------------
    def normalize(self, update):
        """هر سه شکل ورودی را به آپدیت مشترک تبدیل می‌کند."""
        if not isinstance(update, dict):
            return None

        # شکل ۳: از قبل بله/تلگرام‌گونه است
        if update.get("message") or update.get("callback_query"):
            return update

        # شکل ۲: event
        if update.get("event") and not update.get("text") and not update.get("message"):
            ev = update
        else:
            ev = update

        kind = (ev.get("event") or ev.get("type") or "message").lower()
        if kind in ("message", "text", "msg"):
            return {"message": self._build_message(ev, kind="message")}
        if kind in ("callback", "callback_query", "button"):
            cb = self._build_message(ev, kind="callback")
            return {"callback_query": cb}
        return {"message": self._build_message(ev, kind="message")}

    def _build_message(self, ev, kind="message"):
        chat = ev.get("chat") or {}
        user = ev.get("from") or ev.get("user") or {}

        chat_id = ev.get("chat_id")
        if chat_id is None:
            chat_id = chat.get("id")
        chat_title = ev.get("chat_title") or chat.get("title") or chat.get("name") or ""
        chat_type = ev.get("chat_type") or chat.get("type") or (
            "private" if user.get("id") and not chat_title else "supergroup")

        user_id = ev.get("user_id")
        if user_id is None:
            user_id = user.get("id")
        user_name = (ev.get("user_name") or user.get("first_name")
                     or user.get("name") or f"کاربر {user_id}")

        msg_id = ev.get("message_id") or _next_msg_id()
        text = ev.get("text") or ev.get("message") or ev.get("body") or ""

        msg = {
            "message_id": msg_id,
            "date": int(ev.get("date") or time.time()),
            "chat": {"id": _as_int(chat_id), "type": chat_type,
                     "title": chat_title},
            "from": {"id": _as_int(user_id), "is_bot": bool(user.get("is_bot")),
                     "first_name": user_name,
                     "username": user.get("username") or ev.get("username") or ""},
            "text": text if isinstance(text, str) else json.dumps(text,
                                                                  ensure_ascii=False),
        }

        if kind == "callback":
            return {
                "id": ev.get("callback_id") or ev.get("id") or f"wh{msg_id}",
                "from": msg["from"],
                "data": ev.get("data") or ev.get("callback_data") or "",
                "message": msg,
            }

        if ev.get("reply_to_message_id"):
            msg["reply_to_message"] = {
                "message_id": ev["reply_to_message_id"],
                "from": ev.get("reply_from") or {},
                "text": ev.get("reply_text") or "",
            }
        return msg


def _as_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return value
