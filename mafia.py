# -*- coding: utf-8 -*-
"""بازی مافیا حرفه‌ای - آلفا نسخه Unlimited"""
import time
import random
import threading
import api
import storage
from storage import get, set_


# ============================================================
# نقش‌ها
# ============================================================
ROLES = {
    "godfather": {"fa": "پدرخوانده", "emoji": "👑", "team": "mafia", "desc": "رهبر مافیا"},
    "mafia": {"fa": "مافیا", "emoji": "🔫", "team": "mafia", "desc": "عضو مافیا"},
    "doctor": {"fa": "دکتر", "emoji": "💉", "team": "city", "desc": "نجات‌دهنده"},
    "detective": {"fa": "کارآگاه", "emoji": "🕵️", "team": "city", "desc": "استعلام‌کننده"},
    "sniper": {"fa": "تک‌تیرانداز", "emoji": "🎯", "team": "city", "desc": "یه بار تیر"},
    "citizen": {"fa": "شهروند", "emoji": "👤", "team": "city", "desc": "شهروند عادی"},
}

# ✅ تایماوت حذف شد - بازی unlimited
# فقط پاکسازی خیلی قدیمی (۳ ساعت)
MAFIA_SOFT_TIMEOUT = 10800

# ✅ تأخیر بین پیام‌های انبوه
BATCH_DELAY = 1.5
ROLE_DELAY = 2.0


NIGHT_BANNER = (
    "╔══════════════════════╗\n"
    "║   🌙  شـب دسـت داده    ║\n"
    "║  ━━━━━━━━━━━━━━━━━    ║\n"
    "║   همه چشاشون بسته...  ║\n"
    "╚══════════════════════╝"
)

DAY_BANNER = (
    "╔══════════════════════╗\n"
    "║   ☀️  صبـح شـد        ║\n"
    "║  ━━━━━━━━━━━━━━━━━    ║\n"
    "║   شهر بیدار می‌شه...   ║\n"
    "╚══════════════════════╝"
)

MAFIA_LOGO = (
    "╔══════════════════════╗\n"
    "║   🎭   مـافـیـا   🎭   ║\n"
    "║      بـازی  آلـفـا     ║\n"
    "╚══════════════════════╝"
)


# ============================================================
# توابع کمکی
# ============================================================
def kb(rows):
    return {"inline_keyboard": [r for r in rows if r]}


def btn(text, data=None, url=None):
    if url:
        return {"text": text, "url": url}
    return {"text": text, "callback_data": data}


def get_game(chat_id):
    games = storage.get("active_games", chat_id) or {}
    game = games.get("mafia")

    # ✅ فقط بازی‌های خیلی قدیمی پاک میشن
    if game:
        started = game.get("started", 0)
        if started and time.time() - started > MAFIA_SOFT_TIMEOUT:
            games.pop("mafia", None)
            set_("active_games", chat_id, games)
            return None

    return game


def save_game(chat_id, game):
    games = storage.get("active_games", chat_id) or {}
    if game is None:
        games.pop("mafia", None)
    else:
        started = game.get("started", 0)
        if started and time.time() - started > MAFIA_SOFT_TIMEOUT and game.get("state") != "ended":
            games.pop("mafia", None)
        else:
            games["mafia"] = game
    set_("active_games", chat_id, games)


def get_player(game, user_id):
    for p in game["players"]:
        if p["id"] == user_id:
            return p
    return None


def alive_players(game):
    return [p for p in game["players"] if p.get("alive", True)]


def alive_mafia(game):
    return [p for p in alive_players(game) if p["role"] in ("mafia", "godfather")]


def alive_city(game):
    return [p for p in alive_players(game) if p["role"] not in ("mafia", "godfather")]


def get_player_name(game, user_id):
    p = get_player(game, user_id)
    return p["name"] if p else f"کاربر {user_id}"


# ============================================================
# شروع لابی
# ============================================================
def start_lobby(chat_id, creator_id, creator_name):
    game = get_game(chat_id)
    if game and game.get("state") not in ("ended", None):
        return False, "⚠️ یه بازی مافیا در جریانه!"

    game = {
        "state": "lobby",
        "creator": creator_id,
        "creator_name": creator_name,
        "players": [
            {"id": creator_id, "name": creator_name, "alive": True, "role": None}
        ],
        "started": time.time(),
        "round": 0,
        "night_actions": {},
        "votes": {},
        "log": [],
    }
    save_game(chat_id, game)

    text = (
        f"{MAFIA_LOGO}\n\n"
        f"👑 **سازنده:** {creator_name}\n"
        f"👥 **بازیکن‌ها:** `1`\n"
        f"⏳ **وضعیت:** در انتظار بازیکن\n\n"
        f"🎯 **حداقل ۵ نفر برای شروع**\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📋 **لیست بازیکنان:**\n"
        f"└─ {creator_name}\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"👇 برای ورود دکمه بزن:"
    )
    markup = kb([
        [btn("➕ ورود به بازی", "mafia:join"), btn("🚪 خروج", "mafia:leave")],
        [btn("🚀 شروع بازی", "mafia:start")],
        [btn("❌ لغو بازی", "mafia:cancel")],
    ])
    api.send(chat_id, text, reply_to=0, markup=markup, parse_mode="Markdown")
    return True, ""


# ============================================================
# ورود/خروج بازیکن
# ============================================================
def join_game(chat_id, user_id, user_name):
    game = get_game(chat_id)
    if not game or game.get("state") != "lobby":
        return False, "❌ الان لابی فعال نیست!"

    if get_player(game, user_id):
        return False, "❗️ قبلا وارد شدی!"

    if len(game["players"]) >= 20:
        return False, "❌ ظرفیت پره (حداکثر ۲۰ نفر)!"

    game["players"].append({
        "id": user_id, "name": user_name, "alive": True, "role": None
    })
    save_game(chat_id, game)
    return True, f"✅ {api.esc_md(user_name)} وارد بازی شد!"


def leave_game(chat_id, user_id):
    game = get_game(chat_id)
    if not game or game.get("state") != "lobby":
        return False, "❌ الان لابی فعال نیست!"

    p = get_player(game, user_id)
    if not p:
        return False, "❗️ تو توی بازی نیستی!"

    if user_id == game["creator"]:
        return False, "❌ سازنده نمی‌تونه از بازی خارج بشه! (لغو کن)"

    game["players"] = [x for x in game["players"] if x["id"] != user_id]
    save_game(chat_id, game)
    return True, f"👋 {api.esc_md(p['name'])} از بازی خارج شد"


# ============================================================
# شروع بازی
# ============================================================
def start_game(chat_id, user_id):
    game = get_game(chat_id)
    if not game or game.get("state") != "lobby":
        return False, "❌ الان لابی فعال نیست!"

    if user_id != game["creator"]:
        return False, "⛔️ فقط سازنده می‌تونه بازی رو شروع کنه!"

    n = len(game["players"])
    if n < 5:
        return False, f"❌ حداقل ۵ نفر لازمه (الان {n} نفر)"

    players = game["players"][:]
    random.shuffle(players)

    if n <= 6:
        roles_pool = ["godfather", "doctor", "detective"] + ["citizen"] * (n - 3)
    elif n <= 9:
        roles_pool = ["godfather", "mafia", "doctor", "detective"] + ["citizen"] * (n - 4)
    elif n <= 12:
        roles_pool = ["godfather", "mafia", "doctor", "detective", "sniper"] + ["citizen"] * (n - 5)
    else:
        roles_pool = ["godfather", "mafia", "mafia", "doctor", "detective", "sniper"] + ["citizen"] * (n - 6)

    random.shuffle(roles_pool)

    for i, p in enumerate(players):
        p["role"] = roles_pool[i]
        p["alive"] = True

    game["players"] = players
    game["state"] = "night"
    game["round"] = 1
    game["night_actions"] = {}
    game["votes"] = {}
    save_game(chat_id, game)

    mafia_count = len([r for r in roles_pool if r in ('mafia', 'godfather')])

    text = (
        f"╔══════════════════════╗\n"
        f"║   🎬  بـازی شـروع شـد   ║\n"
        f"╚══════════════════════╝\n"
        f"👥 بازیکن‌ها: `{n}`\n"
        f"🔫 مافیاها: `{mafia_count}`\n"
        f"🏙 شهروندها: `{n - mafia_count}`\n\n"
        f"🌃 **راند ۱ - شب اول**\n"
        f"📩 نقش‌ها به پیوی فرستاده شد.\n"
        f"_شب‌هنگامه، چشمات رو ببند..._"
    )
    api.send(chat_id, text, reply_to=0, parse_mode="Markdown")

    # ✅ ارسال نقش‌ها با تأخیر (ضد اسپم)
    def _send_roles():
        for idx, p in enumerate(players):
            role = ROLES[p["role"]]
            teammates = ""
            if role["team"] == "mafia":
                mates = [x["name"] for x in players if x["role"] in ("mafia", "godfather") and x["id"] != p["id"]]
                if mates:
                    teammates = f"\n\n👥 **هم‌تیمی‌ها:** {', '.join(mates)}"

            role_card = (
                f"╔══════════════════════╗\n"
                f"║  {role['emoji']}  نـقـش شـمـا  ║\n"
                f"╚══════════════════════╝\n\n"
                f"🎭 **{api.esc_md(role['fa'])}**\n\n"
                f"📖 {role['desc']}{teammates}\n\n"
                f"_موفق باشی!_ 🍀"
            )
            try:
                # ✅ تأخیر بین ارسال‌ها
                if idx > 0:
                    time.sleep(ROLE_DELAY)
                api.send(p["id"], role_card, reply_to=0, parse_mode="Markdown")
            except Exception as e:
                print(f"[mafia:role_send] {e}")

    threading.Thread(target=_send_roles, daemon=True).start()

    # ✅ شروع فاز شب با تأخیر بیشتر (تا نقش‌ها برسن)
    time.sleep(2)
    threading.Thread(target=night_phase, args=(chat_id,), daemon=True).start()
    return True, ""


# ============================================================
# فاز شب
# ============================================================
def night_phase(chat_id):
    # ✅ تأخیر بیشتر برای اینکه نقش‌ها برسن
    time.sleep(5)
    game = get_game(chat_id)
    if not game or game.get("state") != "night":
        return

    alive = alive_players(game)
    mafia = alive_mafia(game)

    api.send(chat_id,
        f"{NIGHT_BANNER}\n\n"
        f"🌃 **راند {game['round']} - شب**\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🌙 همه چشاشون رو بستن...\n"
        f"🔫 مافیا بیدار شد\n"
        f"💉 دکتر داره تصمیم می‌گیره\n"
        f"🕵️ کارآگاه دنبال مدرکه\n"
        f"━━━━━━━━━━━━━━━",
        reply_to=0,
        parse_mode="Markdown")

    # ✅ ارسال به مافیاها با تأخیر
    for idx, m in enumerate(mafia):
        rows = []
        targets = [p for p in alive if p["id"] != m["id"]]
        for t in targets:
            rows.append([btn(f"🔫 {t['name']}", f"mafia:kill:{t['id']}")])
        try:
            if idx > 0:
                time.sleep(BATCH_DELAY)
            api.send(m["id"],
                f"🌃 **شب {game['round']}**\n"
                f"━━━━━━━━━━━━━━━\n"
                f"🎯 انتخاب کن کی رو بکشی:\n\n"
                f"_بعد از انتخاب، منتظر بمون._",
                reply_to=0,
                markup=kb(rows),
                parse_mode="Markdown")
        except Exception as e:
            print(f"[mafia:night:mafia] {e}")

    # دکتر
    doctor = next((p for p in alive if p["role"] == "doctor"), None)
    if doctor:
        time.sleep(BATCH_DELAY)
        rows = []
        for t in alive:
            rows.append([btn(f"💉 {t['name']}", f"mafia:save:{t['id']}")])
        try:
            api.send(doctor["id"],
                f"🌃 **شب {game['round']}**\n"
                f"━━━━━━━━━━━━━━━\n"
                f"💉 می‌خوای کی رو از مرگ نجات بدی؟\n"
                f"(می‌تونی خودت رو هم انتخاب کنی)",
                reply_to=0,
                markup=kb(rows),
                parse_mode="Markdown")
        except Exception as e:
            print(f"[mafia:night:doctor] {e}")

    # کارآگاه
    detective = next((p for p in alive if p["role"] == "detective"), None)
    if detective:
        time.sleep(BATCH_DELAY)
        rows = []
        for t in alive:
            if t["id"] == detective["id"]:
                continue
            rows.append([btn(f"🔍 {t['name']}", f"mafia:check:{t['id']}")])
        try:
            api.send(detective["id"],
                f"🌃 **شب {game['round']}**\n"
                f"━━━━━━━━━━━━━━━\n"
                f"🕵️ کی رو استعلام کنم؟",
                reply_to=0,
                markup=kb(rows),
                parse_mode="Markdown")
        except Exception as e:
            print(f"[mafia:night:detective] {e}")

    threading.Thread(target=night_timeout, args=(chat_id,), daemon=True).start()


def night_timeout(chat_id):
    # ✅ زمان بیشتر (۹۰ ثانیه به جای ۶۰)
    time.sleep(90)
    game = get_game(chat_id)
    if not game or game.get("state") != "night":
        return
    end_night(chat_id)


# ============================================================
# ثبت اکشن شب
# ============================================================
def night_action(chat_id, user_id, action, target_id):
    game = get_game(chat_id)
    if not game or game.get("state") != "night":
        return False, "❌ الان فاز شب نیست!"

    p = get_player(game, user_id)
    if not p or not p.get("alive"):
        return False, "❌ تو توی بازی نیستی!"

    role = p["role"]
    actions = game.get("night_actions", {})

    if action == "kill" and role in ("mafia", "godfather"):
        actions.setdefault(user_id, {})["kill"] = target_id
        save_game(chat_id, game)
        return True, "🔫 انتخاب شد"

    if action == "save" and role == "doctor":
        actions.setdefault(user_id, {})["save"] = target_id
        save_game(chat_id, game)
        return True, "💉 نجات انتخاب شد"

    if action == "check" and role == "detective":
        target = get_player(game, target_id)
        if not target:
            return False, "❌ کاربر پیدا نشد"
        is_mafia = target["role"] in ("mafia", "godfather")
        actions.setdefault(user_id, {})["check"] = target_id
        save_game(chat_id, game)
        emoji = "🔴" if is_mafia else "🟢"
        status = "مافیا" if is_mafia else "شهروند"
        return True, f"{emoji} **{api.esc_md(target['name'])}** {status}ه!"

    return False, "❌ اکشن نامعتبر"


# ============================================================
# پایان فاز شب
# ============================================================
def end_night(chat_id):
    game = get_game(chat_id)
    if not game or game.get("state") != "night":
        return

    actions = game.get("night_actions", {})

    kill_targets = {}
    for uid, acts in actions.items():
        p = get_player(game, int(uid))
        if not p or p["role"] not in ("mafia", "godfather"):
            continue
        if "kill" in acts:
            tid = acts["kill"]
            kill_targets[tid] = kill_targets.get(tid, 0) + 1

    killed_id = None
    if kill_targets:
        killed_id = max(kill_targets, key=kill_targets.get)

    saved_id = None
    for uid, acts in actions.items():
        p = get_player(game, int(uid))
        if p and p["role"] == "doctor" and "save" in acts:
            saved_id = acts["save"]

    result_text = f"{DAY_BANNER}\n\n☀️ **صبح راند {game['round']}**\n━━━━━━━━━━━━━━━\n"

    if killed_id and killed_id != saved_id:
        victim = get_player(game, killed_id)
        if victim:
            victim["alive"] = False
            result_text += f"💀 **{api.esc_md(victim['name'])}** شب گذشته کشته شد!\n"
        else:
            result_text += "🌅 امشب کسی کشته نشد.\n"
    elif killed_id and killed_id == saved_id:
        victim = get_player(game, killed_id)
        result_text += f"💉 دکتر **{api.esc_md(victim['name'] if victim else '?')}** رو نجات داد!\n🌅 کسی نمرد.\n"
    else:
        result_text += "🌅 امشب کسی کشته نشد.\n"

    save_game(chat_id, game)

    if check_game_end(chat_id):
        return

    game = get_game(chat_id)
    game["state"] = "day_vote"
    game["votes"] = {}
    game["night_actions"] = {}
    save_game(chat_id, game)

    api.send(chat_id, result_text, reply_to=0, parse_mode="Markdown")
    time.sleep(3)
    start_day_vote(chat_id)


# ============================================================
# رأی‌گیری روز
# ============================================================
def start_day_vote(chat_id):
    game = get_game(chat_id)
    if not game:
        return

    alive = alive_players(game)
    rows = []
    for p in alive:
        rows.append([btn(f"🗳 {p['name']}", f"mafia:vote:{p['id']}")])

    text = (
        f"╔══════════════════════╗\n"
        f"║   🗳  رأی‌گـیـری روز   ║\n"
        f"╚══════════════════════╝\n"
        f"👥 زنده‌ها: `{len(alive)}` نفر\n\n"
        "کی باید اخراج بشه؟\n\n"
        "⏱ ۹۰ ثانیه فرصت\n"
        "_هر کی فقط ۱ رأی می‌تونه بده_"
    )
    api.send(chat_id, text, reply_to=0, markup=kb(rows), parse_mode="Markdown")

    threading.Thread(target=vote_timeout, args=(chat_id,), daemon=True).start()


def vote_timeout(chat_id):
    # ✅ زمان بیشتر (۹۰ ثانیه به جای ۶۰)
    time.sleep(90)
    game = get_game(chat_id)
    if not game or game.get("state") != "day_vote":
        return
    end_day_vote(chat_id)


def register_vote(chat_id, voter_id, target_id):
    game = get_game(chat_id)
    if not game or game.get("state") != "day_vote":
        return False, "❌ الان رأی‌گیری نیست!"

    p = get_player(game, voter_id)
    if not p or not p.get("alive"):
        return False, "❌ تو زنده نیستی!"

    if voter_id == target_id:
        return False, "❌ نمی‌تونی به خودت رأی بدی!"

    game["votes"][str(voter_id)] = target_id
    save_game(chat_id, game)
    return True, f"🗳 رأیت ثبت شد"


def end_day_vote(chat_id):
    game = get_game(chat_id)
    if not game or game.get("state") != "day_vote":
        return

    votes = game.get("votes", {})
    counts = {}
    for voter, target in votes.items():
        counts[target] = counts.get(target, 0) + 1

    if not counts:
        api.send(chat_id, "🗳 کسی رأی نداد! هیچ‌کس اخراج نشد.", reply_to=0)
        game["state"] = "night"
        game["round"] += 1
        game["votes"] = {}
        save_game(chat_id, game)
        time.sleep(3)
        night_phase(chat_id)
        return

    max_count = max(counts.values())
    top = [tid for tid, c in counts.items() if c == max_count]

    if len(top) > 1:
        names = [get_player_name(game, int(t)) for t in top]
        api.send(chat_id,
            f"🗳 **رأی‌گیری مساوی شد!**\n"
            f"بین: {', '.join(names)}\n"
            f"هیچ‌کس اخراج نشد.",
            reply_to=0,
            parse_mode="Markdown")
    else:
        target_id = int(top[0])
        target = get_player(game, target_id)
        if target:
            target["alive"] = False
            role_info = ROLES[target["role"]]
            save_game(chat_id, game)
            api.send(chat_id,
                f"╔══════════════════════╗\n"
                f"║   🗳  نـتـیـجـه‌ی رأی   ║\n"
                f"╚══════════════════════╝\n"
                f"🚪 **{api.esc_md(target['name'])}** اخراج شد!\n"
                f"🎭 نقشش: {role_info['emoji']} **{api.esc_md(role_info['fa'])}**\n",
                reply_to=0,
                parse_mode="Markdown")

    if check_game_end(chat_id):
        return

    game = get_game(chat_id)
    game["state"] = "night"
    game["round"] += 1
    game["votes"] = {}
    game["night_actions"] = {}
    save_game(chat_id, game)
    time.sleep(3)
    night_phase(chat_id)


# ============================================================
# چک پایان بازی
# ============================================================
def check_game_end(chat_id):
    game = get_game(chat_id)
    if not game:
        return True

    mafia_count = len(alive_mafia(game))
    city_count = len(alive_city(game))

    if mafia_count == 0:
        text = (
            "╔══════════════════════╗\n"
            "║   🎉  بـازی تـمـوم شـد   ║\n"
            "╚══════════════════════╝\n"
            "🏙 **شهر برنده شد!**\n\n"
            "🔍 همه مافیاها پیدا شدن.\n\n"
            "📋 **نقش‌های همه:**\n"
        )
        for p in game["players"]:
            r = ROLES[p["role"]]
            status = "💀" if not p.get("alive") else "✅"
            text += f"{status} {r['emoji']} **{api.esc_md(p['name'])}** → {r['fa']}\n"
        api.send(chat_id, text, reply_to=0, parse_mode="Markdown")
        game["state"] = "ended"
        save_game(chat_id, game)

        def _cleanup():
            time.sleep(15)
            save_game(chat_id, None)
        threading.Thread(target=_cleanup, daemon=True).start()
        return True

    if mafia_count >= city_count:
        text = (
            "╔══════════════════════╗\n"
            "║   🎉  بـازی تـمـوم شـد   ║\n"
            "╚══════════════════════╝\n"
            "🔫 **مافیا برنده شد!**\n\n"
            "💀 تعداد مافیا با شهر برابر شد.\n\n"
            "📋 **نقش‌های همه:**\n"
        )
        for p in game["players"]:
            r = ROLES[p["role"]]
            status = "💀" if not p.get("alive") else "✅"
            text += f"{status} {r['emoji']} **{api.esc_md(p['name'])}** → {r['fa']}\n"
        api.send(chat_id, text, reply_to=0, parse_mode="Markdown")
        game["state"] = "ended"
        save_game(chat_id, game)

        def _cleanup():
            time.sleep(15)
            save_game(chat_id, None)
        threading.Thread(target=_cleanup, daemon=True).start()
        return True

    return False


# ============================================================
# لغو بازی
# ============================================================
def cancel_game(chat_id, user_id):
    game = get_game(chat_id)
    if not game:
        return False, "❌ بازی فعالی نیست!"

    if user_id != game["creator"]:
        return False, "⛔️ فقط سازنده می‌تونه لغو کنه!"

    save_game(chat_id, None)
    return True, "❌ بازی مافیا لغو شد"


# ============================================================
# پردازش callback مافیا
# ============================================================
def handle_callback(cb, cb_id, data, chat_id, msg_id, user):
    user_id = user["id"]
    user_name = user.get("first_name", "کاربر")

    if data == "mafia:join":
        ok, msg = join_game(chat_id, user_id, user_name)
        api.answer_callback(cb_id, msg, alert=not ok)
        if ok:
            game = get_game(chat_id)
            if game:
                players_list = "\n".join([f"└─ {api.esc_md(p['name'])}" for p in game["players"]])
                text = (
                    f"{MAFIA_LOGO}\n\n"
                    f"👑 **سازنده:** {game['creator_name']}\n"
                    f"👥 **بازیکن‌ها:** `{len(game['players'])}`\n\n"
                    f"📋 **لیست بازیکنان:**\n{players_list}\n\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"👇 برای ورود دکمه بزن:"
                )
                markup = kb([
                    [btn("➕ ورود به بازی", "mafia:join"), btn("🚪 خروج", "mafia:leave")],
                    [btn("🚀 شروع بازی", "mafia:start")],
                    [btn("❌ لغو بازی", "mafia:cancel")],
                ])
                api.edit_message(chat_id, msg_id, text, markup=markup, parse_mode="Markdown")
        return

    if data == "mafia:leave":
        ok, msg = leave_game(chat_id, user_id)
        api.answer_callback(cb_id, msg, alert=True)
        if ok:
            game = get_game(chat_id)
            if game:
                players_list = "\n".join([f"└─ {api.esc_md(p['name'])}" for p in game["players"]])
                text = (
                    f"{MAFIA_LOGO}\n\n"
                    f"👑 **سازنده:** {game['creator_name']}\n"
                    f"👥 **بازیکن‌ها:** `{len(game['players'])}`\n\n"
                    f"📋 **لیست بازیکنان:**\n{players_list}\n\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"👇 برای ورود دکمه بزن:"
                )
                markup = kb([
                    [btn("➕ ورود به بازی", "mafia:join"), btn("🚪 خروج", "mafia:leave")],
                    [btn("🚀 شروع بازی", "mafia:start")],
                    [btn("❌ لغو بازی", "mafia:cancel")],
                ])
                api.edit_message(chat_id, msg_id, text, markup=markup, parse_mode="Markdown")
        return

    if data == "mafia:start":
        ok, msg = start_game(chat_id, user_id)
        if not ok:
            api.answer_callback(cb_id, msg, alert=True)
        else:
            api.answer_callback(cb_id, "🎭 بازی شروع شد!")
            api.delete(chat_id, msg_id)
        return

    if data == "mafia:cancel":
        ok, msg = cancel_game(chat_id, user_id)
        api.answer_callback(cb_id, msg, alert=True)
        if ok:
            api.delete(chat_id, msg_id)
        return

    if data.startswith("mafia:kill:"):
        target_id = int(data.split(":")[2])
        ok, msg = night_action(chat_id, user_id, "kill", target_id)
        api.answer_callback(cb_id, msg, alert=True)
        if ok:
            target = get_player(get_game(chat_id), target_id)
            api.edit_message(chat_id, msg_id,
                f"✅ **انتخاب شد:** {target['name'] if target else '?'}\n"
                "_منتظر بقیه مافیا بمون..._",
                parse_mode="Markdown")
        return

    if data.startswith("mafia:save:"):
        target_id = int(data.split(":")[2])
        ok, msg = night_action(chat_id, user_id, "save", target_id)
        api.answer_callback(cb_id, msg, alert=True)
        if ok:
            target = get_player(get_game(chat_id), target_id)
            api.edit_message(chat_id, msg_id,
                f"✅ **{api.esc_md(target['name'] if target else '?')}** رو نجات دادی.\n"
                "_منتظر بمون تا صبح..._",
                parse_mode="Markdown")
        return

    if data.startswith("mafia:check:"):
        target_id = int(data.split(":")[2])
        ok, msg = night_action(chat_id, user_id, "check", target_id)
        api.answer_callback(cb_id, msg, alert=True)
        if ok:
            api.edit_message(chat_id, msg_id, msg, parse_mode="Markdown")
        return

    if data.startswith("mafia:vote:"):
        target_id = int(data.split(":")[2])
        ok, msg = register_vote(chat_id, user_id, target_id)
        api.answer_callback(cb_id, msg, alert=True)
        return

    api.answer_callback(cb_id, "❓")