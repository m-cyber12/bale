# performance.py — لایه اول سرعت
import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict

import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from config import *
from core import db


# ============ ThreadPool ============
class UpdateProcessor:
    def __init__(self, max_workers=10):
        self.executor = ThreadPoolExecutor(max_workers=max_workers,
                                           thread_name_prefix="w")
        self._handler = None
        self.active = 0
        self.processed = 0
        self.dropped = 0
        self.errors = 0
        self._lock = threading.Lock()

    def set_handler(self, fn):
        self._handler = fn

    def submit(self, update):
        if not self._handler:
            return
        with self._lock:
            self.active += 1
        self.executor.submit(self._run, update)

    def _run(self, update):
        try:
            uid = self._extract_uid(update)

            # 1) user rate: فقط برای اسپم واقعی (30/s برای هر کاربر)
            if uid and not user_rate.allow(uid):
                with self._lock:
                    self.dropped += 1
                return

            # 2) global rate: فقط وقتی ربات تحت فشاره (نه همیشه)
            with self._lock:
                is_loaded = self.active >= (self.executor._max_workers - 2)

            if is_loaded and not global_rate.allow():
                with self._lock:
                    self.dropped += 1
                return

            try:
                if uid:
                    with user_lock(uid):
                        self._handler(update)
                else:
                    self._handler(update)
                with self._lock:
                    self.processed += 1
            except Exception as e:
                with self._lock:
                    self.errors += 1
                print(f"❌ handler error (user={uid}): {e}")
        finally:
            with self._lock:
                self.active -= 1

    def _extract_uid(self, update):
        for key in ("callback_query", "message", "pre_checkout_query"):
            if key in update:
                return str(update[key].get("from", {}).get("id", "")) or None
        return None

    def stats(self):
        with self._lock:
            return {
                "active": self.active, "done": self.processed,
                "drop": self.dropped, "err": self.errors,
            }


processor = UpdateProcessor(max_workers=10)   # 🆕 10 worker (قبلاً 60 بود)


# ============ User Locks ============
class UserLockManager:
    def __init__(self):
        self._locks = {}
        self._guard = threading.Lock()

    def get(self, user_id):
        uid = str(user_id)
        with self._guard:
            if uid not in self._locks:
                self._locks[uid] = threading.Lock()
            return self._locks[uid]


user_locks = UserLockManager()


class user_lock:
    def __init__(self, user_id):
        self.lock = user_locks.get(user_id)

    def __enter__(self):
        self.lock.acquire()
        return self

    def __exit__(self, *args):
        self.lock.release()


class two_user_locks:
    def __init__(self, uid1, uid2):
        a, b = str(uid1), str(uid2)
        if a == b:
            self.locks = [user_locks.get(a)]
        elif a < b:
            self.locks = [user_locks.get(a), user_locks.get(b)]
        else:
            self.locks = [user_locks.get(b), user_locks.get(a)]

    def __enter__(self):
        for l in self.locks:
            l.acquire()
        return self

    def __exit__(self, *args):
        for l in reversed(self.locks):
            l.release()


# ============ Rate Limiter ============
class RateLimiter:
    def __init__(self, max_req, window):
        self.max_req = max_req
        self.window = window
        self._data = defaultdict(list)
        self._lock = threading.Lock()

    def allow(self, key="global"):
        now = time.time()
        with self._lock:
            ts = self._data[key]
            if len(ts) >= self.max_req:
                ts[:] = [t for t in ts if now - t < self.window]
                if len(ts) >= self.max_req:
                    return False
            ts.append(now)
            return True

    def cleanup(self, max_age=120):
        now = time.time()
        with self._lock:
            for k in list(self._data.keys()):
                ts = self._data[k]
                ts[:] = [t for t in ts if now - t < self.window]
                if not ts:
                    del self._data[k]


user_rate = RateLimiter(30, 1.0)
global_rate = RateLimiter(500, 1.0)


# ============ HTTP Session pool ============
_tls = threading.local()


def _session():
    if not hasattr(_tls, "s"):
        s = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=20, pool_maxsize=50,
            max_retries=1, pool_block=False,
        )
        s.mount("https://", adapter)
        s.mount("http://", adapter)
        _tls.s = s
    return _tls.s


# ============ Latency tracker ============
class LatencyTracker:
    def __init__(self):
        self._lock = threading.Lock()
        self._api_calls = 0
        self._api_total = 0.0
        self._last_report = time.time()

    def record(self, seconds):
        with self._lock:
            self._api_calls += 1
            self._api_total += seconds

    def maybe_report(self):
        now = time.time()
        with self._lock:
            if now - self._last_report > 60 and self._api_calls > 0:
                avg = (self._api_total / self._api_calls) * 1000
                print(f"📊 API latency: avg={avg:.0f}ms ({self._api_calls} calls)")
                self._api_calls = 0
                self._api_total = 0.0
                self._last_report = now


latency = LatencyTracker()


# ============ Cleanup thread ============
def _cleanup_loop():
    while True:
        try:
            time.sleep(120)
            user_rate.cleanup(max_age=120)
            global_rate.cleanup(max_age=120)
        except Exception as e:
            print(f"⚠️ cleanup loop: {e}")


# ============ Warmup ============
def warmup_connections():
    try:
        r = _session().get(f"{API_URL}/getMe", verify=False, timeout=5)
        r.json()
        print("   🔌 Connections warmed up")
    except Exception:
        pass


# ============ init ============
def init_performance():
    print("⚡ ULTRA FAST MODE")
    print("   📦 JSON: json-compact")
    print("   ⚡ ThreadPool: 10 workers")
    print("   🚀 Rate Limit: 30/s user, 500/s global (under-load only)")
    print("   💾 DB: async (no blocking)")
    print("   🔌 HTTP: pooled session")
    warmup_connections()
    threading.Thread(target=_cleanup_loop, daemon=True).start()
    print("✅ بهینه‌سازی کامل!")


def get_stats():
    return processor.stats()