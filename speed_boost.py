# speed_boost.py — لایه دوم سرعت (بدون پکیج خارجی)
import sys
import json
import threading
import functools
from collections import OrderedDict

import core
import data
from core import db


# ============ لیست توابع cacheable ============
CACHEABLE_FUNCS = [
    'get_level_info',           # 🥇 بزرگترین برد — تا 1000 بار loop
    'get_league',
    'get_loot_coins',
    'get_loot_oil',
    'get_loot_rank',
    'get_upgrade_cost',
    'get_upgrade_oil_cost',
    'get_upgrade_time',
    'get_missile_upgrade_base_cost',
    'get_refinery_cap',
    'get_refinery_rate',
]

MODULES_TO_PATCH = ['builders', 'handlers', 'handlers_message',
                    'handlers_callback', 'clan_war', 'data',
                    'handlers_payment']

_applied = set()


def _apply_caches():
    """LRU cache روی توابع خالص در همه ماژول‌ها"""
    for fname in CACHEABLE_FUNCS:
        orig = getattr(data, fname, None)
        if orig is None or fname in _applied:
            continue
        _applied.add(fname)
        cached = functools.lru_cache(maxsize=16384)(orig)
        setattr(data, fname, cached)
        for mod_name in MODULES_TO_PATCH:
            mod = sys.modules.get(mod_name)
            if mod and hasattr(mod, fname):
                setattr(mod, fname, cached)


# ============ Markup Cache ============
class _MarkupCache:
    """Cache JSON serialized reply_markup (نگه‌داشتن ref → id یکتا)"""
    def __init__(self, max_size=500):
        self._data = OrderedDict()
        self._lock = threading.Lock()
        self._max = max_size

    def get(self, markup):
        if not markup:
            return None
        mid = id(markup)
        with self._lock:
            if mid in self._data:
                self._data.move_to_end(mid)
                return self._data[mid][1]
        s = json.dumps(markup, ensure_ascii=False, separators=(",", ":"))
        with self._lock:
            self._data[mid] = (markup, s)  # نگه‌داشتن ref → id یکتا
            self._data.move_to_end(mid)
            if len(self._data) > self._max:
                self._data.popitem(last=False)
        return s

    def clear(self):
        with self._lock:
            self._data.clear()


markup_cache = _MarkupCache()


# ============ Edit Cache (skip no-op) ============
class _EditCache:
    def __init__(self, max_size=500):
        self._data = OrderedDict()
        self._lock = threading.Lock()
        self._max = max_size

    def check_and_update(self, chat_id, msg_id, sig):
        key = (chat_id, msg_id)
        with self._lock:
            if self._data.get(key) == sig:
                return True  # محتوا همونه → skip
            self._data[key] = sig
            self._data.move_to_end(key)
            if len(self._data) > self._max:
                self._data.popitem(last=False)
            return False

    def clear(self):
        with self._lock:
            self._data.clear()


edit_cache = _EditCache()


# ============ Wrappers ============
_orig_send = core.send_message
_orig_edit = core.edit_message


def fast_send_message(chat_id, text, reply_markup=None,
                      reply_to_message_id=None):
    """send_message با markup cache"""
    if reply_markup:
        cached = markup_cache.get(reply_markup)
        if cached is not None:
            data_dict = {"chat_id": chat_id, "text": text,
                         "reply_markup": cached}
            if reply_to_message_id:
                data_dict["reply_to_message_id"] = reply_to_message_id
            return core._post("sendMessage", data_dict)
    return _orig_send(chat_id, text, reply_markup, reply_to_message_id)


def fast_edit_message(chat_id, msg_id, text, reply_markup=None):
    """edit_message با skip no-op + markup cache"""
    sig = (text, str(reply_markup) if reply_markup else "")
    if edit_cache.check_and_update(chat_id, msg_id, sig):
        return {"ok": True, "skipped": True}
    return _orig_edit(chat_id, msg_id, text, reply_markup)


def _patch_send_edit():
    core.send_message = fast_send_message
    core.edit_message = fast_edit_message
    for mod_name in MODULES_TO_PATCH:
        mod = sys.modules.get(mod_name)
        if not mod:
            continue
        if hasattr(mod, 'send_message'):
            setattr(mod, 'send_message', fast_send_message)
        if hasattr(mod, 'edit_message'):
            setattr(mod, 'edit_message', fast_edit_message)


# ============ Prewarm ============
def _prewarm():
    count = 0
    for uid, p in db.items():
        if not isinstance(p, dict) or "user_id" not in p:
            continue
        td = p.get("total_damage", 0)
        if td:
            data.get_level_info(td)
        r = p.get("rank", 0)
        if r:
            data.get_league(r)
        count += 1
    print(f"   ✅ Prewarmed {count} users")


# ============ Public API ============
_initialized = False


def init():
    """فقط یک بار صدا زده بشه، در main.py بعد از همه importها"""
    global _initialized
    if _initialized:
        return
    _initialized = True
    print("🚀 SPEED BOOST LEVEL 2 فعال شد")
    _apply_caches()
    print("   📊 LRU cache: 11 تابع × 7 ماژول")
    _patch_send_edit()
    print("   💾 markup cache + skip no-op edits")
    threading.Thread(target=_prewarm, daemon=True).start()


def stats():
    """آمار cacheها"""
    result = {}
    for fname in CACHEABLE_FUNCS:
        f = getattr(data, fname, None)
        if f and hasattr(f, 'cache_info'):
            info = f.cache_info()
            hit_rate = (info.hits / (info.hits + info.misses) * 100
                       if info.hits + info.misses > 0 else 0)
            result[fname] = f"hit={hit_rate:.1f}% ({info.hits}/{info.hits+info.misses})"
    return result


def clear_caches():
    """اگه کلنی rename شد یا نیاز بود، cache ها رو ریست کن"""
    for fname in CACHEABLE_FUNCS:
        f = getattr(data, fname, None)
        if f and hasattr(f, 'cache_clear'):
            f.cache_clear()
    markup_cache.clear()
    edit_cache.clear()
    print("✅ همه cacheها ریست شدند")