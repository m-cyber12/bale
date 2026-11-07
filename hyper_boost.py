# hyper_boost.py — حذف fsync + batch saves
import os
import time
import shutil
import core
from core import db

_last_flush_at = 0
_MIN_INTERVAL = 5           # حداقل ۵ ثانیه بین هر نوشتن
_BACKUP_INTERVAL = 180      # بکاپ هر ۳ دقیقه (قبلاً ۶۰ ثانیه)


def _fast_flush(backup=False):
    """DB write بدون fsync + با گیت ۵ ثانیه"""
    global _last_flush_at
    now = time.time()
    
    # gate: اگه ۵ ثانیه نشده، skip کن
    if not backup and (now - _last_flush_at) < _MIN_INTERVAL:
        return
    
    try:
        data = core._dumps_bytes(db)
        tmp = core.DB_FILE + ".tmp"
        with open(tmp, "wb") as f:
            f.write(data)
            # ❌ fsync حذف شد — روی گوشی خیلی کنده
        os.replace(tmp, core.DB_FILE)
        core._db_dirty = False
        _last_flush_at = now
        
        # بکاپ هر ۳ دقیقه (نه هر ۱ دقیقه)
        if backup or (now - core._last_backup > _BACKUP_INTERVAL):
            try:
                shutil.copy2(core.DB_FILE, core.DB_FILE + ".bak")
                core._last_backup = now
            except:
                pass
    except Exception as e:
        print(f"❌ fast_flush: {e}")


def init():
    print("🚀 HYPER BOOST v5 فعال شد")
    
    # 1. جایگزینی flush کند با سریع
    core._flush_db = _fast_flush
    print("   💾 DB: بدون fsync (5-10x سریع‌تر)")
    print("   ⏱️ Min flush interval: 5s (قبلاً 2s)")
    print("   🎨 Backup: هر 3 دقیقه (قبلاً 1 دقیقه)")
    
    # 2. کش عضویت ۳۰ دقیقه (به جای ۵ دقیقه)
    core._membership_ttl = 1800
    print("   🔍 Membership cache: 30 دقیقه")
    
    print("✅ HYPER BOOST آماده!")