import time
import random
from datetime import datetime
from config import *
from core import (db, save_db, is_subscription_active,
                  get_subscription_days_left)
from data import *


# ==================== ایموجی پدافند ====================
DEFENSE_EMOJI = {
    "تیربار": "🔫", "گنبد آهنین": "🛡️", "باور": "🚀",
    "پاتریوت": "🎯", "S-400": "💥", "گاردین": "💎", "تاد": "⚡",
}

TALISMAN_INFO = {
    "eye": {"name": "چشم", "emoji": "🧿", "price": 5000, "currency": "coins",
            "callback": "tal_buy_eye", "count_key": "talisman_eye_count",
            "desc": "25٪ شانس نادیده گرفتن پدافند حریف (مهاجم)", "target": "attacker", "req_level": 5},
    "fire": {"name": "آتش", "emoji": "🔥", "price": 10000, "currency": "coins",
             "callback": "tal_buy_fire", "count_key": "talisman_fire_count",
             "desc": "20٪ دمیج بیشتر (مهاجم)", "target": "attacker", "req_level": 8},
    "water": {"name": "آب", "emoji": "💧", "price": 15000, "currency": "coins",
              "callback": "tal_buy_water", "count_key": "talisman_water_count",
              "desc": "30٪ کاهش دمیج و غارت (مدافع)", "target": "defender", "req_level": 10},
    "storm": {"name": "طوفان", "emoji": "🌪", "price": 100, "currency": "oil",
              "callback": "tal_buy_storm", "count_key": "talisman_storm_count",
              "desc": "2 موشک اضافه (مهاجم)", "target": "attacker", "req_level": 14},
    "lightning": {"name": "صاعقه", "emoji": "⚡", "price": 150, "currency": "oil",
                  "callback": "tal_buy_lightning", "count_key": "talisman_lightning_count",
                  "desc": "حریف 60 ثانیه فلج (مهاجم)", "target": "attacker", "req_level": 17},
    "shield": {"name": "سپر", "emoji": "🛡", "price": 50000, "currency": "coins",
               "callback": "tal_buy_shield", "count_key": "talisman_shield_count",
               "desc": "50٪ کاهش غارت سکه و نفت (مدافع)", "target": "defender", "req_level": 20},
    "hunt": {"name": "شکار", "emoji": "👁", "price": 200, "currency": "oil",
             "callback": "tal_buy_hunt", "count_key": "talisman_hunt_count",
             "desc": "حریف 40٪ ضعیف‌تر / دمیج بیشتر (مهاجم)", "target": "attacker", "req_level": 23},
    "ice": {"name": "یخ", "emoji": "❄️", "price": 250, "currency": "oil",
            "callback": "tal_buy_ice", "count_key": "talisman_ice_count",
            "desc": "حریف 30 ثانیه فلج (مهاجم)", "target": "attacker", "req_level": 25},
}


def get_missile_emoji(name):
    data = MISSILES.get(name)
    if data:
        return data.get("emoji", "🚀")
    return "🚀"


def get_defense_emoji(name):
    if name in DEFENSE_EMOJI:
        return DEFENSE_EMOJI[name]
    return DEFENSES.get(name, {}).get("emoji", "🛡️")


def get_talisman_by_callback(cb):
    for key, info in TALISMAN_INFO.items():
        if info["callback"] == cb:
            return key, info
    return None, None


def make_loot_chart(taken, available, width=10):
    if available <= 0:
        return "⬜" * width, 0
    pct = min(int((taken / available) * 100), 100)
    filled = int((pct / 100) * width)
    if taken > 0 and filled == 0:
        filled = 1

    if pct >= 75:
        block = "🟩"
    elif pct >= 50:
        block = "🟨"
    elif pct >= 25:
        block = "🟧"
    else:
        block = "🟥"

    return block * filled + "⬜" * (width - filled), pct


# ==================== توابع کارخانه ====================
def update_factory_iron(user_id):
    p = db.get(user_id, {})
    level = p.get("iron_mine_level", 1)
    rate = level * 100
    cap = level * 500
    now = time.time()
    last = p.get("iron_last_dig", 0)
    if last == 0:
        db[user_id]["iron_last_dig"] = now
        save_db()
        return
    sp = int(now - last)
    if sp <= 0:
        return
    earned = (sp * rate) // 3600
    if earned <= 0:
        return
    current = p.get("iron", 0)
    db[user_id]["iron"] = min(current + earned, cap)
    db[user_id]["iron_last_dig"] = now
    save_db()


def update_factory_steel(user_id):
    p = db.get(user_id, {})
    level = p.get("steel_factory_level", 0)
    if level == 0:
        return
    rate = level * 50
    cap = level * 250
    now = time.time()
    last = p.get("steel_last_dig", 0)
    if last == 0:
        db[user_id]["steel_last_dig"] = now
        save_db()
        return
    sp = int(now - last)
    if sp <= 0:
        return
    earned = (sp * rate) // 3600
    if earned <= 0:
        return
    current = p.get("steel", 0)
    db[user_id]["steel"] = min(current + earned, cap)
    db[user_id]["steel_last_dig"] = now
    save_db()


def update_factory_weapon(user_id):
    p = db.get(user_id, {})
    level = p.get("weapon_factory_level", 0)
    if level == 0:
        return
    rate = level * 10
    cap = level * 50
    now = time.time()
    last = p.get("weapon_last_dig", 0)
    if last == 0:
        db[user_id]["weapon_last_dig"] = now
        save_db()
        return
    sp = int(now - last)
    if sp <= 0:
        return
    earned = (sp * rate) // 3600
    if earned <= 0:
        return
    current = p.get("weapon", 0)
    db[user_id]["weapon"] = min(current + earned, cap)
    db[user_id]["weapon_last_dig"] = now
    save_db()


def build_factory_keyboard():
    return {"inline_keyboard": [
        [{"text": "⛏️ معدن آهن", "callback_data": "factory_iron"},
         {"text": "🏭 کارخانه فولاد", "callback_data": "factory_steel"}],
        [{"text": "⚔️ کارخانه سلاح", "callback_data": "factory_weapon"},
         {"text": "🪙 فروشگاه", "callback_data": "factory_sell"}],
        [{"text": "🔙 بازگشت به منوی اصلی", "callback_data": "go_main"}],
    ]}


def build_factory_text(user_id):
    p = db.get(user_id, {})
    iron = p.get("iron", 0)
    steel = p.get("steel", 0)
    weapon = p.get("weapon", 0)
    il = p.get("iron_mine_level", 1)
    sl = p.get("steel_factory_level", 0)
    wl = p.get("weapon_factory_level", 0)

    text = "🏭 کارخانه\n\n"

    iron_cap = il * 500
    ip = min(int((iron / iron_cap) * 100), 100) if iron_cap > 0 else 0
    ifill = ip // 10
    ibar = "█" * ifill + "░" * (10 - ifill)
    text += f"⛏️ معدن آهن (سطح {il})\n"
    text += f"   📦 آهن: {iron:,}/{iron_cap:,}\n"
    text += f"   ⚙️ تولید: {il*100:,} آهن/ساعت\n"
    text += f"   {ibar} {ip}%\n\n"

    if sl == 0:
        text += "🏭 کارخانه فولاد: ❌ ساخته نشده\n"
        text += "   🎯 لول مورد نیاز: 25\n"
        text += "   🪙 هزینه: 50,000 سکه + 500 آهن\n\n"
    else:
        steel_cap = sl * 250
        sp = min(int((steel / steel_cap) * 100), 100) if steel_cap > 0 else 0
        sfill = sp // 10
        sbar = "█" * sfill + "░" * (10 - sfill)
        text += f"🏭 کارخانه فولاد (سطح {sl})\n"
        text += f"   📦 فولاد: {steel:,}/{steel_cap:,}\n"
        text += f"   ⚙️ تولید: {sl*50:,} فولاد/ساعت\n"
        text += f"   {sbar} {sp}%\n\n"

    if wl == 0:
        text += "⚔️ کارخانه سلاح: ❌ ساخته نشده\n"
        text += "   🎯 لول مورد نیاز: 40\n"
        text += "   🪙 هزینه: 100,000 سکه + 500 فولاد\n\n"
    else:
        weapon_cap = wl * 50
        wp = min(int((weapon / weapon_cap) * 100), 100) if weapon_cap > 0 else 0
        wfill = wp // 10
        wbar = "█" * wfill + "░" * (10 - wfill)
        text += f"⚔️ کارخانه سلاح (سطح {wl})\n"
        text += f"   📦 سلاح: {weapon:,}/{weapon_cap:,}\n"
        text += f"   ⚙️ تولید: {wl*10:,} سلاح/ساعت\n"
        text += f"   {wbar} {wp}%\n\n"

    text += "🔻 یکی از بخش‌ها رو انتخاب کن:"
    return text


def build_iron_text(user_id):
    p = db.get(user_id, {})
    level = p.get("iron_mine_level", 1)
    iron = p.get("iron", 0)
    rate = level * 100
    cap = level * 500
    cost = (level + 1) * 5000

    percent = min(int((iron / cap) * 100), 100) if cap > 0 else 0
    filled = percent // 10
    bar = "█" * filled + "░" * (10 - filled)

    text = f"⛏️ معدن آهن\n\n📊 سطح: {level}/10\n"
    text += f"📦 آهن: {iron:,} / {cap:,}\n"
    text += f"{bar} {percent}%\n"
    text += f"⚙️ تولید: {rate:,} آهن/ساعت\n🪙 سکه: {p.get('coins', 0):,}\n\n"
    if level >= 10:
        text += "🚫 حداکثر سطح\n"
    else:
        text += f"⬆️ ارتقا به سطح {level+1}:\n   🪙 هزینه: {cost:,} سکه\n"
    return text


def build_iron_keyboard(user_id):
    p = db.get(user_id, {})
    level = p.get("iron_mine_level", 1)
    iron = p.get("iron", 0)
    items = []
    if iron > 0:
        items.append({"text": f"📦 برداشت آهن ({iron:,})",
                      "callback_data": "iron_collect"})
    if level < 10:
        cost = (level + 1) * 5000
        items.append({"text": f"⬆️ ارتقا ({cost:,} سکه)",
                      "callback_data": "iron_upgrade"})
    buttons = []
    for i in range(0, len(items), 2):
        buttons.append(items[i:i + 2])
    buttons.append([{"text": "🔙 بازگشت به منوی اصلی",
                     "callback_data": "go_factory"}])
    return {"inline_keyboard": buttons}


def build_steel_text(user_id):
    p = db.get(user_id, {})
    level = p.get("steel_factory_level", 0)
    steel = p.get("steel", 0)
    iron = p.get("iron", 0)

    if level == 0:
        return (f"🏭 کارخانه فولاد\n\n❌ ساخته نشده!\n\n"
                f"🪙 هزینه ساخت: 50,000 سکه\n"
                f"⛏️ نیاز: 500 آهن\n"
                f"📦 آهن فعلی: {iron:,}\n"
                f"🎯 لول مورد نیاز: 25\n")

    rate = level * 50
    cap = level * 250
    cost = (level + 1) * 10000

    percent = min(int((steel / cap) * 100), 100) if cap > 0 else 0
    filled = percent // 10
    bar = "█" * filled + "░" * (10 - filled)

    text = f"🏭 کارخانه فولاد\n\n📊 سطح: {level}/10\n"
    text += f"📦 فولاد: {steel:,} / {cap:,}\n"
    text += f"{bar} {percent}%\n"
    text += f"⚙️ تولید: {rate:,} فولاد/ساعت\n"
    text += f"⛏️ آهن: {iron:,}\n🪙 سکه: {p.get('coins', 0):,}\n\n"
    if level >= 10:
        text += "🚫 حداکثر سطح\n"
    else:
        text += f"⬆️ ارتقا به سطح {level+1}:\n   🪙 هزینه: {cost:,} سکه\n"
    return text


def build_steel_keyboard(user_id):
    p = db.get(user_id, {})
    level = p.get("steel_factory_level", 0)
    buttons = []
    if level == 0:
        buttons.append([{"text": "🛒 ساخت (50,000 سکه)",
                         "callback_data": "steel_build"}])
    else:
        items = []
        steel = p.get("steel", 0)
        if steel > 0:
            items.append({"text": f"📦 برداشت فولاد ({steel:,})",
                          "callback_data": "steel_collect"})
        if level < 10:
            cost = (level + 1) * 10000
            items.append({"text": f"⬆️ ارتقا ({cost:,} سکه)",
                          "callback_data": "steel_upgrade"})
        for i in range(0, len(items), 2):
            buttons.append(items[i:i + 2])
    buttons.append([{"text": "🔙 بازگشت به منوی اصلی",
                     "callback_data": "go_factory"}])
    return {"inline_keyboard": buttons}


def build_weapon_text(user_id):
    p = db.get(user_id, {})
    level = p.get("weapon_factory_level", 0)
    weapon = p.get("weapon", 0)
    steel = p.get("steel", 0)

    if level == 0:
        return (f"⚔️ کارخانه سلاح\n\n❌ ساخته نشده!\n\n"
                f"🪙 هزینه ساخت: 100,000 سکه\n"
                f"🏭 نیاز: 500 فولاد\n"
                f"📦 فولاد فعلی: {steel:,}\n"
                f"🎯 لول مورد نیاز: 40\n")

    rate = level * 10
    cap = level * 50
    cost = (level + 1) * 20000

    percent = min(int((weapon / cap) * 100), 100) if cap > 0 else 0
    filled = percent // 10
    bar = "█" * filled + "░" * (10 - filled)

    text = f"⚔️ کارخانه سلاح\n\n📊 سطح: {level}/10\n"
    text += f"📦 سلاح: {weapon:,} / {cap:,}\n"
    text += f"{bar} {percent}%\n"
    text += f"⚙️ تولید: {rate:,} سلاح/ساعت\n"
    text += f"🏭 فولاد: {steel:,}\n🪙 سکه: {p.get('coins', 0):,}\n\n"
    if level >= 10:
        text += "🚫 حداکثر سطح\n"
    else:
        text += f"⬆️ ارتقا به سطح {level+1}:\n   🪙 هزینه: {cost:,} سکه\n"
    return text


def build_weapon_keyboard(user_id):
    p = db.get(user_id, {})
    level = p.get("weapon_factory_level", 0)
    buttons = []
    if level == 0:
        buttons.append([{"text": "🛒 ساخت (100,000 سکه)",
                         "callback_data": "weapon_build"}])
    else:
        items = []
        weapon = p.get("weapon", 0)
        if weapon > 0:
            items.append({"text": f"📦 برداشت سلاح ({weapon:,})",
                          "callback_data": "weapon_collect"})
        if level < 10:
            cost = (level + 1) * 20000
            items.append({"text": f"⬆️ ارتقا ({cost:,} سکه)",
                          "callback_data": "weapon_upgrade"})
        for i in range(0, len(items), 2):
            buttons.append(items[i:i + 2])
    buttons.append([{"text": "🔙 بازگشت به منوی اصلی",
                     "callback_data": "go_factory"}])
    return {"inline_keyboard": buttons}


def build_factory_sell_text(user_id):
    p = db.get(user_id, {})
    return (f"🪙 فروشگاه کارخانه\n\n"
            f"⛏️ آهن: {p.get('iron', 0):,} (هر عدد 10 سکه)\n"
            f"🏭 فولاد: {p.get('steel', 0):,} (هر عدد 50 سکه)\n"
            f"⚔️ سلاح: {p.get('weapon', 0):,} (هر عدد 500 سکه)\n\n"
            f"🪙 سکه: {p.get('coins', 0):,}\n\n🔻 چی می‌خوای بفروشی؟")


def build_factory_sell_keyboard():
    return {"inline_keyboard": [
        [{"text": "⛏️ فروش آهن", "callback_data": "sell_iron"},
         {"text": "🏭 فروش فولاد", "callback_data": "sell_steel"}],
        [{"text": "⚔️ فروش سلاح", "callback_data": "sell_weapon"}],
        [{"text": "🔙 بازگشت به منوی اصلی", "callback_data": "go_factory"}],
    ]}


# ==================== رنکینگ روزانه ====================
def build_daily_ranking(page=0, my_user_id=None):
    per_page = 10
    today = datetime.now().strftime("%Y-%m-%d")

    my_today = 0
    my_name = "شما"
    my_rank = 0
    my_pos = 0
    if my_user_id:
        my_user_id = str(my_user_id)
        me = db.get(my_user_id, {})
        my_name = me.get("name", "شما")
        my_rank = me.get("rank", 0)
        if me.get("rank_date") == today:
            my_today = me.get("rank_today", 0)

    users = []
    for uid, p in db.items():
        if not isinstance(p, dict):
            continue
        if "user_id" not in p:
            continue
        if p.get("banned"):
            continue
        if p.get("rank_date") != today:
            continue
        rt = p.get("rank_today", 0)
        if rt < 1:
            continue
        users.append({
            "name": p.get("name", "کاربر"),
            "rank_today": rt,
            "uid": uid,
            "rank": p.get("rank", 0),
        })
    users.sort(key=lambda x: x["rank_today"], reverse=True)

    top_users = users[:10]

    if my_user_id:
        for i, u in enumerate(users, 1):
            if u["uid"] == my_user_id:
                my_pos = i
                break

    text = "🌼 *رنکینگ روزانه*\n\n"
    if not top_users:
        text += "❌ هنوز کسی امروز امتیاز نگرفته!\n"
    else:
        for i, u in enumerate(top_users, 1):
            league_emoji = get_league(u["rank"]).split()[0]
            text += f"{i}- {league_emoji} {u['name']} ‏- {u['rank_today']} ⭐️\n"

    text += "\n➖➖➖➖➖\n📌 رتبه تو\n"
    my_league_emoji = get_league(my_rank).split()[0]
    if my_pos > 0:
        text += f"{my_pos}. {my_league_emoji} {my_name} - {my_today} ⭐️\n"
    else:
        text += f"—. {my_league_emoji} {my_name} - {my_today} ⭐️\n"

    text += f"\nصفحه 1 از 1"

    buttons = [[
        {"text": "🏅 برترین‌ها", "callback_data": "rank_p_0"},
        {"text": "👥 کلن", "callback_data": "rank_clan"},
        {"text": "📆 روزانه", "callback_data": "rank_daily"},
    ]]
    buttons.append([{"text": "🔄 بروزرسانی", "callback_data": "rank_daily"}])
    buttons.append([{"text": "🔙 بازگشت به منوی اصلی", "callback_data": "go_main"}])
    return text, {"inline_keyboard": buttons}


# ==================== منابع ====================
def update_mine_coins(user_id):
    p = db.get(user_id, {})
    level = p.get("mine_level", 1)
    rate = level * 100
    cap = level * 300
    now = time.time()
    last = p.get("mine_last_dig", 0)
    if last == 0:
        db[user_id]["mine_last_dig"] = now
        save_db()
        return
    sp = int(now - last)
    if sp <= 0:
        return
    earned = (sp * rate) // 3600
    if earned <= 0:
        return
    db[user_id]["mine_coins"] = min(p.get("mine_coins", 0) + earned, cap)
    db[user_id]["mine_last_dig"] = now
    save_db()


def update_refinery_oil(user_id):
    p = db.get(user_id, {})
    level = p.get("refinery_level", 0)
    if level == 0:
        return
    rate = get_refinery_rate(level)
    cap = get_refinery_cap(level)
    now = time.time()
    last = p.get("oil_last_dig", 0)
    if last == 0:
        db[user_id]["oil_last_dig"] = now
        save_db()
        return
    sp = int(now - last)
    if sp <= 0:
        return
    earned = (sp * rate) // 3600
    if earned <= 0:
        return
    db[user_id]["refinery_oil"] = min(p.get("refinery_oil", 0) + earned, cap)
    db[user_id]["oil_last_dig"] = now
    save_db()


def build_resources_text(user_id):
    update_mine_coins(user_id)
    update_refinery_oil(user_id)
    update_factory_iron(user_id)
    update_factory_steel(user_id)
    update_factory_weapon(user_id)

    p = db.get(user_id, {})

    ml = p.get("mine_level", 1)
    mr = ml * 100
    mc = mr * 3
    mc_have = p.get("mine_coins", 0)
    mp = min(int((mc_have / mc) * 100), 100) if mc > 0 else 0
    mf = mp // 10
    mbar = "█" * mf + "░" * (10 - mf)
    mstat = "معدن در حداکثر سطح است 🚫" if ml >= 40 else f"🔼 ارتقا به سطح {ml+1}"

    rl = p.get("refinery_level", 0)
    if rl == 0:
        rtext = ("❌ شما پالایشگاه ندارید!\n"
                 "🪙 هزینه خرید: 10,000 سکه\n🎯 لول مورد نیاز: 10\n")
        rbar = "░" * 10
        rp = 0
    else:
        rr = get_refinery_rate(rl)
        rc = get_refinery_cap(rl)
        rh = p.get("refinery_oil", 0)
        rp = min(int((rh / rc) * 100), 100) if rc > 0 else 0
        rf = rp // 10
        rbar = "█" * rf + "░" * (10 - rf)
        rstat = ("پالایشگاه در حداکثر سطح است 🚫" if rl >= 10
                 else f"🔼 ارتقا به سطح {rl+1}")
        rtext = (f"📊 سطح: {rl}/10\n{rstat}\n"
                 f"تولید: {rr:,} نفت/ساعت\n"
                 f"آماده: {rh:,} نفت\n"
                 f"سقف: 4 ساعت\n{rbar} {rp}%")

    il = p.get("iron_mine_level", 1)
    sl = p.get("steel_factory_level", 0)
    wl = p.get("weapon_factory_level", 0)
    iron = p.get("iron", 0)
    steel = p.get("steel", 0)
    weapon = p.get("weapon", 0)

    iron_cap = il * 500
    ip = min(int((iron / iron_cap) * 100), 100) if iron_cap > 0 else 0
    ifill = ip // 10
    ibar = "█" * ifill + "░" * (10 - ifill)

    ftext = f"⛏️ معدن آهن (سطح {il})\n"
    ftext += f"   📦 {iron:,}/{iron_cap:,}  |  ⚙️ {il*100:,}/ساعت\n"
    ftext += f"   {ibar} {ip}%\n"

    if sl > 0:
        steel_cap = sl * 250
        sp = min(int((steel / steel_cap) * 100), 100) if steel_cap > 0 else 0
        sfill = sp // 10
        sbar = "█" * sfill + "░" * (10 - sfill)
        ftext += f"\n🏭 فولاد (سطح {sl})\n"
        ftext += f"   📦 {steel:,}/{steel_cap:,}  |  ⚙️ {sl*50:,}/ساعت\n"
        ftext += f"   {sbar} {sp}%\n"
    else:
        ftext += "\n🏭 فولاد: ❌ ساخته نشده (لول 25)\n"

    if wl > 0:
        weapon_cap = wl * 50
        wp = min(int((weapon / weapon_cap) * 100), 100) if weapon_cap > 0 else 0
        wfill = wp // 10
        wbar = "█" * wfill + "░" * (10 - wfill)
        ftext += f"\n⚔️ سلاح (سطح {wl})\n"
        ftext += f"   📦 {weapon:,}/{weapon_cap:,}  |  ⚙️ {wl*10:,}/ساعت\n"
        ftext += f"   {wbar} {wp}%\n"
    else:
        ftext += "\n⚔️ سلاح: ❌ ساخته نشده (لول 40)\n"

    text = "🏦 مرکز منابع\n\n"
    text += f"🪙 معدن سکه\n📊 سطح: {ml}\n{mstat}\n"
    text += f"تولید: {mr:,} سکه/ساعت\nآماده: {mc_have:,} سکه\n"
    text += f"سقف: 3 ساعت\n{mbar} {mp}%\n\n"
    text += "➖➖➖➖➖➖➖➖➖➖\n\n"

    text += f"🏭 پالایشگاه نفت\n{rtext}\n\n"
    text += "➖➖➖➖➖➖➖➖➖➖\n\n"

    text += f"⚙️ کارخانه\n{ftext}\n"

    text += "🔻 یکی از منابع زیر را انتخاب کنید 👇"
    return text


def build_resources_keyboard():
    return {"inline_keyboard": [
        [{"text": "🪙 معدن سکه", "callback_data": "res_mine"},
         {"text": "🏭 پالایشگاه نفت", "callback_data": "res_refinery"}],
        [{"text": "🏭 کارخانه", "callback_data": "go_factory"}],
        [{"text": "🔙 بازگشت به منوی اصلی", "callback_data": "go_main"}],
    ]}


def build_mine_text(user_id):
    p = db.get(user_id, {})
    level = p.get("mine_level", 1)
    mc = p.get("mine_coins", 0)
    rate = level * 100
    cap = level * 300
    cost = (level + 1) * 1000

    percent = min(int((mc / cap) * 100), 100) if cap > 0 else 0
    filled = percent // 10
    bar = "█" * filled + "░" * (10 - filled)

    text = (f"🏦 منابع\n\n📊 سطح معدن: {level}\n"
            f"🪙 سکه‌های آماده: {mc}\n"
            f"{bar} {percent}%\n"
            f"📅 تولید: هر ساعت {rate} سکه\n📦 سقف: {cap} سکه\n")
    if level < 40:
        text += f"💎 ارتقا به سطح {level+1}: {cost} سکه"
    else:
        text += "🚫 معدن در حداکثر سطح است"
    return text


def build_mine_keyboard():
    return {"inline_keyboard": [
        [{"text": "🪙 برداشت سکه", "callback_data": "mine_collect"},
         {"text": "🔼 ارتقا معدن", "callback_data": "mine_upgrade"}],
        [{"text": "🔙 بازگشت به منوی اصلی", "callback_data": "go_resources"}],
    ]}


def build_refinery_keyboard_from_mine():
    return {"inline_keyboard": [
        [{"text": "🛢️ برداشت نفت", "callback_data": "ref_collect"},
         {"text": "🔼 ارتقا پالایشگاه", "callback_data": "ref_upgrade"}],
        [{"text": "🔙 بازگشت به منوی اصلی", "callback_data": "go_mine"}],
    ]}


def build_refinery_keyboard():
    return {"inline_keyboard": [
        [{"text": "🛢️ برداشت نفت", "callback_data": "ref_collect"},
         {"text": "🔼 ارتقا پالایشگاه", "callback_data": "ref_upgrade"}],
        [{"text": "🔙 بازگشت به منوی اصلی", "callback_data": "go_main"}],
    ]}


def build_refinery_text(user_id):
    p = db.get(user_id, {})
    level = p.get("refinery_level", 0)
    oil = p.get("refinery_oil", 0)
    if level == 0:
        return ("🏭 پالایشگاه نفت\n\n❌ شما پالایشگاه ندارید!\n\n"
                "🪙 هزینه خرید: 10,000 سکه\n🎯 لول مورد نیاز: 10\n\n🔻 برای خرید:")
    rate = level * 40
    cap = rate * 4
    percent = min(int((oil / cap) * 100), 100) if cap > 0 else 0
    filled = percent // 10
    bar = "█" * filled + "░" * (10 - filled)
    status = ("پالایشگاه در حداکثر سطح است 🚫" if level >= 10
              else f"🔼 ارتقا به سطح {level+1}")
    return (f"🏭 پالایشگاه نفت\n\n🔼 سطح پالایشگاه: {level}/10\n{status}\n"
            f"🛢 نفت آماده جمع‌آوری: {oil:,}\n"
            f"⚙️ تولید: {rate:,} نفت در هر 1 ساعت\n"
            f"🔴 حداکثر تولید قابل جمع‌آوری: 4 ساعت\n{bar} {percent}%")


# ==================== فرودگاه ====================
def build_airport_text(user_id):
    p = db.get(user_id, {})
    level = p.get("airport_level", 0)
    if level == 0:
        return ("🛩 فرودگاه\n\n❌ شما فرودگاه ندارید!\n\n"
                "🪙 هزینه خرید: 5,000 سکه\n"
                "🔒 برای خرید، سطح کاربر 10 لازمه\n\n"
                "🛒 برای خرید از دکمه زیر استفاده کن")
    cap = AIRPORT_LEVELS.get(level, AIRPORT_LEVELS[1])
    drone_count = len(p.get("drones", {}))
    text = (f"🛩 فرودگاه\n\n📊 سطح فرودگاه: {level}/7\n"
            f"🛢️ نفت: {p.get('oil', 0):,}\n"
            f"🛩 پهبادها: {drone_count}/{cap['drone_cap']}\n")
    if level < 7:
        cost = AIRPORT_LEVELS[level + 1]["upgrade_cost"]
        text += f"\n💎 ارتقا به سطح {level+1}: {cost:,} نفت"
        text += (f"\n🔒 ظرفیت جدید: {AIRPORT_LEVELS[level+1]['fighter_cap']} جنگنده + "
                 f"{AIRPORT_LEVELS[level+1]['drone_cap']} پهباد")
    else:
        text += "\n🚫 فرودگاه در حداکثر سطح است"
    return text


def build_airport_keyboard(user_id):
    p = db.get(user_id, {})
    level = p.get("airport_level", 0)
    if level == 0:
        return {"inline_keyboard": [
            [{"text": "🛒 خرید فرودگاه (5,000 سکه)",
              "callback_data": "airport_buy"}],
            [{"text": "📖 راهنما", "callback_data": "help_airport"}],
            [{"text": "🔙 بازگشت به منوی اصلی", "callback_data": "go_main"}],
        ]}
    return {"inline_keyboard": [
        [{"text": "🔼 ارتقا فرودگاه", "callback_data": "airport_upgrade"},
         {"text": "🛩 خرید پهباد", "callback_data": "airport_buy_drone"}],
        [{"text": "📖 راهنما", "callback_data": "help_airport"}],
        [{"text": "🔙 بازگشت به منوی اصلی", "callback_data": "go_main"}],
    ]}


# ==================== پروفایل ====================
def build_profile(chat_id, user_name):
    from core import create_user, is_subscription_active
    user_id = str(chat_id)
    if user_id not in db or not isinstance(db.get(user_id), dict):
        create_user(user_id, user_name)
    p = db[user_id]
    if p.get("name") != user_name:
        p["name"] = user_name
        save_db()
    name = p.get("name", "کاربر")
    uid = p.get("user_id", "?")
    join_date = p.get("join_date", "نامشخص")
    total_damage = p.get("total_damage", 0)
    level, cur, need = get_level_info(total_damage)
    coins = p.get("coins", 0)
    gems = p.get("gems", 0)
    oil = p.get("oil", 0)
    rank = p.get("rank", 0)
    best_rank = p.get("best_rank", 0)
    league = get_league(rank)
    shield = p.get("shield", "ندارد")

    wp_badge = " 👑" if p.get("world_pass_active") else ""
    sub_badge = " ⭐️" if is_subscription_active(user_id) else ""

    text = (f"👤 کاربر: {name}{wp_badge}{sub_badge}\n🔢 آیدی عددی: {uid}\n"
            f"📆 تاریخ عضویت: {join_date}\n\n"
            f"🔼 سطح: {level}\n⭐ تجربه: {cur}/{need}\n"
            f"🪙 سکه: {coins:,}\n🛢️ نفت: {oil:,}\n💎 الماس: {gems:,}\n"
            f"🏆 رنک: {rank:,}\n"
            f"🏵 بالاترین رنک: {best_rank:,}\n"
            f"🏅 لیگ: {league}\n\n"
            f"🛡️ سپر فعال: {shield}\n\n")

    assets = ""
    any_assets = False
    for cat_key, cat_label in [("cruise", "🧨 کروز"),
                                ("ballistic", "🚀 بالستیک"),
                                ("hypersonic", "⚡ هایپرسونیک"),
                                ("chemical", "☣️ شیمیایی"),
                                ("nuclear", "☢️ هسته‌ای"),
                                ("fighters", "✈️ جنگنده"),
                                ("defense", "🛡️ پدافندها"),
                                ("drones", "🛩 پهباد")]:
        items = [(n, i) for n, i in p.get(cat_key, {}).items()
                 if i.get("count", 0) > 0]
        if items:
            any_assets = True
            assets += f"{cat_label}:\n"
            for wn, info in items:
                if cat_key in ["cruise", "ballistic", "hypersonic", "nuclear"]:
                    if is_wheel_only(wn):
                        assets += f"• {wn}: {info.get('count',0):,} (گردونه)\n"
                    else:
                        assets += f"• {wn} (سطح {info.get('level',1)}): {info.get('count',0):,}\n"
                else:
                    assets += f"• {wn}: {info.get('count',0):,}\n"
            assets += "\n"

    hero_fighters = p.get("fighters_hero", {})
    hero_items = [(n, i) for n, i in hero_fighters.items() if i.get("count", 0) > 0]
    if hero_items:
        any_assets = True
        assets += "✈️ جنگنده‌های هیرو:\n"
        for fn, info in hero_items:
            lvl = info.get("level", 1)
            if fn == "فونیکس":
                assets += f"• {fn} (سطح {lvl}): {info.get('count', 0):,}\n"
            else:
                assets += f"• {fn}: {info.get('count', 0):,}\n"
        assets += "\n"

    tal_text = ""
    for key, label in [("talisman_eye_count", "🧿 چشم"),
                        ("talisman_fire_count", "🔥 آتش"),
                        ("talisman_water_count", "💧 آب"),
                        ("talisman_storm_count", "🌪 طوفان"),
                        ("talisman_lightning_count", "⚡ صاعقه"),
                        ("talisman_shield_count", "🛡 سپر"),
                        ("talisman_hunt_count", "👁 شکار"),
                        ("talisman_ice_count", "❄️ یخ")]:
        v = p.get(key, 0)
        if v > 0:
            tal_text += f"• {label}: {v:,}\n"
    if tal_text:
        any_assets = True
        assets += "✨ طلسم‌ها:\n" + tal_text + "\n"

    f2 = p.get("fatah2_count", 0)
    if f2 > 0:
        any_assets = True
        assets += f"🧨 موشک ویژه:\n• ⚡ فتاح 2: {f2:,}\n"

    if any_assets:
        text += "📦 دارایی:\n\n" + assets
    else:
        text += "📦 دارایی:\n\n❌ هیچ دارایی نداری!\n"

    return text


# ==================== فروشگاه ====================
def build_shop_text(user_id):
    p = db.get(user_id, {})
    coins = p.get("coins", 0)
    oil = p.get("oil", 0)
    gems = p.get("gems", 0)
    lvl, _, _ = get_level_info(p.get("total_damage", 0))
    return (f"🏪 به فروشگاه ⚜️WORLD WAR⚜️ خوش آمدید\n\n"
            f"🪙 سکه‌های شما: {coins:,}\n"
            f"💎 الماس شما: {gems}\n"
            f"🛢 نفت شما: {oil:,}\n📊 لول شما: {lvl}\n\n"
            f"🔻 یکی از دسته‌ها رو برای خرید انتخاب کن:")


def build_shop_keyboard(user_id=None):
    return {"inline_keyboard": [
        [{"text": "🚀 موشک", "callback_data": "shop_missile"},
         {"text": "🛡️ پدافند", "callback_data": "shop_defense"}],
        [{"text": "🔮 طلسم", "callback_data": "shop_talisman"},
         {"text": "🛩 پهباد", "callback_data": "shop_drone"}],
        [{"text": "📖 راهنما", "callback_data": "help_shop"}],
        [{"text": "🔙 بازگشت به منوی اصلی", "callback_data": "go_start"}],
    ]}


def build_missile_keyboard():
    return {"inline_keyboard": [
        [{"text": "🧨 کروز", "callback_data": "shop_cruise"},
         {"text": "🚀 بالستیک", "callback_data": "shop_ballistic"}],
        [{"text": "⚡ هایپرسونیک", "callback_data": "shop_hypersonic"},
         {"text": "☣️ شیمیایی", "callback_data": "shop_chemical"}],
        [{"text": "☢️ هسته‌ای", "callback_data": "shop_nuclear"}],
        [{"text": "🔙 بازگشت به منوی اصلی", "callback_data": "shop_back"}],
    ]}


# ==================== 🧪 آزمایشگاه ====================
def build_lab_keyboard(user_id):
    return {"inline_keyboard": [
        [{"text": "🚀 ارتقا موشک", "callback_data": "lab_upgrade_missile"},
         {"text": "🔼 ارتقا آزمایشگاه", "callback_data": "lab_upgrade"}],
        [{"text": "🔬 دانشمندان", "callback_data": "lab_scientists"}],
        [{"text": "📖 راهنما", "callback_data": "help_lab"}],
        [{"text": "🔙 بازگشت به منوی اصلی", "callback_data": "go_main"}],
    ]}


def build_lab_text(user_id):
    p = db.get(user_id, {})
    rl = p.get("research_level", 1)
    user_level, _, _ = get_level_info(p.get("total_damage", 0))
    coins = p.get("coins", 0)

    text = f"🧪 آزمایشگاه\n\n📊 سطح فعلی: *{rl}/{LAB_MAX_LEVEL}*\n"
    text += f"👤 سطح شما: *{user_level}*\n"
    text += f"🪙 سکه: *{coins:,}*\n\n"

    text += "📋 *قفل‌های بازشده ارتقای موشک:*\n"
    for lvl_check in [1, 2, 3, 4, 5]:
        req = LAB_MISSILE_UPGRADE_REQUIREMENTS.get(lvl_check, 6)
        label = f"موشک {lvl_check}→{lvl_check+1}"
        if rl >= req:
            text += f"   ✅ {label} (لاب {req})\n"
        else:
            text += f"   🔒 {label} (نیاز: لاب {req})\n"

    text += "\n"

    if rl >= LAB_MAX_LEVEL:
        text += "🚫 آزمایشگاه در حداکثر سطح است\n"
    else:
        cost = LAB_UPGRADE_COSTS.get(rl, 0)
        req_user = LAB_UPGRADE_USER_LEVELS.get(rl, 0)
        text += f"⬆️ *ارتقا به سطح {rl + 1}:*\n"
        text += f"   🪙 هزینه: *{cost:,}* سکه\n"
        text += f"   👤 لول کاربر لازم: *{req_user}*\n"
        if user_level < req_user:
            text += f"   ❌ سطح شما کافی نیست! (نیاز: {req_user - user_level} لول بیشتر)\n"

    return text


# ==================== 🔬 دانشمندان ====================
def _fmt_remaining(seconds):
    seconds = int(seconds)
    if seconds <= 0:
        return "الان"
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h} ساعت و {m} دقیقه"
    elif m > 0:
        return f"{m} دقیقه و {s} ثانیه"
    return f"{s} ثانیه"


def get_actual_upgrade_time(user_id, base_duration):
    p = db.get(user_id, {})
    boost = p.get("active_boost")
    if not boost or not isinstance(boost, dict):
        return base_duration
    if time.time() >= boost.get("expires_at", 0):
        return base_duration
    mult = boost.get("time_multiplier", 1.0)
    return max(1, int(base_duration * mult))


def get_busy_scientists(user_id):
    p = db.get(user_id, {})
    upgrades = p.get("upgrades", {})
    now = time.time()
    busy = set()
    for key, up in upgrades.items():
        if now < up.get("end_time", 0):
            busy.add(up.get("scientist_id", 1))
    return busy


def get_free_scientist(user_id):
    p = db.get(user_id, {})
    count = p.get("scientists_count", 1)
    busy = get_busy_scientists(user_id)
    for i in range(1, count + 1):
        if i not in busy:
            return i
    return None


def build_upgrade_started_text(missile_name, current_level, new_level,
                                scientist_id, duration, end_time):
    end_str = datetime.fromtimestamp(end_time).strftime("%Y-%m-%d %H:%M:%S")
    return (f"✅ ارتقای «{missile_name}» شروع شد!\n\n"
            f"سطح فعلی: {current_level}\n"
            f"سطح بعدی: {new_level}\n"
            f"🔬 دانشمند: {scientist_id}\n"
            f"⏳ زمان: {duration} دقیقه\n"
            f"🕒 پایان: {end_str}")


def build_scientists_text(user_id):
    p = db.get(user_id, {})
    count = p.get("scientists_count", 1)
    upgrades = p.get("upgrades", {})
    now = time.time()
    gems = p.get("gems", 0)

    busy = {}
    for key, up in upgrades.items():
        if now < up.get("end_time", 0):
            busy[up.get("scientist_id", 1)] = up

    text = "🔬 دانشمندان\n\n"

    text += "🔬 دانشمند شماره یک\n"
    if 1 in busy:
        up = busy[1]
        cat = up.get("category", "")
        missile = up.get("missile", "?")
        lvl = db[user_id].get(cat, {}).get(missile, {}).get("level", 1)
        remaining = int(up["end_time"] - now)
        end_str = datetime.fromtimestamp(up["end_time"]).strftime("%Y-%m-%d %H:%M:%S")
        text += f"🔬 در حال ارتقای: {missile} (سطح {lvl} → {lvl+1})\n"
        text += f"⏳ باقی‌مانده: {_fmt_remaining(remaining)}\n"
        text += f"🕒 پایان: {end_str}\n"
    else:
        text += "❌ در حال حاضر این دانشمند بیکار است\n"

    text += "➖➖➖➖➖\n"

    text += "🔬 دانشمند شماره دو\n"
    if count >= 2:
        if 2 in busy:
            up = busy[2]
            cat = up.get("category", "")
            missile = up.get("missile", "?")
            lvl = db[user_id].get(cat, {}).get(missile, {}).get("level", 1)
            remaining = int(up["end_time"] - now)
            end_str = datetime.fromtimestamp(up["end_time"]).strftime("%Y-%m-%d %H:%M:%S")
            text += f"🔬 در حال ارتقای: {missile} (سطح {lvl} → {lvl+1})\n"
            text += f"⏳ باقی‌مانده: {_fmt_remaining(remaining)}\n"
            text += f"🕒 پایان: {end_str}\n"
        else:
            text += "❌ در حال حاضر این دانشمند بیکار است\n"
    else:
        text += f"💎 خرید این دانشمند با هزینه {SCIENTIST_2_COST} الماس\n"
        text += "برای خرید از دکمه «💎 خرید دانشمند دوم» استفاده کنید.\n"
        text += "❗️ با خرید این دانشمند می‌توانید همزمان دو موشک ارتقا دهید.\n"
        text += f"💰 الماس شما: {gems}\n"

    text += "➖➖➖➖➖\n"

    boost = p.get("active_boost")
    if boost and isinstance(boost, dict) and boost.get("expires_at", 0) > now:
        bname = BOOST_TYPES.get(boost.get("type", "20"), {}).get("name", "?")
        exp_str = _fmt_remaining(int(boost["expires_at"] - now))
        text += f"🟢 بوست فعال: {bname} (تا {exp_str} دیگر)\n\n"
    else:
        text += "❌ بوست فعال ندارید.\n\n"

    text += "🟢 با خرید بوست برای 🔬 دانشمندان سرعت آنها را می‌توانید افزایش دهید."

    return text


def build_scientists_keyboard(user_id):
    p = db.get(user_id, {})
    count = p.get("scientists_count", 1)
    gems = p.get("gems", 0)
    boost = p.get("active_boost")
    now = time.time()
    boost_active = bool(boost and isinstance(boost, dict) and boost.get("expires_at", 0) > now)

    buttons = []

    if count < 2:
        if gems >= SCIENTIST_2_COST:
            buttons.append([{"text": f"💎 خرید دانشمند دوم ({SCIENTIST_2_COST} الماس)",
                             "callback_data": "buy_scientist"}])
        else:
            buttons.append([{"text": f"🔒 خرید دانشمند دوم ({SCIENTIST_2_COST} الماس - کمبود الماس)",
                             "callback_data": "no_gems"}])

    if not boost_active:
        buttons.append([{"text": "🟢 خرید بوست",
                         "callback_data": "lab_boost"}])

    buttons.append([{"text": "🔙 بازگشت به آزمایشگاه",
                     "callback_data": "lab_back"}])
    return {"inline_keyboard": buttons}


def build_boost_text(user_id):
    p = db.get(user_id, {})
    gems = p.get("gems", 0)
    boost = p.get("active_boost")
    now = time.time()

    text = "🟢 بوست دانشمندان\n\n"
    text += f"💎 الماس شما: {gems}\n\n"

    if boost and isinstance(boost, dict) and boost.get("expires_at", 0) > now:
        bname = BOOST_TYPES.get(boost.get("type", "20"), {}).get("name", "?")
        exp_str = _fmt_remaining(int(boost["expires_at"] - now))
        text += f"⚠️ شما یک بوست فعال دارید: {bname} (تا {exp_str} دیگر)\n\n"

    text += "یکی از بوست‌ها را انتخاب کنید:\n\n"
    text += "1⃣ بوست 20 درصدی با 15 الماس خریداری میشه و باعث کاهش زمان ارتقا تا 20 درصد میشود و تا یک ساعت اعتبار دارد.\n\n"
    text += "2⃣ بوست 50 درصدی با 40 الماس خریداری میشه و باعث کاهش زمان ارتقا تا 50 درصد میشود و تا یک ساعت اعتبار دارد.\n\n"
    text += "💥 بوست دو برابری با 80 الماس خریداری میشه و باعث دو برابر شدن سرعت دانشمندان میشود و زمان ارتقای موشک ها تا 2 برابر کاهش می‌یابد و تا 2 ساعت اعتبار دارد.\n\n"
    text += "❌ دقت کنید باید قبل از ارتقا بوست رو فعال کنید. بوست روی ارتقا های در حال انجام تاثیری ندارد."

    return text


def build_boost_keyboard(user_id):
    p = db.get(user_id, {})
    gems = p.get("gems", 0)
    boost = p.get("active_boost")
    now = time.time()
    boost_active = bool(boost and isinstance(boost, dict) and boost.get("expires_at", 0) > now)

    buttons = []

    if not boost_active:
        if gems >= 15:
            buttons.append([{"text": "1⃣ بوست 20% (15 الماس)",
                             "callback_data": "buy_boost_20"}])
        else:
            buttons.append([{"text": "🔒 بوست 20% (15 الماس)",
                             "callback_data": "no_gems"}])

        if gems >= 40:
            buttons.append([{"text": "2⃣ بوست 50% (40 الماس)",
                             "callback_data": "buy_boost_50"}])
        else:
            buttons.append([{"text": "🔒 بوست 50% (40 الماس)",
                             "callback_data": "no_gems"}])

        if gems >= 80:
            buttons.append([{"text": "💥 بوست 2x (80 الماس)",
                             "callback_data": "buy_boost_100"}])
        else:
            buttons.append([{"text": "🔒 بوست 2x (80 الماس)",
                             "callback_data": "no_gems"}])

    buttons.append([{"text": "🔙 بازگشت به دانشمندان",
                     "callback_data": "lab_scientists"}])
    return {"inline_keyboard": buttons}


# ==================== ارتقا موشک ====================
def check_level_requirement(user_id, shop_key):
    if shop_key not in LEVEL_REQUIREMENTS:
        return True, 0
    required = LEVEL_REQUIREMENTS[shop_key]
    p = db.get(user_id, {})
    total_damage = p.get("total_damage", 0)
    level, _, _ = get_level_info(total_damage)
    if level >= required:
        return True, level
    return False, level


def check_upgrade_in_progress(user_id, missile_name, category):
    p = db.get(user_id, {})
    upgrades = p.get("upgrades", {})
    key = f"{category}_{missile_name}"
    return upgrades.get(key)


def start_upgrade(user_id, missile_name, category, cost, duration, scientist_id):
    p = db.get(user_id, {})
    if "upgrades" not in p:
        db[user_id]["upgrades"] = {}
    now = time.time()
    key = f"{category}_{missile_name}"
    db[user_id]["upgrades"][key] = {
        "missile": missile_name,
        "category": category,
        "start_time": now,
        "end_time": now + (duration * 60),
        "cost": cost,
        "scientist_id": scientist_id,
    }
    save_db()


def check_finished_upgrades(user_id):
    p = db.get(user_id, {})
    upgrades = p.get("upgrades", {})
    now = time.time()
    finished = []
    for key, up in list(upgrades.items()):
        if now >= up["end_time"]:
            mn = up["missile"]
            cat = up["category"]
            if cat in db[user_id] and mn in db[user_id][cat]:
                current_lvl = db[user_id][cat][mn].get("level", 1)
                db[user_id][cat][mn]["level"] = min(current_lvl + 1, MISSILE_MAX_LEVEL)
                finished.append(f"{mn} - سطح {db[user_id][cat][mn]['level']}")
            del db[user_id]["upgrades"][key]
    if finished:
        save_db()
    return finished


def build_missile_list_text(user_id, cat_key):
    check_finished_upgrades(user_id)

    if cat_key not in LAB_ALLOWED_CATEGORIES:
        return f"❌ این دسته قابل ارتقا نیست!"

    p = db.get(user_id, {})
    missiles = p.get(cat_key, {})
    cat_name = get_category_name(cat_key)
    user_lab = p.get("research_level", 1)
    coins = p.get("coins", 0)
    oil = p.get("oil", 0)

    upgrades = p.get("upgrades", {})
    now = time.time()
    active = []
    for key, up in upgrades.items():
        if now < up.get("end_time", 0):
            missile = up.get("missile", "?")
            cat = up.get("category", "")
            lvl = db[user_id].get(cat, {}).get(missile, {}).get("level", 1)
            end_str = datetime.fromtimestamp(up["end_time"]).strftime("%Y-%m-%d %H:%M:%S")
            active.append({
                "sci": up.get("scientist_id", 1),
                "missile": missile,
                "new_level": lvl + 1,
                "end_str": end_str,
            })

    free_sci = get_free_scientist(user_id)

    text = f"🔬 ارتقای موشک‌ها — دسته {cat_name}\n"

    if active:
        text += "⏳ ارتقاهای درحال انجام:\n"
        for a in active:
            text += f"دانشمند {a['sci']}: {a['missile']} → سطح {a['new_level']} (تا {a['end_str']})\n"
        text += "\n"

    text += f"📊 آزمایشگاه شما: *{user_lab}/{LAB_MAX_LEVEL}*\n"
    text += f"🪙 سکه: {coins:,}\n"
    text += f"🛢️ نفت: {oil:,}\n"
    if free_sci:
        text += f"🔬 دانشمند آزاد: {free_sci}\n"
    else:
        text += f"🔬 دانشمند آزاد: ❌ (همه مشغول)\n"
    text += "\n"

    valid = [(mn, info) for mn, info in missiles.items()
             if mn not in LAB_BLOCKED_MISSILES
             and info.get("count", 0) > 0
             and is_upgradeable(mn)]

    if not valid:
        return f"🔬 ارتقای موشک‌ها — {cat_name}\n\n❌ هیچ موشک قابل ارتقایی از این دسته نداری!"

    buttons = []

    for mn, info in valid:
        lvl = info.get("level", 1)
        count = info.get("count", 0)

        if lvl >= MISSILE_MAX_LEVEL:
            text += f"🚀 {mn} سطح {lvl}\n   ✅ در حداکثر سطح\n"
            text += "➖➖➖➖➖➖\n"
            continue

        up = check_upgrade_in_progress(user_id, mn, cat_key)
        if up and now < up.get("end_time", 0):
            remaining = int(up["end_time"] - now)
            text += f"🚀 {mn} سطح {lvl}\n"
            text += f"   ⏳ در حال ارتقا: {_fmt_remaining(remaining)}\n"
            text += "➖➖➖➖➖➖\n"
            continue

        req_lab = LAB_MISSILE_UPGRADE_REQUIREMENTS.get(lvl, 6)
        if user_lab < req_lab:
            text += f"🚀 {mn} سطح {lvl}\n"
            text += f"   🔒 نیاز به آزمایشگاه سطح {req_lab} (فعلی: {user_lab})\n"
            text += "➖➖➖➖➖➖\n"
            continue

        if free_sci is None:
            text += f"🚀 {mn} سطح {lvl}\n"
            text += "   ⏳ همه دانشمندان شما در حال کار هستند؛ بعد از اتمام، می‌توانید ارتقا دهید.\n"
            text += "➖➖➖➖➖➖\n"
            continue

        cost_coin = get_upgrade_cost(mn, lvl)
        cost_oil = get_upgrade_oil_cost(mn, lvl)
        duration = get_actual_upgrade_time(user_id, get_upgrade_time(mn, lvl))

        text += f"🚀 {mn} سطح {lvl} (تعداد: {count})\n"
        text += f"   🪙 هزینه سکه: {cost_coin:,}\n"
        if cost_oil > 0:
            text += f"   🛢️ هزینه نفت: {cost_oil:,}\n"
        text += f"   🕒 زمان: {duration} دقیقه\n"
        text += "➖➖➖➖➖➖\n"

        can = (coins >= cost_coin and oil >= cost_oil)
        if can:
            buttons.append([{"text": f"🚀 ارتقا {mn} (سطح {lvl} → {lvl+1})",
                             "callback_data": f"upg_{cat_key}_{mn}"}])
        else:
            buttons.append([{"text": f"🔒 {mn} - موجودی کافی نیست",
                             "callback_data": "upg_no_funds"}])

    text += "🔻 از دکمه‌های زیر استفاده کن:"
    buttons.append([{"text": "🔙 بازگشت به منوی اصلی",
                     "callback_data": "lab_upgrade_missile"}])
    return text, {"inline_keyboard": buttons}


def build_upgrade_confirm_text(user_id, cat_key, missile_name):
    p = db.get(user_id, {})
    info = p.get(cat_key, {}).get(missile_name, {})
    lvl = info.get("level", 1)

    if lvl >= MISSILE_MAX_LEVEL or info.get("count", 0) <= 0:
        return None, None

    if not is_upgradeable(missile_name):
        return None, None

    free_sci = get_free_scientist(user_id)
    if free_sci is None:
        return None, None

    cost_coin = get_upgrade_cost(missile_name, lvl)
    cost_oil = get_upgrade_oil_cost(missile_name, lvl)
    base_time = get_upgrade_time(missile_name, lvl)
    duration = get_actual_upgrade_time(user_id, base_time)

    current_dmg = get_missile_damage(missile_name, lvl, cat_key)
    next_dmg = get_missile_damage(missile_name, lvl + 1, cat_key)
    current_coin = get_loot_coins(missile_name, lvl)
    next_coin = get_loot_coins(missile_name, lvl + 1)
    current_oil = get_loot_oil(missile_name, lvl)
    next_oil = get_loot_oil(missile_name, lvl + 1)
    current_rank = get_loot_rank(missile_name, lvl)
    next_rank = get_loot_rank(missile_name, lvl + 1)

    boost = p.get("active_boost")
    boost_txt = ""
    if boost and isinstance(boost, dict) and boost.get("expires_at", 0) > time.time():
        bname = BOOST_TYPES.get(boost.get("type", "20"), {}).get("name", "?")
        boost_txt = f"\n🟢 بوست فعال: {bname} (اعمال شد)\n"

    text = (f"🔬 تأیید ارتقا\n\n"
            f"⚡ موشک: {missile_name}\n"
            f"📊 سطح فعلی: {lvl} → {lvl + 1}\n"
            f"🔬 دانشمند: {free_sci}\n\n"
            f"💥 دمیج: {current_dmg} → {next_dmg}\n"
            f"🪙 غارت سکه: {current_coin} → {next_coin}\n"
            f"🛢️ غارت نفت: {current_oil} → {next_oil}\n"
            f"🏅 رنک: {current_rank} → {next_rank}\n\n"
            f"🪙 هزینه سکه: *{cost_coin:,}*\n")
    if cost_oil > 0:
        text += f"🛢️ هزینه نفت: *{cost_oil:,}*\n"
    text += (f"🕒 زمان: {duration} دقیقه\n"
             f"{boost_txt}\n"
             f"🔻 مطمئنی؟")
    kb = {"inline_keyboard": [
        [{"text": "✅ تأیید و شروع ارتقا",
          "callback_data": f"upg_confirm_{cat_key}_{missile_name}"}],
        [{"text": "❌ لغو", "callback_data": f"upg_back_{cat_key}"}],
    ]}
    return text, kb


# ==================== طلسم ====================
def build_talisman_inline_keyboard(user_id):
    p = db.get(user_id, {})
    coins = p.get("coins", 0)
    oil = p.get("oil", 0)
    user_level, _, _ = get_level_info(p.get("total_damage", 0))
    items = []
    for key, info in TALISMAN_INFO.items():
        req = info.get("req_level", 1)
        if user_level < req:
            continue

        cnt = p.get(info["count_key"], 0)
        price = info["price"]
        emoji = info["emoji"]
        if info["currency"] == "coins":
            can_buy = coins // price if price > 0 else 0
            if cnt >= 20:
                items.append({
                    "text": f"{emoji} {info['name']} ({cnt}/20) پر",
                    "callback_data": info["callback"]
                })
            else:
                items.append({
                    "text": f"{emoji} {info['name']} | {price:,}🪙 | x{can_buy}",
                    "callback_data": info["callback"]
                })
        else:
            can_buy = oil // price if price > 0 else 0
            if cnt >= 20:
                items.append({
                    "text": f"{emoji} {info['name']} ({cnt}/20) پر",
                    "callback_data": info["callback"]
                })
            else:
                items.append({
                    "text": f"{emoji} {info['name']} | {price}🛢 | x{can_buy}",
                    "callback_data": info["callback"]
                })
    buttons = []
    for i in range(0, len(items), 2):
        buttons.append(items[i:i + 2])

    if not items:
        buttons.append([{"text": "❌ طلسمی برای لول تو موجود نیست", "callback_data": "tal_locked"}])

    buttons.append([{"text": "🔙 بازگشت به منوی اصلی", "callback_data": "shop_back"}])
    return {"inline_keyboard": buttons}


def build_talisman_text(user_id):
    return ("✨ طلسم‌های من:\n\n"
            "🧿 طلسم چشم (لول 5): 25٪ شانس نادیده گرفتن پدافند حریف\n"
            "🔥 طلسم آتش (لول 8): 20٪ دمیج بیشتر\n"
            "💧 طلسم آب (لول 10): 30٪ دفع دمیج و غارت\n"
            "🌪 طلسم طوفان (لول 14): 2 موشک اضافه\n"
            "⚡ طلسم صاعقه (لول 17): حریف 60 ثانیه فلج\n"
            "🛡 طلسم سپر (لول 20): 50٪ دمیج و غارت کم\n"
            "👁 طلسم شکار (لول 23): حریف 40٪ ضعیف‌تر\n"
            "❄️ طلسم یخ (لول 25): حریف 30 ثانیه فلج\n\n"
            "📝 نحوه استفاده در حمله عادی:\n"
            "مثال: `حمله اطلس آتش`\n"
            "(طلسم‌های آب و سپر خودکار برای مدافع کار می‌کنند)")


def build_packs_keyboard(page=0):
    per_page = 4
    pack_list = list(PACKS.items())
    total = len(pack_list)
    total_pages = (total + per_page - 1) // per_page
    if page < 0:
        page = 0
    if page >= total_pages:
        page = total_pages - 1
    start = page * per_page
    slice_list = pack_list[start:start + per_page]
    items = []
    for key, pack in slice_list:
        items.append({"text": f"{pack['emoji']} {pack['name']} - {pack['price']}",
                      "callback_data": f"pack_{key}"})
    buttons = []
    for i in range(0, len(items), 2):
        buttons.append(items[i:i + 2])
    nav = []
    if page > 0:
        nav.append({"text": "⬅️ قبلی", "callback_data": f"packs_p_{page-1}"})
    if page + 1 < total_pages:
        nav.append({"text": "➡️ بعدی", "callback_data": f"packs_p_{page+1}"})
    if nav:
        buttons.append(nav)
    buttons.append([{"text": "📞 پیوی مدیریت", "url": f"https://ble.ir/{SUPPORT_ID}"}])
    buttons.append([{"text": "🔙 بازگشت به منوی اصلی", "callback_data": "go_main"}])
    return {"inline_keyboard": buttons}


def build_pack_text(key):
    if key not in PACKS:
        return None, None
    pack = PACKS[key]
    text = f"{pack['emoji']} {pack['name']}\n\n💰 قیمت: {pack['price']}\n\n📦 محتویات:\n"
    for item in pack["items"]:
        text += f"• {item}\n"
    text += "\n🔻 برای خرید، روی دکمه زیر بزن:"
    kb = {"inline_keyboard": [
        [{"text": "🛒 سفارش", "callback_data": f"order_{key}"}],
        [{"text": "🔙 بازگشت به منوی اصلی", "callback_data": "shop_items"}],
    ]}
    return text, kb


# ==================== پدافند ====================
def build_defense_text(user_id):
    p = db.get(user_id, {})
    defenses = p.get("defense", {})
    active = p.get("active_defense")
    user_level, _, _ = get_level_info(p.get("total_damage", 0))

    text = "🛡️ پدافندهای شما:\n\n"
    text += f"📊 سطح شما: {user_level}\n"
    text += f"⚡ پدافند فعال: {active if active else '❌ هیچ'}\n\n"

    if defenses:
        text += "📦 پدافندهای موجود:\n"
        for name, info in defenses.items():
            count = info.get("count", 0)
            if count <= 0:
                continue
            emoji = get_defense_emoji(name)
            mark = " ✅" if name == active else ""
            dtype = DEFENSES.get(name, {}).get("type", "block")
            block = DEFENSES.get(name, {}).get("block_chance", 0)
            if dtype == "damage_reduce":
                text += (f"{emoji} {name}: {count} عدد "
                         f"(💥 کاهش دمیج: {block}%){mark}\n")
            else:
                text += (f"{emoji} {name}: {count} عدد "
                         f"(🛡 شانس بلاک: {block}%){mark}\n")
    else:
        text += "❌ هیچ پدافندی نداری!\n"

    text += "\n📖 راهنمای پدافندها:\n"
    for name, info in DEFENSES.items():
        req = info.get("required_level", 1)
        emoji = get_defense_emoji(name)
        chance = info.get("block_chance", 0)
        dtype = info.get("type", "block")

        if dtype == "damage_reduce":
            text += f"{emoji} {name} (لول {req}): {chance}٪ کاهش دمیج\n"
        else:
            text += f"{emoji} {name} (لول {req}): {chance}٪ شانس بلاک حمله\n"

    text += "\n🔻 یکی از پدافندها رو انتخاب کن:"
    return text


def build_defense_keyboard(user_id):
    p = db.get(user_id, {})
    defenses = p.get("defense", {})
    active = p.get("active_defense")
    items = []
    for name, info in defenses.items():
        if info.get("count", 0) > 0:
            mark = " ✅" if name == active else ""
            emoji = get_defense_emoji(name)
            items.append({"text": f"{emoji} {name}{mark}",
                          "callback_data": f"def_select_{name}"})
    buttons = []
    for i in range(0, len(items), 2):
        buttons.append(items[i:i + 2])
    buttons.append([{"text": "🛒 خرید پدافند", "callback_data": "def_buy"}])
    buttons.append([{"text": "📖 راهنما", "callback_data": "help_defense"}])
    buttons.append([{"text": "🔙 بازگشت به منوی اصلی", "callback_data": "shop_back"}])
    return {"inline_keyboard": buttons}


def build_defense_buy_keyboard(user_id=None):
    p = db.get(user_id, {}) if user_id else {}
    user_level, _, _ = get_level_info(p.get("total_damage", 0))
    coins = p.get("coins", 0)
    items = []
    for name, info in DEFENSES.items():
        req = info.get("required_level", 1)
        if user_level < req:
            continue
        emoji = get_defense_emoji(name)
        price = info["price"]
        can_buy = coins // price if price > 0 else 0
        items.append({
            "text": f"{emoji} {name} | {price:,}🪙 | x{can_buy}",
            "callback_data": f"def_buy_{name}"
        })
    buttons = []
    for i in range(0, len(items), 2):
        buttons.append(items[i:i + 2])
    if not items:
        buttons.append([{"text": "❌ پدافندی برای لول تو نیست",
                         "callback_data": "def_locked"}])
    buttons.append([{"text": "📖 راهنما", "callback_data": "help_defense"}])
    buttons.append([{"text": "🔙 بازگشت به منوی اصلی", "callback_data": "go_defense"}])
    return {"inline_keyboard": buttons}


# ==================== 🏰 زرادخانه (ظرفیت حمله ترکیبی) ====================
def build_combo_arsenal_text(user_id):
    """صفحه زرادخانه — ظرفیت حمله ترکیبی"""
    p = db.get(user_id, {})
    lvl = p.get("arsenal_level", 1)
    if lvl > ARSENAL_MAX_LEVEL:
        lvl = ARSENAL_MAX_LEVEL
    cur_cap = ARSENAL_LEVELS[lvl]["capacity"]

    text = "🏰 *زرادخانه (ظرفیت حمله ترکیبی)*\n"
    text += "━━━━━━━━━━━━━━━━━\n\n"
    text += f"📊 سطح فعلی: *{lvl}/{ARSENAL_MAX_LEVEL}*\n"
    text += f"📦 ظرفیت حمله ترکیبی: *{cur_cap} موشک*\n"
    text += f"🪙 سکه: *{p.get('coins', 0):,}*\n"
    text += f"🛢️ نفت: *{p.get('oil', 0):,}*\n\n"

    if lvl < ARSENAL_MAX_LEVEL:
        next_lvl = lvl + 1
        next_cap = ARSENAL_LEVELS[next_lvl]["capacity"]
        costs = ARSENAL_ATTACK_COSTS[lvl]
        text += f"⬆️ *ارتقا به سطح {next_lvl}:*\n"
        text += f"   📦 ظرفیت جدید: *{next_cap} موشک*\n"
        text += f"   🪙 هزینه: *{costs['coins']:,} سکه*\n"
        if costs["oil"] > 0:
            text += f"   🛢️ هزینه: *{costs['oil']:,} نفت*\n"

        if p.get("coins", 0) < costs["coins"]:
            text += "   ❌ سکه کافی نیست!\n"
        if costs["oil"] > 0 and p.get("oil", 0) < costs["oil"]:
            text += "   ❌ نفت کافی نیست!\n"
    else:
        text += "🚫 در حداکثر سطح!\n"

    text += "\n💡 *زرادخانه فقط ظرفیت حمله ترکیبی رو تعیین می‌کنه*"
    text += "\n⚠️ برای ذخیره موشک، به «💥 تسلیحات» برو"
    return text


def build_combo_arsenal_keyboard(user_id):
    p = db.get(user_id, {})
    lvl = p.get("arsenal_level", 1)
    if lvl > ARSENAL_MAX_LEVEL:
        lvl = ARSENAL_MAX_LEVEL
    buttons = []
    if lvl < ARSENAL_MAX_LEVEL:
        costs = ARSENAL_ATTACK_COSTS[lvl]
        label = f"⬆️ ارتقا ({costs['coins']:,} سکه"
        if costs["oil"] > 0:
            label += f" + {costs['oil']:,} نفت"
        label += ")"
        buttons.append([{"text": label, "callback_data": "upgrade_arsenal_attack"}])
    buttons.append([{"text": "🔙 بازگشت", "callback_data": "combo_back"}])
    return {"inline_keyboard": buttons}


# ==================== 💥 تسلیحات خانه (ذخیره موشک) ====================
def build_weapons_house_text(user_id):
    p = db.get(user_id, {})
    arsenal_lvl = p.get("weapons_house_level", 1)
    if arsenal_lvl > 5:
        arsenal_lvl = 5

    caps = ARSENAL_CAPACITIES[arsenal_lvl]

    text = "⚔️🚀  *تسلیحات خانه* \n"
    text += "━━━━━━━━━━━━━━━━━━━━\n"
    text += "🏰  *وضعیت تسلیحات* \n"
    text += f"▫️ سطح فعلی:  *{arsenal_lvl}* \n"

    if arsenal_lvl < 5:
        next_lvl = arsenal_lvl + 1
        cost = ARSENAL_UPGRADE_COSTS[arsenal_lvl]
        text += f"▫️ لول بعدی:  *{next_lvl}* \n"
        text += f"▫️ هزینه ارتقا:  *{cost:,}*  سکه\n\n"
    else:
        text += "▫️ وضعیت: *حداکثر سطح* 🚫\n\n"

    text += "━━━━━━━━━━━━━━━━━━━━\n"
    text += "📦  *ظرفیت دسته‌های موشکی* \n\n"

    cats = [
        ("cruise", "🛫 کروز"),
        ("ballistic", "🚀 بالستیک"),
        ("hypersonic", "⚡ هایپرسونیک"),
        ("chemical", "🧪 شیمیایی"),
        ("nuclear", "☢️ هسته‌ای")
    ]

    for cat_key, cat_name in cats:
        count = sum(m.get("count", 0) for m in p.get(cat_key, {}).values())
        max_cap = caps.get(cat_key, 0)
        pct = min(int((count / max_cap) * 100), 100) if max_cap > 0 else 0
        filled = pct // 10
        bar = "█" * filled + "░" * (10 - filled)

        text += f"{cat_name} \n"
        text += f"{bar}  *{pct}%* \n"
        text += f"▫️ موجودی:  *{count}* \n"
        text += f"▫️ ظرفیت:  *{max_cap}* \n\n"

    text += "━━━━━━━━━━━━━━━━━━━━\n"
    text += "ℹ️ موجودی بالاتر از ظرفیت فعلاً حذف نمی‌شود؛ فقط دریافت موشک جدید با ظرفیت چک می‌شود.\n"
    text += "🔻 از دکمه‌های زیر استفاده کنید."
    return text


def build_weapons_house_keyboard(user_id):
    p = db.get(user_id, {})
    arsenal_lvl = p.get("weapons_house_level", 1)
    if arsenal_lvl > 5:
        arsenal_lvl = 5

    buttons = []
    if arsenal_lvl < 5:
        cost = ARSENAL_UPGRADE_COSTS[arsenal_lvl]
        buttons.append([{"text": f"⬆️ ارتقای تسلیحات ({cost:,} سکه)",
                         "callback_data": "upgrade_weapons_house"}])

    buttons.append([{"text": "📖 راهنما", "callback_data": "help_arsenal"}])
    buttons.append([{"text": "❌ بستن", "callback_data": "go_main"}])
    return {"inline_keyboard": buttons}


# ==================== کلن ====================
def get_clan_name(clan_id):
    if "clans" in db and clan_id in db["clans"]:
        name = db["clans"][clan_id].get("name")
        if name and str(name).strip() and str(name) != "None":
            return str(name)
    for uid, p in db.items():
        if isinstance(p, dict) and p.get("clan_id") == clan_id:
            name = p.get("clan")
            if name and str(name).strip() and str(name) != "None":
                return str(name)
    return "نامشخص"


def get_clan_members(clan_id):
    members = []
    for uid, p in db.items():
        if isinstance(p, dict) and p.get("clan_id") == clan_id:
            members.append((uid, p))
    return members


def is_clan_full(clan_id):
    if clan_id == OFFICIAL_CLAN_ID:
        return False
    return len(get_clan_members(clan_id)) >= CLAN_MAX_MEMBERS


def generate_clan_id():
    while True:
        cid = str(random.randint(10000000, 99999999))
        if not any(isinstance(p, dict) and p.get("clan_id") == cid
                   for p in db.values()):
            return cid


def get_clan_rank_points(clan_id):
    if "clans" not in db:
        return 0
    return db["clans"].get(clan_id, {}).get("rank_points", 0)


def set_clan_rank_points(clan_id, points):
    if "clans" not in db:
        db["clans"] = {}
    if clan_id not in db["clans"]:
        db["clans"][clan_id] = {"name": get_clan_name(clan_id),
                                "rank_points": 0, "leader_id": None}
    db["clans"][clan_id]["rank_points"] = points
    save_db()
    return True


def add_clan_rank_points(clan_id, points):
    set_clan_rank_points(clan_id, get_clan_rank_points(clan_id) + points)


def build_clan_inline_keyboard(user_id):
    """کیبورد کلن - با جنگ کلن + ارتقای کلن + مدیریت کامل"""
    p = db.get(user_id, {})
    if p.get("clan_id"):
        is_leader = p.get("clan_role") == "leader"
        is_officer = p.get("clan_role") == "officer"

        if is_leader:
            return {"inline_keyboard": [
                [{"text": "⚔️ جنگ کلن‌ها", "callback_data": "clan_war"}],
                [{"text": "🔧 ارتقای کلن", "callback_data": "clan_upgrade"}],
                [{"text": "⚙️ مدیریت کلن", "callback_data": "clan_manage"},
                 {"text": "📋 لیست اعضای کلن", "callback_data": "clan_members"}],
                [{"text": "📩 دعوت عضو", "callback_data": "clan_invite"},
                 {"text": "🚪 اخراج عضو", "callback_data": "clan_kick_menu"}],
                [{"text": "⬆️ ارتقا نقش", "callback_data": "clan_promote_menu"},
                 {"text": "⬇️ تنزل نقش", "callback_data": "clan_demote_menu"}],
                [{"text": "👑 انتقال مالکیت",
                  "callback_data": "clan_transfer_leader_menu"}],
                [{"text": "📢 پیام به اعضا", "callback_data": "clan_msg_all"}],
                [{"text": "🗑️ حذف کلن", "callback_data": "clan_delete"}],
                [{"text": "🔙 بازگشت به منوی اصلی", "callback_data": "go_main"}],
            ]}
        elif is_officer:
            return {"inline_keyboard": [
                [{"text": "⚔️ جنگ کلن‌ها", "callback_data": "clan_war"}],
                [{"text": "🔧 ارتقای کلن", "callback_data": "clan_upgrade"}],
                [{"text": "⚙️ مدیریت کلن", "callback_data": "clan_manage"},
                 {"text": "📋 لیست اعضای کلن", "callback_data": "clan_members"}],
                [{"text": "📩 دعوت عضو", "callback_data": "clan_invite"}],
                [{"text": "📢 پیام به اعضا", "callback_data": "clan_msg_all"}],
                [{"text": "🚪 خروج از کلن", "callback_data": "clan_leave"}],
                [{"text": "🔙 بازگشت به منوی اصلی", "callback_data": "go_main"}],
            ]}
        else:
            return {"inline_keyboard": [
                [{"text": "⚔️ جنگ کلن‌ها", "callback_data": "clan_war"}],
                [{"text": "🔧 ارتقای کلن", "callback_data": "clan_upgrade"}],
                [{"text": "📋 لیست اعضای کلن", "callback_data": "clan_members"},
                 {"text": "🚪 خروج از کلن", "callback_data": "clan_leave"}],
                [{"text": "🔙 بازگشت به منوی اصلی", "callback_data": "go_main"}],
            ]}
    return {"inline_keyboard": [
        [{"text": "👥 خرید کلن", "callback_data": "clan_buy"},
         {"text": "🔍 جستجوی کلن", "callback_data": "clan_search"}],
        [{"text": "🔙 بازگشت به منوی اصلی", "callback_data": "go_main"}],
    ]}


def build_clans_ranking(page=0, my_user_id=None):
    per_page = 10
    clans = {}
    for uid, p in db.items():
        if not isinstance(p, dict):
            continue
        if "user_id" not in p:
            continue
        cid = p.get("clan_id")
        if not cid:
            continue
        if cid not in clans:
            clans[cid] = {
                "name": get_clan_name(cid),
                "members": 0,
                "total_rank": 0,
            }
        clans[cid]["members"] += 1
        clans[cid]["total_rank"] += p.get("rank", 0)

    if not clans:
        return None, None

    clan_list = sorted(clans.items(), key=lambda x: x[1]["total_rank"],
                       reverse=True)
    total_clans = len(clan_list)
    total_pages = (total_clans + per_page - 1) // per_page
    if page < 0:
        page = 0
    if page >= total_pages:
        page = total_pages - 1
    start = page * per_page
    slice_list = clan_list[start:start + per_page]

    text = f"🏵 *لیست برترین کلن‌ها*\n"
    text += f"تعداد کل کلن‌ها: {total_clans}\n\n"

    for i, (cid, info) in enumerate(slice_list, start + 1):
        text += (f"{i}. {info['name']} — "
                 f"{info['members']}/{CLAN_MAX_MEMBERS} | "
                 f"{info['total_rank']}\n")

    text += "\n➖➖➖➖➖\n📌 رتبه کلن تو\n"

    user_clan_rank = None
    user_clan_name = None
    if my_user_id:
        my_clan_id = db.get(str(my_user_id), {}).get("clan_id")
        if my_clan_id and my_clan_id in clans:
            user_clan_name = clans[my_clan_id]["name"]
            for i, (cid, _) in enumerate(clan_list, 1):
                if cid == my_clan_id:
                    user_clan_rank = i
                    break

    if user_clan_rank:
        text += f"{user_clan_rank}. {user_clan_name}\n"
    else:
        text += "شما عضو هیچ کلنی نیستید.\n"

    text += f"\nصفحه {page + 1} از {total_pages}"

    nav = []
    if page > 0:
        nav.append({"text": "⬅️ قبلی",
                    "callback_data": f"rank_clan_p_{page - 1}"})
    if page + 1 < total_pages:
        nav.append({"text": "➡️ بعدی",
                    "callback_data": f"rank_clan_p_{page + 1}"})

    buttons = [[
        {"text": "🏅 برترین‌ها", "callback_data": "rank_p_0"},
        {"text": "👥 کلن", "callback_data": "rank_clan"},
        {"text": "📆 روزانه", "callback_data": "rank_daily"},
    ]]
    if nav:
        buttons.append(nav)
    buttons.append([{"text": "🔙 بازگشت به منوی اصلی", "callback_data": "go_main"}])
    return text, {"inline_keyboard": buttons}


def build_admin_clans_ranking(page=0):
    per_page = 10
    clans = {}
    for uid, p in db.items():
        if not isinstance(p, dict):
            continue
        if "user_id" not in p:
            continue
        cid = p.get("clan_id")
        if not cid:
            continue
        if cid not in clans:
            clans[cid] = {
                "name": get_clan_name(cid),
                "members": 0,
                "total_rank": 0,
            }
        clans[cid]["members"] += 1
        clans[cid]["total_rank"] += p.get("rank", 0)

    if not clans:
        return None, None

    clan_list = sorted(clans.items(), key=lambda x: x[1]["total_rank"],
                       reverse=True)
    total_clans = len(clan_list)
    total_pages = (total_clans + per_page - 1) // per_page
    if page < 0:
        page = 0
    if page >= total_pages:
        page = total_pages - 1
    start = page * per_page
    slice_list = clan_list[start:start + per_page]

    text = f"🏵 *رنکینگ کلن‌ها (پنل ادمین)*\n"
    text += f"━━━━━━━━━━━━━━━━━\n"
    text += f"📊 تعداد کل کلن‌ها: {total_clans}\n\n"

    for i, (cid, info) in enumerate(slice_list, start + 1):
        text += (f"{i}. 🏰 *{info['name']}*\n"
                 f"   👥 {info['members']}/{CLAN_MAX_MEMBERS} | "
                 f"🏆 {info['total_rank']:,} رنک\n")

    text += f"\n━━━━━━━━━━━━━━━━━\n"
    text += f"📄 صفحه {page + 1} از {total_pages}"

    nav = []
    if page > 0:
        nav.append({"text": "⬅️ قبلی",
                    "callback_data": f"admin_clan_ranking_p_{page - 1}"})
    if page + 1 < total_pages:
        nav.append({"text": "➡️ بعدی",
                    "callback_data": f"admin_clan_ranking_p_{page + 1}"})

    buttons = []
    if nav:
        buttons.append(nav)
    buttons.append([{"text": "🔙 بازگشت به پنل ادمین",
                     "callback_data": "other_admin_back"}])
    return text, {"inline_keyboard": buttons}


def build_players_ranking(page=0, my_user_id=None):
    per_page = 10
    users = []
    for uid, p in db.items():
        if not isinstance(p, dict):
            continue
        if "user_id" not in p:
            continue
        if p.get("banned"):
            continue
        users.append({
            "name": p.get("name", "کاربر"),
            "rank": p.get("rank", 0),
            "uid": uid,
        })
    users.sort(key=lambda x: x["rank"], reverse=True)

    total_users = len(users)
    if total_users == 0:
        text = "🏵 *لیست برترین بازیکن‌ها*\n"
        text += "امتیاز شما: 0\n\n❌ هنوز کسی رنکینگ نداره!"
        kb = {"inline_keyboard": [
            [{"text": "🏅 برترین‌ها", "callback_data": "rank_p_0"},
             {"text": "👥 کلن", "callback_data": "rank_clan"},
             {"text": "📆 روزانه", "callback_data": "rank_daily"}],
            [{"text": "🔙 بازگشت به منوی اصلی", "callback_data": "go_main"}],
        ]}
        return text, kb

    total_pages = (total_users + per_page - 1) // per_page
    if page < 0:
        page = 0
    if page >= total_pages:
        page = total_pages - 1
    start_idx = page * per_page
    slice_list = users[start_idx:start_idx + per_page]

    my_score = 0
    my_global_rank = 0
    my_name = "کاربر"
    if my_user_id:
        my_user_id = str(my_user_id)
        for i, u in enumerate(users, 1):
            if u["uid"] == my_user_id:
                my_score = u["rank"]
                my_global_rank = i
                my_name = u["name"]
                break

    text = "🏵 *لیست برترین بازیکن‌ها*\n"
    text += f"👥 تعداد کل: {total_users:,}\n"
    text += f"⭐ امتیاز شما: {my_score:,}\n\n"

    for i, user in enumerate(slice_list, start_idx + 1):
        league_emoji = get_league(user["rank"]).split()[0]
        text += f"{i}. {league_emoji} {user['name']} — {user['rank']:,} ⭐\n"

    text += "\n➖➖➖➖➖\n📌 رتبه تو\n"
    if my_global_rank > 0:
        my_league_emoji = get_league(my_score).split()[0]
        text += f"{my_global_rank}. {my_league_emoji} {my_name} — {my_score:,} ⭐\n"
    else:
        text += f"—. {my_name} — {my_score:,} ⭐\n"

    text += f"\n📄 صفحه {page + 1} از {total_pages}"

    buttons = [[
        {"text": "🏅 برترین‌ها", "callback_data": "rank_p_0"},
        {"text": "👥 کلن", "callback_data": "rank_clan"},
        {"text": "📆 روزانه", "callback_data": "rank_daily"},
    ]]
    nav = []
    if page > 0:
        nav.append({"text": "⬅️ صفحه قبل", "callback_data": f"rank_p_{page-1}"})
    if page + 1 < total_pages:
        nav.append({"text": "➡️ صفحه بعد", "callback_data": f"rank_p_{page+1}"})
    if nav:
        buttons.append(nav)
    buttons.append([{"text": "🔙 بازگشت به منوی اصلی", "callback_data": "go_main"}])
    return text, {"inline_keyboard": buttons}


def update_rank_today():
    today = datetime.now().strftime("%Y-%m-%d")
    changed = False
    for uid, p in db.items():
        if uid in ["pending_transfers", "clan_wars", "clan_war_requests",
                   "transfer_tokens", "clans", "clan_invites", "clan_requests"]:
            continue
        if not isinstance(p, dict):
            continue
        if "user_id" not in p:
            continue
        if p.get("rank_date") != today:
            p["rank_today"] = 0
            p["rank_date"] = today
            changed = True
    if changed:
        save_db()


def find_battle_target(user_id):
    my_rank = db.get(user_id, {}).get("rank", 0)
    my_league = get_league(my_rank)

    my_idx = None
    for i, (name, _, _) in enumerate(RANK_LEAGUES):
        if name == my_league:
            my_idx = i
            break

    if my_idx is None:
        return None

    for uid, d in db.items():
        if uid == str(user_id):
            continue
        if not isinstance(d, dict):
            continue
        if "user_id" not in d:
            continue
        if d.get("banned"):
            continue
        if get_league(d.get("rank", 0)) == my_league:
            return uid

    for i in range(my_idx + 1, len(RANK_LEAGUES)):
        lower_league = RANK_LEAGUES[i][0]
        for uid, d in db.items():
            if uid == str(user_id):
                continue
            if not isinstance(d, dict):
                continue
            if "user_id" not in d:
                continue
            if d.get("banned"):
                continue
            if get_league(d.get("rank", 0)) == lower_league:
                return uid

    return None


def build_battle_text(user_id):
    my_rank = db.get(user_id, {}).get("rank", 0)
    my_league = get_league(my_rank)

    now = time.time()
    target_id = db.get(user_id, {}).get("battle_target")
    target_time = db.get(user_id, {}).get("battle_target_time", 0)

    if (not target_id or target_id not in db
            or now - target_time > 30):
        target_id = find_battle_target(user_id)
        if target_id:
            db[user_id]["battle_target"] = target_id
            db[user_id]["battle_target_time"] = now
            save_db()
            target_time = now

    if not target_id:
        return "🌐 حمله جهانی\n\n❌ هنوز حریفی توی لیگت وجود نداره!"

    t = db[target_id]
    t_league = get_league(t.get("rank", 0))
    t_name = t.get("name", "کاربر")
    t_rank = t.get("rank", 0)
    t_coins = t.get("coins", 0)

    remaining = max(0, 30 - int(now - target_time))

    league_parts = t_league.split()
    league_emoji = league_parts[0] if league_parts else "🎗"
    league_name = league_parts[-1] if len(league_parts) > 1 else t_league

    text = (f"🌐 *حریف پیشنهادی*\n\n"
            f"👤 نام: *{t_name}*\n"
            f"🆔 آیدی: `{target_id}`\n"
            f"⭐ رنک: *{t_rank:,}*  — {league_emoji} {league_name}\n"
            f"🪙 سکه‌های او: *{t_coins:,}*\n\n"
            f"🔻 برای «حمله عادی» یا «حمله ترکیبی» یا جایگزین کردن حریف از دکمه‌ها استفاده کنید.\n"
            f"⏳ _این پیشنهاد تا {remaining} ثانیه معتبر است._")

    return text


# ==================== گردونه ====================
def build_wheel_keyboard():
    return {"inline_keyboard": [
        [{"text": "🎁 گردونه روزانه (رایگان)", "callback_data": "wheel_daily"}],
        [{"text": "🎡 گردونه افسانه‌ای (15,000 سکه)", "callback_data": "wheel_legendary"}],
        [{"text": "🎰 گردونه بخت (20,000 سکه)", "callback_data": "wheel_luck"}],
        [{"text": "🌊 گردونه طوفان (2,500 سکه)", "callback_data": "wheel_storm"}],
        [{"text": "🐉 گردونه شکار (5,000 سکه)", "callback_data": "wheel_hunt"}],
        [{"text": "🔥 گردونه آتش (15,000 سکه)", "callback_data": "wheel_fire"}],
        [{"text": "🐲 گردونه اژدها (25,000 سکه)", "callback_data": "wheel_dragon"}],
        [{"text": "📖 راهنما", "callback_data": "help_wheel"}],
        [{"text": "🔙 بازگشت به منوی اصلی", "callback_data": "go_main"}],
    ]}


def build_battle_keyboard():
    return {"inline_keyboard": [
        [{"text": "⚔️ حمله موشکی", "callback_data": "battle_attack"},
         {"text": "🚀 حمله ترکیبی", "callback_data": "battle_combo_start"}],
        [{"text": "➡️ بعدی (10 سکه)", "callback_data": "battle_next"}],
        [{"text": "📖 راهنما", "callback_data": "help_battle"}],
        [{"text": "🔙 بازگشت به منوی اصلی", "callback_data": "go_main"}],
    ]}


def build_battle_cancel_keyboard():
    return {"inline_keyboard": [[{"text": "❌ لغو", "callback_data": "battle_cancel"}]]}


# ==================== گزارش حمله ترکیبی ====================
def build_combo_attack_report(attacker, target, raw_dmg, defense_pct,
                               stolen_c, stolen_o, rank_gain,
                               weapons_used, fighter_dmg=0,
                               fighter_loot=None, fighter_note="",
                               vernix_msgs=None, moon_note="",
                               defender_had_coins=0, defender_had_oil=0,
                               want_c=0, want_o=0):
    a_name = attacker.get("name", "کاربر")
    t_name = target.get("name", "کاربر")
    a_league = get_league(attacker.get("rank", 0))
    t_league = get_league(target.get("rank", 0))

    if fighter_loot is None:
        fighter_loot = {"coins": 0, "oil": 0}

    raw_fighter_coins = fighter_loot.get("coins", 0)
    raw_fighter_oil = fighter_loot.get("oil", 0)

    if want_c > 0 and defender_had_coins > 0:
        actual_fighter_coins = int(raw_fighter_coins * (stolen_c / want_c))
    else:
        actual_fighter_coins = 0

    if want_o > 0 and defender_had_oil > 0:
        actual_fighter_oil = int(raw_fighter_oil * (stolen_o / want_o))
    else:
        actual_fighter_oil = 0

    defense_absorbed = int(raw_dmg * defense_pct / 100)
    net_dmg = raw_dmg - defense_absorbed
    if net_dmg < 1:
        net_dmg = 1

    destruction_pct = int((net_dmg / raw_dmg) * 100) if raw_dmg > 0 else 0
    if destruction_pct > 100:
        destruction_pct = 100

    if destruction_pct >= 80:
        stars = "⭐⭐⭐"
    elif destruction_pct >= 50:
        stars = "⭐⭐"
    elif destruction_pct >= 20:
        stars = "⭐"
    else:
        stars = "—"

    text = (f"🚀💥 *حمله ترکیبی موفق!* 💥🚀\n\n"
            f"👤 مهاجم: {a_name} ({a_league})\n"
            f"🛡️ مدافع: {t_name} ({t_league})\n\n"
            f"💥 دمیج خام کل: *{raw_dmg:,}*\n"
            f"🛡️ کاهش توسط ساختمان‌ها: *{defense_absorbed:,}*\n"
            f"💣 درصد تخریب: *{destruction_pct}%*\n"
            f"⭐ ستاره‌ها: {stars}\n\n")

    text += "📊 *نمودار غارت*\n"
    text += "━━━━━━━━━━━━━━━━━\n"

    text += "🪙 *سکه*\n"
    if defender_had_coins <= 0:
        text += "⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜  0%\n"
        text += "❌ مدافع سکه‌ای نداشت\n\n"
    else:
        coin_bar, coin_pct = make_loot_chart(stolen_c, defender_had_coins)
        text += f"{coin_bar}  {coin_pct}%\n"
        text += f"📦 {stolen_c:,} از {defender_had_coins:,}\n\n"

    text += "🛢 *نفت*\n"
    if defender_had_oil <= 0:
        text += "⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜  0%\n"
        text += "❌ مدافع نفتی نداشت\n"
    else:
        oil_bar, oil_pct = make_loot_chart(stolen_o, defender_had_oil)
        text += f"{oil_bar}  {oil_pct}%\n"
        text += f"📦 {stolen_o:,} از {defender_had_oil:,}\n"

    text += "━━━━━━━━━━━━━━━━━\n\n"

    text += f"🏆 رنک: ⬆️ +{rank_gain} مهاجم | ➖ -{rank_gain} مدافع\n\n"

    if weapons_used:
        text += "📊 *جزئیات موشک‌ها:*\n"
        for w in weapons_used:
            if w.get("used", 0) > 0:
                lvl = w.get("level", 1)
                cat = w.get("category", "cruise")
                dmg_each = get_missile_damage(w["name"], lvl, cat)
                total_each = dmg_each * w["used"]
                text += (f"• {w['name']} (سطح {lvl}): "
                         f"{w['used']} عدد — جمع {total_each:,}\n")
        text += "\n"

    if fighter_dmg > 0:
        text += f"✈️ دمیج جنگنده‌ها: *+{fighter_dmg:,}*\n"
        if actual_fighter_coins > 0:
            text += f"🪙 سکه اضافه: +{actual_fighter_coins:,}\n"
        else:
            text += "🪙 سکه اضافه: ❌ (مدافع سکه‌ای نداشت)\n"
        if actual_fighter_oil > 0:
            text += f"🛢️ نفت اضافه: +{actual_fighter_oil:,}\n\n"
        else:
            text += "🛢️ نفت اضافه: ❌ (مدافع نفتی نداشت)\n\n"

    if fighter_note:
        text += fighter_note + "\n"

    if vernix_msgs:
        text += "🔥 *آسیب ورنیکس به جنگنده‌ها:*\n"
        for vm in vernix_msgs:
            text += f"   {vm}\n"
        text += "\n"

    target_buildings = target.get("buildings", {})
    arsenal_level = target.get("arsenal_level", 1)

    if target_buildings or arsenal_level > 0:
        text += "🏗️ *وضعیت ساختمان‌های مدافع:*\n\n"
        all_buildings = dict(target_buildings)
        if arsenal_level > 0:
            all_buildings["زرادخانه"] = arsenal_level

        for bname, blevel in all_buildings.items():
            base_hp = BUILDINGS_HP.get(bname, 100)
            max_hp = base_hp + (blevel - 1) * 20
            dmg_pct = random.randint(3, 9)
            dmg = int(max_hp * dmg_pct / 100)
            cur_hp = max_hp - dmg
            text += (f"🏗️ *{bname}* (Lv.{blevel})\n"
                     f"❤️ {cur_hp}/{max_hp} HP  |  "
                     f"💢 خسارت: {dmg_pct}%\n\n")

    if moon_note:
        text += moon_note + "\n"

    text += f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    return text


# ==================== جستجوی کلن ====================
def build_clan_search(page=0):
    per_page = 10

    clans = {}
    for uid, d in db.items():
        if isinstance(d, dict) and d.get("clan_id"):
            cid = d["clan_id"]
            if cid not in clans:
                clans[cid] = {
                    "clan_id": cid,
                    "name": get_clan_name(cid),
                    "members": [],
                    "total_rank": 0,
                    "leader": "نامشخص",
                }
            clans[cid]["members"].append(d.get("name", "کاربر"))
            clans[cid]["total_rank"] += d.get("rank", 0)
            if d.get("clan_role") == "leader":
                clans[cid]["leader"] = d.get("name", "کاربر")

    if not clans:
        return ("🔍 جستجوی کلن\n\n❌ هیچ کلنی وجود نداره!",
                {"inline_keyboard": [[{"text": "🔙 بازگشت به منوی اصلی",
                                       "callback_data": "clan_back"}]]})

    clan_list = []
    if OFFICIAL_CLAN_ID in clans:
        clan_list.append((OFFICIAL_CLAN_ID, clans[OFFICIAL_CLAN_ID]))

    for cid, info in clans.items():
        if cid == OFFICIAL_CLAN_ID:
            continue
        if len(info["members"]) >= CLAN_MAX_MEMBERS:
            continue
        clan_list.append((cid, info))

    total = len(clan_list)
    if total == 0:
        return ("🔍 جستجوی کلن\n\n❌ هیچ کلن بازی وجود نداره!",
                {"inline_keyboard": [[{"text": "🔙 بازگشت به منوی اصلی",
                                       "callback_data": "clan_back"}]]})

    total_pages = (total + per_page - 1) // per_page
    if page < 0:
        page = 0
    if page >= total_pages:
        page = total_pages - 1

    start = page * per_page
    slice_list = clan_list[start:start + per_page]

    text = f"🔍 جستجوی کلن\n\n📋 کلن‌های موجود: {total}\n\n"

    buttons = []
    for cid, info in slice_list:
        if cid == OFFICIAL_CLAN_ID:
            text += f"👑 {info['name']} (رسمی)\n"
        else:
            text += (f"🏰 {info['name']} — "
                     f"{len(info['members'])}/{CLAN_MAX_MEMBERS} عضو\n")
        buttons.append([{"text": f"🏰 {info['name']}",
                         "callback_data": f"clan_view_{cid}"}])

    text += f"\n📄 صفحه {page + 1} از {total_pages}"

    nav = []
    if page > 0:
        nav.append({"text": "⬅️ قبلی",
                    "callback_data": f"clan_search_p_{page - 1}"})
    if page + 1 < total_pages:
        nav.append({"text": "➡️ بعدی",
                    "callback_data": f"clan_search_p_{page + 1}"})
    if nav:
        buttons.append(nav)

    buttons.append([{"text": "🔙 بازگشت به منوی اصلی", "callback_data": "clan_back"}])
    return text, {"inline_keyboard": buttons}


def build_clan_members_page(user_id, page=0):
    per_page = 10
    p = db.get(user_id, {})
    cid = p.get("clan_id")

    if not cid:
        return ("❌ شما کلن ندارید!",
                {"inline_keyboard": [[{"text": "🔙 بازگشت به منوی اصلی",
                                       "callback_data": "clan_back"}]]})

    clan_name = get_clan_name(cid)
    members = get_clan_members(cid)

    if not members:
        return (f"👥 کلن {clan_name}\n\n❌ عضوی نداره!",
                {"inline_keyboard": [[{"text": "🔙 بازگشت به منوی اصلی",
                                       "callback_data": "clan_back"}]]})

    members_sorted = sorted(members, key=lambda x: x[1].get("rank", 0), reverse=True)
    total = len(members_sorted)
    total_pages = (total + per_page - 1) // per_page

    if page < 0:
        page = 0
    if page >= total_pages:
        page = total_pages - 1

    start = page * per_page
    slice_list = members_sorted[start:start + per_page]

    text = f"📋 لیست اعضای کلن {clan_name}\n\n👥 تعداد اعضا: {total}\n\n"

    for i, (uid, d) in enumerate(slice_list, start + 1):
        name = d.get("name", "کاربر")
        rank = d.get("rank", 0)
        role = d.get("clan_role", "member")
        role_emoji = "👑" if role == "leader" else ("🎖️" if role == "officer" else "👤")
        text += f"{i}. {role_emoji} {name} — رنک: {rank}\n"

    text += f"\n📄 صفحه {page + 1} از {total_pages}"

    nav = []
    if page > 0:
        nav.append({"text": "⬅️ قبلی",
                    "callback_data": f"clan_members_p_{page - 1}"})
    if page + 1 < total_pages:
        nav.append({"text": "➡️ بعدی",
                    "callback_data": f"clan_members_p_{page + 1}"})

    buttons = []
    if nav:
        buttons.append(nav)
    buttons.append([{"text": "🔙 بازگشت به منوی اصلی", "callback_data": "clan_back"}])
    return text, {"inline_keyboard": buttons}


# ==================== پایگاه جنگنده ====================
def build_fighter_base_text(user_id):
    p = db.get(user_id, {})
    level = p.get("fighter_base_level", 0)
    user_level, _, _ = get_level_info(p.get("total_damage", 0))
    fighters = p.get("fighters_hero", {})

    if level == 0 and not fighters:
        return (f"✈️🔥 *پایگاه جنگنده*\n\n"
                f"❌ شما هنوز پایگاه و جنگنده‌ای ندارید!\n\n"
                f"🪙 هزینه ساخت پایگاه: {FIGHTER_BASE_BUILD_COST:,} سکه\n"
                f"🔒 سطح کاربر لازم: 5 (سطح شما: {user_level})\n\n"
                f"🎡 یا می‌تونی از گردونه جنگنده، جنگنده بگیری!\n"
                f"🔻 برای ساخت:")

    text = "✈️🔥 *پایگاه جنگنده*\n\n"
    if level > 0:
        base = FIGHTER_BASE_LEVELS.get(level, {})
        slots = base.get("slots", 0)
        used = get_used_fighter_slots(p)
        text += (f"📊 سطح پایگاه: {level}/{FIGHTER_BASE_MAX_LEVEL}\n"
                 f"🎯 ظرفیت: {used}/{slots}\n\n")
    else:
        text += ("❌ پایگاه نداری!\n"
                 "⚠️ برای ساخت جنگنده‌های سکه‌ای پایگاه لازمه.\n"
                 "🎡 ولی جنگنده‌های گردونه بدون پایگاه هم کار می‌کنن.\n\n")

    text += ("💥 جنگنده مثل هیرو در حمله ترکیبی دمیج اضافه می‌کند\n"
             "⚠️ از پدافند «ورنیکس» آسیب می‌گیرد\n"
             "🛡 فونیکس، حمله جنگنده‌های دشمن رو کم می‌کند\n\n")

    build_fighters = []
    wheel_fighters = []
    for fname, finfo in fighters.items():
        if finfo.get("count", 0) <= 0:
            continue
        f_data = HERO_FIGHTERS.get(fname, {})
        if f_data.get("source") == "wheel":
            wheel_fighters.append((fname, finfo, f_data))
        else:
            build_fighters.append((fname, finfo, f_data))

    def fmt_fighter(fname, finfo, f_data, emoji="🆕"):
        hp_c = finfo.get("hp_current", f_data.get("hp", 50))
        hp_m = f_data.get("hp", 50)
        bar_len = 12
        filled = int((hp_c / hp_m) * bar_len) if hp_m > 0 else 0
        bar = "█" * filled + "░" * (bar_len - filled)
        level_txt = ""
        if fname == "فونیکس":
            phx_lvl = finfo.get("level", 1)
            red = PHOENIX_REDUCTION.get(phx_lvl, 0)
            level_txt = (f"📊 سطح فونیکس: {phx_lvl}/{PHOENIX_MAX_LEVEL}\n"
                         f"🛡 کاهش حمله جنگنده دشمن: {red}%\n")
        return (f"{emoji} *{fname}*\n"
                f"{level_txt}"
                f"💥 دمیج: *{f_data.get('damage', 0)}* | "
                f"⚡ سرعت: *{f_data.get('speed', 0)}*\n"
                f"❤️ HP: *{hp_c}* / {hp_m}  {bar}\n"
                f"🔢 تعداد: {finfo['count']}\n")

    if build_fighters:
        text += "🛠 جنگنده‌های ساختنی:\n\n"
        for fname, finfo, f_data in build_fighters:
            text += fmt_fighter(fname, finfo, f_data) + "\n"

    if wheel_fighters:
        text += "🎡 جنگنده‌های گردونه:\n\n"
        for fname, finfo, f_data in wheel_fighters:
            text += fmt_fighter(fname, finfo, f_data) + "\n"

    text += "🔻 یکی از گزینه‌ها:"
    return text


def build_fighter_base_keyboard(user_id):
    p = db.get(user_id, {})
    level = p.get("fighter_base_level", 0)

    if level == 0:
        return {"inline_keyboard": [
            [{"text": f"🛒 ساخت پایگاه ({FIGHTER_BASE_BUILD_COST:,} سکه)",
              "callback_data": "fbase_build"}],
            [{"text": "🎡 گردونه جنگنده", "callback_data": "wheel_fighter"}],
            [{"text": "📖 راهنما", "callback_data": "help_fighter_base"}],
            [{"text": "🔙 بازگشت به منوی اصلی", "callback_data": "combo_back"}],
        ]}

    buttons = []
    items = []
    if level < FIGHTER_BASE_MAX_LEVEL:
        next_level = level + 1
        cost = FIGHTER_BASE_LEVELS[next_level]["upgrade_cost"]
        req = FIGHTER_BASE_LEVELS[next_level]["required_user_level"]
        items.append({"text": f"⬆️ ارتقا پایگاه ({cost:,} - لول {req})",
                      "callback_data": "fbase_upgrade"})

    items.append({"text": "🛩 خرید جنگنده سکه‌ای", "callback_data": "fbase_buy"})
    items.append({"text": "🎡 گردونه جنگنده", "callback_data": "wheel_fighter"})

    phoenix = p.get("fighters_hero", {}).get("فونیکس", {})
    if phoenix.get("count", 0) > 0:
        phx_lvl = phoenix.get("level", 1)
        if phx_lvl < PHOENIX_MAX_LEVEL:
            next_lvl = phx_lvl + 1
            cost = next_lvl * 150000
            items.append({
                "text": f"⬆️ ارتقا فونیکس {phx_lvl} → {next_lvl} ({cost:,})",
                "callback_data": "phoenix_upgrade"
            })

    items.append({"text": "🔧 تعمیر جنگنده‌ها", "callback_data": "fbase_repair"})

    for i in range(0, len(items), 2):
        buttons.append(items[i:i + 2])
    buttons.append([{"text": "📖 راهنما", "callback_data": "help_fighter_base"}])
    buttons.append([{"text": "🔙 بازگشت به منوی اصلی", "callback_data": "combo_back"}])
    return {"inline_keyboard": buttons}


def build_fighter_buy_text(user_id):
    p = db.get(user_id, {})
    level = p.get("fighter_base_level", 0)
    user_level, _, _ = get_level_info(p.get("total_damage", 0))
    coins = p.get("coins", 0)

    if level == 0:
        return "❌ اول باید پایگاه بسازی!"

    text = (f"🛠 خرید جنگنده سکه‌ای\n\n"
            f"🪙 سکه شما: {coins:,}\n"
            f"📊 سطح پایگاه: {level}/{FIGHTER_BASE_MAX_LEVEL}\n"
            f"📊 سطح شما: {user_level}\n\n"
            f"🔻 جنگنده‌های موجود:\n")
    return text


def build_fighter_buy_keyboard(user_id):
    p = db.get(user_id, {})
    level = p.get("fighter_base_level", 0)
    coins = p.get("coins", 0)

    items = []
    for fname, f_data in HERO_FIGHTERS.items():
        if f_data.get("source") != "build":
            continue
        if f_data["min_base_level"] <= level:
            cost = f_data["build_cost"]
            can_buy = coins // cost if cost > 0 else 0
            items.append({
                "text": f"✈️ {fname} | {cost:,}🪙 | x{can_buy}",
                "callback_data": f"fbase_buy_{fname}"
            })
    buttons = []
    for i in range(0, len(items), 2):
        buttons.append(items[i:i + 2])
    buttons.append([{"text": "🔙 بازگشت به منوی اصلی", "callback_data": "combo_fighter"}])
    return {"inline_keyboard": buttons}


def build_repair_fighters_text(user_id):
    p = db.get(user_id, {})
    fighters = p.get("fighters_hero", {})
    text = "🔧 تعمیر جنگنده‌ها\n\n"
    has_damaged = False
    for fname, finfo in fighters.items():
        if finfo.get("count", 0) <= 0:
            continue
        f_data = HERO_FIGHTERS.get(fname, {})
        hp_m = f_data.get("hp", 50)
        hp_c = finfo.get("hp_current", hp_m)
        if hp_c < hp_m:
            has_damaged = True
            need = hp_m - hp_c
            cost = need * 100
            text += f"✈️ {fname}: {hp_c}/{hp_m} → هزینه تعمیر: {cost:,} سکه\n"
    if not has_damaged:
        text += "✅ همه جنگنده‌ها سالم هستند!\n"
    return text


def build_repair_fighters_keyboard(user_id):
    p = db.get(user_id, {})
    fighters = p.get("fighters_hero", {})
    items = []
    for fname, finfo in fighters.items():
        if finfo.get("count", 0) <= 0:
            continue
        f_data = HERO_FIGHTERS.get(fname, {})
        hp_m = f_data.get("hp", 50)
        hp_c = finfo.get("hp_current", hp_m)
        if hp_c < hp_m:
            need = hp_m - hp_c
            cost = need * 100
            items.append({
                "text": f"🔧 {fname} ({cost:,})",
                "callback_data": f"fbase_repair_{fname}"
            })
    buttons = []
    for i in range(0, len(items), 2):
        buttons.append(items[i:i + 2])
    buttons.append([{"text": "🔙 بازگشت به منوی اصلی", "callback_data": "combo_fighter"}])
    return {"inline_keyboard": buttons}


# ==================== گردونه جنگنده ====================
def build_wheel_fighter_menu(user_id):
    p = db.get(user_id, {})
    coins = p.get("coins", 0)

    text = "🎡 *گردونه جنگنده*\n\n"
    text += "📊 *لیست جنگنده‌ها و قدرتشون:*\n\n"

    for prize in WHEEL_FIGHTER_PRIZES:
        if prize.get("name") is None:
            continue
        fname = prize["name"]
        f_data = HERO_FIGHTERS.get(fname, {})
        tier = f_data.get("tier", 0)
        dmg = f_data.get("damage", 0)
        speed = f_data.get("speed", 0)
        hp = f_data.get("hp", 0)

        if tier <= 1:
            emoji = "🟢"
        elif tier <= 2:
            emoji = "🟡"
        elif tier <= 3:
            emoji = "🟠"
        elif tier <= 4:
            emoji = "🔴"
        elif tier <= 5:
            emoji = "🟣"
        else:
            emoji = "⭐"

        text += (f"{emoji} *{fname}*\n"
                 f"   💥 دمیج: {dmg} | ⚡ سرعت: {speed} | ❤️ HP: {hp}\n"
                 f"   🎯 شانس: {prize['chance']}%\n\n")

    for prize in WHEEL_FIGHTER_PRIZES:
        if prize.get("type") == "coins":
            text += (f"🪙 *جایزه تسلی:* {prize['amount']:,} سکه "
                     f"({prize['chance']}%)\n\n")
            break

    text += "➖➖➖➖➖➖➖➖➖➖\n"
    text += f"🪙 سکه شما: {coins:,}\n\n"
    text += f"🎯 *هزینه هر بار:* {WHEEL_FIGHTER_PRICE_1:,} سکه\n"
    text += f"🎯 *هزینه 10 بار:* {WHEEL_FIGHTER_PRICE_10:,} سکه\n\n"
    text += "🔻 چند بار می‌خوای بچرخونی؟"

    buttons = [
        [{"text": f"🎡 1 بار ({WHEEL_FIGHTER_PRICE_1:,} سکه)",
          "callback_data": "wheel_fighter_1"}],
        [{"text": f"🎡 10 بار ({WHEEL_FIGHTER_PRICE_10:,} سکه)",
          "callback_data": "wheel_fighter_10"}],
        [{"text": "🔙 بازگشت", "callback_data": "combo_back"}],
    ]
    return text, {"inline_keyboard": buttons}


def build_wheel_fighter_result(user_id, prizes):
    text = "🎡 *گردونه جنگنده*\n\n"
    text += "🎰 نتیجه چرخش:\n\n"

    total_coins = 0
    total_fighters = 0

    for i, prize in enumerate(prizes, 1):
        if prize.get("type") == "coins":
            total_coins += prize["amount"]
            text += f"{i}. 🪙 {prize['amount']:,} سکه\n"
        else:
            total_fighters += 1
            fname = prize["name"]
            f_data = HERO_FIGHTERS.get(fname, {})
            text += (f"{i}. ✈️ *{fname}* "
                     f"(💥 {f_data.get('damage', 0)})\n")

    text += "\n➖➖➖➖➖➖➖➖➖➖\n"
    text += f"🎯 *خلاصه:*\n"
    text += f"✈️ جنگنده: {total_fighters}\n"
    text += f"🪙 سکه: {total_coins:,}\n\n"

    p = db.get(user_id, {})
    text += f"🪙 سکه باقیمانده: {p.get('coins', 0):,}\n"
    text += (f"✈️ مجموع جنگنده‌های تو: "
             f"{sum(f.get('count',0) for f in p.get('fighters_hero',{}).values())}")

    buttons = [
        [{"text": "🎡 چرخش مجدد", "callback_data": "wheel_fighter"}],
        [{"text": "✈️ پایگاه جنگنده", "callback_data": "combo_fighter"}],
        [{"text": "🔙 بازگشت", "callback_data": "combo_back"}],
    ]
    return text, {"inline_keyboard": buttons}


# ==================== گردونه طوفان ====================
def build_wheel_storm_menu(user_id):
    p = db.get(user_id, {})
    coins = p.get("coins", 0)

    text = "🌊 *گردونه طوفان*\n\n"
    text += "🚀 موشک‌های کروز انحصاری\n"
    text += "⚠️ فقط در حمله عادی قابل استفاده هستند\n"
    text += "❌ قابل ارتقا نیستند\n\n"
    text += "📊 *جوایز:*\n\n"

    for prize in WHEEL_STORM_PRIZES:
        if prize["type"] == "coins":
            text += f"🪙 {prize['name']} — 🎯 {prize['chance']}%\n"
        elif prize["type"] == "weapon":
            emoji = get_missile_emoji(prize["weapon"])
            text += f"{emoji} {prize['name']} — 🎯 {prize['chance']}%\n"

    text += "\n➖➖➖➖➖➖➖➖➖➖\n"
    text += f"🪙 سکه شما: {coins:,}\n\n"
    text += f"🎯 *هزینه 1 بار:* {WHEEL_STORM_PRICE_1:,} سکه\n"
    text += f"🎯 *هزینه 10 بار:* {WHEEL_STORM_PRICE_10:,} سکه\n\n"
    text += "🔻 چند بار می‌خوای بچرخونی؟"

    buttons = [
        [{"text": f"🎡 1 بار ({WHEEL_STORM_PRICE_1:,} سکه)",
          "callback_data": "wheel_storm_1"}],
        [{"text": f"🎡 10 بار ({WHEEL_STORM_PRICE_10:,} سکه)",
          "callback_data": "wheel_storm_10"}],
        [{"text": "🔙 بازگشت", "callback_data": "go_wheel"}],
    ]
    return text, {"inline_keyboard": buttons}


def build_wheel_storm_result(user_id, prizes):
    text = "🌊 *گردونه طوفان*\n\n"
    text += "🎰 نتیجه چرخش:\n\n"

    total_coins = 0
    total_weapons = 0

    for i, prize in enumerate(prizes, 1):
        if prize["type"] == "coins":
            total_coins += prize["amount"]
            text += f"{i}. 🪙 {prize['amount']:,} سکه\n"
        elif prize["type"] == "weapon":
            total_weapons += prize["amount"]
            emoji = get_missile_emoji(prize["weapon"])
            text += f"{i}. {emoji} {prize['weapon']} × {prize['amount']}\n"

    text += "\n➖➖➖➖➖➖➖➖➖➖\n"
    text += "🎯 *خلاصه:*\n"
    if total_weapons > 0:
        text += f"🚀 موشک: {total_weapons} عدد\n"
    text += f"🪙 سکه: {total_coins:,}\n\n"

    p = db.get(user_id, {})
    text += f"🪙 سکه باقی‌مانده: {p.get('coins', 0):,}"

    buttons = [
        [{"text": "🎡 چرخش مجدد", "callback_data": "wheel_storm"}],
        [{"text": "🔙 بازگشت به گردونه‌ها", "callback_data": "go_wheel"}],
    ]
    return text, {"inline_keyboard": buttons}


# ==================== گردونه شکار ====================
def build_wheel_hunt_menu(user_id):
    p = db.get(user_id, {})
    coins = p.get("coins", 0)

    text = "🐉 *گردونه شکار*\n\n"
    text += "🚀 موشک‌های بالستیک انحصاری\n"
    text += "⚠️ فقط در حمله عادی قابل استفاده هستند\n"
    text += "❌ قابل ارتقا نیستند\n\n"
    text += "📊 *جوایز:*\n\n"

    for prize in WHEEL_HUNT_PRIZES:
        if prize["type"] == "coins":
            text += f"🪙 {prize['name']} — 🎯 {prize['chance']}%\n"
        elif prize["type"] == "weapon":
            emoji = get_missile_emoji(prize["weapon"])
            text += f"{emoji} {prize['name']} — 🎯 {prize['chance']}%\n"
        elif prize["type"] == "defense":
            emoji = get_defense_emoji(prize["defense"])
            text += f"{emoji} {prize['name']} — 🎯 {prize['chance']}%\n"

    text += "\n➖➖➖➖➖➖➖➖➖➖\n"
    text += f"🪙 سکه شما: {coins:,}\n\n"
    text += f"🎯 *هزینه 1 بار:* {WHEEL_HUNT_PRICE_1:,} سکه\n"
    text += f"🎯 *هزینه 10 بار:* {WHEEL_HUNT_PRICE_10:,} سکه\n\n"
    text += "🔻 چند بار می‌خوای بچرخونی؟"

    buttons = [
        [{"text": f"🎡 1 بار ({WHEEL_HUNT_PRICE_1:,} سکه)",
          "callback_data": "wheel_hunt_1"}],
        [{"text": f"🎡 10 بار ({WHEEL_HUNT_PRICE_10:,} سکه)",
          "callback_data": "wheel_hunt_10"}],
        [{"text": "🔙 بازگشت", "callback_data": "go_wheel"}],
    ]
    return text, {"inline_keyboard": buttons}


def build_wheel_hunt_result(user_id, prizes):
    text = "🐉 *گردونه شکار*\n\n"
    text += "🎰 نتیجه چرخش:\n\n"

    total_coins = 0
    total_weapons = 0
    total_defenses = 0

    for i, prize in enumerate(prizes, 1):
        if prize["type"] == "coins":
            total_coins += prize["amount"]
            text += f"{i}. 🪙 {prize['amount']:,} سکه\n"
        elif prize["type"] == "weapon":
            total_weapons += prize["amount"]
            emoji = get_missile_emoji(prize["weapon"])
            text += f"{i}. {emoji} {prize['weapon']} × {prize['amount']}\n"
        elif prize["type"] == "defense":
            total_defenses += prize["amount"]
            emoji = get_defense_emoji(prize["defense"])
            text += f"{i}. {emoji} {prize['defense']} × {prize['amount']}\n"

    text += "\n➖➖➖➖➖➖➖➖➖➖\n"
    text += "🎯 *خلاصه:*\n"
    if total_weapons > 0:
        text += f"🚀 موشک: {total_weapons} عدد\n"
    if total_defenses > 0:
        text += f"🛡 پدافند: {total_defenses} عدد\n"
    text += f"🪙 سکه: {total_coins:,}\n\n"

    p = db.get(user_id, {})
    text += f"🪙 سکه باقی‌مانده: {p.get('coins', 0):,}"

    buttons = [
        [{"text": "🎡 چرخش مجدد", "callback_data": "wheel_hunt"}],
        [{"text": "🔙 بازگشت به گردونه‌ها", "callback_data": "go_wheel"}],
    ]
    return text, {"inline_keyboard": buttons}


# ==================== گردونه آتش ====================
def build_wheel_fire_menu(user_id):
    p = db.get(user_id, {})
    coins = p.get("coins", 0)

    text = "🔥 *گردونه آتش*\n\n"
    text += "🚀 موشک‌های هایپرسونیک انحصاری\n"
    text += "⚠️ فقط در حمله عادی قابل استفاده هستند\n"
    text += "❌ قابل ارتقا نیستند\n\n"
    text += "📊 *جوایز:*\n\n"

    for prize in WHEEL_FIRE_PRIZES:
        if prize["type"] == "coins":
            text += f"🪙 {prize['name']} — 🎯 {prize['chance']}%\n"
        elif prize["type"] == "weapon":
            emoji = get_missile_emoji(prize["weapon"])
            text += f"{emoji} {prize['name']} — 🎯 {prize['chance']}%\n"
        elif prize["type"] == "defense":
            emoji = get_defense_emoji(prize["defense"])
            text += f"{emoji} {prize['name']} — 🎯 {prize['chance']}%\n"

    text += "\n➖➖➖➖➖➖➖➖➖➖\n"
    text += f"🪙 سکه شما: {coins:,}\n\n"
    text += f"🎯 *هزینه 1 بار:* {WHEEL_FIRE_PRICE_1:,} سکه\n"
    text += f"🎯 *هزینه 10 بار:* {WHEEL_FIRE_PRICE_10:,} سکه\n\n"
    text += "🔻 چند بار می‌خوای بچرخونی؟"

    buttons = [
        [{"text": f"🎡 1 بار ({WHEEL_FIRE_PRICE_1:,} سکه)",
          "callback_data": "wheel_fire_1"}],
        [{"text": f"🎡 10 بار ({WHEEL_FIRE_PRICE_10:,} سکه)",
          "callback_data": "wheel_fire_10"}],
        [{"text": "🔙 بازگشت", "callback_data": "go_wheel"}],
    ]
    return text, {"inline_keyboard": buttons}


def build_wheel_fire_result(user_id, prizes):
    text = "🔥 *گردونه آتش*\n\n"
    text += "🎰 نتیجه چرخش:\n\n"

    total_coins = 0
    total_weapons = 0
    total_defenses = 0

    for i, prize in enumerate(prizes, 1):
        if prize["type"] == "coins":
            total_coins += prize["amount"]
            text += f"{i}. 🪙 {prize['amount']:,} سکه\n"
        elif prize["type"] == "weapon":
            total_weapons += prize["amount"]
            emoji = get_missile_emoji(prize["weapon"])
            text += f"{i}. {emoji} {prize['weapon']} × {prize['amount']}\n"
        elif prize["type"] == "defense":
            total_defenses += prize["amount"]
            emoji = get_defense_emoji(prize["defense"])
            text += f"{i}. {emoji} {prize['defense']} × {prize['amount']}\n"

    text += "\n➖➖➖➖➖➖➖➖➖➖\n"
    text += "🎯 *خلاصه:*\n"
    if total_weapons > 0:
        text += f"🚀 موشک: {total_weapons} عدد\n"
    if total_defenses > 0:
        text += f"🛡 پدافند: {total_defenses} عدد\n"
    text += f"🪙 سکه: {total_coins:,}\n\n"

    p = db.get(user_id, {})
    text += f"🪙 سکه باقی‌مانده: {p.get('coins', 0):,}"

    buttons = [
        [{"text": "🎡 چرخش مجدد", "callback_data": "wheel_fire"}],
        [{"text": "🔙 بازگشت به گردونه‌ها", "callback_data": "go_wheel"}],
    ]
    return text, {"inline_keyboard": buttons}


# ==================== گردونه اژدها ====================
def build_wheel_dragon_menu(user_id):
    p = db.get(user_id, {})
    coins = p.get("coins", 0)

    text = "🐲 *گردونه اژدها*\n\n"
    text += "✈️ جنگنده‌های انحصاری\n\n"
    text += "📊 *جوایز:*\n\n"

    for prize in WHEEL_DRAGON_PRIZES:
        if prize["type"] == "coins":
            text += f"🪙 {prize['name']} — 🎯 {prize['chance']}%\n"
        elif prize["type"] == "fighter":
            fname = prize["fighter"]
            f_data = HERO_FIGHTERS.get(fname, {})
            text += (f"✈️ {prize['name']} "
                     f"(💥 {f_data.get('damage', 0)}) — 🎯 {prize['chance']}%\n")

    text += "\n➖➖➖➖➖➖➖➖➖➖\n"
    text += f"🪙 سکه شما: {coins:,}\n\n"
    text += f"🎯 *هزینه 1 بار:* {WHEEL_DRAGON_PRICE_1:,} سکه\n"
    text += f"🎯 *هزینه 10 بار:* {WHEEL_DRAGON_PRICE_10:,} سکه\n\n"
    text += "🔻 چند بار می‌خوای بچرخونی؟"

    buttons = [
        [{"text": f"🎡 1 بار ({WHEEL_DRAGON_PRICE_1:,} سکه)",
          "callback_data": "wheel_dragon_1"}],
        [{"text": f"🎡 10 بار ({WHEEL_DRAGON_PRICE_10:,} سکه)",
          "callback_data": "wheel_dragon_10"}],
        [{"text": "🔙 بازگشت", "callback_data": "go_wheel"}],
    ]
    return text, {"inline_keyboard": buttons}


def build_wheel_dragon_result(user_id, prizes):
    text = "🐲 *گردونه اژدها*\n\n"
    text += "🎰 نتیجه چرخش:\n\n"

    total_coins = 0
    total_fighters = 0

    for i, prize in enumerate(prizes, 1):
        if prize["type"] == "coins":
            total_coins += prize["amount"]
            text += f"{i}. 🪙 {prize['amount']:,} سکه\n"
        elif prize["type"] == "fighter":
            total_fighters += prize["amount"]
            fname = prize["fighter"]
            f_data = HERO_FIGHTERS.get(fname, {})
            text += (f"{i}. ✈️ {fname} × {prize['amount']} "
                     f"(💥 {f_data.get('damage', 0)})\n")

    text += "\n➖➖➖➖➖➖➖➖➖➖\n"
    text += "🎯 *خلاصه:*\n"
    if total_fighters > 0:
        text += f"✈️ جنگنده: {total_fighters}\n"
    text += f"🪙 سکه: {total_coins:,}\n\n"

    p = db.get(user_id, {})
    text += f"🪙 سکه باقی‌مانده: {p.get('coins', 0):,}\n"
    text += (f"✈️ مجموع جنگنده‌های تو: "
             f"{sum(f.get('count',0) for f in p.get('fighters_hero',{}).values())}")

    buttons = [
        [{"text": "🎡 چرخش مجدد", "callback_data": "wheel_dragon"}],
        [{"text": "✈️ پایگاه جنگنده", "callback_data": "combo_fighter"}],
        [{"text": "🔙 بازگشت به گردونه‌ها", "callback_data": "go_wheel"}],
    ]
    return text, {"inline_keyboard": buttons}


# ==================== گردونه روزانه ====================
def build_wheel_daily_menu(user_id):
    p = db.get(user_id, {})
    last = p.get("last_free_wheel", 0)
    now = time.time()
    diff = now - last
    cooldown = 24 * 3600
    ready = diff >= cooldown

    text = "🎁 *گردونه روزانه*\n\n"
    text += "🎉 هر 24 ساعت یکبار رایگان!\n\n"
    text += "📊 *جوایز:*\n\n"

    for prize in WHEEL_DAILY_PRIZES:
        if prize["type"] == "weapon":
            emoji = get_missile_emoji(prize["weapon"])
            text += f"{emoji} {prize['name']} — 🎯 {prize['chance']}%\n"
        elif prize["type"] == "coins":
            text += f"🪙 {prize['name']} — 🎯 {prize['chance']}%\n"
        elif prize["type"] == "oil":
            text += f"🛢 {prize['name']} — 🎯 {prize['chance']}%\n"
        elif prize["type"] == "iron":
            text += f"⛏ {prize['name']} — 🎯 {prize['chance']}%\n"
        elif prize["type"] == "steel":
            text += f"🏭 {prize['name']} — 🎯 {prize['chance']}%\n"

    text += "\n➖➖➖➖➖➖➖➖➖➖\n"

    if ready:
        text += "✅ آماده چرخش!\n\n"
        buttons = [
            [{"text": "🎁 بچرخون (رایگان)", "callback_data": "wheel_daily_1"}],
            [{"text": "🔙 بازگشت", "callback_data": "go_wheel"}],
        ]
    else:
        rem = int(cooldown - diff)
        text += f"⏳ بعدی در: {_fmt_remaining(rem)}\n\n"
        buttons = [
            [{"text": "🔙 بازگشت", "callback_data": "go_wheel"}],
        ]

    return text, {"inline_keyboard": buttons}


def build_wheel_daily_result(user_id, prizes):
    text = "🎁 *گردونه روزانه*\n\n"
    text += "🎰 نتیجه چرخش:\n\n"

    for i, prize in enumerate(prizes, 1):
        if prize["type"] == "weapon":
            emoji = get_missile_emoji(prize["weapon"])
            text += f"{i}. {emoji} {prize['weapon']} × {prize['amount']}\n"
        elif prize["type"] == "coins":
            text += f"{i}. 🪙 {prize['amount']:,} سکه\n"
        elif prize["type"] == "oil":
            text += f"{i}. 🛢 {prize['amount']:,} نفت\n"
        elif prize["type"] == "iron":
            text += f"{i}. ⛏ {prize['amount']:,} آهن\n"
        elif prize["type"] == "steel":
            text += f"{i}. 🏭 {prize['amount']:,} فولاد\n"

    text += "\n➖➖➖➖➖➖➖➖➖➖\n"
    text += "🎉 فردا دوباره بیا!\n\n"

    p = db.get(user_id, {})
    text += f"🪙 سکه: {p.get('coins', 0):,}\n"
    text += f"🛢 نفت: {p.get('oil', 0):,}\n"
    text += f"⛏ آهن: {p.get('iron', 0):,}"

    buttons = [
        [{"text": "🔙 بازگشت به گردونه‌ها", "callback_data": "go_wheel"}],
    ]
    return text, {"inline_keyboard": buttons}


# ==================== گردونه افسانه‌ای ====================
def build_wheel_legendary_menu(user_id):
    p = db.get(user_id, {})
    coins = p.get("coins", 0)

    text = "🎡 *گردونه افسانه‌ای*\n\n"
    text += "📊 *جوایز:*\n\n"

    for prize in WHEEL_LEGENDARY_PRIZES:
        if prize["type"] == "weapon":
            emoji = get_missile_emoji(prize["weapon"])
            text += f"{emoji} {prize['name']} — 🎯 {prize['chance']}%\n"
        elif prize["type"] == "fighter":
            text += f"✈️ {prize['name']} — 🎯 {prize['chance']}%\n"
        elif prize["type"] == "defense":
            emoji = get_defense_emoji(prize["defense"])
            text += f"{emoji} {prize['name']} — 🎯 {prize['chance']}%\n"
        elif prize["type"] == "coins":
            text += f"🪙 {prize['name']} — 🎯 {prize['chance']}%\n"

    text += "\n➖➖➖➖➖➖➖➖➖➖\n"
    text += f"🪙 سکه شما: {coins:,}\n\n"
    text += f"🎯 *هزینه 1 بار:* {WHEEL_LEGENDARY_PRICE_1:,} سکه\n"
    text += f"🎯 *هزینه 10 بار:* {WHEEL_LEGENDARY_PRICE_10:,} سکه\n\n"
    text += "🔻 چند بار می‌خوای بچرخونی؟"

    buttons = [
        [{"text": f"🎡 1 بار ({WHEEL_LEGENDARY_PRICE_1:,} سکه)",
          "callback_data": "wheel_legendary_1"}],
        [{"text": f"🎡 10 بار ({WHEEL_LEGENDARY_PRICE_10:,} سکه)",
          "callback_data": "wheel_legendary_10"}],
        [{"text": "🔙 بازگشت", "callback_data": "go_wheel"}],
    ]
    return text, {"inline_keyboard": buttons}


def build_wheel_legendary_result(user_id, prizes):
    text = "🎡 *گردونه افسانه‌ای*\n\n"
    text += "🎰 نتیجه چرخش:\n\n"

    total_coins = 0
    total_weapons = 0
    total_fighters = 0
    total_defenses = 0

    for i, prize in enumerate(prizes, 1):
        if prize["type"] == "weapon":
            total_weapons += prize["amount"]
            emoji = get_missile_emoji(prize["weapon"])
            text += f"{i}. {emoji} {prize['weapon']} × {prize['amount']}\n"
        elif prize["type"] == "fighter":
            total_fighters += prize["amount"]
            text += f"{i}. ✈️ {prize['fighter']} × {prize['amount']}\n"
        elif prize["type"] == "defense":
            total_defenses += prize["amount"]
            emoji = get_defense_emoji(prize["defense"])
            text += f"{i}. {emoji} {prize['defense']} × {prize['amount']}\n"
        elif prize["type"] == "coins":
            total_coins += prize["amount"]
            text += f"{i}. 🪙 {prize['amount']:,} سکه\n"

    text += "\n➖➖➖➖➖➖➖➖➖➖\n"
    text += "🎯 *خلاصه:*\n"
    if total_weapons > 0: text += f"🚀 موشک: {total_weapons}\n"
    if total_fighters > 0: text += f"✈️ جنگنده: {total_fighters}\n"
    if total_defenses > 0: text += f"🛡 پدافند: {total_defenses}\n"
    text += f"🪙 سکه: {total_coins:,}\n\n"

    p = db.get(user_id, {})
    text += f"🪙 سکه باقی‌مانده: {p.get('coins', 0):,}"

    buttons = [
        [{"text": "🎡 چرخش مجدد", "callback_data": "wheel_legendary"}],
        [{"text": "🔙 بازگشت به گردونه‌ها", "callback_data": "go_wheel"}],
    ]
    return text, {"inline_keyboard": buttons}


# ==================== گردونه بخت ====================
def build_wheel_luck_menu(user_id):
    p = db.get(user_id, {})
    coins = p.get("coins", 0)

    text = "🎰 *گردونه بخت*\n\n"
    text += "⚠️ *ریسک بالا، جایزه بالا!*\n"
    text += "❌ 50% شانس = هیچی\n\n"
    text += "📊 *جوایز:*\n\n"

    for prize in WHEEL_LUCK_PRIZES:
        if prize["type"] == "nothing":
            text += f"😔 هیچی — 🎯 {prize['chance']}%\n"
        elif prize["type"] == "multi":
            text += f"{prize['name']} — 🎯 {prize['chance']}%\n"
        elif prize["type"] == "coins":
            text += f"🪙 {prize['name']} — 🎯 {prize['chance']}%\n"

    text += "\n➖➖➖➖➖➖➖➖➖➖\n"
    text += f"🪙 سکه شما: {coins:,}\n\n"
    text += f"🎯 *هزینه هر بار:* {WHEEL_LUCK_PRICE_1:,} سکه\n\n"
    text += "🔻 بختی؟ بچرخون!"

    buttons = [
        [{"text": f"🎰 بچرخون ({WHEEL_LUCK_PRICE_1:,} سکه)",
          "callback_data": "wheel_luck_1"}],
        [{"text": "🔙 بازگشت", "callback_data": "go_wheel"}],
    ]
    return text, {"inline_keyboard": buttons}


def build_wheel_luck_result(user_id, prizes):
    text = "🎰 *گردونه بخت*\n\n"
    text += "🎰 نتیجه چرخش:\n\n"

    for i, prize in enumerate(prizes, 1):
        if prize["type"] == "nothing":
            text += f"{i}. 😔 بخت یارت نبود!\n"
        elif prize["type"] == "coins":
            text += f"{i}. 🪙 {prize['amount']:,} سکه\n"
        elif prize["type"] == "multi":
            text += f"{i}. 🏆 {prize['name']}!\n"

    text += "\n➖➖➖➖➖➖➖➖➖➖\n"

    p = db.get(user_id, {})
    text += f"🪙 سکه باقی‌مانده: {p.get('coins', 0):,}\n\n"

    if prizes[0]["type"] == "nothing":
        text += "💡 دفعه بعد شانس بیار!"
    else:
        text += "🎉 تبریک!"

    buttons = [
        [{"text": "🎰 چرخش مجدد", "callback_data": "wheel_luck"}],
        [{"text": "🔙 بازگشت به گردونه‌ها", "callback_data": "go_wheel"}],
    ]
    return text, {"inline_keyboard": buttons}


# ==================== راهنمای پهباد ====================
def build_drone_text(user_id):
    p = db.get(user_id, {})
    coins = p.get("coins", 0)
    user_level, _, _ = get_level_info(p.get("total_damage", 0))

    text = "🛩️ پهبادها:\n\n"
    text += f"📊 سطح شما: {user_level}\n"
    text += f"🪙 سکه‌های شما: {coins:,}\n\n"

    text += "📖 راهنمای پهبادها:\n"
    for name, info in DRONES.items():
        price = info["price"]
        desc = info["desc"]
        text += f"🛩 {name} (لول {info['required_level']}): {price:,}🪙\n"
        text += f"   └ {desc}\n"

    text += "\n🔻 یکی از پهبادها رو برای خرید انتخاب کن:"
    return text


def build_drone_keyboard(user_id):
    p = db.get(user_id, {})
    coins = p.get("coins", 0)
    items = []
    for d_name, d_info in DRONES.items():
        price = d_info["price"]
        can_buy = coins // price if price > 0 else 0
        desc = d_info["desc"]
        items.append({
            "text": f"🛩 {d_name} | {price}🪙 | x{can_buy}",
            "callback_data": f"buy_drone_{d_name}"
        })
    buttons = [items[i:i + 2] for i in range(0, len(items), 2)]
    buttons.append([{"text": "📖 راهنما", "callback_data": "help_drone"}])
    buttons.append([{"text": "🔙 بازگشت به منوی اصلی", "callback_data": "shop_back"}])
    return {"inline_keyboard": buttons}


# ==================== 🛒 World Shop ====================
def get_today_str():
    return datetime.now().strftime("%Y-%m-%d")


def build_world_pass_text(user_id):
    """متن صفحه World Shop"""
    p = db.get(user_id, {})

    active = p.get("world_pass_active", False)
    claimed = p.get("world_pass_days_claimed", 0)
    last_claim = p.get("world_pass_last_claim_date", "")
    today = get_today_str()

    if not active:
        if claimed >= WORLD_PASS_TOTAL_DAYS:
            header = (
                f"🎉 *فصل قبل کامل شد!*\n"
                f"📊 پیشرفت قبلی: *{claimed}/{WORLD_PASS_TOTAL_DAYS}*\n\n"
                f"━━━━━━━━━━━━━━━━━\n"
                f"💎 *فصل جدید بخر:*\n"
            )
        else:
            header = (
                f"با خرید امکانات ویژه‌ای دریافت می‌کنید:\n"
                f"• دسترسی به جوایز روزانه اختصاصی\n"
                f"• دریافت بج اختصاصی 👑\n\n"
                f"━━━━━━━━━━━━━━━━━\n"
                f"📦 *جوایز این فصل:*\n\n"
            )

        text = (
            f"⭐️ *{WORLD_PASS_TITLE}* ⭐️\n"
            f"━━━━━━━━━━━━━━━━━\n\n"
            f"{header}"
        )

        for r in WORLD_PASS_REWARDS:
            text += f"روز {r['day']} → {r['text']}\n"

        text += (
            f"\n━━━━━━━━━━━━━━━━━\n"
            f"💎 *هزینه:* {WORLD_PASS_PRICE_TOMAN:,} تومان\n\n"
            f"🔻 برای خرید روی دکمه زیر بزن:"
        )
        return text

    text = (
        f"⭐️ *{WORLD_PASS_TITLE}* ⭐️\n"
        f"━━━━━━━━━━━━━━━━━\n\n"
        f"✅ *اشتراک فعال*\n"
        f"📊 پیشرفت: *{claimed}/{WORLD_PASS_TOTAL_DAYS} روز*\n\n"
        f"📦 *لیست جوایز:*\n\n"
    )

    for r in WORLD_PASS_REWARDS:
        if r["day"] <= claimed:
            text += f"✅ روز {r['day']} → {r['text']}\n"
        elif r["day"] == claimed + 1:
            text += f"🔔 روز {r['day']} → {r['text']} ← *آماده دریافت*\n"
        else:
            text += f"🔒 روز {r['day']} → {r['text']}\n"

    text += "\n━━━━━━━━━━━━━━━━━\n"

    if claimed >= WORLD_PASS_TOTAL_DAYS:
        text += (
            "🎉 *فصل تموم شد!*\n"
            "همه جوایز رو دریافت کردی.\n\n"
            "💎 می‌تونی فصل جدید بخری:"
        )
    elif last_claim == today:
        text += "⏳ *جایزه امروز رو گرفتی!*\nفردا دوباره بیا 🎁"
    else:
        text += f"🎁 *جایزه امروز آماده‌ست!*\nروز {claimed+1} → {WORLD_PASS_REWARDS[claimed]['text']}"

    return text


def build_world_pass_keyboard(user_id):
    """کیبورد World Shop"""
    p = db.get(user_id, {})
    active = p.get("world_pass_active", False)
    claimed = p.get("world_pass_days_claimed", 0)
    last_claim = p.get("world_pass_last_claim_date", "")
    today = get_today_str()

    if not active:
        kb = {"inline_keyboard": [
            [{"text": f"💳 خرید World Shop ({WORLD_PASS_PRICE_TOMAN:,} تومان)",
              "callback_data": "world_pass_buy"}],
            [{"text": "🔙 بازگشت به منوی اصلی", "callback_data": "go_main"}],
        ]}
        return kb

    buttons = []

    if claimed >= WORLD_PASS_TOTAL_DAYS:
        buttons.append([{"text": f"💳 خرید فصل جدید ({WORLD_PASS_PRICE_TOMAN:,} تومان)",
                         "callback_data": "world_pass_buy"}])
    elif last_claim != today:
        buttons.append([{"text": f"🎁 دریافت جایزه روز {claimed+1}",
                         "callback_data": "world_pass_claim"}])
    else:
        buttons.append([{"text": "✅ جایزه امروز دریافت شد",
                         "callback_data": "world_pass_already"}])

    buttons.append([{"text": "🔙 بازگشت به منوی اصلی", "callback_data": "go_main"}])
    return {"inline_keyboard": buttons}


# ==================== ⭐️ اشتراک ویژه (Subscription) ====================
def build_subscription_text(user_id):
    """متن صفحه اشتراک ویژه — کاملاً جدا از World Shop"""
    p = db.get(user_id, {})
    is_sub = is_subscription_active(user_id)
    today = get_today_str()
    claimed_today = p.get("subscription_last_mission_claim") == today

    text = "⭐️ *اشتراک ویژه WORLD WAR* ⭐️\n"
    text += "━━━━━━━━━━━━━━━━━\n\n"

    if is_sub:
        days_left = get_subscription_days_left(user_id)
        text += f"✅ *اشتراک فعال*\n"
        text += f"📅 باقی‌مانده: *{days_left} روز*\n\n"
    else:
        text += f"❌ *اشتراک غیرفعال*\n\n"
        text += f"💰 *قیمت:* {SUBSCRIPTION_PRICE_TOMAN:,} تومان\n"
        text += f"📅 *مدت:* {SUBSCRIPTION_DURATION_DAYS} روز\n\n"

    text += "🎁 *مزایای اشتراک:*\n"
    text += f"• 🚀 {SUB_DISCOUNT_MISSILE}٪ تخفیف روی همه موشک‌ها\n"
    text += f"• 💎 الماس در جایزه روزانه (شانس {SUB_GEMS_CHANCE}٪)\n"
    text += f"• 💰 انتقال سکه تا {SUB_TRANSFER_LIMIT:,}\n"
    text += f"• 🚀 {SUB_DAILY_CRUISE} کروز + {SUB_DAILY_BALLISTIC} بالستیک + {SUB_DAILY_HYPERSONIC} هایپرسونیک روزانه\n"
    text += f"• 🛡 سپر تا {SUB_SHIELD_MAX_SECONDS//3600} ساعت در روز\n\n"

    if is_sub:
        text += f"📦 *وضعیت امروز:*\n"
        text += f"🎁 موشک روزانه: {'✅ دریافت شده' if claimed_today else '🔔 آماده دریافت'}\n"

        shield_used = p.get("sub_shield_used_today", 0)
        if p.get("sub_shield_date") != today:
            shield_used = 0
        text += f"🛡 سپر استفاده‌شده: {shield_used//60} از {SUB_SHIELD_MAX_SECONDS//60} دقیقه\n"

        shield_until = p.get("sub_shield_until", 0)
        if shield_until > time.time():
            remaining = int(shield_until - time.time())
            text += f"\n🛡 *سپر فعال:* {remaining//60} دقیقه دیگر\n"

    text += "\n━━━━━━━━━━━━━━━━━\n"
    text += "💡 *جدا از World Shop است*"
    return text


def build_subscription_keyboard(user_id):
    """کیبورد اشتراک ویژه"""
    p = db.get(user_id, {})
    is_sub = is_subscription_active(user_id)
    today = get_today_str()
    claimed_today = p.get("subscription_last_mission_claim") == today

    buttons = []

    if not is_sub:
        buttons.append([{"text": f"💳 خرید اشتراک ({SUBSCRIPTION_PRICE_TOMAN:,} تومان)",
                         "callback_data": "subscription_buy"}])
    else:
        if not claimed_today:
            buttons.append([{"text": "🎁 دریافت موشک‌های روزانه",
                             "callback_data": "sub_claim_missiles"}])
        else:
            buttons.append([{"text": "✅ موشک‌های امروز دریافت شد",
                             "callback_data": "sub_already_claimed"}])

        buttons.append([{"text": "🛡 فعال‌سازی سپر",
                         "callback_data": "sub_shield"}])

    buttons.append([{"text": "🔙 بازگشت به سایر",
                     "callback_data": "other_back"}])
    return {"inline_keyboard": buttons}


# ==================== 💳 خرید آیتم ====================
def build_item_shop_keyboard():
    return {"inline_keyboard": [
        [{"text": "⭐ پک لول", "callback_data": "item_buy_level"}],
        [{"text": "🛢 پک نفت", "callback_data": "item_buy_oil"}],
        [{"text": "🪙 پک سکه", "callback_data": "item_buy_coins"}],
        [{"text": "💎 پک الماس", "callback_data": "item_buy_gems"}],
        [{"text": "🔙 بازگشت به منوی اصلی", "callback_data": "go_main"}],
    ]}


def build_item_shop_text():
    text = "💎 *فروشگاه آیتم*\n"
    text += "━━━━━━━━━━━━━━━━━━━\n\n"
    text += "سلام! 👋\n"
    text += "هرچی می‌خوای رو انتخاب کن، خودش برات حساب می‌کنه:\n\n"
    text += "⭐ *پک لول* ← هر سطح ۲۰,۰۰۰ تومان\n"
    text += "🛢 *پک نفت* ← هر ۱,۰۰۰ نفت ۲,۰۰۰ تومان\n"
    text += "🪙 *پک سکه* ← هر ۱,۰۰۰ سکه ۲,۰۰۰ تومان\n"
    text += "💎 *پک الماس* ← هر ۵۰ الماس ۵۰ تومان\n\n"
    text += "💰 قیمت‌ها به تومان حساب می‌شن\n"
    text += "👇 یکی رو انتخاب کن"
    return text


def build_item_ask_text(key):
    pack = ITEM_PACKS[key]

    if key == "level":
        return (
            f"{pack['emoji']} *{pack['name']}*\n"
            f"━━━━━━━━━━━━━━━━━━━\n\n"
            f"💰 قیمت هر سطح: *{pack['price_per_unit']:,}* تومان\n\n"
            f"چند تا سطح می‌خوای؟ 🤔\n"
            f"یه عدد بفرست (مثلاً `3`)\n\n"
            f"⚠️ حداقل {pack['min_qty']} | حداکثر {pack['max_qty']}"
        )

    if key == "gems":
        return (
            f"{pack['emoji']} *{pack['name']}*\n"
            f"━━━━━━━━━━━━━━━━━━━\n\n"
            f"💰 هر ۵۰ الماس = *۵۰* تومان\n\n"
            f"چند تا الماس می‌خوای؟ 🤔\n"
            f"تعداد الماس رو بفرست (مثلاً `100`)\n\n"
            f"⚠️ حداقل {pack['min_qty']} | حداکثر {pack['max_qty']:,}"
        )

    return (
        f"{pack['emoji']} *{pack['name']}*\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 قیمت هر {pack['unit_name']}: *{pack['price_per_unit']:,}* تومان\n"
        f"🎁 جایزه هر {pack['unit_name']}: *{pack['reward_per_unit']:,}* {pack['reward_name']}\n\n"
        f"چند {pack['unit_name']} می‌خوای؟ 🤔\n"
        f"یه عدد بفرست (مثلاً `3`)\n\n"
        f"⚠️ حداقل {pack['min_qty']} | حداکثر {pack['max_qty']}"
    )


def build_item_ask_keyboard():
    return {"inline_keyboard": [
        [{"text": "🔙 بازگشت به لیست پک‌ها", "callback_data": "item_shop"}],
        [{"text": "❌ لغو", "callback_data": "item_buy_cancel"}],
    ]}