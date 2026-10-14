# -*- coding: utf-8 -*-
"""اسکریپت مهاجرت یک‌باره — قبلاً اجرا شده و نتیجه‌اش در کد اعمال است.

این فایل صرفاً برای مستندسازی نحوه‌ی اعمال escape در ~۱۰۰ نقطه نگه داشته شده؛
اجرای دوباره‌اش بی‌خطر است (idempotent) ولی لازم نیست.
"""

"""بازنویسی خودکار: escape کردن مقادیر تحت کنترل کاربر در متن‌های Markdown.

الگوها:
  **{EXPR}**   →  **{api.esc_md(EXPR)}**
  @{EXPR}      →  @{api.esc_md(EXPR)}      (فقط بیرون از بک‌تیک)

موارد پیچیده/دستی گزارش می‌شوند تا خودم بررسی کنم.
"""
import re
import sys
import os

FILES = ["admin.py", "asl_laqab.py", "doss.py", "extras.py", "features.py",
         "games.py", "mafia.py", "main.py", "multiplayer.py",
         "panels.py", "user_panels.py", "locks.py", "questions.py", "user.py",
         "antispam.py", "gifmaker.py"]

# notify.py با parse_mode="HTML" می‌فرستد → به html.escape نیاز دارد نه esc_md
HTML_FILES = {"notify.py"}

BOLD = re.compile(r"\*\*\{([^{}]+)\}\*\*")
AT = re.compile(r"@\{([^{}]+)\}")

# مقادیری که ثابت و امن‌اند (اسم بازی، برچسب ثابت و ...) — ولی escape بی‌ضرر است
SKIP_IF_CONTAINS = ("esc_md", "*", "\\")

# استثناها: عباراتی که عمداً شامل مارک‌داون‌اند
ALLOWLIST = {
    # (file, lineno): دلیل
}


def esc(expr):
    return f"api.esc_md({expr})"


def rewrite_line(line):
    """یک خط را بازنویسی می‌کند؛ (خط_جدید، تعداد_تغییر)."""
    orig = line
    n = 0

    def _bold(m):
        nonlocal n
        expr = m.group(1)
        if "esc_md(" in expr:
            return m.group(0)
        n += 1
        return "**{" + esc(expr) + "}**"

    line = BOLD.sub(_bold, line)

    def _at(m):
        nonlocal n
        expr = m.group(1)
        if "esc_md(" in expr:
            return m.group(0)
        n += 1
        return "@{" + esc(expr) + "}"

    # @{...} فقط اگر داخل بک‌تیک نباشد
    parts = line.split("`")
    for i in range(0, len(parts), 2):   # بیرون از بک‌تیک
        parts[i] = AT.sub(_at, parts[i])
    line = "`".join(parts)

    return line, n


def main(apply=False):
    total = 0
    for path in FILES:
        if not os.path.exists(path):
            continue
        src = open(path, encoding="utf-8").read()
        lines = src.split("\n")
        out = []
        changed = 0
        for i, ln in enumerate(lines, 1):
            new, n = rewrite_line(ln)
            if n:
                changed += n
                if (path, i) not in ALLOWLIST:
                    out.append(new)
                else:
                    out.append(ln)
            else:
                out.append(ln)
        if changed:
            print(f"{path}: {changed} جای escape شد")
            total += changed
            if apply:
                open(path, "w", encoding="utf-8").write("\n".join(out))
    print(f"\nجمع: {total}")
    if not apply:
        print("(حالت آزمایشی — برای اعمال: --apply)")


if __name__ == "__main__":
    main(apply="--apply" in sys.argv)
