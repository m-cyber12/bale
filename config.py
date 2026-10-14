# -*- coding: utf-8 -*-
"""تنظیمات ربات.

⚠️ توکن ربات **در کد نگه داشته نمی‌شود**. اولویت خواندن:

  1) متغیر محیطی  `BALE_TOKEN`
  2) فایل        `data/token.txt`   (داخل .gitignore هست)
  3) متغیر محیطی  `BOT_TOKEN`  (برای سازگاری با ستاپ‌های قدیمی)

نمونه‌ی اجرا:

    BALE_TOKEN=123:abc python3 main.py
"""
import os

DATA_DIR = os.environ.get("BALE_DATA_DIR") or "data"


def _read_token():
    for env in ("BALE_TOKEN", "BOT_TOKEN"):
        t = (os.environ.get(env) or "").strip()
        if t:
            return t
    path = os.path.join(DATA_DIR, "token.txt")
    try:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read().strip()
    except Exception as e:
        print(f"[config] خطا در خواندن {path}: {e}")
    return ""


TOKEN = _read_token()

# اگر توکن نباشد، BASE_URL خالی می‌ماند تا خطای واضح بدهیم نه آدرس خراب
BASE_URL = f"https://tapi.bale.ai/bot{TOKEN}/" if TOKEN else ""

DATA_DIR_ENV = DATA_DIR
ADMIN_CACHE_TTL = 60

try:
    OWNER_ID = int(os.environ.get("BALE_OWNER_ID") or 234775012)
except ValueError:
    OWNER_ID = 234775012


def has_token():
    return bool(TOKEN)


def token_hint():
    """راهنمای فارسی وقتی توکن تنظیم نشده."""
    return (
        "❌ توکن ربات تنظیم نشده!\n"
        "  یکی از این دو کار را بکن:\n"
        "  1) متغیر محیطی:\n"
        "       export BALE_TOKEN=\"123456:ABC...\"\n"
        "  2) یا توکن را در فایل زیر بگذار:\n"
        f"       {os.path.join(DATA_DIR, 'token.txt')}\n"
        "  (این فایل داخل .gitignore است و کامیت نمی‌شود)\n"
    )
