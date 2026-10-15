# -*- coding: utf-8 -*-
"""تست معماری چند-پیام‌رسانی + وب‌سرور (کاملاً آفلاین).

چه چیزهایی چک می‌شود:
  ۱) ثبت آداپتورها و انتخاب پیام‌رسان از روی متغیر محیطی
  ۲) خواندن توکن (env اول، بعد فایل) و اینکه توکن لو نمی‌رود
  ۳) نرمال‌سازی آپدیت‌ها (بله/تلگرام = همان شکل، وب‌هوک = سه شکل ورودی)
  ۴) مسیریابی ارسال: هر چت به پیام‌رسان خودش می‌رود
  ۵) ترجمه‌ی parse_mode و نام متدها (مثلاً getChatMembersCount → تلگرام)
  ۶) وب‌سرور: /healthz، /webhook/...، رد کردن توکن اشتباه، JSON خراب
  ۷) کلید OpenRouter: متغیر محیطی بر پنل اولویت دارد
"""
import json
import os
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

TMP = tempfile.mkdtemp(prefix="bale_plat_")

# --- پاک‌سازی env قبل از import (تا تست‌ها قطعی باشند) ---
for _k in ("PLATFORM", "PLATFORMS", "BALE_TOKEN", "BOT_TOKEN", "TOKEN",
           "TELEGRAM_TOKEN", "TG_TOKEN", "TELEGRAM_BOT_TOKEN",
           "WEBHOOK_TOKEN", "WEBHOOK_SEND_URL", "OPENROUTER_API_KEY",
           "OPENROUTER_KEY", "PORT", "OWNER_ID"):
    os.environ.pop(_k, None)

import config                    # noqa: E402
config.DATA_DIR = TMP

import fake_bale                 # noqa: E402
import platforms                 # noqa: E402
import api                       # noqa: E402

#: پیاده‌سازی اصلی (چون تست سرتاسری، api را با شبیه‌ساز عوض می‌کند)
ORIGINAL_REQUEST = api.request
ORIGINAL_GET_UPDATES = api.get_updates
ORIGINAL_UPLOAD = api.upload_file

FAILS = []


def check(cond, msg):
    if not cond:
        FAILS.append(msg)
    return cond


def fresh():
    """پاک‌کردن نمونه‌های ساخته‌شده (تا env جدید دیده شود)."""
    platforms._INSTANCES.clear()


# ============================================================
# ۱) ثبت و انتخاب
# ============================================================
def test_registry():
    fresh()
    check(set(platforms.available()) >= {"bale", "telegram", "webhook"},
          f"آداپتورهای پایه ثبت نشده‌اند: {platforms.available()}")
    check(platforms.resolve_key("TG") == "telegram", "alias تلگرام کار نکرد")
    check(platforms.resolve_key("بله") == "bale", "alias فارسی بله کار نکرد")

    # بدون توکن → لیست خالی
    check(platforms.enabled() == [], "بدون توکن نباید پلتفرمی فعال باشد")
    # پیش‌فرضِ خالی: بله برمی‌گردد تا خطای واضح بدهد
    check(platforms.default().key == "bale", "پیش‌فرض باید بله باشد")

    # توکن بله از env
    os.environ["BALE_TOKEN"] = "111:baletoken"
    fresh()
    keys = [p.key for p in platforms.enabled()]
    check(keys == ["bale"], f"با توکن بله باید فقط bale فعال شود: {keys}")

    # دو پیام‌رسان با هم
    os.environ["TELEGRAM_TOKEN"] = "222:telegramtoken"
    os.environ["PLATFORMS"] = "bale,telegram"
    fresh()
    keys = [p.key for p in platforms.enabled()]
    check(keys == ["bale", "telegram"], f"حالت چند-پیام‌رسانی: {keys}")

    # فقط تلگرام
    os.environ["PLATFORMS"] = "telegram"
    fresh()
    keys = [p.key for p in platforms.enabled()]
    check(keys == ["telegram"], f"انتخاب دستی تلگرام: {keys}")
    check(platforms.default().key == "telegram", "پیش‌فرض باید تلگرام باشد")

    # آدرس API
    tg = platforms.get("telegram")
    check(tg.api_url() == "https://api.telegram.org/bot222:telegramtoken/",
          f"آدرس تلگرام غلط: {tg.api_url()}")
    fresh()
    os.environ["PLATFORMS"] = "bale,telegram"
    check(platforms.get("bale").api_url() ==
          "https://tapi.bale.ai/bot111:baletoken/",
          "آدرس بله غلط")

    # پلتفرم ناشناس → خطا
    try:
        platforms.get("whatsapp")
        check(False, "پلتفرم ناشناس باید خطا بدهد")
    except platforms.PlatformError:
        pass
    print("  ✓ ثبت/انتخاب/آدرس‌ها")


# ============================================================
# ۲) خواندن توکن (env → فایل)
# ============================================================
def test_token_sources():
    fresh()
    os.environ.pop("BALE_TOKEN", None)

    # فایل اختصاصی پلتفرم
    with open(os.path.join(TMP, "bale_token.txt"), "w", encoding="utf-8") as f:
        f.write("333:filetoken\n")
    check(platforms.get("bale").token == "333:filetoken",
          "توکن از فایل خوانده نشد")

    # env اولویت دارد
    os.environ["BALE_TOKEN"] = "444:envtoken"
    check(platforms.get("bale").token == "444:envtoken",
          "env باید بر فایل اولویت داشته باشد")

    # BOT_TOKEN قدیمی هم کار می‌کند
    os.environ.pop("BALE_TOKEN", None)
    os.environ["BOT_TOKEN"] = "555:legacytoken"
    fresh()
    check(platforms.get("bale").token == "555:legacytoken",
          "BOT_TOKEN قدیمی خوانده نشد")

    # هیچ‌جا توکن به‌صورت خام لاگ/گزارش نشود
    h = platforms.get("bale").health()
    check("555" not in json.dumps(h), "توکن در health لو رفت!")

    os.environ.pop("BOT_TOKEN", None)
    os.environ["BALE_TOKEN"] = "111:baletoken"
    os.remove(os.path.join(TMP, "bale_token.txt"))
    fresh()
    print("  ✓ اولویت توکن: env → فایل (و لو نرفتن توکن)")


# ============================================================
# ۳) نرمال‌سازی آپدیت‌ها
# ============================================================
def test_normalize():
    fresh()
    bale = platforms.get("bale")
    tg = platforms.get("telegram")
    wh = platforms.get("webhook")

    raw = {"update_id": 1, "message": {"message_id": 5, "text": "سلام",
                                       "chat": {"id": -100, "type": "supergroup"},
                                       "from": {"id": 7, "first_name": "علی"}}}
    check(bale.normalize(raw) == raw, "بله نباید آپدیت را تغییر دهد")
    check(tg.normalize(raw) == raw, "تلگرام نباید آپدیت را تغییر دهد")

    # --- وب‌هوک: شکل ساده ---
    simple = {"chat_id": "-100777", "chat_type": "group", "chat_title": "گروه من",
              "user_id": 555, "user_name": "علی رضایی", "text": "سلام",
              "message_id": 12, "reply_to_message_id": 11}
    out = wh.normalize(simple)
    m = out.get("message")
    check(m and m["chat"]["id"] == -100777, f"chat_id ساده تبدیل نشد: {m}")
    check(m["from"]["id"] == 555 and m["from"]["first_name"] == "علی رضایی",
          f"فرستنده تبدیل نشد: {m['from']}")
    check(m["text"] == "سلام", "متن تبدیل نشد")
    check(m["reply_to_message"]["message_id"] == 11, "ریپلای تبدیل نشد")

    # --- وب‌هوک: شکل رویداد ---
    ev = {"event": "message", "chat": {"id": -55, "title": "تست", "type": "group"},
          "from": {"id": 9, "first_name": "رضا"}, "text": "hi"}
    out2 = wh.normalize(ev)
    check(out2["message"]["chat"]["id"] == -55, f"شکل رویداد: {out2}")

    # --- وب‌هوک: دکمه ---
    cb = {"event": "callback", "chat_id": -55, "chat_title": "تست",
          "user_id": 9, "user_name": "رضا", "data": "panel:main",
          "callback_id": "cb9", "message_id": 3}
    out3 = wh.normalize(cb)
    q = out3.get("callback_query")
    check(q and q["data"] == "panel:main", f"دکمه تبدیل نشد: {out3}")
    check(q["message"]["chat"]["id"] == -55, "چتِ دکمه تبدیل نشد")

    # --- وب‌هوک: شکل خام بله/تلگرام ---
    check(wh.normalize(raw) == raw, "شکل خام باید دست‌نخورده بماند")

    # --- ورودی بی‌معنی ---
    check(wh.normalize("سلام") is None, "رشته نباید آپدیت شود")
    check(wh.normalize({}) is not None, "{} باید آپدیت خالی بسازد")
    print("  ✓ نرمال‌سازی: بله/تلگرام/وب‌هوک (۳ شکل ورودی)")


# ============================================================
# ۴) ترجمه‌ی parse_mode و نام متد
# ============================================================
def test_parse_mode_and_methods():
    fresh()
    bale = platforms.get("bale")
    tg = platforms.get("telegram")

    check(bale.parse_mode("Markdown") == "Markdown", "بله Markdown را دارد")
    check(bale.parse_mode("MarkdownV2") is None,
          "بله MarkdownV2 ندارد → باید None بدهد")
    check(tg.parse_mode("MarkdownV2") == "MarkdownV2", "تلگرام MarkdownV2 دارد")
    check(tg.method_name("getChatMembersCount") == "getChatMemberCount",
          "نقشه‌ی نام متد تلگرام کار نکرد")
    check(bale.method_name("getChatMembersCount") == "getChatMembersCount",
          "بله نباید نام متد را عوض کند")

    # پارامترهای MarkdownV2 روی بله حذف می‌شوند (متن خام امن‌تر است)
    import api
    fresh()
    os.environ["PLATFORMS"] = "bale"
    check(api._pm(-100, "Markdown") == "Markdown", "_pm روی بله")
    check(api._pm(-100, "MarkdownV2") is None, "_pm باید None بدهد")
    check(api._pm(-100, None) is None, "_pm روی None")
    print("  ✓ parse_mode و نام متدها")


# ============================================================
# ۵) مسیریابی ارسال بین پیام‌رسان‌ها
# ============================================================
class Recorder:
    """به‌جای پلتفرم واقعی، فقط درخواست‌ها را ثبت می‌کند."""

    def __init__(self, key):
        self.key = key
        self.requested = []

    def request(self, method, data=None, timeout=30, **kw):
        self.requested.append((method, dict(data or {})))
        return {"ok": True, "result": {"message_id": len(self.requested)}}

    def get_updates(self, offset=None, timeout=30, **kw):
        return {"ok": True, "result": []}

    def parse_mode(self, mode):
        return mode


def test_routing():
    fresh()
    os.environ["PLATFORMS"] = "bale,telegram"
    import storage
    storage.load()
    storage.set_("platforms", "chat_map", {})

    import api
    platforms.get("bale")          # نمونه‌ها را بساز
    platforms.get("telegram")
    bale_rec = Recorder("bale")
    tg_rec = Recorder("telegram")
    platforms._INSTANCES["bale"].request = bale_rec.request
    platforms._INSTANCES["telegram"].request = tg_rec.request

    # چت‌ها را ثبت کن
    platforms.remember_chat("telegram", -100222)
    platforms.remember_chat("bale", -100111)

    api.clear_platform()
    api.send(-100111, "سلام بله")
    api.send(-100222, "سلام تلگرام")
    check(len(bale_rec.requested) == 1 and
          bale_rec.requested[0][1]["chat_id"] == -100111,
          f"پیام بله به بله نرفت: {bale_rec.requested}")
    check(len(tg_rec.requested) == 1 and
          tg_rec.requested[0][1]["chat_id"] == -100222,
          f"پیام تلگرام به تلگرام نرفت: {tg_rec.requested}")

    # context دستی (مثل وقتی داریم آپدیت تلگرام را پردازش می‌کنیم)
    api.clear_platform()
    api.set_platform("telegram")
    api.send(-999999, "چت ناشناس ولی context=تلگرام")
    check(len(tg_rec.requested) == 2, "context پیام‌رسان کار نکرد")
    api.clear_platform()

    # چت ناشناس → پیش‌فرض (bale)
    api.send(-424242, "چت ناشناس")
    check(len(bale_rec.requested) == 2, "چت ناشناس باید به پیش‌فرض برود")

    # چت‌های خصوصی هم درست مسیریابی شوند
    platforms.remember_chat("telegram", 777)
    api.send(777, "پیوی")
    check(len(tg_rec.requested) == 3, "پیوی تلگرام به تلگرام نرفت")
    print("  ✓ مسیریابی: chat_map + context + پیش‌فرض")


# ============================================================
# ۶) وب‌سرور (health + webhook)
# ============================================================
def test_web_server():
    fresh()
    os.environ["PLATFORMS"] = "bale,webhook"
    os.environ["WEBHOOK_SEND_URL"] = "http://127.0.0.1:9/never"
    os.environ["WEBHOOK_TOKEN"] = "secret123"

    import importlib
    import server
    importlib.reload(server)

    # هندلر جعلی: آپدیت‌ها را جمع می‌کند
    got = []
    server.set_handler(lambda upd, key: got.append((key, upd)))

    httpd = server.start(port=0 + 18765, host="127.0.0.1")
    check(httpd is not None, "سرور بالا نیامد")
    base = "http://127.0.0.1:18765"

    def get(path, headers=None):
        req = urllib.request.Request(base + path, headers=headers or {})
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, r.read().decode("utf-8")

    def post(path, payload, headers=None):
        req = urllib.request.Request(
            base + path, data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", **(headers or {})})
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8")

    # --- صفحه‌ی اصلی و /healthz ---
    st, body = get("/")
    check(st == 200 and "روشن" in body, f"صفحه‌ی اصلی: {st} {body[:60]}")
    st, body = get("/healthz")
    data = json.loads(body)
    check(st == 200 and data["ok"] is True, "healthz خراب است")
    check("platforms" in data and "uptime_sec" in data, "healthz ناقص است")
    check("secret123" not in body, "توکن وب‌هوک در health لو رفت!")
    keys = {p["key"] for p in data["platforms"]}
    check({"bale", "telegram", "webhook"} <= keys, f"پلتفرم‌ها در healthz: {keys}")

    st, body = get("/version")
    check(st == 200 and "active" in json.loads(body), "/version خراب است")
    st, _ = get("/nope") if False else (404, "")
    try:
        get("/nope")
        check(False, "مسیر ناشناس باید 404 بدهد")
    except urllib.error.HTTPError as e:
        check(e.code == 404, f"مسیر ناشناس: {e.code}")

    # --- webhook: توکن اشتباه ---
    st, body = post("/webhook/webhook", {"chat_id": -1, "text": "x"},
                    {"X-Webhook-Token": "wrong"})
    check(st == 401, f"توکن اشتباه باید 401 بدهد: {st}")

    # --- webhook: JSON خراب ---
    req = urllib.request.Request(base + "/webhook/webhook", data=b"{not json",
                                 headers={"Content-Type": "application/json",
                                          "X-Webhook-Token": "secret123"})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            st = r.status
    except urllib.error.HTTPError as e:
        st = e.code
    check(st == 400, f"JSON خراب باید 400 بدهد: {st}")

    # --- webhook: آپدیت سالم ---
    got.clear()
    st, body = post("/webhook/webhook",
                    {"chat_id": -100500, "chat_title": "گروه وب‌هوک",
                     "user_id": 42, "user_name": "وب‌هوکی", "text": "سلام"},
                    {"X-Webhook-Token": "secret123"})
    check(st == 200 and json.loads(body)["queued"] == 1,
          f"آپدیت وب‌هوک پذیرفته نشد: {st} {body}")

    end = time.time() + 3
    while not got and time.time() < end:
        time.sleep(0.05)
    check(bool(got), "آپدیت وب‌هوک به هندلر نرسید")
    if got:
        key, upd = got[0]
        check(key == "webhook", f"کلید پلتفرم اشتباه: {key}")
        check(upd["message"]["chat"]["id"] == -100500, "chat_id نرمال نشد")
        check(upd["message"]["from"]["first_name"] == "وب‌هوکی", "نام نرمال نشد")

    # --- webhook: دسته‌ای ---
    got.clear()
    st, body = post("/webhook/webhook",
                    {"updates": [{"chat_id": -1, "text": "a", "user_id": 1},
                                 {"chat_id": -2, "text": "b", "user_id": 2}]},
                    {"X-Webhook-Token": "secret123"})
    check(json.loads(body)["queued"] == 2, f"دسته‌ای: {body}")
    end = time.time() + 3
    while len(got) < 2 and time.time() < end:
        time.sleep(0.05)
    check(len(got) == 2, f"آپدیت‌های دسته‌ای نرسیدند: {len(got)}")

    # --- /webhook/bale هم قبول می‌شود (شکل خام) ---
    got.clear()
    raw = {"update_id": 5, "message": {"message_id": 1, "text": "خام",
                                       "chat": {"id": -7, "type": "group"},
                                       "from": {"id": 3, "first_name": "الف"}}}
    st, body = post("/webhook/bale", raw, {"X-Webhook-Token": "secret123"})
    check(st == 200, f"webhook/bale: {st}")
    end = time.time() + 3
    while not got and time.time() < end:
        time.sleep(0.05)
    check(got and got[0][0] == "bale", "آپدیت خام به بله نرسید")

    httpd.shutdown()
    httpd.server_close()
    print("  ✓ وب‌سرور: / /healthz /version /webhook (توکن، JSON خراب، دسته‌ای)")


# ============================================================
# ۷) کلید OpenRouter از env
# ============================================================
def test_ai_env_key():
    import ai
    fresh()
    os.environ.pop("OPENROUTER_API_KEY", None)
    ai.set_api_key("sk-or-v1-frompanel")
    check(ai.api_key() == "sk-or-v1-frompanel", "کلید پنل خوانده نشد")
    check(ai.key_source() == "panel", f"منبع کلید: {ai.key_source()}")

    os.environ["OPENROUTER_API_KEY"] = "sk-or-v1-fromenv"
    check(ai.api_key() == "sk-or-v1-fromenv",
          "env باید بر کلید پنل اولویت داشته باشد")
    check(ai.key_source() == "env", f"منبع کلید: {ai.key_source()}")
    check(ai.status()["key_source"] == "env", "status منبع کلید را نمی‌دهد")

    # نام‌های دیگر
    os.environ.pop("OPENROUTER_API_KEY")
    os.environ["OPENROUTER_KEY"] = "sk-or-v1-alt"
    check(ai.api_key() == "sk-or-v1-alt", "OPENROUTER_KEY خوانده نشد")

    os.environ.pop("OPENROUTER_KEY")
    ai.set_api_key("")
    check(ai.api_key() == "", "کلید باید خالی شود")
    check(ai.ready() is False, "بدون کلید نباید ready باشد")
    print("  ✓ کلید OpenRouter: env → پنل")


# ============================================================
# ۸) گزارش تنظیمات (بدون لو دادن راز)
# ============================================================
def test_env_report():
    fresh()
    os.environ["PLATFORMS"] = "bale,telegram"
    os.environ["BALE_TOKEN"] = "777:secretbale"
    os.environ["TELEGRAM_TOKEN"] = "888:secrettelegram"
    os.environ["OPENROUTER_API_KEY"] = "sk-or-v1-secret"
    rep = config.env_report()
    blob = json.dumps(rep)
    check("777:secretbale" not in blob, "توکن بله در گزارش لو رفت")
    check("888:secrettelegram" not in blob, "توکن تلگرام در گزارش لو رفت")
    check("sk-or-v1-secret" not in blob, "کلید AI در گزارش لو رفت")
    check(rep["tokens_set"] == {"bale": True, "telegram": True},
          f"tokens_set غلط: {rep['tokens_set']}")
    check(rep["openrouter_key"] is True, "openrouter_key غلط")
    check(rep["platforms"] == ["bale", "telegram"], f"لیست پلتفرم‌ها: {rep['platforms']}")
    print("  ✓ گزارش تنظیمات بدون راز")


# ============================================================
# ۹) سرتاسری: وب‌هوک → ربات → پاسخ روی همان پیام‌رسان
# ============================================================
def test_end_to_end_webhook():
    """یک پیام از راه وب‌هوک می‌آید و ربات همان‌جا جواب می‌دهد."""
    fresh()
    os.environ["PLATFORMS"] = "bale,webhook"
    os.environ["WEBHOOK_SEND_URL"] = "http://127.0.0.1:9/never"
    os.environ["WEBHOOK_TOKEN"] = "e2e-secret"

    import storage
    import admin
    import main
    import server
    import importlib
    importlib.reload(server)

    # پلتفرم وب‌هوک را به شبیه‌ساز بله وصل می‌کنیم (تا متدها جواب داشته باشند)
    fake = fake_bale.install(api_stub := __import__("api"))
    wh = platforms.get("webhook")
    wh.request = fake.request
    # بله هم شبیه‌ساز شود تا مسیرهای ادمین جواب بدهند
    platforms.get("bale").request = fake.request

    GROUP = -100900
    ADMIN_USER = fake_bale.make_user(11, "مدیر وب‌هوک", "admin_wh")
    fake.statuses[(GROUP, 11)] = "creator"
    fake.bot_group_status = "administrator"
    admin._admin_cache.clear()

    # چت وب‌هوکی را به پلتفرم وب‌هوک نسبت بده
    platforms.remember_chat("webhook", GROUP)

    server.set_handler(main.handle)
    httpd = server.start(port=18767, host="127.0.0.1")
    check(httpd is not None, "سرور e2e بالا نیامد")

    fake.sent.clear()
    body = {"chat_id": GROUP, "chat_type": "group", "chat_title": "گروه وب‌هوکی",
            "user_id": 11, "user_name": "مدیر وب‌هوک", "text": "پنل",
            "message_id": 44}
    req = urllib.request.Request(
        "http://127.0.0.1:18767/webhook/webhook",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "X-Webhook-Token": "e2e-secret"})
    with urllib.request.urlopen(req, timeout=5) as r:
        check(r.status == 200, f"کد پاسخ: {r.status}")

    end = time.time() + 8
    while not fake.sent and time.time() < end:
        time.sleep(0.1)

    check(bool(fake.sent), "ربات به پیام وب‌هوکی جواب نداد")
    if fake.sent:
        txt = fake.sent[0].get("text") or ""
        check("پنل" in txt or "مدیریت" in txt,
              f"پاسخ مناسب نبود: {txt[:70]!r}")
        markup = fake.sent[0].get("reply_markup") or fake.sent[0].get("markup") or {}
        if isinstance(markup, str):
            markup = json.loads(markup)
        datas = [b.get("callback_data") for row in
                 (markup.get("inline_keyboard") or []) for b in row]
        check(any((d or "").startswith("panel:") for d in datas),
              f"دکمه‌های پنل مدیریت نیامد: {datas[:6]} | "
              f"متن: {txt[:80]!r}")

    # پیام ناشناس (چت ثبت‌نشده) هم نباید سرور را بیندازد
    got_before = len(fake.sent)
    body2 = {"chat_id": -424242, "text": "سلام", "user_id": 5,
             "user_name": "ناشناس", "message_id": 1}
    req2 = urllib.request.Request(
        "http://127.0.0.1:18767/webhook/webhook",
        data=json.dumps(body2).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "X-Webhook-Token": "e2e-secret"})
    with urllib.request.urlopen(req2, timeout=5) as r:
        check(r.status == 200, "پیام ناشناس رد شد")

    httpd.shutdown()
    httpd.server_close()
    print("  ✓ سرتاسری: وب‌هوک → دستور «پنل» → پاسخ + دکمه‌ها")


# ============================================================
# ۱۰) هر آپدیت از هر پیام‌رسانی → پاسخ روی همان
# ============================================================
def test_handle_platform_context():
    """چتی که تا حالا دیده نشده هم پاسخش به پیام‌رسان درست برمی‌گردد."""
    fresh()
    os.environ["PLATFORMS"] = "bale,telegram"

    import storage
    import admin
    import main

    # شبیه‌ساز تست قبلی را کنار بگذار تا مسیریابی واقعی تست شود
    api.request = ORIGINAL_REQUEST
    api.get_updates = ORIGINAL_GET_UPDATES
    api.upload_file = ORIGINAL_UPLOAD

    platforms.get("bale")
    platforms.get("telegram")
    bale_rec = Recorder("bale")
    tg_rec = Recorder("telegram")
    platforms._INSTANCES["bale"].request = bale_rec.request
    platforms._INSTANCES["telegram"].request = tg_rec.request

    storage.load()
    storage.set_("platforms", "chat_map", {})
    admin._admin_cache.clear()

    # یک گروه تازه روی تلگرام (هیچ‌جای storage ثبت نشده)
    GROUP = -100555
    who = fake_bale.make_user(11, "مدیر", "admin_x")
    upd = {"update_id": 1,
           "message": fake_bale.make_message(GROUP, who, "راهنما")}
    main.handle(upd, "telegram")
    check(len(tg_rec.requested) >= 1,
          f"پاسخ روی تلگرام نرفت: {len(tg_rec.requested)}")
    check(len(bale_rec.requested) == 0,
          f"پاسخ اشتباهی روی بله رفت: {bale_rec.requested}")
    check(tg_rec.requested[-1][1].get("chat_id") == GROUP,
          "chat_id در پاسخ غلط است")

    # حالا همان چت روی بله
    tg_before = len(tg_rec.requested)
    upd2 = {"update_id": 2,
            "message": fake_bale.make_message(GROUP, who, "راهنما")}
    main.handle(upd2, "bale")
    check(len(bale_rec.requested) >= 1, "پاسخ دوم روی بله نرفت")
    check(len(tg_rec.requested) == tg_before, "پاسخ دوم اشتباهی روی تلگرام رفت")

    # و چت در نقشه ثبت شده تا تایمرها هم بعداً درست بروند
    m = storage.get("platforms", "chat_map") or {}
    check(m.get(str(GROUP)) == "bale", f"نقشه‌ی چت به‌روز نشد: {m}")
    print("  ✓ context آپدیت: پاسخ همیشه روی همان پیام‌رسان")


# ============================================================
# ۱۱) مالک ربات: عدد یا نام کاربری + دستور «آیدی من»
# ============================================================
def test_owner_from_env():
    """OWNER_ID هم عدد می‌گیرد هم نام کاربری."""
    import config

    def with_env(**env):
        old = {k: os.environ.get(k) for k in env}
        for k, v in env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        try:
            return config._owner_from_env()
        finally:
            for k, v in old.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    for k in ("OWNER_ID", "BALE_OWNER_ID", "TELEGRAM_OWNER_ID",
              "OWNER_USERNAME", "OWNER_USER", "BALE_OWNER_USERNAME",
              "TELEGRAM_OWNER_USERNAME"):
        os.environ.pop(k, None)

    uid, uname = with_env(OWNER_ID="123456789")
    check(uid == 123456789 and uname == "", f"عدد درست خوانده نشد: {(uid, uname)}")

    uid, uname = with_env(OWNER_ID="@Spinner5698")
    check(uid == 0 and uname == "spinner5698",
          f"نام کاربری داخل OWNER_ID خوانده نشد: {(uid, uname)}")

    uid, uname = with_env(OWNER_ID="  Spinner5698  ")
    check(uid == 0 and uname == "spinner5698",
          f"نام کاربری بدون @ خوانده نشد: {(uid, uname)}")

    uid, uname = with_env(OWNER_USERNAME="@Spinner5698")
    check(uid == 0 and uname == "spinner5698",
          f"OWNER_USERNAME خوانده نشد: {(uid, uname)}")

    uid, uname = with_env(OWNER_ID="+98 912", OWNER_USERNAME="Spinner5698")
    check(uname == "spinner5698", f"ترکیب عدد بی‌معنی + نام کاربری: {(uid, uname)}")
    print("  ✓ مالک از env: عدد / @نام‌کاربری / OWNER_USERNAME")


def test_id_command_and_owner_claim():
    """«آیدی من» عدد را می‌گوید و مالک با نام کاربری خودکار ثبت می‌شود."""
    import config
    import storage
    import panels
    import main as bot_main

    fresh()
    api.request = ORIGINAL_REQUEST
    api.get_updates = ORIGINAL_GET_UPDATES
    api.upload_file = ORIGINAL_UPLOAD

    storage.load()
    storage.set_("bot_owner", "id", {})
    storage.set_("platforms", "chat_map", {})
    storage.set_("bot_admins", "list", {})

    old_uid = config.OWNER_ID
    old_uname = getattr(config, "OWNER_USERNAME", "")
    config.OWNER_ID = 0
    config.OWNER_USERNAME = "spinner5698"

    platforms.get("bale")
    rec = Recorder("bale")
    platforms._INSTANCES["bale"].request = rec.request

    try:
        # ۱) پیوی مالک → ثبت خودکار + پیام خوش‌آمد مالکی
        owner = fake_bale.make_user(778899, "اسپینر", "Spinner5698")
        bot_main.handle({"update_id": 71001, "message": fake_bale.make_message(
            778899, owner, "سلام", chat_type="private")}, "bale")
        check(panels.get_owner_id() == 778899,
              f"مالک از نام کاربری ثبت نشد: {panels.get_owner_id()}")
        texts = [str(x[1].get("text") or "") for x in rec.requested]
        check(any("مالک ربات" in t for t in texts),
              f"پیام معرفی مالک نیامد: {texts[-2:]}")

        # ۲) غریبه نباید مالک شود
        other = fake_bale.make_user(555111, "غریبه", "stranger")
        bot_main.handle({"update_id": 71002, "message": fake_bale.make_message(
            555111, other, "سلام", chat_type="private")}, "bale")
        check(panels.get_owner_id() == 778899, "غریبه مالک شد!")
        check(not panels.is_bot_owner(555111), "غریبه مالک شناخته شد!")

        # ۳) دستور «آیدی من» → عدد درست
        rec.requested.clear()
        bot_main.handle({"update_id": 71003, "message": fake_bale.make_message(
            555111, other, "آیدی من", chat_type="private")}, "bale")
        got = " ".join(str(x[1].get("text") or "") for x in rec.requested)
        check("555111" in got, f"آیدی عددی در پاسخ نبود: {got[:120]}")
        check("OWNER_ID=555111" in got, f"راهنمای env در پاسخ نبود: {got[:150]}")

        # ۴) در گروه: کاربر عادی جواب نمی‌گیرد، ادمین می‌گیرد
        def sends():
            """فقط پیام‌های ارسالی (نه getChatMember و …)."""
            return [r for r in rec.requested if r[0] == "sendMessage"]

        import admin as admin_mod
        admin_mod._admin_cache.clear()

        rec.requested.clear()
        GRP = -100888
        bot_main.handle({"update_id": 71004, "message": fake_bale.make_message(
            GRP, other, "myid")}, "bale")
        check(not sends(), f"کاربر عادی نباید جواب بگیرد: {sends()}")

        upd = {"update_id": 71005,
               "message": fake_bale.make_message(GRP, owner, "/myid")}
        bot_main.handle(upd, "bale")
        new = [str(x[1].get("text") or "") for x in sends()]
        check(any("778899" in t for t in new),
              f"ادمین گروه آیدی‌اش را نگرفت: {sends()}")

    finally:
        config.OWNER_ID = old_uid
        config.OWNER_USERNAME = old_uname
        storage.set_("bot_owner", "id", {})
    print("  ✓ «آیدی من» + ثبت مالک با نام کاربری")




def main():
    tests = [
        ("ثبت و انتخاب پیام‌رسان", test_registry),
        ("منبع توکن", test_token_sources),
        ("نرمال‌سازی آپدیت", test_normalize),
        ("parse_mode و نام متد", test_parse_mode_and_methods),
        ("مسیریابی ارسال", test_routing),
        ("وب‌سرور و وب‌هوک", test_web_server),
        ("کلید AI از env", test_ai_env_key),
        ("گزارش تنظیمات", test_env_report),
        ("سرتاسری وب‌هوک", test_end_to_end_webhook),
        ("context آپدیت چند-پیام‌رسانی", test_handle_platform_context),
        ("مالک از env (عدد/نام کاربری)", test_owner_from_env),
        ("دستور آیدی من", test_id_command_and_owner_claim),
    ]
    print("=" * 70)
    print("تست لایه‌ی چند-پیام‌رسانی و وب‌سرور")
    print("=" * 70)
    for name, fn in tests:
        before = len(FAILS)
        try:
            fn()
        except Exception:
            import traceback
            FAILS.append(f"{name}: استثنا\n{traceback.format_exc()}")
        mark = "❌" if len(FAILS) > before else "✅"
        print(f"{mark} {name}")

    print("=" * 70)
    if FAILS:
        print(f"❌ {len(FAILS)} مشکل:")
        for f in FAILS:
            print("  •", f)
        return 1
    print("🎉 همه‌ی تست‌های پیام‌رسان‌ها سبز")
    return 0


if __name__ == "__main__":
    sys.exit(main())
