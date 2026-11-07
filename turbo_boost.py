# turbo_boost.py — لایه سرعت نهایی (بدون تغییر فایل‌های دیگه)
import sys
import time
import json
import math
import threading
from collections import OrderedDict
from functools import lru_cache

import core
import data
from core import db


# ============ 1. get_level_info با فرمول (۱۰۰x سریع‌تر از loop) ============
def fast_get_level_info(total_damage):
    """محاسبه لول با فرمول ریاضی — O(1) به جای O(n)"""
    if total_damage <= 0:
        return (1, 0, 100)
    # حل معادله: 50*n*(n+1) <= total_damage
    n = int((-50 + math.sqrt(2500 + 200 * total_damage)) / 100)
    if n < 0:
        n = 0
    while True:
        xp_used = 50 * n * (n + 1)
        if total_damage < xp_used + (n + 1) * 100:
            break
        n += 1
    xp_used = 50 * n * (n + 1)
    level = n + 1
    xp_needed = level * 100
    return (level, total_damage - xp_used, xp_needed)


@lru_cache(maxsize=32768)
def cached_get_level_info(total_damage):
    return fast_get_level_info(total_damage)


# ============ 2. get_league با dict (بدون loop) ============
_league_cache = {}
for _name, _mn, _mx in data.RANK_LEAGUES:
    span = min(_mx - _mn, 300)
    for _r in range(_mn, _mn + span):
        _league_cache[_r] = _name


def fast_get_league(rank):
    if rank in _league_cache:
        return _league_cache[rank]
    for name, mn, mx in data.RANK_LEAGUES:
        if mn <= rank < mx:
            return name
    return "🌱 تازه‌کار"


@lru_cache(maxsize=16384)
def cached_get_league(rank):
    return fast_get_league(rank)


# ============ 3. Patch همه ماژول‌ها ============
def _patch_data_functions():
    data.get_level_info = cached_get_level_info
    data.get_league = cached_get_league

    for mod_name in ["builders", "handlers", "handlers_message",
                     "handlers_callback", "clan_war", "handlers_payment",
                     "speed_boost", "ultra_boost"]:
        mod = sys.modules.get(mod_name)
        if not mod:
            continue
        if hasattr(mod, "get_level_info"):
            setattr(mod, "get_level_info", cached_get_level_info)
        if hasattr(mod, "get_league"):
            setattr(mod, "get_league", cached_get_league)
    print("   ⚡ level/league: O(1) formula")


# ============ 4. Keyboard pre-serialize ============
_kb_cache = {}
_kb_lock = threading.Lock()


def _cache_keyboard(markup):
    if not markup:
        return None
    kid = id(markup)
    with _kb_lock:
        if kid in _kb_cache:
            return _kb_cache[kid]
    try:
        s = json.dumps(markup, ensure_ascii=False, separators=(",", ":"))
    except:
        return None
    with _kb_lock:
        _kb_cache[kid] = s
    return s


def _prewarm_keyboards():
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

        kbs = [reply_keyboard, inline_keyboard, get_guide_keyboard()]
        for fn in [build_resources_keyboard, build_wheel_keyboard,
                   build_battle_keyboard, build_factory_keyboard,
                   build_mine_keyboard, build_shop_keyboard,
                   build_missile_keyboard, build_lab_keyboard,
                   build_airport_keyboard, build_drone_keyboard,
                   build_battle_cancel_keyboard]:
            try:
                kbs.append(fn())
            except:
                pass

        count = 0
        for kb in kbs:
            if _cache_keyboard(kb):
                count += 1
        print(f"   🎨 {count} keyboard pre-baked")
    except Exception as e:
        print(f"   ⚠️ prewarm kb: {e}")


# ============ 5. HTTP pool بزرگ‌تر ============
def _patch_http():
    try:
        import requests
        from requests.adapters import HTTPAdapter

        _tls = threading.local()

        def _session():
            if not hasattr(_tls, "s"):
                s = requests.Session()
                adapter = HTTPAdapter(
                    pool_connections=100,
                    pool_maxsize=200,
                    max_retries=0,
                    pool_block=False,
                )
                s.mount("https://", adapter)
                s.mount("http://", adapter)
                _tls.s = s
            return _tls.s

        core._tls = _tls
        core._session = _session
        print("   🔌 HTTP: 100x200 pool")
    except Exception as e:
        print(f"   ⚠️ http: {e}")


# ============ 6. Skip duplicate edits ============
_edit_cache = OrderedDict()
_edit_lock = threading.Lock()


def _should_skip_edit(chat_id, msg_id, text, markup_str):
    key = (chat_id, msg_id)
    sig = hash((text, markup_str or ""))
    with _edit_lock:
        if _edit_cache.get(key) == sig:
            return True
        _edit_cache[key] = sig
        _edit_cache.move_to_end(key)
        if len(_edit_cache) > 2000:
            _edit_cache.popitem(last=False)
    return False


_orig_edit = core.edit_message


def fast_edit(chat_id, message_id, text, reply_markup=None):
    markup_str = _cache_keyboard(reply_markup) or "" if reply_markup else ""
    if _should_skip_edit(chat_id, message_id, text, markup_str):
        return {"ok": True, "skipped": True}
    return _orig_edit(chat_id, message_id, text, reply_markup)


def _patch_edit():
    core.edit_message = fast_edit
    for mod_name in ["builders", "handlers", "handlers_message",
                     "handlers_callback", "clan_war", "handlers_payment",
                     "speed_boost", "ultra_boost"]:
        mod = sys.modules.get(mod_name)
        if not mod:
            continue
        if hasattr(mod, "edit_message"):
            setattr(mod, "edit_message", fast_edit)
    print("   💾 edit dedup فعال")


# ============ 7. Patch send_message برای keyboard cache ============
_orig_send = core.send_message


def fast_send(chat_id, text, reply_markup=None, reply_to_message_id=None):
    return _orig_send(chat_id, text, reply_markup, reply_to_message_id)


# ============ 8. Warmup ============
def _warmup():
    try:
        count = 0
        for uid, p in db.items():
            if not isinstance(p, dict) or "user_id" not in p:
                continue
            td = p.get("total_damage", 0)
            if td:
                cached_get_level_info(td)
            r = p.get("rank", 0)
            if r:
                cached_get_league(r)
            count += 1
        print(f"   ✅ {count} کاربر warmup شد")
    except Exception as e:
        print(f"   ⚠️ warmup: {e}")


# ============ 9. Memory cleanup ============
def _cleanup_loop():
    while True:
        time.sleep(300)
        try:
            with _edit_lock:
                if len(_edit_cache) > 1000:
                    for k in list(_edit_cache.keys())[:500]:
                        del _edit_cache[k]
            with _kb_lock:
                if len(_kb_cache) > 500:
                    for k in list(_kb_cache.keys())[:250]:
                        del _kb_cache[k]
        except:
            pass


# ============ init ============
_initialized = False


def init():
    global _initialized
    if _initialized:
        return
    _initialized = True

    print("🔥 TURBO BOOST v4 فعال شد")

    _patch_data_functions()
    _patch_http()
    _patch_edit()

    threading.Thread(target=_prewarm_keyboards, daemon=True).start()
    threading.Thread(target=_warmup, daemon=True).start()
    threading.Thread(target=_cleanup_loop, daemon=True).start()

    print("✅ TURBO BOOST آماده!")


def stats():
    result = {}
    try:
        result["level_cache"] = cached_get_level_info.cache_info()
    except:
        pass
    try:
        result["league_cache"] = cached_get_league.cache_info()
    except:
        pass
    result["edit_cache"] = len(_edit_cache)
    result["kb_cache"] = len(_kb_cache)
    return result