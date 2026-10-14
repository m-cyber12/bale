# -*- coding: utf-8 -*-
"""بازسازی main.py: گاردهای KeyError + escape داده‌ی کاربر + سیم‌کشی کامل هوش مصنوعی.

این اسکریپت idempotent است: هر تغییر فقط اگر دقیقاً یک‌بار پیدا شود اعمال می‌گردد
و در انتها با «نوشتن اتمیک» ذخیره می‌شود (اگر جایی پیدا نشد، فایل اصلاً نوشته نمی‌شود).

اجرا:  python3 tools/rebuild_main.py
"""
import io
import os
import sys

P = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 "main.py")
s = io.open(P, encoding="utf-8").read()
log = []


def rep(old, new, label, count=1):
    global s
    n = s.count(old)
    if n < count:
        log.append(("❌", label, f"پیدا نشد ({n})"))
        return False
    s = s.replace(old, new, count)
    log.append(("✅", label, ""))
    return True


# ============================================================
# ۱) گاردهای KeyError (طبق گزارش دیباگ)
# ============================================================
rep('''            msg = cb.get("message", {})
            chat_id = msg["chat"]["id"]
            msg_id = msg.get("message_id")
            user_id = cb["from"]["id"]''',
    '''            msg = cb.get("message", {}) or {}
            chat_id = (msg.get("chat") or {}).get("id")
            msg_id = msg.get("message_id")
            user_id = (cb.get("from") or {}).get("id")
            if not chat_id or not user_id:
                print("[callback] skip: chat_id/user_id ندارد")
                return''',
    "گارد callback")

rep('''    chat_type = chat["type"]
    user = m["from"]
    user_id = user["id"]
    user_name = admin.u_name(user)
    raw_text = (m.get("text") or "").strip()
    text = normalize(raw_text)
    msg_id = m["message_id"]''',
    '''    chat_type = chat.get("type", "private")
    user = m["from"]
    user_id = user.get("id")
    if not user_id:
        return
    user_name = admin.u_name(user)
    raw_text = (m.get("text") or "").strip()
    text = normalize(raw_text)
    msg_id = m.get("message_id")
    if msg_id is None:
        print("[handle] skip: message_id ندارد")
        return''',
    "گارد message")

# ============================================================
# ۲) escape داده‌ی کاربر
# ============================================================
pairs = [
    ('f"🎯 حقیقت برای {first_name}\\n\\n"',
     'f"🎯 حقیقت برای {api.esc_md(first_name)}\\n\\n"', "حقیقت"),
    ('f"🔥 جرئت برای {first_name}\\n\\n"',
     'f"🔥 جرئت برای {api.esc_md(first_name)}\\n\\n"', "جرئت"),
    ("f\"🎯 حقیقت برای <a href='tg://user?id={target_id}'>{target_name}</a>\\n\\n\"",
     "f\"🎯 حقیقت برای <a href='tg://user?id={target_id}'>"
     "{api.esc_html(target_name)}</a>\\n\\n\"", "حقیقت HTML"),
    ("f\"🔥 جرئت برای <a href='tg://user?id={target_id}'>{target_name}</a>\\n\\n\"",
     "f\"🔥 جرئت برای <a href='tg://user?id={target_id}'>"
     "{api.esc_html(target_name)}</a>\\n\\n\"", "جرئت HTML"),
    ('f"📩 پاسخ مدیریت:\\n\\n{raw_text}"',
     'f"📩 پاسخ مدیریت:\\n\\n{api.esc_md(raw_text)}"', "پاسخ مدیریت (پیوی)"),
    ('f"📩 پاسخ مدیریت:\\n\\n{reply_text}"',
     'f"📩 پاسخ مدیریت:\\n\\n{api.esc_md(reply_text)}"', "پاسخ مدیریت (دستور)"),
    ('f"اسم: {name}\\n\\n"', 'f"اسم: {api.esc_md(name)}\\n\\n"', "یادداشت (اسم)"),
    ('f"✅ یادداشت «{name}» ذخیره شد.",',
     'f"✅ یادداشت «{api.esc_md(name)}» ذخیره شد.",', "یادداشت ذخیره"),
    ('f"✅ یادداشت {name} ذخیره شد.",',
     'f"✅ یادداشت {api.esc_md(name)} ذخیره شد.",', "یادداشت ذخیره (auto)"),
    ('f"🏷 لقب ثبت شد: {raw_text}",',
     'f"🏷 لقب ثبت شد: {api.esc_md(raw_text)}",', "لقب"),
    ('f"✅ اسم: {name}\\n\\nحالا متن پاسخ رو بفرست.",',
     'f"✅ اسم: {api.esc_md(name)}\\n\\nحالا متن پاسخ رو بفرست.",', "دستور سفارشی (اسم)"),
    ('f"✅ دستور /{name} ثبت شد.",',
     'f"✅ دستور /{api.esc_md(name)} ثبت شد.",', "دستور سفارشی ثبت"),
    ('f"گروه قفل است.\\n{user_name} جان، فقط ادمین‌ها پیام می‌دن.",',
     'f"گروه قفل است.\\n{api.esc_md(user_name)} جان، فقط ادمین‌ها پیام می‌دن.",',
     "قفل گروه"),
    ('f"👢 {user_name} به دلیل {threshold} بار نقض قوانین ({fa}) اخراج شد.",',
     'f"👢 {api.esc_md(user_name)} به دلیل {threshold} بار نقض قوانین ({fa}) اخراج شد.",',
     "اخراج (قفل)"),
    ('f"{user_name} جان، این پیام ممنوعه.\\n"',
     'f"{api.esc_md(user_name)} جان، این پیام ممنوعه.\\n"', "پیام ممنوعه"),
    ("f\"{user_name} جان، از {cfg.get('start','23:00')} \"",
     "f\"{api.esc_md(user_name)} جان، از {cfg.get('start','23:00')} \"", "حالت شب"),
    ('f"{user_name} جان، الان گروه خوابه.",',
     'f"{api.esc_md(user_name)} جان، الان گروه خوابه.",', "حالت خواب"),
    ('f"{user_name} جان، {total_sec} ثانیه صبر کن.\\n"',
     'f"{api.esc_md(user_name)} جان، {total_sec} ثانیه صبر کن.\\n"', "حالت آهسته"),
    ('f"⚠️ {user_name} فحش نده. ({cur}/{max_warns})",',
     'f"⚠️ {api.esc_md(user_name)} فحش نده. ({cur}/{max_warns})",', "فحش (هشدار)"),
    ('f"{user_name} جان، این کلمه در گروه ممنوعه.\\n"',
     'f"{api.esc_md(user_name)} جان، این کلمه در گروه ممنوعه.\\n"', "کلمه ممنوعه"),
    ('f"🎉 تبریک {user_name}!\\nسطح {leveled}",',
     'f"🎉 تبریک {api.esc_md(user_name)}!\\nسطح {leveled}",', "تبریک سطح"),
]
for old, new, label in pairs:
    rep(old, new, "escape: " + label)

for label, emoji, tail in [
    ("اخراج", "👢", "اخراج شد."),
    ("بن", "🚫", "بن شد."),
    ("سکوت ۱ساعت", "🔇", "یک ساعت سکوت شد."),
    ("سکوت ۱۰دقیقه", "🔇", "۱۰ دقیقه سکوت شد."),
]:
    rep(f'f"{emoji} {{user_name}} به دلیل {{bw_threshold}} بار کلمات ممنوعه {tail}",',
        f'f"{emoji} {{api.esc_md(user_name)}} به دلیل {{bw_threshold}} بار کلمات '
        f'ممنوعه {tail}",', "escape: کلمات ممنوعه " + label)

rep('''            if uname:
                txt += f"• {fname} — @{uname}\\n"''',
    '''            if uname:
                txt += (f"• {api.esc_md(fname)} — "
                        f"@{api.esc_md(uname)}\\n")''', "escape: لیست کاربران")

rep("""api.send(chat_id, f"📜 قوانین:\\n\\n{r.get('text') or 'تنظیم نشده'}", parse_mode="Markdown")""",
    """api.send(chat_id,
                 f"📜 قوانین:\\n\\n{api.esc_md(r.get('text') or 'تنظیم نشده')}",
                 parse_mode="Markdown")""", "escape: قوانین")

rep('''            result_txt += f"• {e}\\n"''',
    '''            result_txt += f"• {api.esc_md(str(e))}\\n"''', "escape: خطاهای همگانی")

# ============================================================
# ۳) سیم‌کشی هوش مصنوعی
# ============================================================
rep("import notify\nfrom config import OWNER_ID",
    "import notify\nimport ai\nimport ai_persona\nimport ai_panel\nimport config\n"
    "from config import OWNER_ID", "import ماژول‌های AI")

rep('''    "tagall": "تگ", "tag_all": "تگ",
}''',
    '''    "tagall": "تگ", "tag_all": "تگ",
    "ai": "هوش‌مصنوعی", "هوش": "هوش‌مصنوعی", "هوش‌مصنوعی": "هوش‌مصنوعی",
    "دستیار": "هوش‌مصنوعی", "دستیارai": "هوش‌مصنوعی",
    "aikey": "کلیدai", "کلیدai": "کلیدai",
    "openrouter": "کلیدai", "کلید ai": "کلیدai",
}''', "ALIASES")

rep('''            if data.startswith("cp:"):''',
    '''            if data.startswith("ai:"):
                ai_panel.handle_callback(cb, cb["id"], data, chat_id, msg_id,
                                         user)
                return

            if data.startswith("cp:"):''', "روتینگ callback هوش مصنوعی")

rep('''    if cmd == "/راهنما":
        api.send(chat_id, HELP, parse_mode="Markdown")
        return
''',
    '''    if cmd == "/راهنما":
        api.send(chat_id, HELP, parse_mode="Markdown")
        return

    # ============================================
    # 🧠 هوش مصنوعی — دستیار مدیریت گروه
    # ============================================
    if cmd == "/هوش‌مصنوعی":
        if not is_user_admin:
            api.send(chat_id, "🧠 این بخش فقط برای ادمین‌های گروهه.", reply_to=0)
            return
        ai_panel.cmd_ai_command(chat_id, user_id, user_name, m, args,
                                chat.get("title", ""))
        return

    if cmd == "/کلیدai":
        if user_id != OWNER_ID:
            api.send(chat_id, "👑 فقط مالک ربات.", reply_to=0)
            return
        if not args or not args[0].startswith("sk-"):
            api.send(chat_id,
                     "🔑 فرمت درست: `/کلیدai sk-or-v1-...`\\n\\n"
                     "کلید را از openrouter.ai/keys بگیر.\\n"
                     "می‌تونی از پنل هم بفرستی: `هوش مصنوعی` → 🔑",
                     parse_mode="Markdown", reply_to=0)
            return
        key = args[0]
        ai.set_api_key(key)
        ai.reset_runtime()
        st = ai.status()
        try:
            api.delete(chat_id, msg_id)
        except Exception:
            pass
        api.send(chat_id,
                 f"✅ کلید ذخیره شد.\\n🧠 مدل‌های رایگان: `{st['models_total']}`\\n"
                 f"برای تست بزن: `/هوش‌مصنوعی تست`",
                 parse_mode="Markdown", reply_to=0)
        return
''', "دستورات /هوش‌مصنوعی و /کلیدai")

rep('''        if g_settings.get("wait_bug_reply") == user_id:''',
    '''        # 🔑 انتظار کلید OpenRouter
        if g_settings.get("wait_ai_key") == user_id:
            if ai_panel.handle_wait_key(chat_id, user_id, raw_text):
                try:
                    api.delete(chat_id, msg_id)
                except Exception as e:
                    print(f"[ai:del-key-msg] {e}")
                return

        if g_settings.get("wait_bug_reply") == user_id:''', "هوک انتظار کلید")

rep('''    except Exception as e:
        print(f"[xp] {e}")

    if not cmd:
        return''',
    '''    except Exception as e:
        print(f"[xp] {e}")

    # 🧠 ثبت فعالیت در پرونده‌ی شخصیت (تاریخ عضویت/درجه/لحن)
    try:
        ai_persona.note_message(chat_id, user_id, user_name)
    except Exception as e:
        print(f"[persona:msg] {e}")

    if not cmd:
        return''', "note_message")

rep('''                    count, threshold, should_kick = locks.handle_lock_violation(
                        chat_id, user_id, blocked
                    )
                    fa = locks.LOCKS.get(blocked, {}).get("fa", blocked)''',
    '''                    count, threshold, should_kick = locks.handle_lock_violation(
                        chat_id, user_id, blocked
                    )
                    fa = locks.LOCKS.get(blocked, {}).get("fa", blocked)
                    try:
                        ai_persona.note_violation(chat_id, user_id, "lock",
                                                  user_name)
                    except Exception as e:
                        print(f"[persona:lock] {e}")''', "note_violation قفل")

rep('''                    warns[str(user_id)] = cur
                    storage.set_("warnings", chat_id, warns)
                    if cur >= max_warns:
                        api.send(chat_id,
                            f"{user_name} به دلیل فحش مکرر بن شد.",
                            parse_mode="Markdown", reply_to=0)''',
    '''                    warns[str(user_id)] = cur
                    storage.set_("warnings", chat_id, warns)
                    try:
                        ai_persona.note_violation(chat_id, user_id, "badword",
                                                  user_name)
                    except Exception as e:
                        print(f"[persona:badword] {e}")
                    if cur >= max_warns:
                        _fb_bad = (f"🚫 {api.esc_md(user_name)} به دلیل فحش "
                                   f"مکرر بن شد.")
                        try:
                            if ai_panel.feature_on(chat_id, "announce"):
                                ai_persona.announce_punish(
                                    chat_id, "ban", user_id, user_name,
                                    by_name="سیستم ضدفحش", reason="فحش مکرر",
                                    chat_title=chat.get("title", ""),
                                    count=max_warns)
                            else:
                                api.send(chat_id, _fb_bad,
                                         parse_mode="Markdown", reply_to=0)
                        except Exception as e:
                            print(f"[persona:announce-ban] {e}")
                            api.send(chat_id, _fb_bad,
                                     parse_mode="Markdown", reply_to=0)''',
    "note_violation + پیام فحش مکرر")

rep('''                bw_warns[uid] = bw_warns.get(uid, 0) + 1
                count = bw_warns[uid]''',
    '''                bw_warns[uid] = bw_warns.get(uid, 0) + 1
                count = bw_warns[uid]
                try:
                    ai_persona.note_violation(chat_id, user_id, "banned_word",
                                              user_name)
                except Exception as e:
                    print(f"[persona:bw] {e}")''', "note_violation کلمه ممنوعه")

rep('''                msg_id_w = features.send_welcome(chat_id, admin.u_name(member), chat.get("title", ""))''',
    '''                msg_id_w = features.send_welcome(chat_id, admin.u_name(member),
                                                 chat.get("title", ""),
                                                 member_id=member.get("id"))''',
    "send_welcome با member_id")

rep('''    print("🏆 مدیریت گروه آلفا روشن شد!")
    print("=" * 50)

    storage.load()''',
    '''    print("🏆 مدیریت گروه آلفا روشن شد!")
    print("=" * 50)

    if not config.has_token():
        print(config.token_hint())
        return
    if ai.enabled():
        if ai.api_key():
            print("🧠 موتور هوش مصنوعی: روشن (OpenRouter)")
        else:
            print("🧠 هوش مصنوعی روشن است ولی کلید OpenRouter تنظیم نشده.")
            print("   برای تنظیم: پیوی ربات → پنل → 🧠 هوش مصنوعی → 🔑")

    storage.load()''', "main(): گارد توکن + وضعیت AI")

# ============================================================
# نوشتن اتمیک — فقط اگر همه‌ی موارد اعمال شده باشند
# ============================================================
bad = [e for e in log if e[0] == "❌"]
for ok, label, extra in log:
    print(f"  {ok} {label} {extra}")

if bad:
    print("—" * 50)
    print(f"❌ {len(bad)} مورد پیدا نشد — فایل دست‌نخورده ماند")
    sys.exit(1)

tmp = P + ".tmp"
with io.open(tmp, "w", encoding="utf-8") as f:
    f.write(s)
os.replace(tmp, P)
print("—" * 50)
print("✅ همه‌ی تغییرات main.py اعمال و ذخیره شد")
