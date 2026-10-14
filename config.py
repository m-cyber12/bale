# -*- coding: utf-8 -*-
"""تنظیمات ربات — همه‌چیز از متغیر محیطی.

⚠️ هیچ توکنی در کد نگه داشته نمی‌شود.

توکن پیام‌رسان‌ها (هر کدام که بگذاری همان فعال می‌شود):

    BALE_TOKEN        توکن ربات بله
    TELEGRAM_TOKEN    توکن ربات تلگرام
    WEBHOOK_TOKEN     رمز دلخواهِ ورودی وب‌هوک (اختیاری)

و برای انتخاب دستی:

    PLATFORM=bale                فقط یکی
    PLATFORMS=bale,telegram      چند تا با هم (هر کدام polling خودش)
    PLATFORMS=webhook            فقط وب‌هوک عمومی

بقیه:

    OPENROUTER_API_KEY   کلید هوش مصنوعی (اختیاری — از پنل هم می‌شود)
    OWNER_ID             آیدی مالک ربات
    DATA_DIR             پوشه‌ی داده‌ها (روی Render: مسیر دیسک)
    PORT                 اگر ست باشد، وب‌سرور سلامت/webhook بالا می‌آید

نمونه اجرا:

    BALE_TOKEN=123:abc OPENROUTER_API_KEY=sk-or-v1-... python3 main.py
"""
import os

# ============================================================
# پوشه‌ی داده‌ها
# ============================================================
DATA_DIR = (os.environ.get("DATA_DIR")
            or os.environ.get("BALE_DATA_DIR")
            or "data")
DATA_DIR_ENV = DATA_DIR

ADMIN_CACHE_TTL = 60


# ============================================================
# مالک ربات
# ============================================================
def _owner_id():
    for env in ("OWNER_ID", "BALE_OWNER_ID", "TELEGRAM_OWNER_ID"):
        raw = (os.environ.get(env) or "").strip()
        if raw:
            try:
                return int(raw)
            except ValueError:
                print(f"[config] {env} عدد نیست: {raw!r}")
    return 234775012


OWNER_ID = _owner_id()


# ============================================================
# پیام‌رسان‌ها (توکن از env — جای دیگری نگه نمی‌داریم)
# ============================================================
def active_platforms():
    """لیست پیام‌رسان‌های فعال (از platforms/__init__.py)."""
    try:
        import platforms
        return platforms.enabled()
    except Exception as e:
        print(f"[config] خطا در خواندن پیام‌رسان‌ها: {e}")
        return []


def primary_platform():
    try:
        import platforms
        plats = platforms.enabled()
        if plats:
            return plats[0]
    except Exception:
        pass
    return None


def _primary_token():
    plat = primary_platform()
    if plat:
        return plat.token
    # هیچ پلتفرمی فعال نشد → متغیرهای رایج را برای پیام خطای بهتر بگرد
    for env in ("BALE_TOKEN", "BOT_TOKEN", "TOKEN", "TELEGRAM_TOKEN"):
        val = (os.environ.get(env) or "").strip()
        if val:
            return val
    return ""


#: توکن پیام‌رسان اصلی — برای سازگاری با کدهای قدیمی
TOKEN = _primary_token()


def base_url():
    plat = primary_platform()
    return plat.api_url() if plat and plat.configured() else ""


#: آدرس API پیام‌رسان اصلی (اگر توکن نباشد خالی است)
BASE_URL = base_url()


def has_token():
    return bool(TOKEN) or bool(active_platforms())


def port():
    """پورت وب‌سرور (Render خودش ست می‌کند)."""
    raw = (os.environ.get("PORT") or "").strip()
    try:
        return int(raw) if raw else 0
    except ValueError:
        return 0


def web_server_enabled():
    """اگر PORT ست شده باشد (Render / هر میزبان وب) سرور بالا می‌آید."""
    return bool(port()) or (os.environ.get("WEB_SERVER") or "").strip() in (
        "1", "true", "yes", "on")


def token_hint():
    """راهنمای فارسی وقتی هیچ توکنی تنظیم نشده."""
    return (
        "❌ هیچ توکنی تنظیم نشده — ربات نمی‌تواند وصل شود.\n\n"
        "  روی سرور (Render) این‌ها را در Environment بگذار:\n"
        "      BALE_TOKEN = توکن ربات بله\n"
        "      TELEGRAM_TOKEN = توکن ربات تلگرام (اگر می‌خواهی)\n"
        "      PLATFORMS = bale,telegram   (یا فقط bale)\n\n"
        "  روی سیستم خودت:\n"
        "      export BALE_TOKEN=\"123456:ABC...\"\n"
        f"      یا توکن را در فایل بگذار: {os.path.join(DATA_DIR, 'bale_token.txt')}\n"
    )


def env_report():
    """خلاصه‌ی وضعیت تنظیمات (بدون لو دادن توکن‌ها) — برای لاگ و /healthz"""
    plats = active_platforms()
    return {
        "data_dir": os.path.abspath(DATA_DIR),
        "owner_id": OWNER_ID,
        "platforms": [p.key for p in plats],
        "tokens_set": {p.key: bool(p.token) for p in plats},
        "openrouter_key": bool(
            (os.environ.get("OPENROUTER_API_KEY")
             or os.environ.get("OPENROUTER_KEY")
             or os.environ.get("OPENROUTER_TOKEN") or "").strip()),
        "port": port(),
        "web_server": web_server_enabled(),
    }
