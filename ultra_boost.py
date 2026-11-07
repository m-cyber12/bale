# ultra_boost.py — Ultimate speed optimization
import sys
import time
import json
import threading
from collections import OrderedDict

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import *
import core


# ==================== 1. HTTP pool 200 connections ====================
def install_ultra_http():
    """HTTP pool خیلی بزرگتر + keep-alive + بدون retry (fail fast)"""
    _tls = threading.local()

    def ultra_session():
        if not hasattr(_tls, "s"):
            s = requests.Session()
            retry = Retry(total=0, connect=0, read=0, backoff_factor=0)
            adapter = HTTPAdapter(
                pool_connections=200,
                pool_maxsize=300,
                max_retries=retry,
                pool_block=False,
            )
            s.mount("https://", adapter)
            s.mount("http://", adapter)
            s.headers.update({
                "Connection": "keep-alive",
                "Keep-Alive": "timeout=120, max=10000",
            })
            _tls.s = s
        return _tls.s

    core._tls = _tls
    core._session = ultra_session


# ==================== 2. Pre-bake keyboards ====================
class KeyboardBakery:
    """JSON keyboards رو یک‌بار serialize می‌کنه و cache می‌کنه"""
    def __init__(self, max_size=500):
        self._cache = OrderedDict()
        self._lock = threading.Lock()
        self._max = max_size

    def bake(self, markup):
        if not markup:
            return None
        # structural hash سریع
        try:
            key = str(markup)
        except Exception:
            key = id(markup)

        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]

        s = json.dumps(markup, ensure_ascii=False, separators=(",", ":"))

        with self._lock:
            self._cache[key] = s
            self._cache.move_to_end(key)
            if len(self._cache) > self._max:
                self._cache.popitem(last=False)
        return s


bakery = KeyboardBakery()


# ==================== 3. Ultra fast send/edit ====================
def ultra_send_message(chat_id, text, reply_markup=None,
                       reply_to_message_id=None):
    data = {"chat_id": chat_id, "text": text}
    if reply_markup:
        data["reply_markup"] = bakery.bake(reply_markup)
    if reply_to_message_id:
        data["reply_to_message_id"] = reply_to_message_id
    return core._post("sendMessage", data, timeout=4)


def ultra_edit_message(chat_id, message_id, text, reply_markup=None):
    data = {"chat_id": chat_id, "message_id": message_id, "text": text}
    if reply_markup:
        data["reply_markup"] = bakery.bake(reply_markup)

    result = core._post("editMessageText", data, timeout=4)
    if result.get("ok"):
        return result

    desc = result.get("description", "").lower()
    if "message is not modified" in desc:
        return {"ok": True, "skipped": True}
    if "no text" in desc or "can't be edited" in desc:
        cap = {"chat_id": chat_id, "message_id": message_id, "caption": text}
        if reply_markup:
            cap["reply_markup"] = bakery.bake(reply_markup)
        return core._post("editMessageCaption", cap, timeout=4)
    return result


# ==================== 4. Skip redundant edits ====================
class EditDedup:
    """اگه محتوا همونه، دیگه درخواست نده"""
    def __init__(self, max_size=1000):
        self._cache = OrderedDict()
        self._lock = threading.Lock()
        self._max = max_size

    def is_same(self, chat_id, msg_id, text, markup):
        key = (chat_id, msg_id)
        sig = (text, str(markup) if markup else "")
        with self._lock:
            if self._cache.get(key) == sig:
                return True
            self._cache[key] = sig
            self._cache.move_to_end(key)
            if len(self._cache) > self._max:
                self._cache.popitem(last=False)
            return False


edit_dedup = EditDedup()


def ultra_edit_dedup(chat_id, message_id, text, reply_markup=None):
    if edit_dedup.is_same(chat_id, message_id, text, reply_markup):
        return {"ok": True, "deduplicated": True}
    return ultra_edit_message(chat_id, message_id, text, reply_markup)


# ==================== 5. User hot cache ====================
class UserHotCache:
    """داده‌های پرکاربرد کاربر رو در RAM نگه می‌داره (L1 cache)"""
    def __init__(self, max_size=5000):
        self._cache = {}
        self._lock = threading.Lock()
        self._max = max_size

    def get_level(self, total_damage):
        key = f"lvl_{total_damage}"
        with self._lock:
            if key in self._cache:
                return self._cache[key]
        from data import get_level_info
        result = get_level_info(total_damage)
        with self._lock:
            if len(self._cache) > self._max:
                # clear half
                for k in list(self._cache.keys())[:self._max // 2]:
                    del self._cache[k]
            self._cache[key] = result
        return result

    def get_league(self, rank):
        key = f"lg_{rank}"
        with self._lock:
            if key in self._cache:
                return self._cache[key]
        from data import get_league
        result = get_league(rank)
        with self._lock:
            self._cache[key] = result
        return result


hot_cache = UserHotCache()


# ==================== 6. Prewarm keyboards ====================
def _prewarm():
    """تمام keyboardهای ثابت رو pre-bake کن"""
    try:
        from builders import (
            build_resources_keyboard, build_wheel_keyboard,
            build_battle_keyboard, build_factory_keyboard,
            build_mine_keyboard, build_shop_keyboard,
            build_missile_keyboard, build_lab_keyboard,
            build_airport_keyboard, build_drone_keyboard,
            build_battle_cancel_keyboard,
        )
        from handlers import reply_keyboard, inline_keyboard, get_guide_keyboard

        kbs = [
            reply_keyboard, inline_keyboard,
            get_guide_keyboard(),
        ]

        for fn in [build_resources_keyboard, build_wheel_keyboard,
                   build_battle_keyboard, build_factory_keyboard,
                   build_mine_keyboard, build_shop_keyboard,
                   build_missile_keyboard, build_lab_keyboard,
                   build_airport_keyboard, build_drone_keyboard,
                   build_battle_cancel_keyboard]:
            try:
                kbs.append(fn())
            except Exception:
                pass

        count = 0
        for kb in kbs:
            try:
                bakery.bake(kb)
                count += 1
            except Exception:
                pass
        print(f"   🎨 Pre-baked {count} keyboards")
    except Exception as e:
        print(f"   ⚠️ Prewarm error: {e}")


# ==================== 7. Reduce DB write frequency ====================
def _reduce_db_writes():
    """DB رو هر 2 ثانیه به 5 ثانیه افزایش بده (کمتر block)"""
    # این کار به‌طور خودکار در core.py انجام می‌شه (2s)
    # ولی می‌تونیم تهاجمی‌تر کنیم
    pass


# ==================== init ====================
_initialized = False


def init():
    global _initialized
    if _initialized:
        return
    _initialized = True

    print("🚀 ULTRA BOOST v3 فعال شد")

    # 1. HTTP pool
    install_ultra_http()
    print("   🔌 HTTP: 200 connection pool")

    # 2. Patch core + همه ماژول‌ها
    core.send_message = ultra_send_message
    core.edit_message = ultra_edit_dedup

    for mod_name in ["builders", "handlers", "handlers_message",
                     "handlers_callback", "clan_war", "handlers_payment"]:
        mod = sys.modules.get(mod_name)
        if not mod:
            continue
        if hasattr(mod, "send_message"):
            setattr(mod, "send_message", ultra_send_message)
        if hasattr(mod, "edit_message"):
            setattr(mod, "edit_message", ultra_edit_dedup)
    print("   💾 Ultra fast send/edit + dedup")

    # 3. Prewarm keyboards
    threading.Thread(target=_prewarm, daemon=True).start()
    print("   🎨 Pre-baking keyboards (async)")

    # 4. Clear dedup cache every 5 min (avoid memory growth)
    def _cleanup():
        while True:
            time.sleep(300)
            try:
                with edit_dedup._lock:
                    if len(edit_dedup._cache) > 500:
                        for k in list(edit_dedup._cache.keys())[:250]:
                            del edit_dedup._cache[k]
            except Exception:
                pass
    threading.Thread(target=_cleanup, daemon=True).start()

    print("✅ Ultra Boost آماده!")


def stats():
    return {
        "keyboard_cache": len(bakery._cache),
        "edit_dedup": len(edit_dedup._cache),
        "hot_cache": len(hot_cache._cache),
    }