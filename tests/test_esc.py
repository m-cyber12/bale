# -*- coding: utf-8 -*-
"""تست واحد برای api.esc_md / api.esc_html و فالبک parse_mode."""
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

TMP = tempfile.mkdtemp(prefix="bale_esc_")
import config  # noqa: E402
config.DATA_DIR = TMP

import fake_bale  # noqa: E402
import api  # noqa: E402

FAKE = fake_bale.install(api)     # request/get_updates را جایگزین می‌کند

fails = []


def eq(got, want, label):
    if got != want:
        fails.append(f"{label}: got={got!r} want={want!r}")


# ---------- esc_md ----------
eq(api.esc_md("علی_رضا"), "علی\\_رضا", "underscore")
eq(api.esc_md("*ستاره*"), "\\*ستاره\\*", "asterisk")
eq(api.esc_md("`کد`"), "\\`کد\\`", "backtick")
eq(api.esc_md("[لینک](x)"), "\\[لینک\\](x)", "brackets")
eq(api.esc_md("سلام"), "سلام", "plain untouched")
eq(api.esc_md(""), "", "empty")
eq(api.esc_md(None), "", "None")
eq(api.esc_md(123), "123", "int")

# ---------- esc_html ----------
eq(api.esc_html("<b>x</b>"), "&lt;b&gt;x&lt;/b&gt;", "html tags")
eq(api.esc_html("a & b"), "a &amp; b", "amp")
eq(api.esc_html("علی_رضا"), "علی_رضا", "html keeps underscore")

# ---------- متن escape‌شده باید برای پارسر معتبر باشد ----------
for name in ["علی_رضا", "*ستاره*", "`کد`", "[لینک](x)", "a_b_c", "***", "___"]:
    text = f"🏆 برنده: **{api.esc_md(name)}**"
    err = FAKE._check_markdown(text)
    if err:
        fails.append(f"esc_md({name!r}) → پیام هنوز نامعتبر: {err} ({text!r})")

for name in ["<b>x</b>", "a & b", "<script>", "علی_رضا"]:
    text = f"👤 {api.esc_html(name)}"
    if any(c in api.esc_html(name) for c in "<>"):
        fails.append(f"esc_html({name!r}) تگ باقی گذاشت: {api.esc_html(name)!r}")

# ---------- فالبک: پیام خراب هم باید برسد ----------
FAKE.parse_errors.clear()
r = api.send(999, "شکستن **تگ", parse_mode="Markdown")
if not (r and r.get("ok")):
    fails.append("فالبک parse_mode کار نکرد — پیام ارسال نشد")
if not any("شکستن" in (m.get("text") or "") and not m.get("parse_mode")
           for m in FAKE.sent):
    fails.append("پیام فالبک به‌صورت متن ساده ارسال نشد")

# ---------- esc_md فقط برای «داده» است، نه متن ثابت ----------
# متن ثابت بدون کاراکتر ویژه نباید تغییر کند
if api.esc_md("گروه تست") != "گروه تست":
    fails.append("esc_md متن ساده را تغییر داد")
# و ولیدیتور باید **تگ ناقص را بگیرد
if not FAKE._check_markdown("شکستن **تگ"):
    fails.append("ولیدیتور، بولد بسته‌نشده را نگرفت")

if fails:
    print(f"❌ {len(fails)} تست شکست خورد:")
    for f in fails:
        print("  ", f)
    sys.exit(1)
print("✅ همه‌ی تست‌های واحد پاس شدند")
