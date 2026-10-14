# -*- coding: utf-8 -*-
import time
import api
import storage
from storage import get, set_
import features
import games
import extras
import multiplayer

EDIT_DELAY = 0.3


def kb(rows):
    return {"inline_keyboard": [r for r in rows if r]}


def btn(text, data=None, url=None):
    if url:
        return {"text": text, "url": url}
    return {"text": text, "callback_data": data}


def _edit(chat_id, msg_id, text, markup=None):
    try:
        time.sleep(EDIT_DELAY)
        return api.edit_message(chat_id, msg_id, text, markup=markup, parse_mode="Markdown")
    except Exception as e:
        print(f"[edit] {e}")
        return None


# ============================================================
# پنل کاربر (فقط تو پیوی)
# ============================================================
def user_main_panel(chat_id, user_id):
    rows = [
        [btn("🎮 بازی‌ها", "user:entertainment"),
         btn("🎬 گیف ساز", "gif:start")],
        [btn("🧠 آزمون", "user:quiz"),
         btn("🎁 قرعه‌کشی", "user:lottery")],
        [btn("⭐ امتیاز من", "user:myxp"),
         btn("🏆 تاپ ۱۰", "user:top")],
        [btn("📅 روزانه", "user:rank_daily"),
         btn("📆 هفتگی", "user:rank_weekly")],
        [btn("🗓 ماهانه", "user:rank_monthly")],
        [btn("🔗 دعوت‌ها", "user:invites"),
         btn("📜 قوانین", "user:rules")],
        [btn("🆔 اطلاعات من", "user:id"),
         btn("🐛 گزارش باگ", "user:bug")],
        [btn("➕ افزودن به گروه", "ug:panel")],
        [btn("📖 راهنما", "user:help"),
         btn("❌ بستن", "user:close")],
    ]

    text = (
        "👋 سلام! خوش اومدی\n\n"
        "اینجا می‌تونی بازی کنی، امتیاز بگیری و با بقیه رقابت کنی.\n\n"
        "یکی از گزینه‌های زیر رو انتخاب کن 👇"
    )
    return text, kb(rows)


# ============================================================
# پنل بازی‌ها
# ============================================================
def user_entertainment_panel(chat_id):
    rows = [
        [btn("🎯 حدس عدد", "game:guess"), btn("💭 حدس کلمه", "game:word")],
        [btn("🔤 حروف بهم ریخته", "game:scramble"), btn("🪨 سنگ کاغذ قیچی", "game:rps")],
        [btn("🎮 دوز", "game:doss"), btn("🎯 جرئت یا حقیقت", "game:todd")],
        [btn("😂 جوک", "game:joke"), btn("🎭 مافیا", "game:mafia")],
        [btn("🎲 تاس", "game:dice"), btn("🪙 شیر یا خط", "game:coin")],
        [btn("🏆 لیدربرد", "user:leaderboards"), btn("📖 راهنما", "user:ent_help")],
        [btn("🔙 برگشت", "user:main")],
    ]

    text = (
        "🎮 بازی‌ها\n\n"
        "هر بازی سه حالت داره:\n"
        "🤖 با ربات\n"
        "👤 با یه دوست\n"
        "🎭 ناشناس\n\n"
        "کدوم رو می‌خوای؟ 👇"
    )
    return text, kb(rows)


# ============================================================
# منوی حالت‌ها
# ============================================================
def mode_menu(chat_id, game_key):
    info = {
        "guess":    ("🎯", "حدس عدد", "عددی بین ۱ تا ۱۰۰ رو حدس بزن", ["bot", "friend", "anon"]),
        "word":     ("💭", "حدس کلمه", "کلمه‌ی مخفی رو پیدا کن", ["bot", "friend", "anon"]),
        "scramble": ("🔤", "حروف بهم ریخته", "حروف رو مرتب کن", ["bot", "friend", "anon"]),
        "rps":      ("🪨", "سنگ کاغذ قیچی", "با حریف مسابقه بده", ["bot", "friend", "anon"]),
        "doss":     ("🎮", "دوز", "بازی استراتژیک سه‌تایی", ["bot", "friend", "anon"]),
        "joke":     ("😂", "جوک", "یه جوک بامزه", ["bot"]),
        "todd":     ("🎯", "جرئت یا حقیقت", "بازی با رأی‌گیری", ["bot", "friend", "anon", "rounds"]),
        "mafia":    ("🎭", "مافیا", "بازی گروهی هیجانی", ["group", "help"]),
        "dice":     ("🎲", "تاس", "شانست رو امتحان کن", ["bot", "friend", "anon"]),
        "coin":     ("🪙", "شیر یا خط", "شیر یا خط؟", ["bot", "friend", "anon"]),
    }

    data = info.get(game_key)
    if not data:
        return "بازی پیدا نشد.", kb([[btn("🔙 برگشت", "user:entertainment")]])

    emoji, title, desc, modes = data
    settings = get("settings", chat_id) or {}
    rounds = settings.get("todd_rounds", 3) if game_key == "todd" else None

    rows = []
    if "group" in modes:
        rows.append([btn("👥 با اعضای گروه", f"mode:{game_key}:group")])

    if "bot" in modes:
        label = "🤖 با ربات"
        if rounds:
            label += f" ({rounds} راند)"
        rows.append([btn(label, f"mode:{game_key}:bot")])

    if "friend" in modes:
        label = "👤 با یه دوست"
        if rounds:
            label += f" ({rounds} راند)"
        rows.append([btn(label, f"mode:{game_key}:friend")])

    if "anon" in modes:
        label = "🎭 ناشناس"
        if rounds:
            label += f" ({rounds} راند)"
        rows.append([btn(label, f"mode:{game_key}:anon")])

    if "rounds" in modes:
        rows.append([btn(f"⚙️ تعداد راند ({rounds or 3})", f"mode:{game_key}:rounds")])

    if "help" in modes:
        rows.append([btn("📖 راهنمای مافیا", "mode:mafia:help")])

    rows.append([btn("🔙 برگشت", "user:entertainment")])

    text = f"{emoji} {title}\n\n{desc}\n\nحالت بازی رو انتخاب کن 👇"
    return text, kb(rows)


# ============================================================
# لیدربرد
# ============================================================
def user_leaderboards_panel(chat_id):
    rows = [
        [btn("🎯 حدس عدد", "lb:guess"), btn("💭 حدس کلمه", "lb:word")],
        [btn("🔤 حروف بهم ریخته", "lb:scramble"), btn("🪨 سنگ کاغذ قیچی", "lb:rps")],
        [btn("🎮 دوز", "lb:doss"), btn("🧠 آزمون", "lb:quiz")],
        [btn("😂 جوک", "lb:joke")],
        [btn("🏆 همه بازی‌ها", "lb:all")],
        [btn("📅 روزانه", "rank:daily"), btn("📆 هفتگی", "rank:weekly")],
        [btn("🗓 ماهانه", "rank:monthly")],
        [btn("🔙 برگشت", "user:main")],
    ]
    return "🏆 لیدربردها\n\nکدوم رو ببینی؟", kb(rows)


# ============================================================
# پردازش callback
# ============================================================
def handle_user_callback(cb, cb_id, data, chat_id, msg_id, user):
    user_id = user["id"]
    first_name = user.get("first_name", "کاربر")

    if data == "user:main":
        text, markup = user_main_panel(chat_id, user_id)
        _edit(chat_id, msg_id, text, markup)
        api.answer_callback(cb_id, "")
        return

    if data == "user:close":
        api.delete(chat_id, msg_id)
        api.answer_callback(cb_id, "بسته شد")
        return

    if data == "user:entertainment":
        text, markup = user_entertainment_panel(chat_id)
        _edit(chat_id, msg_id, text, markup)
        api.answer_callback(cb_id, "")
        return

    if data == "user:leaderboards":
        text, markup = user_leaderboards_panel(chat_id)
        _edit(chat_id, msg_id, text, markup)
        api.answer_callback(cb_id, "")
        return

    # ============ گروه‌های کاربر ============
    if data == "ug:panel":
        import panels
        text, markup = panels.user_groups_panel(user_id)
        _edit(chat_id, msg_id, text, markup)
        api.answer_callback(cb_id, "")
        return

    if data.startswith("ug:info:"):
        try:
            gid = int(data.split(":")[2])
        except Exception:
            gid = 0
        import panels
        text, markup = panels.user_group_info_panel(chat_id, gid)
        _edit(chat_id, msg_id, text, markup)
        api.answer_callback(cb_id, "")
        return

    if data == "ug:how":
        api.answer_callback(cb_id,
            "روی منوی ربات، گزینه «افزودن به گروه» رو بزن و گروه رو انتخاب کن.",
            alert=True)
        return

    if data.startswith("game:"):
        game_key = data.split(":")[1]
        text, markup = mode_menu(chat_id, game_key)
        _edit(chat_id, msg_id, text, markup)
        api.answer_callback(cb_id, "")
        return

    if data.startswith("mode:") and data.endswith(":rounds"):
        game_key = data.split(":")[1]
        if game_key == "todd":
            settings = get("settings", chat_id) or {}
            cur = settings.get("todd_rounds", 3)

            rows = [
                [btn(f"{'✅ ' if cur == 3 else ''}۳ راند", "todd:setrounds:3")],
                [btn(f"{'✅ ' if cur == 5 else ''}۵ راند", "todd:setrounds:5")],
                [btn(f"{'✅ ' if cur == 7 else ''}۷ راند", "todd:setrounds:7")],
                [btn(f"{'✅ ' if cur == 10 else ''}۱۰ راند", "todd:setrounds:10")],
                [btn("🔙 برگشت", "game:todd")],
            ]
            _edit(chat_id, msg_id,
                  f"⚙️ تعداد راند\n\nالان روی {cur} رانده.\nچند راند باشه؟",
                  kb(rows))
            api.answer_callback(cb_id, "")
            return

    if data.startswith("todd:setrounds:"):
        rounds = int(data.split(":")[2])
        settings = get("settings", chat_id) or {}
        settings["todd_rounds"] = rounds
        set_("settings", chat_id, settings)
        text, markup = mode_menu(chat_id, "todd")
        _edit(chat_id, msg_id, text, markup)
        api.answer_callback(cb_id, f"✅ {rounds} راند")
        return

    if data.startswith("mode:"):
        parts = data.split(":")
        if len(parts) < 3:
            api.answer_callback(cb_id, "❓")
            return
        game_key = parts[1]
        mode = parts[2]

        if game_key == "mafia":
            if mode == "group":
                games.cmd_mafia_start(chat_id, user_id, first_name)
                api.answer_callback(cb_id, "🎭")
                api.delete(chat_id, msg_id)
                return
            elif mode == "help":
                txt = (
                    "📖 راهنمای مافیا\n\n"
                    "🎭 نقش‌ها:\n"
                    "👑 پدرخوانده — رهبر مافیا\n"
                    "🔫 مافیا — عضو تیم\n"
                    "💉 دکتر — نجات‌دهنده\n"
                    "🕵️ کارآگاه — استعلام\n"
                    "🎯 تک‌تیرانداز — یه بار تیر\n"
                    "👤 شهروند — رأی‌دهنده\n\n"
                    "🎬 مراحل:\n"
                    "۱. لابی بساز (۵+ نفر)\n"
                    "۲. نقش‌ها به پیوی میاد\n"
                    "۳. شب: کشتن، نجات، استعلام\n"
                    "۴. روز: رأی‌گیری\n"
                    "۵. تا یکی از تیم‌ها ببره"
                )
                _edit(chat_id, msg_id, txt, kb([[btn("🔙 برگشت", "game:mafia")]]))
                api.answer_callback(cb_id, "")
                return

        if mode == "bot":
            if game_key == "guess":
                games.cmd_guess(chat_id)
            elif game_key == "word":
                games.cmd_word(chat_id)
            elif game_key == "scramble":
                games.cmd_scramble(chat_id)
            elif game_key == "rps":
                games.cmd_rps(chat_id)
            elif game_key == "doss":
                import doss
                doss.start_with_bot(chat_id, user_id, first_name)
            elif game_key == "todd":
                games.cmd_tod_panel(chat_id, user_id, first_name, "bot")
            elif game_key == "joke":
                games.cmd_joke(chat_id, user_id, first_name, msg_id)
            elif game_key == "dice":
                games.cmd_dice(chat_id, msg_id, first_name)
            elif game_key == "coin":
                games.cmd_coin(chat_id, msg_id, first_name)
            else:
                api.answer_callback(cb_id, "❓")
                return
            api.answer_callback(cb_id, "▶️ شروع شد")
            try:
                api.delete(chat_id, msg_id)
            except Exception:
                pass
            return

        if mode == "friend":
            if game_key in ("rps", "guess", "word", "scramble", "dice", "coin", "doss", "todd"):
                multiplayer.ask_pick_target(chat_id, user_id, game_key, msg_id)
                api.answer_callback(cb_id, "روی پیام دوستت ریپلای کن")
                try:
                    api.delete(chat_id, msg_id)
                except Exception:
                    pass
                return
            else:
                api.answer_callback(cb_id, "این حالت نیست", alert=True)
                return

        if mode == "anon":
            if game_key == "doss":
                import doss
                result = doss.add_to_queue(user_id, first_name, chat_id)
            else:
                result = multiplayer.add_to_queue(game_key, user_id, first_name, chat_id)

            if result == "already":
                api.answer_callback(cb_id, "قبلاً تو صفی", alert=True)
                return
            elif result == "matched":
                api.answer_callback(cb_id, "🎉 حریف پیدا شد، برو پیوی", alert=True)
                try:
                    api.delete(chat_id, msg_id)
                except Exception:
                    pass
                return
            else:
                _edit(chat_id, msg_id,
                      f"🎭 دنبال حریف می‌گردیم...\n\n"
                      f"👤 تو: {first_name}\n"
                      f"⏳ وقتی یکی بیاد خبرت می‌کنیم.",
                      kb([[btn("❌ لغو", f"anon_cancel:{game_key}")]]))
                api.answer_callback(cb_id, "⏳ صبر کن")
                return

    if data.startswith("anon_cancel:"):
        game_key = data.split(":")[1]
        if game_key == "doss":
            import doss
            doss.remove_from_queue(user_id)
        else:
            multiplayer.remove_from_queue(game_key, user_id)
        text, markup = user_entertainment_panel(chat_id)
        _edit(chat_id, msg_id, text, markup)
        api.answer_callback(cb_id, "لغو شد")
        return

    if data == "user:quiz":
        ok, msg_txt = extras.start_quiz(chat_id, user_id, first_name)
        if not ok:
            api.answer_callback(cb_id, msg_txt, alert=True)
        else:
            api.answer_callback(cb_id, "شروع شد")
        return

    if data == "user:lottery":
        winners, err = extras.draw_lottery(chat_id, user_id, first_name, 1)
        if err:
            api.answer_callback(cb_id, err, alert=True)
            return
        bot_users = storage.get("bot_users", "list") or {}
        xp_data = get("xp", chat_id) or {}
        name = xp_data.get(winners[0], {}).get("name", "") or bot_users.get(winners[0], {}).get("name", "کاربر")
        api.send(chat_id, f"🎁 برنده: {name}\nتبریک!", parse_mode="Markdown")
        api.answer_callback(cb_id, "🎁")
        return

    if data == "user:rank":
        txt = extras.get_weekly_ranking(chat_id)
        api.send(chat_id, txt, parse_mode="Markdown")
        api.answer_callback(cb_id, "")
        return

    if data == "user:rank_daily":
        games.cmd_ranking_period(chat_id, "daily")
        api.answer_callback(cb_id, "📅")
        return
    if data == "user:rank_weekly":
        games.cmd_ranking_period(chat_id, "weekly")
        api.answer_callback(cb_id, "📆")
        return
    if data == "user:rank_monthly":
        games.cmd_ranking_period(chat_id, "monthly")
        api.answer_callback(cb_id, "🗓")
        return

    if data == "user:invites":
        txt = extras.get_user_invites(chat_id, user_id)
        api.send(chat_id, txt, parse_mode="Markdown")
        api.answer_callback(cb_id, "")
        return

    if data == "user:myxp":
        from xp import get_user
        u = get_user(chat_id, user_id)
        api.send(chat_id,
                 f"⭐ امتیاز تو\n\n"
                 f"XP: {u['xp']}\n"
                 f"سطح: {u['level']}",
                 parse_mode="Markdown")
        api.answer_callback(cb_id, "")
        return

    if data == "user:top":
        from xp import top
        items = top(chat_id, 10)
        if not items:
            api.answer_callback(cb_id, "هنوز کسی امتیاز نگرفته", alert=True)
            return

        txt = "🏆 تاپ ۱۰ گروه\n\n"
        medals = ["🥇", "🥈", "🥉"]
        for i, (uid, u) in enumerate(items, 1):
            m = medals[i - 1] if i <= 3 else f"{i}."
            txt += (f"{m} {api.esc_md(u.get('name', 'کاربر'))} — "
                    f"{u.get('xp', 0)} XP (سطح {u.get('level', 1)})\n")

        api.send(chat_id, txt, parse_mode="Markdown")
        api.answer_callback(cb_id, "")
        return

    if data == "user:top10":
        games.cmd_ranking_period(chat_id, "all")
        api.answer_callback(cb_id, "🏆")
        return

    if data == "user:rules":
        r = get("rules", chat_id) or {}
        txt = r.get("text") or "هنوز قانونی تنظیم نشده"
        api.send(chat_id, f"📜 قوانین گروه\n\n{txt}", parse_mode="Markdown")
        api.answer_callback(cb_id, "")
        return

    # ============================================================
    # اطلاعات کاربر — فقط آیدی قابل کپی
    # ============================================================
    if data == "user:id":
        from xp import get_user
        udata = get_user(chat_id, user_id)
        warns = (get("warnings", chat_id) or {}).get(str(user_id), 0)
        is_banned = str(user_id) in (get("banned_users", chat_id) or {})
        is_muted = str(user_id) in (get("muted", chat_id) or {})
        try:
            import panels
            txt, markup = panels.user_info_panel(
                chat_id, user, udata, warns, is_banned, is_muted
            )
            api.send(chat_id, txt, parse_mode="HTML", reply_to=0, markup=markup)
            api.answer_callback(cb_id, "اطلاعات فرستاده شد")
        except Exception as e:
            print(f"[user:id] {e}")
            api.answer_callback(cb_id, f"آیدی تو: {user_id}", alert=True)
        return

    if data == "user:bug":
        api.answer_callback(cb_id, "متن باگ رو بفرست", alert=True)
        st = get("settings", chat_id) or {}
        st["wait_bug_report"] = user_id
        set_("settings", chat_id, st)
        api.send(chat_id,
                 "🐛 گزارش باگ\n\n"
                 "مشکل یا باگ رو کامل توضیح بده.",
                 parse_mode="Markdown")
        return

    if data == "user:help":
        txt = (
            "📖 راهنمای کاربر\n\n"
            "🎮 سرگرمی — بازی کن\n"
            "🧠 آزمون — کوییز\n"
            "🎁 قرعه‌کشی — شانس\n"
            "⭐ امتیاز من — XP\n"
            "🏆 تاپ — برترین‌ها\n"
            "📅 هفتگی — رتبه هفتگی\n"
            "🔗 دعوت‌ها — لینک تو\n"
            "🆔 اطلاعات من — پروفایل\n\n"
            "🎬 برای گیف روی عکس یا گیف ریپلای کن و بزن گیف."
        )
        api.send(chat_id, txt, parse_mode="Markdown")
        api.answer_callback(cb_id, "")
        return

    if data == "user:ent_help":
        txt = (
            "📖 راهنمای بازی‌ها\n\n"
            "هر بازی سه حالت داره:\n\n"
            "🤖 با ربات — مستقیم شروع می‌شه\n"
            "👤 با دوست — روی پیامش ریپلای کن\n"
            "🎭 ناشناس — می‌ری تو صف\n\n"
            "🏆 هر برد ۱۵ امتیاز داره."
        )
        api.send(chat_id, txt, parse_mode="Markdown")
        api.answer_callback(cb_id, "")
        return

    api.answer_callback(cb_id, "❓")