# -*- coding: utf-8 -*-
"""بازی‌های گروهی - آلفا"""
import random
import time
import api
from storage import get, set_, add_game_win, get_game_leaderboard

ACTIVE = {}

WORDS = ["کتاب", "دریا", "خورشید", "ستاره", "کوه", "پرنده", "گل", "برف",
         "آتش", "باد", "ماه", "ابر", "رود", "جنگل", "سنگ", "آسمان",
         "زمین", "شهر", "خانه", "دوست", "مادر", "پدر", "برادر", "خواهر",
         "نان", "آب", "شیر", "عسل", "ماهی", "گربه", "سگ", "اسب", "شیر"]

JOKES = [
    "به یکی گفتن چرا انقدر خوشحالی؟ گفت چون مرغ همسایه غازه! 🐔",
    "یه روز پنگوئن به مامانش گفت: مامانم چرا من سرده؟ مامانش گفت: خفه شو بچه‌ی یخچالی! 🐧",
    "به یکی گفتن چرا اینقدر آروم حرف می‌زنی؟ گفت چون دندونام درد می‌کنه! 😁",
    "مردی به دوستش گفت: من هر روز صبح ۵ کیلو می‌دوم! دوستش گفت: دروغ میگی. گفت: نه، صبح‌ها موتور می‌دوم و شب‌ها دروغ‌های صبحم رو می‌گم! 🏃",
    "یه مرد یه بادکنک خرید، بادکنک گفت: منو باد می‌کنی؟ مرد گفت: نه تو خودت باد داری! 🎈",
    "به گربه گفتن چرا اینقدر میو میو می‌کنی؟ گفت چون نمی‌تونم بگم میا! 🐱",
    "پشه به مامانش گفت: مامان من نمی‌تونم پرواز کنم. مامانش گفت: خوب بمون زمین، مگه ما اسکای دایوینگ داریم؟ 🦟",
    "به یه مرد گفتن چرا اینقدر کوچیکه؟ گفت چون بزرگتر بودم جا نمی‌شدم! 📏",
    "معلم به دانش‌آموز گفت چرا تکالیفت رو ننوشتی؟ گفت چون قلمم نامهربون بود! ✏️",
    "یه روز یخچال به فریزر گفت: چطوری داداش؟ فریزر گفت: سرد! یخچال گفت: منم همینطور! ❄️",
    "به یه خرگوش گفتن چرا اینقدر سریع می‌دوی؟ گفت چون دندون‌هام درد می‌کنه! 🐰",
    "یه بار یه مرد گفت: من می‌تونم پرواز کنم! بعد پرید از پشت‌بوم. حالا تو بیمارستانه و می‌گه: دیدی گفتم می‌تونم! 🏥",
    "به یه ماهی گفتن چرا اینقدر خوشحالی؟ گفت چون تو آبم! 🐟",
    "یه بار یه بچه به مامانش گفت: مامان من گشنمه! مامانش گفت: پس بخور! بچه گفت: چی؟ مامانش گفت: هر چی می‌خوای! بچه گفت: پس بخور! 🤣",
    "به یه پرنده گفتن چرا آواز می‌خونی؟ گفت چون نمی‌تونم حرف بزنم! 🐦",
]

RPS_CHOICES = {
    "سنگ": "🪨", "کاغذ": "📄", "قیچی": "✂️",
    "sang": "🪨", "kaghaz": "📄", "ghichi": "✂️",
}


def stop(chat_id):
    ACTIVE.pop(chat_id, None)


def handle(chat_id, text, user_name, user_id, msg_id):
    game = ACTIVE.get(chat_id)
    if not game:
        return False

    gtype = game.get("type")

    if gtype == "guess":
        try:
            n = int(text.strip())
        except ValueError:
            return False
        target = game["answer"]
        if n == target:
            api.send(chat_id, f"🎉 {api.esc_md(user_name)} درست حدس زد! عدد {target} بود.", reply_to=msg_id)
            add_game_win(chat_id, "guess", user_id, user_name)
            stop(chat_id)
        elif n < target:
            api.send(chat_id, "📈 بزرگ‌تر!", reply_to=msg_id)
        else:
            api.send(chat_id, "📉 کوچک‌تر!", reply_to=msg_id)
        return True

    if gtype == "word":
        if text.strip() == game["answer"]:
            api.send(chat_id, f"🎉 {api.esc_md(user_name)} درست حدس زد! کلمه «{game['answer']}» بود.", reply_to=msg_id)
            add_game_win(chat_id, "word", user_id, user_name)
            stop(chat_id)
        return True

    if gtype == "scramble":
        if text.strip() == game["answer"]:
            api.send(chat_id, f"🎉 {api.esc_md(user_name)} برنده شد! کلمه «{game['answer']}» بود.", reply_to=msg_id)
            add_game_win(chat_id, "scramble", user_id, user_name)
            stop(chat_id)
        return True

    if gtype == "rps":
        choice = RPS_CHOICES.get(text.strip())
        if not choice:
            return False
        bot_choice = random.choice(["🪨", "📄", "✂️"])
        player = choice
        if player == bot_choice:
            result = "🤝 مساوی!"
        elif (player == "🪨" and bot_choice == "✂️") or \
             (player == "📄" and bot_choice == "🪨") or \
             (player == "✂️" and bot_choice == "📄"):
            result = f"🎉 {api.esc_md(user_name)} برنده شد!"
            add_game_win(chat_id, "rps", user_id, user_name)
        else:
            result = "🤖 ربات برنده شد!"
        api.send(chat_id,
            f"🎮 **سنگ کاغذ قیچی**\n\n"
            f"👤 {api.esc_md(user_name)}: {player}\n"
            f"🤖 ربات: {bot_choice}\n\n"
            f"{result}",
            parse_mode="Markdown", reply_to=msg_id)
        stop(chat_id)
        return True

    if gtype == "tod":
        stop(chat_id)
        return False

    return False


def cmd_guess(chat_id):
    n = random.randint(1, 100)
    ACTIVE[chat_id] = {"type": "guess", "answer": n, "started": time.time()}
    api.send(chat_id, "🎮 **بازی حدس عدد**\nعددی بین ۱ تا ۱۰۰ انتخاب کردم. حدس بزن!\nپایان: `پایان بازی`")


def cmd_word(chat_id):
    w = random.choice(WORDS)
    ACTIVE[chat_id] = {"type": "word", "answer": w, "started": time.time()}
    api.send(chat_id, f"🎮 **بازی حدس کلمه**\nمن یه کلمه انتخاب کردم. حدس بزن!\n(راهنما: {len(w)} حرف داره)\nپایان: `پایان بازی`")


def cmd_scramble(chat_id):
    w = random.choice(WORDS)
    letters = list(w)
    random.shuffle(letters)
    scrambled = " ".join(letters)
    ACTIVE[chat_id] = {"type": "scramble", "answer": w, "started": time.time()}
    api.send(chat_id, f"🎮 **حروف بهم ریخته**\nکلمه اصلی چیه؟\n\n🔤 {scrambled}\n\nپایان: `پایان بازی`")


def cmd_dice(chat_id, msg_id, user_name):
    n = random.randint(1, 6)
    faces = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]
    api.send(chat_id, f"🎲 {api.esc_md(user_name)} تاس انداخت: {faces[n-1]} ({n})")


def cmd_coin(chat_id, msg_id, user_name):
    side = random.choice(["شیر 🦁", "خط ✏️"])
    api.send(chat_id, f"🪙 {api.esc_md(user_name)} سکه انداخت: {side}")


def cmd_joke(chat_id, user_id, user_name, msg_id):
    joke = random.choice(JOKES)
    api.send(chat_id, f"😂 **جوک برای {api.esc_md(user_name)}:**\n\n{joke}", parse_mode="Markdown")
    add_game_win(chat_id, "joke", user_id, user_name)


def cmd_tod_panel(chat_id, user_id, user_name, mode="bot"):
    rows = [
        [{"text": "🎯 حقیقت", "callback_data": f"todd:pick:{mode}:truth"}],
        [{"text": "🔥 جرئت", "callback_data": f"todd:pick:{mode}:dare"}],
        [{"text": "❌ لغو", "callback_data": "todd:cancel"}],
    ]
    if mode == "bot":
        title = "🎯 **جرئت یا حقیقت — با ربات**"
    elif mode == "friend":
        title = "🎯 **جرئت یا حقیقت — برای دوستت**"
    elif mode == "anon":
        title = "🎯 **جرئت یا حقیقت — ناشناس**"
    else:
        title = "🎯 **جرئت یا حقیقت**"

    api.send(chat_id,
        f"{title}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👤 {api.esc_md(user_name)}\n\n"
        f"کدوم رو انتخاب می‌کنی؟",
        markup={"inline_keyboard": rows},
        parse_mode="Markdown")


def cmd_tod(chat_id, user_id, user_name, msg_id):
    cmd_tod_panel(chat_id, user_id, user_name, "bot")


def cmd_doss(chat_id, user_id, user_name):
    import doss
    doss.start_with_bot(chat_id, user_id, user_name)


def cmd_rps(chat_id):
    ACTIVE[chat_id] = {"type": "rps", "started": time.time()}
    api.send(chat_id,
        "🎮 **سنگ کاغذ قیچی**\n\n"
        "یکی رو بفرست:\n"
        "🪨 سنگ\n📄 کاغذ\n✂️ قیچی",
        parse_mode="Markdown")


def cmd_mafia_start(chat_id, user_id, user_name):
    try:
        import mafia
        ok, err = mafia.start_lobby(chat_id, user_id, user_name)
        if not ok and err:
            api.send(chat_id, err, parse_mode="Markdown")
    except Exception as e:
        print(f"[mafia_start] error: {e}")
        import traceback
        traceback.print_exc()
        api.send(chat_id, f"❌ خطا در شروع مافیا:\n`{e}`", parse_mode="Markdown")


def cmd_leaderboard(chat_id, game_key=None):
    from storage import get as _get
    if game_key:
        items = get_game_leaderboard(chat_id, game_key, 10)
        game_names = {
            "guess": "🎯 حدس عدد",
            "word": "💭 حدس کلمه",
            "scramble": "🔤 حروف بهم ریخته",
            "rps": "🪨 سنگ کاغذ قیچی",
            "joke": "😂 جوک",
            "truth": "❓ حقیقت",
            "dare": "🔥 جرئت",
            "doss": "🎮 دوز",
            "quiz": "🧠 آزمون",
        }
        name = game_names.get(game_key, game_key)
        if not items:
            api.send(chat_id, f"🏆 هنوز کسی توی «{name}» برنده نشده!")
            return

        xp_data = _get("xp", chat_id) or {}
        txt = f"🏆 **لیدربرد {name}**\n━━━━━━━━━━━━━━━\n"
        for i, (uid, data) in enumerate(items, 1):
            medals = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")
            display_name = (xp_data.get(uid, {}).get("name")
                           or data.get("name", "")
                           or f"کاربر {str(uid)[-4:]}")
            w = data.get("wins", 0)
            txt += f"{medals} **{api.esc_md(display_name)}** → {w} برد\n"
        api.send(chat_id, txt, parse_mode="Markdown")
    else:
        txt = "🏆 **لیدربرد همه بازی‌ها**\n━━━━━━━━━━━━━━━\n"
        xp_data = _get("xp", chat_id) or {}
        games_map = {
            "guess": "🎯 حدس عدد",
            "word": "💭 حدس کلمه",
            "scramble": "🔤 حروف بهم ریخته",
            "rps": "🪨 سنگ کاغذ قیچی",
            "joke": "😂 جوک",
            "truth": "❓ حقیقت",
            "dare": "🔥 جرئت",
            "doss": "🎮 دوز",
        }
        found = False
        for gk, gname in games_map.items():
            items = get_game_leaderboard(chat_id, gk, 1)
            if items:
                uid, data = items[0]
                display_name = (xp_data.get(uid, {}).get("name")
                               or data.get("name", "")
                               or f"کاربر {str(uid)[-4:]}")
                txt += f"{gname}: **{api.esc_md(display_name)}** ({data.get('wins',0)})\n"
                found = True
        if not found:
            txt += "هنوز کسی توی هیچ بازی‌ای برنده نشده!"
        api.send(chat_id, txt, parse_mode="Markdown")


# ============================================================
# رنکینگ XP (کل/روزانه/هفتگی/ماهانه)
# ============================================================
def cmd_xp_ranking(chat_id):
    """تاپ ۱۰ کل"""
    from xp import top

    items = top(chat_id, 10)
    if not items:
        api.send(chat_id,
            "ℹ️ هنوز کسی امتیاز کسب نکرده.\n\n"
            "🙏 با ارسال پیام، امتیاز و سطح بگیرید!")
        return

    txt = (
        "╔══════════════════════════╗\n"
        "║   🏆  بـرتـریـن‌هـای گـروه    ║\n"
        "║         تـاپ ۱۰ نـفـر          ║\n"
        "╚══════════════════════════╝\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
    )

    medals = ["🥇", "🥈", "🥉"]
    for i, (uid, u) in enumerate(items, 1):
        if i <= 3:
            medal = medals[i - 1]
        else:
            medal = f"{i}️⃣"
        name = u.get("name", "کاربر")
        xp = u.get("xp", 0)
        level = u.get("level", 1)
        txt += f"{medal} **{api.esc_md(name)}**\n"
        txt += f"     ⭐ `{xp}` XP | 🏅 سطح `{level}`\n\n"

    txt += "━━━━━━━━━━━━━━━━━━━━━━\n"
    txt += "💐 **با فعالیت بیشتر، به‌روز بالاتر بروید!**\n"
    txt += "🏆 _تیم مدیریت آلفا_"
    api.send(chat_id, txt, parse_mode="Markdown")


def cmd_ranking_period(chat_id, period="all"):
    """period: all / daily / weekly / monthly"""
    from xp import top, top_daily, top_weekly, top_monthly

    if period == "daily":
        items = top_daily(chat_id, 10)
        title = "☀️ برترین‌های امروز"
        empty = "ℹ️ امروز کسی امتیاز نگرفته."
    elif period == "weekly":
        items = top_weekly(chat_id, 10)
        title = "📅 برترین‌های این هفته"
        empty = "ℹ️ این هفته کسی امتیاز نگرفته."
    elif period == "monthly":
        items = top_monthly(chat_id, 10)
        title = "🗓 برترین‌های این ماه"
        empty = "ℹ️ این ماه کسی امتیاز نگرفته."
    else:
        items = top(chat_id, 10)
        title = "🏆 برترین‌های کل گروه"
        empty = "ℹ️ هنوز کسی امتیاز کسب نکرده."

    if not items:
        api.send(chat_id, empty)
        return

    txt = (
        f"╔══════════════════════════╗\n"
        f"║   {title}\n"
        f"║         تـاپ ۱۰ نـفـر          ║\n"
        f"╚══════════════════════════╝\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
    )
    medals = ["🥇", "🥈", "🥉"]
    for i, (uid, u) in enumerate(items, 1):
        medal = medals[i-1] if i <= 3 else f"{i}️⃣"
        name = u.get("name", "کاربر")
        xp = u.get("xp", 0)
        if period == "all":
            level = u.get("level", 1)
            txt += f"{medal} **{api.esc_md(name)}**\n     ⭐ `{xp}` XP | 🏅 سطح `{level}`\n\n"
        else:
            txt += f"{medal} **{api.esc_md(name)}** → `{xp}` XP\n"
    txt += "━━━━━━━━━━━━━━━━━━━━━━\n"
    txt += "🏆 _تیم مدیریت آلفا_"
    api.send(chat_id, txt, parse_mode="Markdown")