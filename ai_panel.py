# -*- coding: utf-8 -*-
"""پنل‌های هوش مصنوعی + پرونده‌ی کاربران.

دو سطح دارد:
  * پنل ربات (مالک/ادمین ربات): کلید API، مدل‌ها، تست، مصرف، کول‌داون‌ها
  * پنل گروه (ادمین گروه): روشن/خاموش‌کردن هر بخش + دیدن پرونده‌ی کاربران
"""
import time

import ai
import ai_persona as persona
import api
import storage
from storage import get, set_

GROUP_SECTION = "ai_group"

GROUP_DEFAULTS = {
    "announce": True,     # پیام‌های اخطار/سکوت/بن با AI نوشته شود
    "assistant": True,    # دستور «هوش مصنوعی ...» فعال باشد
    "welcome": True,      # خوش‌آمدگویی با AI
    "reply": True,        # ریپلای روی پیام ربات → جواب هوش مصنوعی
}


def group_settings(chat_id):
    cfg = dict(GROUP_DEFAULTS)
    try:
        cfg.update(get(GROUP_SECTION, chat_id) or {})
    except Exception:
        pass
    return cfg


def set_group_setting(chat_id, key, value):
    cfg = group_settings(chat_id)
    cfg[key] = value
    try:
        set_(GROUP_SECTION, chat_id, cfg)
    except Exception as e:
        print(f"[ai_panel:save] {e}")
    return cfg


def feature_on(chat_id, key):
    """آیا این قابلیت برای گروه روشن است؟ (هم گروه هم کل ربات)"""
    if not ai.enabled():
        return False
    try:
        return bool(group_settings(chat_id).get(key, True))
    except Exception:
        return True


# ============================================================
# ابزار دکمه
# ============================================================
def btn(text, data=None, url=None):
    if url:
        return {"text": text, "url": url}
    return {"text": text, "callback_data": data}


def kb(rows):
    return {"inline_keyboard": [r for r in rows if r]}


def _edit(chat_id, msg_id, text, markup=None):
    try:
        return api.edit_message(chat_id, msg_id, text, markup=markup,
                                parse_mode="Markdown")
    except Exception as e:
        print(f"[ai_panel:edit] {e}")
        return None


def _on_off(flag):
    return "🟢 روشن" if flag else "🔴 خاموش"


def _fa_num(n):
    return str(n)


# ============================================================
# پنل سطح ربات (مالک)
# ============================================================
def owner_ai_panel():
    st = ai.status()
    cfg = ai.config()

    key_line = "✅ تنظیم شده" if st["key_set"] else "❌ تنظیم نشده"
    lines = [
        "🧠 **موتور هوش مصنوعی**",
        "",
        f"وضعیت: {_on_off(st['enabled'])}",
        f"کلید OpenRouter: {key_line}",
        f"مدل‌های رایگان کشف‌شده: `{st['models_total']}`",
        f"مصرف امروز: `{st['usage_today']}` / `{st['daily_limit']}`",
        f"سقف دقیقه‌ای: `{st['rpm_limit']}`",
        f"درخواست موفق: `{st['stats'].get('ok', 0)}` | "
        f"لیمیت‌خورده: `{st['stats'].get('rate_limited', 0)}`",
    ]
    if st["key_invalid"]:
        lines.append("⚠️ کلید توسط OpenRouter رد شده — دوباره تنظیم کن.")
    last = st["stats"].get("last_error")
    if last:
        lines.append(f"آخرین خطا: `{str(last)[:60]}`")
    if st["cooldowns"]:
        lines.append("")
        lines.append("⏳ مدل‌های در کول‌داون:")
        for m, left in st["cooldowns"][:5]:
            lines.append(f"• `{m}` → {left}s")
    lines.append("")
    lines.append("🔝 مدل‌های برتر به‌ترتیب:")
    for i, m in enumerate(st["top"], 1):
        lines.append(f"{i}. `{m}`")

    rows = [
        [btn(f"⏻ {_on_off(st['enabled'])}", "ai:toggle")],
        [btn("🔑 تنظیم کلید API", "ai:key")],
        [btn("🔄 دریافت لیست مدل‌ها", "ai:refresh")],
        [btn("🧪 تست هوش مصنوعی", "ai:test")],
        [btn("♻️ پاک‌کردن کول‌داون‌ها", "ai:reset")],
        [btn("📊 وضعیت جزئی", "ai:detail")],
        [btn("🗑 حذف کلید", "ai:delkey")],
    ]
    return "\n".join(lines), kb(rows)


def owner_ai_detail_panel():
    st = ai.status()
    chain = ai.model_chain()
    lines = [
        "📊 **جزئیات موتور AI**",
        "",
        "زنجیره‌ی fallback (به‌ترتیب اولویت):",
    ]
    for i, m in enumerate(chain[:12], 1):
        cd = dict(st["cooldowns"]).get(m)
        mark = f" ⏳{cd}s" if cd else ""
        lines.append(f"{i}. `{m}`{mark}")
    if st["dead"]:
        lines.append("")
        lines.append("☠️ حذف‌شده (404):")
        for m in st["dead"][:5]:
            lines.append(f"• `{m}`")
    lines.append("")
    lines.append(f"مدل آخرین موفق: `{st['stats'].get('last_model') or '-'}`")
    lines.append(f"کل درخواست‌ها: `{st['stats'].get('ok', 0) + st['stats'].get('fail', 0)}`")
    return "\n".join(lines), kb([[btn("🔙 برگشت", "ai:main")]])


# ============================================================
# پنل سطح گروه (ادمین گروه)
# ============================================================
def group_ai_panel(chat_id):
    cfg = group_settings(chat_id)
    engine = ai.enabled()
    st = ai.status()

    lines = [
        "🧠 **هوش مصنوعی گروه**",
        "",
        f"موتور ربات: {_on_off(engine)}",
        f"مدل‌های در دسترس: `{st['models_total']}`",
        f"مصرف امروز: `{st['usage_today']}` / `{st['daily_limit']}`",
        "",
        "بخش‌هایی که AI روی آن کار می‌کند:",
        f"• {_on_off(cfg['announce'])} پیام اخطار/سکوت/بن",
        f"• {_on_off(cfg['assistant'])} دستیار مدیریت (`هوش مصنوعی سؤالت`)",
        f"• {_on_off(cfg['welcome'])} خوش‌آمدگویی اعضای جدید",
        f"• {_on_off(cfg['reply'])} جواب به ریپلای روی پیام‌هایم",
        "",
        "اگر AI در دسترس نباشه یا لیمیت بخوره،",
        "ربات همون پاسخ‌های همیشگی خودش رو می‌ده.",
    ]

    rows = [
        [btn(f"📣 پیام تنبیه {_on_off(cfg['announce'])}", "ai:g:announce"),
         btn(f"🤖 دستیار {_on_off(cfg['assistant'])}", "ai:g:assistant")],
        [btn(f"👋 خوش‌آمد {_on_off(cfg['welcome'])}", "ai:g:welcome"),
         btn(f"💬 جواب ریپلای {_on_off(cfg['reply'])}", "ai:g:reply")],
        [btn("👤 پرونده‌ی کاربران", "ai:users:0")],
        [btn("ℹ️ رفتار با هر کاربر چطوره؟", "ai:how")],
        [btn("🔙 برگشت", "panel:main")],
    ]
    return "\n".join(lines), kb(rows)


def group_ai_how_panel(chat_id):
    text = (
        "🧠 **ربات چطور با هر کاربر رفتار می‌کند؟**\n\n"
        "برای هر نفر یک پرونده نگه می‌دارم:\n"
        "• تاریخ عضویت و درجه (تازه‌وارد … ریشه‌سفید گروه)\n"
        "• سطح و امتیاز\n"
        "• تعداد و نوع تخلف‌ها\n"
        "• **لحن** فعلی من با او\n\n"
        "هر تخلف، لحن را یک پله سخت‌تر می‌کند:\n"
        "`مهربان → معمولی → جدی → سخت‌گیر → بی‌گذشت`\n\n"
        "و اگر ۷ روز تخلف نکند، یک پله نرم‌تر می‌شوم.\n\n"
        "پس با یک عضو قدیمی که سابقه‌ی خوبی دارد،\n"
        "رفتارم با یک تازه‌واردِ پرتخلف کاملاً متفاوت است.\n\n"
        "💬 **حرف زدن با من:** روی هر پیامی که در گروه می‌فرستم ریپلای کن\n"
        "و سؤالت را بنویس؛ همان‌جا جواب می‌دهم.\n"
        "ادمین‌ها می‌توانند بنویسند `هوش مصنوعی سؤالت` هم.\n\n"
        "⚠️ من هیچ‌وقت خودم کسی را بن/سکوت نمی‌کنم — تصمیم‌ها با برنامه است."
    )
    return text, kb([[btn("🔙 برگشت", "ai:group")]])


def users_panel(chat_id, page=0):
    """لیست پرونده‌ی کاربران با لحن فعلی."""
    profiles = get(persona.SECTION, chat_id) or {}
    items = sorted(profiles.values(), key=lambda p: (-int(p.get("strikes", 0)),
                                                     -int(p.get("msgs", 0))))
    per_page = 8
    if not items:
        return ("👤 هنوز پرونده‌ای ساخته نشده.\n"
                "به‌محض اینکه کسی پیام بدهد یا تخلفی کند، پرونده‌اش ساخته می‌شود.",
                kb([[btn("🔙 برگشت", "ai:group")]]))

    total = max(1, (len(items) + per_page - 1) // per_page)
    page = max(0, min(page, total - 1))
    chunk = items[page * per_page:(page + 1) * per_page]

    lines = [f"👤 **پرونده‌ها** — {len(items)} کاربر", ""]
    rows = []
    for p in chunk:
        uid = p.get("uid")
        nm = p.get("name") or f"کاربر {uid}"
        tone = persona.effective_tone(chat_id, uid)
        strikes = int(p.get("strikes", 0))
        lines.append(f"• {api.esc_md(str(nm))} — لحن: {persona.TONE_LABELS[tone]}"
                     f" | تخلف: `{strikes}`")
        rows.append([btn(f"👤 {str(nm)[:22]}", f"ai:u:{uid}")])

    nav = []
    if page > 0:
        nav.append(btn("⬅️", f"ai:users:{page-1}"))
    nav.append(btn(f"{page+1}/{total}", "noop"))
    if page < total - 1:
        nav.append(btn("➡️", f"ai:users:{page+1}"))
    rows.append(nav)
    rows.append([btn("🔙 برگشت", "ai:group")])
    return "\n".join(lines), kb(rows)


def user_dossier_panel(chat_id, uid):
    """پرونده‌ی کامل یک کاربر — همان چیزی که AI می‌بیند."""
    info = persona.rank_info(chat_id, uid)
    prof = persona.get_profile(chat_id, uid)
    nm = prof.get("name") or f"کاربر {uid}"

    lines = [
        f"👤 **پرونده‌ی {api.esc_md(str(nm))}**",
        "",
        f"🆔 `{uid}`",
        f"📅 عضویت: `{info['days']}` روز پیش",
        f"🏅 درجه: **{info['rank']}**",
        f"⭐ سطح `{info['level']}` ({info['xp']} XP)",
        f"💬 پیام‌ها: `{info['msgs']}`",
        "",
        f"⚠️ تخلف‌ها: `{info['strikes']}`",
    ]
    if info["violations"]:
        for k, v in sorted(info["violations"].items(), key=lambda x: -x[1])[:6]:
            lines.append(f"   • {persona.violation_text(k)}: `{v}`")
    lines.append("")
    lines.append(f"🎭 لحن فعلی من با این کاربر: **{persona.TONE_LABELS[info['tone']]}**")
    lines.append(f"   _{persona.TONE_BRIEF[info['tone']]}_")
    if info["notes"]:
        lines.append("")
        lines.append("🧠 چیزهایی که یادم مانده:")
        for n in info["notes"][-3:]:
            lines.append(f"• {api.esc_md(str(n)[:80])}")
    if info["last_said"]:
        lines.append("")
        lines.append("💬 آخرین چیزهایی که به او گفتم:")
        for s in info["last_said"][-2:]:
            lines.append(f"• _{api.esc_md(str(s)[:70])}_")

    rows = [
        [btn("🕊 یک پله نرم‌تر", f"ai:relax:{uid}"),
         btn("⚠️ یک پله سخت‌تر", f"ai:harder:{uid}")],
        [btn("♻️ صفر کردن پرونده", f"ai:ureset:{uid}"),
         btn("🗑 حذف کامل", f"ai:udelete:{uid}")],
        [btn("🔄 بروزرسانی", f"ai:u:{uid}")],
        [btn("🔙 برگشت", "ai:users:0")],
    ]
    return "\n".join(lines), kb(rows)


def do_test():
    """تست کوتاه موتور AI."""
    text, model = ai.test_call()
    if not text:
        st = ai.status()
        return (f"❌ مدل جواب نداد.\nدلیل: `{model}`\n"
                f"کلید: {'دارد' if st['key_set'] else 'ندارد'}\n"
                f"اگر لیمیت خورده، چند دقیقه بعد امتحان کن.")
    return f"✅ پاسخ از `{model}`:\n\n{text}"


# ============================================================
# پردازش callback
# ============================================================
BOT_LEVEL = {"toggle", "key", "refresh", "test", "reset", "detail", "delkey"}


def handle_callback(cb, cb_id, data, chat_id, msg_id, user):
    from panels import is_bot_admin      # noqa: WPS433 (import دوری)
    user_id = user["id"]
    parts = data.split(":")
    action = parts[1] if len(parts) > 1 else "main"

    if action in BOT_LEVEL:
        if not is_bot_admin(user_id):
            api.answer_callback(cb_id, "فقط مالک ربات.", alert=True)
            return
        return _handle_owner(cb_id, action, parts, chat_id, msg_id, user)
    return _handle_group(cb_id, action, parts, chat_id, msg_id, user)


def _handle_owner(cb_id, action, parts, chat_id, msg_id, user):
    if action == "toggle":
        ai.set_enabled(not ai.enabled())
        text, markup = owner_ai_panel()
        _edit(chat_id, msg_id, text, markup)
        api.answer_callback(cb_id, "روشن شد" if ai.enabled() else "خاموش شد")
        return

    if action == "key":
        api.answer_callback(cb_id, "کلید را در پیوی بفرست", alert=True)
        api.send(chat_id,
                 "🔑 کلید OpenRouter را همین‌جا بفرست.\n\n"
                 "پیام را بعد از ذخیره پاک می‌کنم.\n"
                 "برای لغو بزن: `لغو`",
                 parse_mode="Markdown", reply_to=0)
        # ⚠️ بخش «global» — چون پیام کلید در پیوی می‌آید و chat_id عوض می‌شود
        settings = get("settings", "global") or {}
        settings["wait_ai_key"] = user["id"]
        set_("settings", "global", settings)
        return

    if action == "refresh":
        api.answer_callback(cb_id, "دارم لیست را می‌گیرم…")
        models = ai.refresh_models(force=True)
        text, markup = owner_ai_panel()
        _edit(chat_id, msg_id, text, markup)
        api.send(chat_id, f"🔄 لیست بروز شد — `{len(models)}` مدل رایگان.",
                 reply_to=0)
        return

    if action == "test":
        api.answer_callback(cb_id, "دارم تست می‌کنم…")
        api.send(chat_id, "🧪 " + do_test(), reply_to=0)
        return

    if action == "reset":
        ai.reset_runtime()
        text, markup = owner_ai_panel()
        _edit(chat_id, msg_id, text, markup)
        api.answer_callback(cb_id, "پاک شد")
        return

    if action == "detail":
        text, markup = owner_ai_detail_panel()
        _edit(chat_id, msg_id, text, markup)
        api.answer_callback(cb_id, "")
        return

    if action == "delkey":
        ai.set_api_key("")
        text, markup = owner_ai_panel()
        _edit(chat_id, msg_id, text, markup)
        api.answer_callback(cb_id, "کلید حذف شد", alert=True)
        return

    api.answer_callback(cb_id, "")


def _handle_group(cb_id, action, parts, chat_id, msg_id, user):
    from admin import is_admin

    # دیدن راهنما برای همه آزاد است
    if action == "how":
        text, markup = group_ai_how_panel(chat_id)
        _edit(chat_id, msg_id, text, markup)
        api.answer_callback(cb_id, "")
        return

    if not is_admin(chat_id, user["id"]):
        api.answer_callback(cb_id, "فقط ادمین‌های گروه.", alert=True)
        return

    if action == "group" or action == "main":
        text, markup = group_ai_panel(chat_id)
        _edit(chat_id, msg_id, text, markup)
        api.answer_callback(cb_id, "")
        return

    if action == "g" and len(parts) >= 3:
        key = parts[2]
        if key in GROUP_DEFAULTS:
            cfg = group_settings(chat_id)
            set_group_setting(chat_id, key, not cfg.get(key, True))
            text, markup = group_ai_panel(chat_id)
            _edit(chat_id, msg_id, text, markup)
            api.answer_callback(cb_id, "تغییر کرد")
            return

    if action == "users":
        page = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
        text, markup = users_panel(chat_id, page)
        _edit(chat_id, msg_id, text, markup)
        api.answer_callback(cb_id, "")
        return

    if action == "u" and len(parts) >= 3:
        uid = parts[2]
        text, markup = user_dossier_panel(chat_id, uid)
        _edit(chat_id, msg_id, text, markup)
        api.answer_callback(cb_id, "")
        return

    if action in ("relax", "harder", "ureset", "udelete") and len(parts) >= 3:
        uid = parts[2]
        if action == "relax":
            persona.note_good(chat_id, uid, relax=True)
            note = "یک پله نرم‌تر شد"
        elif action == "harder":
            persona.note_violation(chat_id, uid, kind="manual", escalate=True)
            note = "یک پله سخت‌تر شد"
        elif action == "ureset":
            persona.reset_user(chat_id, uid)
            note = "پرونده صفر شد"
        else:
            persona.reset_user(chat_id, uid, full=True)
            note = "پرونده حذف شد"
        text, markup = user_dossier_panel(chat_id, uid) if action != "udelete" \
            else users_panel(chat_id, 0)
        _edit(chat_id, msg_id, text, markup)
        api.answer_callback(cb_id, note)
        return

    api.answer_callback(cb_id, "")


# ============================================================
# گرفتن کلید API از پیام خصوصی
# ============================================================
def handle_wait_key(chat_id, user_id, text):
    """True اگر پیام مصرف شد (کلید بود)."""
    settings = get("settings", "global") or {}
    if settings.get("wait_ai_key") != user_id:
        return False

    settings.pop("wait_ai_key", None)
    set_("settings", "global", settings)

    key = (text or "").strip()
    if not key:
        api.send(chat_id, "❌ خالی بود. دوباره از پنل امتحان کن.", reply_to=0)
        return True

    if not key.startswith("sk-"):
        api.send(chat_id,
                 "❌ این کلید معتبر به‌نظر نمی‌رسد. کلید OpenRouter با `sk-or-` "
                 "شروع می‌شود.", parse_mode="Markdown", reply_to=0)
        return True

    ai.set_api_key(key)
    ai.reset_runtime()
    st = ai.status()
    api.send(chat_id,
             "✅ کلید ذخیره شد.\n\n"
             f"مدل‌های رایگان: `{st['models_total']}`\n"
             "برای تست، از پنل «🧪 تست» را بزن.",
             parse_mode="Markdown", reply_to=0)
    return True


# ============================================================
# دستورات
# ============================================================
def cmd_ai_command(chat_id, user_id, user_name, message, args, chat_title=""):
    """دستور «هوش مصنوعی ...» یا «/ai ...»"""
    from admin import is_admin

    question = " ".join(args).strip() if args else ""

    # ریپلای روی پیام کسی + دستور → پرونده‌ی او
    reply = message.get("reply_to_message")
    if not question and reply:
        tid = (reply.get("from") or {}).get("id")
        if tid:
            text, markup = user_dossier_panel(chat_id, str(tid))
            api.send(chat_id, text, parse_mode="Markdown", markup=markup,
                     reply_to=0)
            return True

    if not question:
        api.send(chat_id,
                 "🧠 چی می‌خوای بدونی؟\n"
                 "مثال: `هوش مصنوعی وضعیت گروه چطوره؟`\n"
                 "یا روی پیام یک نفر ریپلای کن و بنویس `هوش مصنوعی` تا "
                 "پرونده‌اش را ببینی.",
                 parse_mode="Markdown", reply_to=0)
        return True

    if not is_admin(chat_id, user_id):
        api.send(chat_id, "فقط ادمین‌های گروه می‌تونن از دستیار بپرسن.",
                 reply_to=0)
        return True

    if not feature_on(chat_id, "assistant"):
        api.send(chat_id,
                 "🤖 دستیار مدیریت برای این گروه خاموشه. "
                 "ادمین‌ها می‌تونن از `هوش مصنوعی` در پنل روشنش کنن.",
                 parse_mode="Markdown", reply_to=0)
        return True

    persona.note_message(chat_id, user_id, user_name)
    persona.answer_question(chat_id, user_id, user_name, question, chat_title)
    return True
