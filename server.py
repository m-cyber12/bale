# -*- coding: utf-8 -*-
"""وب‌سرور سبک ربات — برای Render و هر میزبانی که پورت می‌خواهد.

کارها:

    GET  /                 صفحه‌ی ساده‌ی «ربات روشن است»
    GET  /healthz          وضعیت JSON (برای health-check و مانیتورینگ)
    GET  /version          نسخه/پیام‌رسان‌های فعال
    POST /webhook/<key>    دریافت آپدیت از پیام‌رسان‌های وب‌هوکی
    POST /webhook          همان، با پیام‌رسان پیش‌فرض وب‌هوک

روی Render، متغیر `PORT` خودکار ست می‌شود و همین سرور روی
`0.0.0.0:$PORT` گوش می‌دهد (لازمه‌ی Web Service) — polling هم
هم‌زمان در نخ‌های جداگانه اجرا می‌شود.

امنیت: اگر `WEBHOOK_TOKEN` ست شده باشد، هدر `X-Webhook-Token` باید
مطابقت داشته باشد. هر آپدیت پذیرفته‌شده در یک نخ جدا پردازش می‌شود تا
پاسخ HTTP فوری باشد (پیام‌رسان‌ها روی تأخیر، آپدیت را دوباره می‌فرستند).
"""
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import platforms

START_TS = time.time()
_COUNTERS = {"updates_in": 0, "updates_handled": 0, "updates_rejected": 0}

#: تابع پردازش آپدیت — در main ست می‌شود (تا import دوری نداشته باشیم)
HANDLER = None


def set_handler(fn):
    global HANDLER
    HANDLER = fn


def _json_response(handler, obj, code=200):
    body = json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)


def _text_response(handler, text, code=200):
    body = text.encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "text/plain; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


_AI_CACHE = {"ts": 0, "data": None}
_AI_TTL = 45


def _ai_health():
    """وضعیت AI با کش کوتاه — health-check نباید هر بار شبکه بزند."""
    now = time.time()
    if _AI_CACHE["data"] is not None and now - _AI_CACHE["ts"] < _AI_TTL:
        return _AI_CACHE["data"]
    try:
        import ai
        st = ai.status()
        out = {
            "enabled": st["enabled"],
            "key_set": st["key_set"],
            "key_source": st.get("key_source"),
            "models_total": st["models_total"],
            "usage_today": st["usage_today"],
            "top": st["top"][:3],
        }
    except Exception as e:
        out = {"error": str(e)}
    _AI_CACHE["data"] = out
    _AI_CACHE["ts"] = now
    return out


def health_payload():
    info = {
        "ok": True,
        "service": "alpha-group-bot",
        "uptime_sec": int(time.time() - START_TS),
        "platforms": platforms.summary(),
        "counters": dict(_COUNTERS),
    }
    try:
        import config
        info["config"] = config.env_report()
    except Exception as e:
        info["config_error"] = str(e)
    info["ai"] = _ai_health()
    try:
        import storage
        data = storage.get("groups", "data") or {}
        info["groups"] = len(data) if isinstance(data, dict) else 0
    except Exception:
        pass
    return info


class Handler(BaseHTTPRequestHandler):
    server_version = "AlphaBot/1.0"
    protocol_version = "HTTP/1.0"

    # ----------------------------------------------------------
    def log_message(self, fmt, *args):
        """لاگ کم — روی Render لاگ‌ها را پر نکنیم."""
        if os.environ.get("HTTP_LOG") in ("1", "true", "yes"):
            print(f"[http] {self.address_string()} {fmt % args}")

    # ----------------------------------------------------------
    def _read_body(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length <= 0:
            return b""
        return self.rfile.read(min(length, 2 * 1024 * 1024))

    def do_GET(self):
        path = self.path.split("?")[0].rstrip("/") or "/"
        if path in ("/", "/index.html"):
            names = ", ".join(p.title for p in platforms.enabled()) or "—"
            _text_response(self, f"🤖 ربات مدیریت گروه آلفا روشن است.\n"
                                 f"پیام‌رسان‌ها: {names}\n"
                                 f"وضعیت: /healthz\n")
        elif path in ("/healthz", "/health", "/status"):
            _json_response(self, health_payload())
        elif path == "/version":
            _json_response(self, {"platforms": platforms.available(),
                                  "active": [p.key for p in platforms.enabled()],
                                  "uptime_sec": int(time.time() - START_TS)})
        else:
            _json_response(self, {"ok": False, "error": "not found"}, 404)

    def do_POST(self):
        path = self.path.split("?")[0].rstrip("/")
        if not path.startswith("/webhook"):
            _json_response(self, {"ok": False, "error": "not found"}, 404)
            return

        parts = [p for p in path.split("/") if p]
        key = parts[1] if len(parts) > 1 else "webhook"

        try:
            plat = platforms.get(key)
        except Exception as e:
            _COUNTERS["updates_rejected"] += 1
            _json_response(self, {"ok": False, "error": str(e)}, 404)
            return

        if not plat.token_ok(self.headers.get("X-Webhook-Token")):
            _COUNTERS["updates_rejected"] += 1
            _json_response(self, {"ok": False, "error": "bad token"}, 401)
            return

        raw = self._read_body()
        try:
            payload = json.loads(raw.decode("utf-8")) if raw else {}
        except Exception as e:
            _COUNTERS["updates_rejected"] += 1
            _json_response(self, {"ok": False, "error": f"bad json: {e}"}, 400)
            return

        updates = payload
        if isinstance(payload, dict) and isinstance(payload.get("updates"), list):
            updates = payload["updates"]      # دسته‌ای
        if not isinstance(updates, list):
            updates = [updates]

        _COUNTERS["updates_in"] += len(updates)

        def _work():
            for upd in updates:
                try:
                    norm = plat.normalize(upd)
                    if not norm:
                        continue
                    if HANDLER:
                        HANDLER(norm, plat.key)
                    _COUNTERS["updates_handled"] += 1
                except Exception as e:
                    print(f"[webhook:{plat.key}] {e}")
                    import traceback
                    traceback.print_exc()

        threading.Thread(target=_work, daemon=True).start()
        _json_response(self, {"ok": True, "queued": len(updates),
                              "platform": plat.key})


def start(port=None, host="0.0.0.0"):
    """سرور را در یک نخ پس‌زمینه بالا می‌آورد و نمونه‌اش را برمی‌گرداند."""
    if port is None:
        import config
        port = config.port()
    if not port:
        return None
    srv = ThreadingHTTPServer((host, int(port)), Handler)
    srv.daemon_threads = True

    def _serve():
        print(f"🌐 وب‌سرور روی http://{host}:{port} بالا آمد "
              f"(health-check: /healthz)")
        try:
            srv.serve_forever()
        except Exception as e:
            print(f"[http] {e}")

    threading.Thread(target=_serve, daemon=True, name="http").start()
    return srv
