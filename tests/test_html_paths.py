# -*- coding: utf-8 -*-
"""تست هدفمند: پیام‌هایی که با parse_mode="HTML" فرستاده می‌شوند.

اگر داخل این پیام‌ها escape مارک‌داون (مثل \\_ ) باشد، کاربر بک‌اسلش می‌بیند.
این تست توابع سازنده‌ی این پیام‌ها را مستقیماً با نام آلوده صدا می‌زند.
"""
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

TMP = tempfile.mkdtemp(prefix="bale_html_")
import config  # noqa: E402
config.DATA_DIR = TMP

import fake_bale  # noqa: E402
import api  # noqa: E402

try:
    import gifmaker  # noqa: E402
except Exception:
    gifmaker = None

FAKE = fake_bale.install(api, gifmaker)

import storage  # noqa: E402
import main  # noqa: E402  (برای monkeypatch‌های جانبی)
import multiplayer  # noqa: E402
import notify  # noqa: E402

GROUP = -100555
EVIL = "علی_رضا *ستاره* `کد` <b>x</b>"

problems = []


def check(label, fn):
    before = len(FAKE.mode_mismatch)
    try:
        fn()
    except Exception as e:
        problems.append(f"[EXC] {label}: {type(e).__name__}: {e}")
        return
    for kind, txt in FAKE.mode_mismatch[before:]:
        problems.append(f"[{kind}] {label}: {txt[:200]!r}")


check("_start_todd", lambda: multiplayer._start_todd(GROUP, 1, 2, EVIL))
check("_start_dice", lambda: multiplayer._start_dice(GROUP, 1, 2, EVIL))
check("_start_coin", lambda: multiplayer._start_coin(GROUP, 1, 2, EVIL))
check("notify _admin_links", lambda: notify._admin_links([
    {"id": 5, "name": EVIL, "username": "ali_reza", "status": "creator"},
    {"id": 6, "name": EVIL, "username": "", "status": "administrator"},
]))

# پیام‌های صریح HTML (اگر داخلشان escape مارک‌داون باشد)
check("send HTML مستقیم", lambda: api.send(
    GROUP, f"<b>{api.esc_html(EVIL)}</b>", parse_mode="HTML"))

if problems:
    print(f"❌ {len(problems)} مشکل:")
    for p in problems:
        print("  ", p)
    sys.exit(1)
print("✅ مسیرهای HTML سالم‌اند")
