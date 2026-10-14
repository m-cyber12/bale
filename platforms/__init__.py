# -*- coding: utf-8 -*-
"""ثبت و انتخاب پیام‌رسان‌ها.

فعال‌سازی با متغیر محیطی:

    PLATFORM=bale                 # فقط یکی (پیش‌فرض)
    PLATFORMS=bale,telegram       # چند تا با هم (هر کدام نخ polling خودش)
    PLATFORMS=webhook             # فقط وب‌هوک

اگر `PLATFORMS` تنظیم نشده باشد، به‌ترتیب دنبال توکن‌ها می‌گردد و هر
پیام‌رسانی که توکنش موجود باشد فعال می‌شود (بله اولویت دارد).
"""
import os

from .base import Platform, PlatformError
from .bale import BalePlatform
from .telegram import TelegramPlatform
from .webhook import WebhookPlatform

_CLASSES = {}
_INSTANCES = {}


def register(cls):
    _CLASSES[cls.key] = cls
    return cls


def register_class(cls):
    """ثبت آداپتور دلخواه از بیرون (مثلاً یک پل خصوصی)."""
    _CLASSES[cls.key] = cls
    _INSTANCES.pop(cls.key, None)
    return cls


register(BalePlatform)
register(TelegramPlatform)
register(WebhookPlatform)

#: نام‌های رایج → کلید داخلی
ALIASES = {
    "bale": "bale", "بله": "bale",
    "telegram": "telegram", "tg": "telegram", "تلگرام": "telegram",
    "webhook": "webhook", "webook": "webhook", "hook": "webhook",
    "generic": "webhook", "custom": "webhook",
}


def available():
    return sorted(_CLASSES)


def resolve_key(name):
    name = (name or "").strip().lower()
    return ALIASES.get(name, name)


def get(key):
    """نمونه‌ی singleton هر پیام‌رسان."""
    key = resolve_key(key)
    if key not in _CLASSES:
        raise PlatformError(f"پیام‌رسان ناشناس: {key} (موجود: {', '.join(available())})")
    if key not in _INSTANCES:
        _INSTANCES[key] = _CLASSES[key]()
    return _INSTANCES[key]


def _requested_keys():
    raw = (os.environ.get("PLATFORMS") or os.environ.get("PLATFORM") or "").strip()
    if not raw:
        return []
    keys = []
    for part in raw.replace(" ", "").split(","):
        if not part:
            continue
        keys.append(resolve_key(part))
    return keys


def enabled():
    """لیست پیام‌رسان‌های فعال (به‌ترتیب اولویت)."""
    keys = _requested_keys()
    if keys:
        out = []
        for k in keys:
            try:
                plat = get(k)
            except PlatformError as e:
                print(f"[platforms] {e}")
                continue
            if plat.configured() or plat.key == "webhook":
                out.append(plat)
            else:
                print(f"[platforms] {plat.key} فعال شد ولی توکنش تنظیم نشده "
                      f"({', '.join(plat.token_envs) or 'env'})")
        if out:
            return out
        print("[platforms] هیچ پیام‌رسانی با توکن معتبر پیدا نشد.")
        return []

    # حالت خودکار: هر پیام‌رسانی که توکن دارد
    out = []
    for key in available():
        plat = get(key)
        if plat.configured():
            out.append(plat)
    return out


def default():
    """پیام‌رسانی که پیام‌های بدون مبدأ به آن می‌روند."""
    plats = enabled()
    if plats:
        return plats[0]
    # اگر هیچ توکنی نبود، همان بله برمی‌گردد تا پیام خطای واضح بدهد
    return get("bale")


def all_instances():
    return [get(k) for k in available()]


# ============================================================
# نقشه‌ی چت → پیام‌رسان
# (پیام‌های تأخیری مثل تایمر بازی‌ها هم باید بدانند کجا بروند)
# ============================================================
_MAP_SECTION = "platforms"
_MAP_KEY = "chat_map"


def _load_map():
    try:
        import storage
        m = storage.get(_MAP_SECTION, _MAP_KEY) or {}
        return m if isinstance(m, dict) else {}
    except Exception:
        return {}


def remember_chat(key, chat_id):
    """اولین‌باری که چتی دیده می‌شود، پیام‌رسانش ثبت می‌شود."""
    if chat_id is None:
        return
    try:
        import storage
        m = _load_map()
        sid = str(chat_id)
        if m.get(sid) != key:
            m[sid] = key
            storage.set_(_MAP_SECTION, _MAP_KEY, m)
    except Exception as e:
        print(f"[platforms:remember] {e}")


def platform_of_chat(chat_id):
    if chat_id is None:
        return None
    try:
        key = _load_map().get(str(chat_id))
    except Exception:
        return None
    if key and key in _CLASSES:
        return get(key)
    return None


def forget_chat(chat_id):
    try:
        import storage
        m = _load_map()
        m.pop(str(chat_id), None)
        storage.set_(_MAP_SECTION, _MAP_KEY, m)
    except Exception:
        pass


def summary():
    return [p.health() for p in all_instances()]
