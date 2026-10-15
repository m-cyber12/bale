# -*- coding: utf-8 -*-
"""لایه‌ی پایه‌ی پیام‌رسان‌ها.

هر پیام‌رسان (بله، تلگرام، وب‌هوک عمومی و …) یک زیرکلاس `Platform` می‌سازد و
کارهای مخصوص خودش را تعریف می‌کند:

    key          شناسه‌ی کوتاه (bale / telegram / webhook / …)
    token_envs   نام متغیرهای محیطی توکن، به‌ترتیب اولویت
    base_url     آدرس API (با {token} در آن)
    normalize    تبدیل آپدیت خام → شکل داخلی ربات (هم‌شکل بله/تلگرام)
    parse_mode   ترجمه‌ی Markdown/HTML به چیزی که سرور قبول می‌کند
    adapt        تغییر نام/بدنه‌ی متدها اگر سرور اسم دیگری می‌خواهد
    encode       شکل بدنه‌ی درخواست (فرم‌محور یا JSON)

تمام منطق ربات فقط با شکل داخلی کار می‌کند؛ پس هیچ‌کدام از فایل‌های
panels/games/features/... لازم نیست بدانند روی چه پیام‌رسانی هستند.
"""
import json
import os
import socket
import time
import urllib.error
import urllib.parse
import urllib.request


class PlatformError(Exception):
    pass


class Platform:
    key = "base"
    title = "پیام‌رسان"
    token_envs = ()
    base_url = ""
    body_format = "form"          # form | json
    default_parse_mode = "Markdown"
    supported_parse_modes = ("Markdown", "HTML")
    allowed_updates = (
        "message", "callback_query", "edited_message",
        "channel_post", "edited_channel_post", "inline_query",
        "chosen_inline_result",
        # عضویت/ارتقا: بدون این‌ها ربات نمی‌فهمد ادمین شده یا کسی وارد/خارج شد
        "my_chat_member", "chat_member", "chat_join_request",
    )
    #: اگر True باشد یعنی آپدیت‌ها از راه وب‌هوک می‌آیند، نه long-polling
    webhook_based = False

    def __init__(self, token=None):
        self._token_override = token

    # ------------------------------------------------------------
    # توکن
    # ------------------------------------------------------------
    @property
    def token(self):
        if self._token_override:
            return self._token_override
        for env in self.token_envs:
            val = (os.environ.get(env) or "").strip()
            if val:
                return val
        # فایل اختصاصی پلتفرم: data/<key>_token.txt
        try:
            import config
            path = os.path.join(config.DATA_DIR, f"{self.key}_token.txt")
            if os.path.isfile(path):
                with open(path, "r", encoding="utf-8") as f:
                    return f.read().strip()
        except Exception:
            pass
        return ""

    def set_token(self, token):
        self._token_override = (token or "").strip()

    def configured(self):
        return bool(self.token)

    # ------------------------------------------------------------
    # آدرس و درخواست
    # ------------------------------------------------------------
    def api_url(self):
        base = (self.base_url or "").format(token=self.token)
        if not base.endswith("/"):
            base += "/"
        return base

    def method_name(self, method):
        """نقشه‌ی نام متد (پیش‌فرض: بدون تغییر)."""
        return method

    def adapt(self, method, data):
        """اصلاح بدنه‌ی درخواست برای این پیام‌رسان."""
        return data

    def parse_mode(self, mode):
        """اگر سرور این parse_mode را ندارد، None برگردان (متن خام امن‌تر است)."""
        if not mode:
            return None
        if mode in self.supported_parse_modes:
            return mode
        return None

    def encode(self, data):
        if self.body_format == "json":
            return json.dumps(data, ensure_ascii=False).encode("utf-8")
        clean = {}
        for k, v in (data or {}).items():
            if v is None:
                continue
            clean[k] = v
        return urllib.parse.urlencode(clean, doseq=True).encode("utf-8")

    def content_type(self):
        if self.body_format == "json":
            return "application/json; charset=utf-8"
        return "application/x-www-form-urlencoded"

    def request(self, method, data=None, timeout=30, files=None):
        """درخواست خام به API این پیام‌رسان. همیشه dict برمی‌گرداند."""
        if not self.token and not self.api_url().startswith("http"):
            return {"ok": False, "error_code": 401,
                    "description": f"token for {self.key} is not set"}
        if not self.api_url().startswith("http"):
            return {"ok": False, "error_code": 401,
                    "description": f"{self.key}: base url is not set"}

        method = self.method_name(method)
        data = self.adapt(method, dict(data or {}))
        url = self.api_url() + method

        try:
            if files:
                body, ctype = self._multipart(data, files)
                req = urllib.request.Request(url, data=body)
                req.add_header("Content-Type", ctype)
            elif data:
                req = urllib.request.Request(url, data=self.encode(data))
                req.add_header("Content-Type", self.content_type())
            else:
                req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8", "replace")
            except Exception:
                pass
            out = {"ok": False, "error_code": e.code, "description": str(e)}
            if body:
                try:
                    parsed = json.loads(body)
                    if isinstance(parsed, dict) and parsed.get("description"):
                        out["description"] = parsed["description"]
                except Exception:
                    out["raw"] = body[:300]
            self._log_http(method, e.code, out.get("description"))
            return out
        except (urllib.error.URLError, socket.timeout) as e:
            print(f"[{self.key}:{method}] Network: {e}")
            return {"ok": False, "error_code": 0, "description": str(e)}
        except Exception as e:
            print(f"[{self.key}:{method}] {e}")
            return {"ok": False, "error_code": -1, "description": str(e)}

    def _log_http(self, method, code, desc):
        return None

    def _multipart(self, data, files):
        boundary = f"----Alfa{int(time.time() * 1000)}"
        body = b""
        for key, value in (data or {}).items():
            body += f"--{boundary}\r\n".encode("utf-8")
            body += (f'Content-Disposition: form-data; name="{key}"\r\n\r\n'
                     ).encode("utf-8")
            body += f"{value}\r\n".encode("utf-8")
        for key, filepath in files.items():
            filename = os.path.basename(str(filepath))
            with open(filepath, "rb") as f:
                file_data = f.read()
            body += f"--{boundary}\r\n".encode("utf-8")
            body += (f'Content-Disposition: form-data; name="{key}"; '
                     f'filename="{filename}"\r\n').encode("utf-8")
            body += b"Content-Type: application/octet-stream\r\n\r\n"
            body += file_data + b"\r\n"
        body += f"--{boundary}--\r\n".encode("utf-8")
        return body, f"multipart/form-data; boundary={boundary}"

    # ------------------------------------------------------------
    # دریافت آپدیت (long-polling)
    # ------------------------------------------------------------
    def get_updates(self, offset=None, timeout=30):
        params = {
            "timeout": timeout,
            "allowed_updates": json.dumps(list(self.allowed_updates)),
        }
        if offset:
            params["offset"] = offset
        url = self.api_url() + self.method_name("getUpdates") + "?" + \
            urllib.parse.urlencode(params)
        try:
            with urllib.request.urlopen(url, timeout=timeout + 10) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            print(f"[{self.key}:getUpdates] HTTP {e.code}")
            return None
        except Exception as e:
            print(f"[{self.key}:getUpdates] {e}")
            return None

    def me(self):
        r = self.request("getMe")
        if r and r.get("ok"):
            return r.get("result") or {}
        return None

    # ------------------------------------------------------------
    # تبدیل آپدیت به شکل داخلی
    # ------------------------------------------------------------
    def normalize(self, update):
        """آپدیت خام این پیام‌رسان → شکل مشترک (بله/تلگرام‌گونه).

        پیام‌رسان‌هایی که شکل دیگری دارند این را بازنویسی می‌کنند.
        """
        if not isinstance(update, dict):
            return None
        return update

    # ------------------------------------------------------------
    # اعتبارسنجی ورودی وب‌هوک (پلتفرم‌های polling همیشه True)
    # ------------------------------------------------------------
    def token_ok(self, provided):
        """توکن/رمز ورودی وب‌هوک درست است؟

        یا باید با توکن خودِ پیام‌رسان بخواند، یا با رمز مشترک
        `WEBHOOK_TOKEN` (اگر ست شده باشد).
        """
        given = (provided or "").strip()
        platform_token = (self.token or "").strip()
        shared = (os.environ.get("WEBHOOK_TOKEN") or "").strip()

        if shared and given == shared:
            return True
        if platform_token and given == platform_token:
            return True
        if not shared and not platform_token:
            return True
        return False

    def health(self):
        """اطلاعات کوتاه برای /healthz — ⚠️ هیچ‌وقت توکن را نشان نده."""
        return {
            "key": self.key,
            "title": self.title,
            "configured": self.configured(),
            "token_env": list(self.token_envs),
            "webhook": bool(self.webhook_based),
            "api_host": self.host(),
        }

    def host(self):
        """فقط دامنه‌ی API (بدون توکن) — برای نمایش/لاگ."""
        try:
            url = self.api_url()
        except Exception:
            return ""
        if "://" not in url:
            return ""
        rest = url.split("://", 1)[1]
        return rest.split("/", 1)[0]
