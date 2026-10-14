# -*- coding: utf-8 -*-
"""اسکریپت مهاجرت یک‌باره — قبلاً اجرا شده و نتیجه‌اش در کد اعمال است.

این فایل صرفاً برای مستندسازی نحوه‌ی اعمال escape در ~۱۰۰ نقطه نگه داشته شده؛
اجرای دوباره‌اش بی‌خطر است (idempotent) ولی لازم نیست.
"""

"""مرحله ۲: نام‌های کاربر که *بدون* بولد داخل متن می‌آیند را هم escape می‌کند.

محافظت‌ها:
  * خطوطی که callback_data / url / href / کد دلخواه می‌سازند دست‌نخورده می‌مانند
  * داخل بک‌تیک‌ها (code span) دست‌کاری نمی‌شود
"""
import re
import sys
import os

FILES = ["admin.py", "asl_laqab.py", "doss.py", "extras.py", "features.py",
         "games.py", "mafia.py", "main.py", "multiplayer.py",
         "panels.py", "user_panels.py", "locks.py", "user.py", "antispam.py"]

# نام‌هایی که همیشه داده‌ی کاربرند
NAMES = [
    "user_name", "fname", "uname", "tname", "display_name", "target_name",
    "member_name", "next_performer_name", "performer_name", "opp_name",
    "turn_name", "p1_name", "p2_name", "wname", "victim_name", "target_n",
    "user_display", "new_name", "old_name", "inviter_name", "top_name",
    "today_top_name", "best_day_name", "chat_title", "group_name",
]
# عبارات دقیق (با پرانتز/براکت)
NAME_EXPRS = [
    r"u_name\([^()]*\)", r"u\['name'\]", r"p\['name'\]", r"opp\['name'\]",
    r"victim\['name'\]", r"target\['name'\]", r"game\['names'\]\[[^\]]*\]",
    r"profiles\[[^\]]*\]\[[^\]]*\]",
]

WINDOW = r"(?:%s)" % "|".join(
    [re.escape(n) for n in NAMES] + NAME_EXPRS)

# الگوی کلی: {EXPR} که EXPR دقیقاً یکی از نام‌های بالا (یا با فاصله) است
NAMEPAT = re.compile(r"\{(" + WINDOW + r")\}")

# خطوطی که ساختار دکمه/لینک/کوئری می‌سازند → دست نزن
GUARD = re.compile(
    r"callback_data|url=|href=|f\"(?:user|ug|anon|tag|lb|rank|game|mode|panel|"
    r"mafia|mp|gif|todd|doss|asl|quiz|poll|gj|cp|start|help|locked|wl|bw|"
    r"locks|words|users|note|sleep|night|stats|adm|bc|fj|grp|custom|inv|"
    r"wr|report|bug)\b|telegram\.me|t\.me|tg://|ble\.ir|\?id=|\bid=\{|"
    r"add_game_win|markup|kb\(|btn\("
)


def rewrite(text):
    """escape کردن نام‌های برهنه، بیرون از بازه‌ی بک‌تیک."""
    parts = text.split("`")
    n = 0
    for i in range(0, len(parts), 2):

        def _sub(m):
            nonlocal n
            n += 1
            return "{api.esc_md(" + m.group(1) + ")}"

        parts[i] = NAMEPAT.sub(_sub, parts[i])
    return "`".join(parts), n


def main(apply=False):
    total = 0
    for path in FILES:
        if not os.path.exists(path):
            continue
        lines = open(path, encoding="utf-8").read().split("\n")
        out = []
        for i, ln in enumerate(lines, 1):
            if GUARD.search(ln):
                out.append(ln)
                continue
            new, n = rewrite(ln)
            if n:
                total += n
                if apply:
                    print(f"{path}:{i}: {ln.strip()[:130]}")
                    print(f"    →  {new.strip()[:130]}")
                out.append(new)
            else:
                out.append(ln)
        if apply:
            open(path, "w", encoding="utf-8").write("\n".join(out))
    print(f"\nجمع تغییرات: {total}")
    if not apply:
        main(apply=True) if "--preview" in sys.argv else None
        print("(برای اعمال: --apply)")


if __name__ == "__main__":
    if "--preview" in sys.argv:
        # فقط پیش‌نمایش بدون نوشتن
        for path in FILES:
            if not os.path.exists(path):
                continue
            lines = open(path, encoding="utf-8").read().split("\n")
            for i, ln in enumerate(lines, 1):
                if GUARD.search(ln):
                    continue
                new, n = rewrite(ln)
                if n:
                    print(f"--- {path}:{i}")
                    print("  -", ln.strip()[:150])
                    print("  +", new.strip()[:150])
    else:
        main(apply="--apply" in sys.argv)
