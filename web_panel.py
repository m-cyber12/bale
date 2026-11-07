"""A small status page for Render's web service port."""
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


PAGE = """<!doctype html>
<html lang="fa" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>وضعیت ربات World War</title>
<style>
body{margin:0;min-height:100vh;display:grid;place-items:center;background:#0b1020;color:#edf2ff;font-family:Tahoma,sans-serif}
main{box-sizing:border-box;width:min(90%,480px);padding:36px;border:1px solid #293451;border-radius:20px;background:#141d33;box-shadow:0 20px 60px #0006}
h1{font-size:1.5rem;margin:0 0 24px} .status{color:#7aefb2;font-weight:bold} p{line-height:2;color:#becbe4} small{color:#91a3c5}
</style></head><body><main><h1>⚜️ ربات World War</h1>
<div class="status">● سرویس در حال اجراست</div>
<p>پنل وضعیت ربات فعال است. ربات پیام‌ها را از طریق polling دریافت می‌کند.</p>
<small>این صفحه فقط در دسترس بودن سرویس وب را نشان می‌دهد، نه اتصال ربات به بله.</small>
</main></body></html>""".encode("utf-8")


class StatusHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ("/", "/health"):
            self.send_error(404)
            return
        body = b"ok\n" if self.path == "/health" else PAGE
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8" if self.path == "/health" else "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def start_web_panel():
    """Bind before starting the bot so a port error fails the deployment."""
    port = int(os.environ.get("PORT", "10000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), StatusHandler)
    threading.Thread(target=server.serve_forever, daemon=True, name="web-panel").start()
    print(f"🌐 پنل وب روی پورت {server.server_port} اجرا شد", flush=True)
    return server
