import time
import random
from datetime import datetime
from config import *
from core import (db, save_db, save_db_now, send_message, edit_message,
                  show_alert, is_admin, check_membership, send_join_message,
                  check_daily_transfer_limit, add_daily_transfer, send_invoice,
                  is_subscription_active)
from data import *
from builders import (
    # منابع
    update_mine_coins, update_refinery_oil, update_factory_iron,
    update_factory_steel, update_factory_weapon, build_resources_text,
    build_resources_keyboard, build_mine_text, build_mine_keyboard,
    build_refinery_keyboard, build_refinery_text,
    build_factory_text, build_factory_keyboard, build_iron_text,
    build_iron_keyboard, build_steel_text, build_steel_keyboard,
    build_weapon_text, build_weapon_keyboard, build_factory_sell_text,
    build_factory_sell_keyboard,
    # فرودگاه
    build_airport_text, build_airport_keyboard,
    # پروفایل و فروشگاه
    build_profile, build_shop_text, build_shop_keyboard, build_missile_keyboard,
    # آزمایشگاه
    build_lab_text, build_lab_keyboard, build_scientists_text,
    build_scientists_keyboard, build_boost_text, build_boost_keyboard,
    build_missile_list_text, build_upgrade_confirm_text,
    start_upgrade, get_free_scientist, get_actual_upgrade_time,
    # طلسم و پک
    build_talisman_text, build_talisman_inline_keyboard, build_packs_keyboard,
    build_pack_text, TALISMAN_INFO,
    # پدافند
    build_defense_text, build_defense_keyboard, build_defense_buy_keyboard,
    # کلن
    get_clan_name, get_clan_members, get_clan_rank_points,
    build_clan_inline_keyboard, build_clans_ranking, build_admin_clans_ranking,
    build_players_ranking, build_daily_ranking, build_clan_search,
    build_clan_members_page, update_rank_today,
    # جنگنده
    build_fighter_base_text, build_fighter_base_keyboard,
    build_fighter_buy_text, build_fighter_buy_keyboard,
    build_repair_fighters_text, build_repair_fighters_keyboard,
    build_wheel_fighter_menu, build_wheel_fighter_result,
    # گردونه‌ها
    build_wheel_keyboard, build_wheel_storm_menu, build_wheel_storm_result,
    build_wheel_hunt_menu, build_wheel_hunt_result, build_wheel_fire_menu,
    build_wheel_fire_result, build_wheel_dragon_menu, build_wheel_dragon_result,
    build_wheel_daily_menu, build_wheel_daily_result, build_wheel_legendary_menu,
    build_wheel_legendary_result, build_wheel_luck_menu, build_wheel_luck_result,
    # حمله
    build_battle_text, build_battle_keyboard, build_battle_cancel_keyboard,
    build_combo_attack_report,
    # تسلیحات خانه + زرادخانه
    build_weapons_house_text, build_weapons_house_keyboard,
    build_combo_arsenal_text, build_combo_arsenal_keyboard,
    build_drone_text, build_drone_keyboard,
    # World Shop
    build_world_pass_text, build_world_pass_keyboard, get_today_str,
    # ⭐️ اشتراک ویژه
    build_subscription_text, build_subscription_keyboard,
    # 💳 خرید آیتم
    build_item_shop_text, build_item_shop_keyboard,
    build_item_ask_text, build_item_ask_keyboard,
)
from handlers import get_other_inline_keyboard


# ==================== پدافند بلاک کمکی ====================
def apply_defense_block_to_attack(attacker_id, target_id, target,
                                   weapon_name, weapon_category, weapon_level,
                                   raw_damage, want_c, want_o, want_r):
    """بلاک پدافند و کاهش دمیج/غارت قبل از ضربه."""
    result = {
        "blocked": False,
        "block_chance": 0,
        "defense_name": None,
        "guardian_reduce": 0,
        "damage": raw_damage,
        "coins": want_c,
        "oil": want_o,
        "rank": want_r,
    }

    blocked, chance, d_name = try_defense_block(target, weapon_category, weapon_level)
    if blocked:
        result["blocked"] = True
        result["block_chance"] = chance
        result["defense_name"] = d_name
        return result

    if d_name:
        result["defense_name"] = d_name
        result["block_chance"] = chance

    guardian = get_guardian_reduction(target)
    if guardian > 0:
        result["guardian_reduce"] = guardian

    total_def = get_total_defense(target, "normal")
    if total_def > 0:
        factor = (100 - total_def) / 100
        result["damage"] = max(1, int(raw_damage * factor))
        result["coins"] = int(want_c * factor)
        result["oil"] = int(want_o * factor)
        result["rank"] = max(1, int(want_r * factor)) if want_r > 0 else 0

    return result


# ==================== کمکی: صفحه دسته‌ی موشک ====================
def build_category_shop(user_id, category):
    p = db.get(user_id, {})
    coins = p.get("coins", 0)
    gems = p.get("gems", 0)
    ulvl, _, _ = get_level_info(p.get("total_damage", 0))
    cat_name = {
        "cruise": "کروز", "ballistic": "بالستیک",
        "hypersonic": "هایپرسونیک", "chemical": "شیمیایی",
        "nuclear": "هسته‌ای",
    }.get(category, category)

    text = (f"🛒 موشک‌های {cat_name}\n\n"
            f"🪙 سکه: {coins:,}\n💎 الماس: {gems}\n"
            f"📊 لول شما: {ulvl}\n\n🔻 انتخاب کن:")

    buttons = []
    for name, mdata in MISSILES.items():
        if mdata.get("category") != category:
            continue
        if not mdata.get("shop", False):
            continue
        req = mdata.get("level", 1)
        price = mdata.get("price", 0)
        gem_cost = mdata.get("gems", 0)
        emoji = mdata.get("emoji", "🚀")
        lock = "🔒 " if ulvl < req else ""
        if gem_cost > 0:
            price_str = f"{price}🪙 + {gem_cost}💎"
        else:
            price_str = f"{price}🪙"
        buttons.append([{
            "text": f"{lock}{emoji} {name} | {price_str} | لول {req}",
            "callback_data": f"buy_m_{name}",
        }])

    if not buttons:
        buttons.append([{"text": "❌ موشکی برای لول تو نیست",
                         "callback_data": "shop_missile"}])
    buttons.append([{"text": "🔙 بازگشت", "callback_data": "shop_missile"}])
    return text, {"inline_keyboard": buttons}


def build_combo_menu(user_id):
    from handlers import get_combo_menu
    return get_combo_menu(user_id)


# ==================== آمار ادمین ====================
def build_admin_stats_text():
    total = 0
    active_24h = 0
    banned = 0
    total_coins = 0
    total_rank = 0
    now_ts = time.time()

    for uid, p in db.items():
        if not isinstance(p, dict) or "user_id" not in p:
            continue
        total += 1
        if p.get("banned"):
            banned += 1
        total_coins += p.get("coins", 0)
        total_rank += p.get("rank", 0)
        la = p.get("last_active", "")
        try:
            dt = datetime.strptime(la, "%Y-%m-%d %H:%M:%S")
            if now_ts - dt.timestamp() < 86400:
                active_24h += 1
        except Exception:
            pass

    clans_count = len(db.get("clans", {})) if isinstance(db.get("clans"), dict) else 0
    active_wars = sum(1 for w in db.get("clan_wars", {}).values()
                     if isinstance(w, dict) and w.get("status") == "active")

    return (f"📊 *آمار ربات*\n\n"
            f"👥 کاربران کل: {total:,}\n"
            f"🟢 فعال ۲۴ ساعت: {active_24h:,}\n"
            f"🚫 بن‌شده: {banned:,}\n"
            f"🏰 تعداد کلن: {clans_count:,}\n"
            f"⚔️ جنگ فعال: {active_wars:,}\n\n"
            f"🪙 کل سکه‌ها: {total_coins:,}\n"
            f"🏆 کل رنک: {total_rank:,}")


# ==================== هدایت اصلی ====================
def handle_callback(update):
    cb = update["callback_query"]
    cb_id = cb["id"]
    chat_id = cb["message"]["chat"]["id"]
    msg_id = cb["message"]["message_id"]
    user_id = str(cb["from"]["id"])
    user_name = cb["from"].get("first_name", "کاربر")
    data = cb.get("data", "")

    print(f"🎯 CALLBACK → user={user_id} data={data!r}")

    if user_id not in db or not isinstance(db.get(user_id), dict):
        from core import create_user
        create_user(user_id, user_name)

    if db[user_id].get("banned"):
        show_alert(cb_id, "🚫 شما مسدود هستید!", True)
        return

    # Older shop menus were sent as photo captions. Migrate them on the
    # first click so the rest of navigation uses an editable text message.
    if cb["message"].get("photo") and (data.startswith("shop_") or data == "help_shop"):
        result = send_message(chat_id, build_shop_text(user_id), build_shop_keyboard())
        if result.get("ok") and isinstance(result.get("result"), dict):
            new_id = result["result"].get("message_id")
            if new_id is not None:
                msg_id = new_id

    db[user_id]["last_active"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Acknowledge navigation callbacks so the client stops its loading indicator.
    if data in {"shop_missile", "shop_defense", "shop_talisman", "shop_drone",
                "shop_back", "help_shop", "go_start"} or data in {
                    "shop_cruise", "shop_ballistic", "shop_hypersonic",
                    "shop_chemical", "shop_nuclear"}:
        show_alert(cb_id, "", False)

    # ==================== Join Check ====================
    if data == "check_join":
        is_member, _ = check_membership(user_id)
        if not is_member:
            show_alert(cb_id, "❌ هنوز عضو کانال‌ها نشدی!", True)
        else:
            show_alert(cb_id, "✅ ممنون! به بازی خوش آمدی", False)
            edit_message(chat_id, msg_id,
                f"⚜️WORLD WAR⚜️\nخوش اومدی {user_name}\n"
                f"🔥 اینجا میدان جنگه 🔥\n"
                f"از دکمه‌های پایین استفاده کن👇",
                {"inline_keyboard": [[
                    {"text": "🎮 ورود به بازی", "callback_data": "go_main"}
                ]]})
        return

    # ==================== Navigation ====================
    if data in ("go_main", "go_start"):
        from handlers import reply_keyboard
        send_message(chat_id, "🔻 منوی اصلی:", reply_keyboard)
        return

    if data == "go_resources":
        update_mine_coins(user_id)
        update_refinery_oil(user_id)
        update_factory_iron(user_id)
        update_factory_steel(user_id)
        update_factory_weapon(user_id)
        edit_message(chat_id, msg_id, build_resources_text(user_id),
                     build_resources_keyboard())
        return

    if data == "go_mine":
        update_mine_coins(user_id)
        edit_message(chat_id, msg_id, build_mine_text(user_id),
                     build_mine_keyboard())
        return

    if data == "go_factory":
        update_factory_iron(user_id)
        update_factory_steel(user_id)
        update_factory_weapon(user_id)
        edit_message(chat_id, msg_id, build_factory_text(user_id),
                     build_factory_keyboard())
        return

    if data == "go_wheel":
        edit_message(chat_id, msg_id, "🎰 گردونه شانس\n\n🔻 یکی:",
                     build_wheel_keyboard())
        return

    if data == "go_defense":
        edit_message(chat_id, msg_id, build_defense_text(user_id),
                     build_defense_keyboard(user_id))
        return

    if data == "shop_back":
        edit_message(chat_id, msg_id, build_shop_text(user_id),
                     build_shop_keyboard())
        return

    if data == "combo_back":
        edit_message(chat_id, msg_id, "🎯 ترکیب نظامی\n\n🔻 یکی:",
                     build_combo_menu(user_id))
        return

    if data == "clan_back":
        edit_message(chat_id, msg_id, "👥 کلن:",
                     build_clan_inline_keyboard(user_id))
        return

    if data == "lab_back":
        edit_message(chat_id, msg_id, build_lab_text(user_id),
                     build_lab_keyboard(user_id))
        return

    if data == "other_admin_back":
        edit_message(chat_id, msg_id, "🔐 پنل ادمین:",
            {"inline_keyboard": [
                [{"text": "📊 آمار ربات", "callback_data": "admin_stats"}],
                [{"text": "🏵 رنکینگ کلن‌ها", "callback_data": "admin_clan_ranking"}],
                [{"text": "🪙 دادن سکه", "callback_data": "admin_give"},
                 {"text": "🪙 کم کردن سکه", "callback_data": "admin_take_coins"}],
                [{"text": "🎁 دادن پک", "callback_data": "admin_pack"}],
                [{"text": "🚫 مدیریت مسدودیت", "callback_data": "admin_ban"}],
                [{"text": "🔄 ریست رنک همه", "callback_data": "admin_reset"}],
                [{"text": "🔄 ریست لول همه", "callback_data": "admin_reset_levels"}],
                [{"text": "📢 پیام همگانی", "callback_data": "admin_broadcast"}],
            ]})
        return

    if data == "invite_cancel":
        edit_message(chat_id, msg_id, "❌ لغو شد.",
                     {"inline_keyboard": [[{"text": "🔙 منوی اصلی",
                                            "callback_data": "go_main"}]]})
        return

    if data == "show_rules":
        edit_message(chat_id, msg_id,
            "⚖️ *قوانین ربات*\n\n"
            "1️⃣ از ربات سوءاستفاده نکنید\n"
            "2️⃣ حملات توهین‌آمیز ممنوع\n"
            "3️⃣ چند اکانتی ممنوع\n"
            "4️⃣ خرید و فروش اکانت مسئولیت خود کاربر است\n"
            "5️⃣ تخلف = بن دائمی\n\n"
            "📞 پشتیبانی: @" + SUPPORT_ID,
            {"inline_keyboard": [[{"text": "🔙 بازگشت", "callback_data": "go_main"}]]})
        return

    # ==================== منابع: معدن ====================
    if data == "res_mine":
        update_mine_coins(user_id)
        edit_message(chat_id, msg_id, build_mine_text(user_id),
                     build_mine_keyboard())
        return

    if data == "res_refinery":
        p = db.get(user_id, {})
        if p.get("refinery_level", 0) == 0:
            edit_message(chat_id, msg_id,
                "🏭 پالایشگاه\n\n❌ ندارید!\n🪙 10,000 سکه\n🎯 لول 10\n\n🔻 خرید:",
                {"inline_keyboard": [
                    [{"text": "🛒 خرید", "callback_data": "refinery_buy"}],
                    [{"text": "🔙 بازگشت", "callback_data": "go_resources"}],
                ]})
        else:
            update_refinery_oil(user_id)
            edit_message(chat_id, msg_id, build_refinery_text(user_id),
                         build_refinery_keyboard())
        return

    if data == "mine_collect":
        update_mine_coins(user_id)
        p = db.get(user_id, {})
        mc = p.get("mine_coins", 0)
        if mc <= 0:
            show_alert(cb_id, "❌ سکه‌ای برای برداشت نیست!", True)
            return
        db[user_id]["coins"] = p.get("coins", 0) + mc
        db[user_id]["mine_coins"] = 0
        save_db()
        show_alert(cb_id, f"✅ {mc:,} سکه برداشت شد!", True)
        edit_message(chat_id, msg_id, build_mine_text(user_id),
                     build_mine_keyboard())
        return

    if data == "mine_upgrade":
        p = db.get(user_id, {})
        lvl = p.get("mine_level", 1)
        if lvl >= 40:
            show_alert(cb_id, "🚫 حداکثر سطح!", True)
            return
        cost = (lvl + 1) * 1000
        if p.get("coins", 0) < cost:
            show_alert(cb_id, f"❌ به {cost:,} سکه نیاز داری!", True)
            return
        db[user_id]["coins"] -= cost
        db[user_id]["mine_level"] = lvl + 1
        save_db()
        show_alert(cb_id, f"✅ معدن به سطح {lvl+1} ارتقا یافت!", True)
        edit_message(chat_id, msg_id, build_mine_text(user_id),
                     build_mine_keyboard())
        return

    if data == "refinery_buy":
        p = db.get(user_id, {})
        ulvl, _, _ = get_level_info(p.get("total_damage", 0))
        if ulvl < 10:
            show_alert(cb_id, f"❌ نیاز به لول 10 (تو {ulvl})", True)
            return
        if p.get("coins", 0) < 10000:
            show_alert(cb_id, "❌ به 10,000 سکه نیاز داری!", True)
            return
        db[user_id]["coins"] -= 10000
        db[user_id]["refinery_level"] = 1
        db[user_id]["oil_last_dig"] = time.time()
        save_db()
        show_alert(cb_id, "✅ پالایشگاه خریداری شد!", True)
        edit_message(chat_id, msg_id, build_refinery_text(user_id),
                     build_refinery_keyboard())
        return

    if data == "ref_collect":
        update_refinery_oil(user_id)
        p = db.get(user_id, {})
        oil = p.get("refinery_oil", 0)
        if oil <= 0:
            show_alert(cb_id, "❌ نفتی برای برداشت نیست!", True)
            return
        db[user_id]["oil"] = p.get("oil", 0) + oil
        db[user_id]["refinery_oil"] = 0
        save_db()
        show_alert(cb_id, f"✅ {oil:,} نفت برداشت شد!", True)
        edit_message(chat_id, msg_id, build_refinery_text(user_id),
                     build_refinery_keyboard())
        return

    if data == "ref_upgrade":
        p = db.get(user_id, {})
        lvl = p.get("refinery_level", 0)
        if lvl <= 0:
            show_alert(cb_id, "❌ اول پالایشگاه بخر!", True)
            return
        if lvl >= 10:
            show_alert(cb_id, "🚫 حداکثر سطح!", True)
            return
        cost = (lvl + 1) * 2000
        if p.get("coins", 0) < cost:
            show_alert(cb_id, f"❌ به {cost:,} سکه نیاز داری!", True)
            return
        db[user_id]["coins"] -= cost
        db[user_id]["refinery_level"] = lvl + 1
        save_db()
        show_alert(cb_id, f"✅ پالایشگاه به سطح {lvl+1} ارتقا یافت!", True)
        edit_message(chat_id, msg_id, build_refinery_text(user_id),
                     build_refinery_keyboard())
        return

    # ==================== کارخانه ====================
    if data == "factory_iron":
        update_factory_iron(user_id)
        edit_message(chat_id, msg_id, build_iron_text(user_id),
                     build_iron_keyboard(user_id))
        return

    if data == "factory_steel":
        update_factory_steel(user_id)
        edit_message(chat_id, msg_id, build_steel_text(user_id),
                     build_steel_keyboard(user_id))
        return

    if data == "factory_weapon":
        update_factory_weapon(user_id)
        edit_message(chat_id, msg_id, build_weapon_text(user_id),
                     build_weapon_keyboard(user_id))
        return

    if data == "factory_sell":
        edit_message(chat_id, msg_id, build_factory_sell_text(user_id),
                     build_factory_sell_keyboard())
        return

    if data == "iron_collect":
        update_factory_iron(user_id)
        p = db.get(user_id, {})
        ir = p.get("iron", 0)
        if ir <= 0:
            show_alert(cb_id, "❌ آهنی برای برداشت نیست!", True)
            return
        db[user_id]["iron"] = 0
        save_db()
        show_alert(cb_id, f"✅ {ir:,} آهن برداشت شد!", True)
        edit_message(chat_id, msg_id, build_iron_text(user_id),
                     build_iron_keyboard(user_id))
        return

    if data == "iron_upgrade":
        p = db.get(user_id, {})
        lvl = p.get("iron_mine_level", 1)
        if lvl >= 10:
            show_alert(cb_id, "🚫 حداکثر سطح!", True)
            return
        cost = (lvl + 1) * 5000
        if p.get("coins", 0) < cost:
            show_alert(cb_id, f"❌ به {cost:,} سکه نیاز داری!", True)
            return
        db[user_id]["coins"] -= cost
        db[user_id]["iron_mine_level"] = lvl + 1
        save_db()
        show_alert(cb_id, f"✅ معدن آهن به سطح {lvl+1} ارتقا یافت!", True)
        edit_message(chat_id, msg_id, build_iron_text(user_id),
                     build_iron_keyboard(user_id))
        return

    if data == "steel_build":
        p = db.get(user_id, {})
        ulvl, _, _ = get_level_info(p.get("total_damage", 0))
        if ulvl < 25:
            show_alert(cb_id, f"❌ نیاز به لول 25 (تو {ulvl})", True)
            return
        if p.get("coins", 0) < 50000:
            show_alert(cb_id, "❌ به 50,000 سکه نیاز داری!", True)
            return
        if p.get("iron", 0) < 500:
            show_alert(cb_id, "❌ به 500 آهن نیاز داری!", True)
            return
        db[user_id]["coins"] -= 50000
        db[user_id]["iron"] -= 500
        db[user_id]["steel_factory_level"] = 1
        db[user_id]["steel_last_dig"] = time.time()
        save_db()
        show_alert(cb_id, "✅ کارخانه فولاد ساخته شد!", True)
        edit_message(chat_id, msg_id, build_steel_text(user_id),
                     build_steel_keyboard(user_id))
        return

    if data == "steel_collect":
        update_factory_steel(user_id)
        p = db.get(user_id, {})
        st = p.get("steel", 0)
        if st <= 0:
            show_alert(cb_id, "❌ فولادی نیست!", True)
            return
        db[user_id]["steel"] = 0
        save_db()
        show_alert(cb_id, f"✅ {st:,} فولاد برداشت شد!", True)
        edit_message(chat_id, msg_id, build_steel_text(user_id),
                     build_steel_keyboard(user_id))
        return

    if data == "steel_upgrade":
        p = db.get(user_id, {})
        lvl = p.get("steel_factory_level", 0)
        if lvl <= 0:
            show_alert(cb_id, "❌ اول کارخانه بساز!", True)
            return
        if lvl >= 10:
            show_alert(cb_id, "🚫 حداکثر سطح!", True)
            return
        cost = (lvl + 1) * 10000
        if p.get("coins", 0) < cost:
            show_alert(cb_id, f"❌ به {cost:,} سکه نیاز داری!", True)
            return
        db[user_id]["coins"] -= cost
        db[user_id]["steel_factory_level"] = lvl + 1
        save_db()
        show_alert(cb_id, f"✅ کارخانه فولاد به سطح {lvl+1} ارتقا یافت!", True)
        edit_message(chat_id, msg_id, build_steel_text(user_id),
                     build_steel_keyboard(user_id))
        return

    if data == "weapon_build":
        p = db.get(user_id, {})
        ulvl, _, _ = get_level_info(p.get("total_damage", 0))
        if ulvl < 40:
            show_alert(cb_id, f"❌ نیاز به لول 40 (تو {ulvl})", True)
            return
        if p.get("coins", 0) < 100000:
            show_alert(cb_id, "❌ به 100,000 سکه نیاز داری!", True)
            return
        if p.get("steel", 0) < 500:
            show_alert(cb_id, "❌ به 500 فولاد نیاز داری!", True)
            return
        db[user_id]["coins"] -= 100000
        db[user_id]["steel"] -= 500
        db[user_id]["weapon_factory_level"] = 1
        db[user_id]["weapon_last_dig"] = time.time()
        save_db()
        show_alert(cb_id, "✅ کارخانه سلاح ساخته شد!", True)
        edit_message(chat_id, msg_id, build_weapon_text(user_id),
                     build_weapon_keyboard(user_id))
        return

    if data == "weapon_collect":
        update_factory_weapon(user_id)
        p = db.get(user_id, {})
        wp = p.get("weapon", 0)
        if wp <= 0:
            show_alert(cb_id, "❌ سلاحی نیست!", True)
            return
        db[user_id]["weapon"] = 0
        save_db()
        show_alert(cb_id, f"✅ {wp:,} سلاح برداشت شد!", True)
        edit_message(chat_id, msg_id, build_weapon_text(user_id),
                     build_weapon_keyboard(user_id))
        return

    if data == "weapon_upgrade":
        p = db.get(user_id, {})
        lvl = p.get("weapon_factory_level", 0)
        if lvl <= 0:
            show_alert(cb_id, "❌ اول کارخانه بساز!", True)
            return
        if lvl >= 10:
            show_alert(cb_id, "🚫 حداکثر سطح!", True)
            return
        cost = (lvl + 1) * 20000
        if p.get("coins", 0) < cost:
            show_alert(cb_id, f"❌ به {cost:,} سکه نیاز داری!", True)
            return
        db[user_id]["coins"] -= cost
        db[user_id]["weapon_factory_level"] = lvl + 1
        save_db()
        show_alert(cb_id, f"✅ کارخانه سلاح به سطح {lvl+1} ارتقا یافت!", True)
        edit_message(chat_id, msg_id, build_weapon_text(user_id),
                     build_weapon_keyboard(user_id))
        return

    if data in ("sell_iron", "sell_steel", "sell_weapon"):
        p = db.get(user_id, {})
        rate_map = {"sell_iron": ("iron", 10, "آهن"),
                    "sell_steel": ("steel", 50, "فولاد"),
                    "sell_weapon": ("weapon", 500, "سلاح")}
        key, rate, label = rate_map[data]
        qty = p.get(key, 0)
        if qty <= 0:
            show_alert(cb_id, f"❌ {label}ی برای فروش نداری!", True)
            return
        total = qty * rate
        db[user_id][key] = 0
        db[user_id]["coins"] = p.get("coins", 0) + total
        save_db()
        show_alert(cb_id, f"✅ {qty:,} {label} فروخته شد!\n+{total:,} سکه", True)
        edit_message(chat_id, msg_id, build_factory_sell_text(user_id),
                     build_factory_sell_keyboard())
        return

    # ==================== فرودگاه ====================
    if data == "airport_buy":
        p = db.get(user_id, {})
        ulvl, _, _ = get_level_info(p.get("total_damage", 0))
        if ulvl < 10:
            show_alert(cb_id, f"❌ نیاز به لول 10 (تو {ulvl})", True)
            return
        if p.get("coins", 0) < 5000:
            show_alert(cb_id, "❌ به 5,000 سکه نیاز داری!", True)
            return
        db[user_id]["coins"] -= 5000
        db[user_id]["airport_level"] = 1
        save_db()
        show_alert(cb_id, "✅ فرودگاه ساخته شد!", True)
        edit_message(chat_id, msg_id, build_airport_text(user_id),
                     build_airport_keyboard(user_id))
        return

    if data == "airport_upgrade":
        p = db.get(user_id, {})
        lvl = p.get("airport_level", 0)
        if lvl <= 0:
            show_alert(cb_id, "❌ اول فرودگاه بخر!", True)
            return
        if lvl >= 7:
            show_alert(cb_id, "🚫 حداکثر سطح!", True)
            return
        cost = AIRPORT_LEVELS[lvl + 1]["upgrade_cost"]
        if p.get("oil", 0) < cost:
            show_alert(cb_id, f"❌ به {cost:,} نفت نیاز داری!", True)
            return
        db[user_id]["oil"] -= cost
        db[user_id]["airport_level"] = lvl + 1
        save_db()
        show_alert(cb_id, f"✅ فرودگاه به سطح {lvl+1} ارتقا یافت!", True)
        edit_message(chat_id, msg_id, build_airport_text(user_id),
                     build_airport_keyboard(user_id))
        return

    if data == "airport_buy_drone":
        edit_message(chat_id, msg_id, build_drone_text(user_id),
                     build_drone_keyboard(user_id))
        return

    if data.startswith("buy_drone_"):
        dname = data.replace("buy_drone_", "")
        if dname not in DRONES:
            show_alert(cb_id, "❌ پهباد نامعتبر!", True)
            return
        p = db.get(user_id, {})
        if p.get("airport_level", 0) == 0:
            show_alert(cb_id, "❌ اول فرودگاه بخر!", True)
            return
        db[user_id]["selected_drone"] = dname
        save_db()
        info = DRONES[dname]
        send_message(chat_id,
            f"🛩 خرید {dname}\n\n"
            f"💰 قیمت هر عدد: {info['price']:,} سکه\n"
            f"🪙 موجودی: {p.get('coins', 0):,}\n\n"
            f"🔢 چند عدد می‌خری؟ (عدد بفرست)",
            {"inline_keyboard": [[{"text": "❌ لغو",
                                   "callback_data": "buy_cancel"}]]})
        return

    if data == "buy_cancel":
        db[user_id]["selected_drone"] = None
        db[user_id]["selected_missile"] = None
        db[user_id]["selected_defense"] = None
        db[user_id]["selected_talisman"] = None
        save_db()
        show_alert(cb_id, "❌ لغو شد", False)
        return

    # ==================== فروشگاه ====================
    if data == "shop_missile":
        edit_message(chat_id, msg_id, "🚀 فروشگاه موشک\n\n🔻 دسته:",
                     build_missile_keyboard())
        return

    if data in ("shop_cruise", "shop_ballistic", "shop_hypersonic",
                "shop_chemical", "shop_nuclear"):
        cat = data.replace("shop_", "")
        txt, kb = build_category_shop(user_id, cat)
        edit_message(chat_id, msg_id, txt, kb)
        return

    if data.startswith("buy_m_"):
        mn = data.replace("buy_m_", "")
        if mn not in MISSILES:
            show_alert(cb_id, "❌ موشک نامعتبر!", True)
            return
        mdata = MISSILES[mn]
        p = db.get(user_id, {})
        ulvl, _, _ = get_level_info(p.get("total_damage", 0))
        if ulvl < mdata.get("level", 1):
            show_alert(cb_id, f"❌ نیاز به لول {mdata['level']}", True)
            return
        db[user_id]["selected_missile"] = mn
        save_db()
        price = mdata["price"]
        gem_cost = mdata.get("gems", 0)
        price_str = f"{price:,}🪙"
        if gem_cost > 0:
            price_str += f" + {gem_cost}💎"

        if is_subscription_active(user_id):
            price_str += f" (⭐️ {SUB_DISCOUNT_MISSILE}٪ تخفیف)"

        send_message(chat_id,
            f"🚀 خرید {mn}\n\n"
            f"💰 قیمت هر عدد: {price_str}\n"
            f"🪙 موجودی: {p.get('coins', 0):,}\n"
            f"💎 الماس: {p.get('gems', 0):,}\n\n"
            f"🔢 چند عدد می‌خری؟ (عدد بفرست)",
            {"inline_keyboard": [[{"text": "❌ لغو",
                                   "callback_data": "buy_cancel"}]]})
        return

    if data == "shop_defense":
        edit_message(chat_id, msg_id, build_defense_text(user_id),
                     build_defense_keyboard(user_id))
        return

    if data == "def_buy":
        edit_message(chat_id, msg_id,
            "🛒 خرید پدافند\n\n🔻 انتخاب کن:",
            build_defense_buy_keyboard(user_id))
        return

    if data.startswith("def_buy_"):
        dname = data.replace("def_buy_", "")
        if dname not in DEFENSES:
            show_alert(cb_id, "❌ پدافند نامعتبر!", True)
            return
        p = db.get(user_id, {})
        ulvl, _, _ = get_level_info(p.get("total_damage", 0))
        if ulvl < DEFENSES[dname].get("required_level", 1):
            show_alert(cb_id, f"❌ نیاز به لول {DEFENSES[dname]['required_level']}", True)
            return
        db[user_id]["selected_defense"] = dname
        save_db()
        send_message(chat_id,
            f"🛡 خرید {dname}\n\n"
            f"💰 قیمت هر عدد: {DEFENSES[dname]['price']:,} سکه\n"
            f"🪙 موجودی: {p.get('coins', 0):,}\n\n"
            f"🔢 چند عدد می‌خری؟",
            {"inline_keyboard": [[{"text": "❌ لغو",
                                   "callback_data": "buy_cancel"}]]})
        return

    if data.startswith("def_select_"):
        dname = data.replace("def_select_", "")
        p = db.get(user_id, {})
        if dname not in p.get("defense", {}):
            show_alert(cb_id, "❌ این پدافند رو نداری!", True)
            return
        if p["defense"][dname].get("count", 0) <= 0:
            show_alert(cb_id, "❌ موجودی صفره!", True)
            return
        db[user_id]["active_defense"] = dname
        save_db()
        show_alert(cb_id, f"✅ {dname} فعال شد!", True)
        edit_message(chat_id, msg_id, build_defense_text(user_id),
                     build_defense_keyboard(user_id))
        return

    if data == "def_locked":
        show_alert(cb_id, "❌ پدافندی برای لول تو موجود نیست!", True)
        return

    if data == "shop_talisman":
        edit_message(chat_id, msg_id, build_talisman_text(user_id),
                     build_talisman_inline_keyboard(user_id))
        return

    if data.startswith("tal_buy_"):
        key = data.replace("tal_buy_", "")
        if key not in TALISMAN_INFO:
            show_alert(cb_id, "❌ طلسم نامعتبر!", True)
            return
        info = TALISMAN_INFO[key]
        p = db.get(user_id, {})
        ulvl, _, _ = get_level_info(p.get("total_damage", 0))
        if ulvl < info.get("req_level", 1):
            show_alert(cb_id, f"❌ نیاز به لول {info['req_level']}", True)
            return
        if p.get(info["count_key"], 0) >= 20:
            show_alert(cb_id, "❌ حداکثر 20 عدد!", True)
            return
        db[user_id]["selected_talisman"] = key
        save_db()
        curr = "سکه" if info["currency"] == "coins" else "نفت"
        send_message(chat_id,
            f"{info['emoji']} خرید طلسم {info['name']}\n\n"
            f"💰 قیمت هر عدد: {info['price']:,} {curr}\n"
            f"📦 موجودی: {p.get(info['count_key'], 0)}/20\n\n"
            f"🔢 چند عدد؟",
            {"inline_keyboard": [[{"text": "❌ لغو",
                                   "callback_data": "buy_cancel"}]]})
        return

    if data == "tal_locked":
        show_alert(cb_id, "❌ طلسمی برای لول تو نیست!", True)
        return

    if data == "shop_drone":
        edit_message(chat_id, msg_id, build_drone_text(user_id),
                     build_drone_keyboard(user_id))
        return

    if data == "shop_items":
        edit_message(chat_id, msg_id, "📦 پک‌ها:",
                     build_packs_keyboard(0))
        return

    if data.startswith("packs_p_"):
        try:
            pg = int(data.replace("packs_p_", ""))
        except ValueError:
            pg = 0
        edit_message(chat_id, msg_id, "📦 پک‌ها:",
                     build_packs_keyboard(pg))
        return

    if data.startswith("pack_"):
        pkey = data.replace("pack_", "")
        txt, kb = build_pack_text(pkey)
        if not txt:
            show_alert(cb_id, "❌ پک نامعتبر!", True)
            return
        edit_message(chat_id, msg_id, txt, kb)
        return

    if data.startswith("order_"):
        pkey = data.replace("order_", "")
        if pkey not in PACKS:
            show_alert(cb_id, "❌ پک نامعتبر!", True)
            return
        pack = PACKS[pkey]
        send_message(chat_id,
            f"🛒 سفارش {pack['emoji']} {pack['name']}\n\n"
            f"💰 قیمت: {pack['price']}\n\n"
            f"📞 برای پرداخت به مدیریت پیام بدید:\n"
            f"@{SUPPORT_ID}",
            {"inline_keyboard": [[
                {"text": "💬 پیوی مدیریت",
                 "url": f"https://ble.ir/{SUPPORT_ID}"}
            ], [
                {"text": "🔙 بازگشت", "callback_data": "shop_items"}
            ]]})
        return

    # ==================== 🛒 World Shop ====================
    if data in ("world_pass_open", "world_shop_open"):
        edit_message(chat_id, msg_id, build_world_pass_text(user_id),
                     build_world_pass_keyboard(user_id))
        return

    if data == "world_pass_buy":
        p = db.get(user_id, {})
        if p.get("world_pass_active") and p.get("world_pass_days_claimed", 0) < WORLD_PASS_TOTAL_DAYS:
            show_alert(cb_id, "⚠️ شما World Shop فعال دارید!", True)
            return
        payload = f"world_pass_{user_id}_{int(time.time())}"
        db[user_id]["world_pass_pending_invoice"] = time.time()
        save_db()
        res = send_invoice(
            chat_id=chat_id,
            title="⭐ World Shop",
            description="اشتراک ویژه WORLD WAR - 10 روز جوایز اختصاصی",
            payload=payload,
            amount=WORLD_PASS_PRICE_RIAL,
            currency="IRR",
        )
        if not res.get("ok"):
            show_alert(cb_id, "❌ خطا در ساخت فاکتور. با پشتیبانی تماس بگیرید.", True)
        return

    if data == "world_pass_claim":
        p = db.get(user_id, {})
        if not p.get("world_pass_active"):
            show_alert(cb_id, "❌ World Shop فعال نداری!", True)
            return
        claimed = p.get("world_pass_days_claimed", 0)
        last = p.get("world_pass_last_claim_date", "")
        today = get_today_str()
        if claimed >= WORLD_PASS_TOTAL_DAYS:
            show_alert(cb_id, "🎉 همه جوایز فصل دریافت شد!", True)
            return
        if last == today:
            show_alert(cb_id, "⏳ امروز قبلاً گرفتی! فردا بیا.", True)
            return
        day = claimed + 1
        reward = get_world_pass_reward(day)
        if not reward:
            show_alert(cb_id, "❌ جایزه پیدا نشد!", True)
            return
        ok, err = validate_world_pass_reward(reward)
        if not ok:
            show_alert(cb_id, err, True)
            return
        result_txt = apply_world_pass_reward(db[user_id], reward)
        db[user_id]["world_pass_days_claimed"] = day
        db[user_id]["world_pass_last_claim_date"] = today
        save_db()
        show_alert(cb_id, f"🎉 روز {day}:\n{result_txt}", True)
        edit_message(chat_id, msg_id, build_world_pass_text(user_id),
                     build_world_pass_keyboard(user_id))
        return

    if data == "world_pass_already":
        show_alert(cb_id, "⏳ امروز قبلاً دریافت کردی!", True)
        return

    # ==================== ⭐️ اشتراک ویژه ====================
    if data == "other_subscription":
        edit_message(chat_id, msg_id, build_subscription_text(user_id),
                     build_subscription_keyboard(user_id))
        return

    if data == "subscription_buy":
        if is_subscription_active(user_id):
            show_alert(cb_id, "⚠️ شما اشتراک فعال دارید!", True)
            return
        payload = f"subscription_{user_id}_{int(time.time())}"
        db[user_id]["subscription_pending_invoice"] = time.time()
        save_db()
        res = send_invoice(
            chat_id=chat_id,
            title="⭐️ اشتراک ویژه WORLD WAR",
            description=f"اشتراک ویژه {SUBSCRIPTION_DURATION_DAYS} روزه",
            payload=payload,
            amount=SUBSCRIPTION_PRICE_RIAL,
            currency="IRR",
        )
        if not res.get("ok"):
            show_alert(cb_id, "❌ خطا در ساخت فاکتور. با پشتیبانی تماس بگیرید.", True)
        return

    if data == "sub_claim_missiles":
        if not is_subscription_active(user_id):
            show_alert(cb_id, "❌ اشتراک فعال نداری!", True)
            return
        today = get_today_str()
        if db[user_id].get("subscription_last_mission_claim") == today:
            show_alert(cb_id, "⏳ امروز قبلاً دریافت کردی! فردا بیا.", True)
            return

        p = db[user_id]
        wh_lvl = p.get("weapons_house_level", 1)
        if wh_lvl > 5:
            wh_lvl = 5

        claimed = []
        for cat, count, default_name in [
            ("cruise", SUB_DAILY_CRUISE, "اطلس"),
            ("ballistic", SUB_DAILY_BALLISTIC, "عماد"),
            ("hypersonic", SUB_DAILY_HYPERSONIC, "بلیزارد"),
        ]:
            max_cap = ARSENAL_CAPACITIES[wh_lvl].get(cat, 0)
            current = sum(m.get("count", 0) for m in p.get(cat, {}).values())
            available = max(0, max_cap - current)
            actual = min(count, available)
            if actual > 0:
                if cat not in p:
                    p[cat] = {}
                if default_name not in p[cat]:
                    p[cat][default_name] = {"count": 0, "level": 1}
                p[cat][default_name]["count"] += actual
                claimed.append(f"• {default_name}: {actual:,}")

        p["subscription_last_mission_claim"] = today
        save_db()

        if claimed:
            show_alert(cb_id,
                "✅ دریافت شد!\n\n" + "\n".join(claimed),
                True)
        else:
            show_alert(cb_id, "❌ ظرفیت تسلیحات خانه پر است!", True)
        edit_message(chat_id, msg_id, build_subscription_text(user_id),
                     build_subscription_keyboard(user_id))
        return

    if data == "sub_already_claimed":
        show_alert(cb_id, "⏳ امروز قبلاً دریافت کردی! فردا بیا.", True)
        return

    if data == "sub_shield":
        if not is_subscription_active(user_id):
            show_alert(cb_id, "❌ اشتراک فعال نداری!", True)
            return

        today = get_today_str()
        p = db[user_id]
        if p.get("sub_shield_date") != today:
            p["sub_shield_used_today"] = 0
            p["sub_shield_date"] = today
            save_db()

        used = p.get("sub_shield_used_today", 0)
        remaining_sec = SUB_SHIELD_MAX_SECONDS - used

        if remaining_sec <= 0:
            show_alert(cb_id, "❌ سقف روزانه سپر تمام شده! فردا بیا.", True)
            return

        if p.get("sub_shield_until", 0) > time.time():
            rem = int(p["sub_shield_until"] - time.time())
            show_alert(cb_id, f"🛡 سپر فعلاً فعاله ({rem//60} دقیقه باقی)!", True)
            return

        rem_min = remaining_sec // 60
        buttons = []
        for mins in [30, 60, 90, 120]:
            if mins <= rem_min:
                buttons.append([{"text": f"{mins} دقیقه",
                                 "callback_data": f"sub_shield_{mins*60}"}])

        buttons.append([{"text": "🔙 بازگشت", "callback_data": "other_subscription"}])

        edit_message(chat_id, msg_id,
            f"🛡 *فعال‌سازی سپر*\n\n"
            f"⏱ استفاده امروز: {used//60} از {SUB_SHIELD_MAX_SECONDS//60} دقیقه\n"
            f"✅ باقی‌مانده: {rem_min} دقیقه\n\n"
            f"🔻 مدت زمان سپر رو انتخاب کن:",
            {"inline_keyboard": buttons})
        return

    if data.startswith("sub_shield_"):
        try:
            seconds = int(data.replace("sub_shield_", ""))
        except ValueError:
            return
        if not is_subscription_active(user_id):
            show_alert(cb_id, "❌ اشتراک فعال نداری!", True)
            return
        today = get_today_str()
        p = db[user_id]
        if p.get("sub_shield_date") != today:
            p["sub_shield_used_today"] = 0
            p["sub_shield_date"] = today
        used = p.get("sub_shield_used_today", 0)
        if used + seconds > SUB_SHIELD_MAX_SECONDS:
            show_alert(cb_id, "❌ سقف روزانه عبور می‌کنه!", True)
            return
        p["sub_shield_used_today"] = used + seconds
        p["sub_shield_until"] = time.time() + seconds
        p["sub_shield_date"] = today
        save_db()
        show_alert(cb_id, f"✅ سپر برای {seconds//60} دقیقه فعال شد!", True)
        edit_message(chat_id, msg_id, build_subscription_text(user_id),
                     build_subscription_keyboard(user_id))
        return

    # ==================== 💳 خرید آیتم ====================
    if data == "item_shop":
        if db[user_id].get("selected_item_pack"):
            db[user_id]["selected_item_pack"] = None
            save_db()
        edit_message(chat_id, msg_id, build_item_shop_text(),
                     build_item_shop_keyboard())
        return

    if data == "item_buy_cancel":
        db[user_id]["selected_item_pack"] = None
        save_db()
        edit_message(chat_id, msg_id, build_item_shop_text(),
                     build_item_shop_keyboard())
        return

    if data.startswith("item_buy_"):
        key = data.replace("item_buy_", "")
        if key not in ITEM_PACKS:
            show_alert(cb_id, "❌ پک نامعتبر!", True)
            return
        db[user_id]["selected_item_pack"] = key
        save_db()
        edit_message(chat_id, msg_id, build_item_ask_text(key),
                     build_item_ask_keyboard())
        return

    if data == "no_gems":
        show_alert(cb_id, "💎 الماس کافی نداری!", True)
        return

    if data == "upg_no_funds":
        show_alert(cb_id, "❌ سکه یا نفت کافی نداری!", True)
        return

    # ==================== آزمایشگاه ====================
    if data == "lab_upgrade":
        edit_message(chat_id, msg_id, build_lab_text(user_id),
                     build_lab_keyboard(user_id))
        return

    if data == "lab_upgrade_missile":
        edit_message(chat_id, msg_id, "🚀 ارتقای موشک\n\n🔻 دسته:",
            {"inline_keyboard": [
                [{"text": "🧨 کروز", "callback_data": "lab_cat_cruise"},
                 {"text": "🚀 بالستیک", "callback_data": "lab_cat_ballistic"}],
                [{"text": "⚡ هایپرسونیک", "callback_data": "lab_cat_hypersonic"}],
                [{"text": "🔙 بازگشت", "callback_data": "lab_back"}],
            ]})
        return

    if data.startswith("lab_cat_"):
        cat = data.replace("lab_cat_", "")
        res = build_missile_list_text(user_id, cat)
        if isinstance(res, tuple):
            edit_message(chat_id, msg_id, res[0], res[1])
        else:
            edit_message(chat_id, msg_id, res,
                {"inline_keyboard": [[{"text": "🔙 بازگشت",
                                       "callback_data": "lab_upgrade_missile"}]]})
        return

    if data.startswith("upg_confirm_"):
        raw = data.replace("upg_confirm_", "")
        for cat in ("cruise", "ballistic", "hypersonic"):
            if raw.startswith(cat + "_"):
                mn = raw[len(cat) + 1:]
                p = db.get(user_id, {})
                info = p.get(cat, {}).get(mn, {})
                lvl = info.get("level", 1)
                free_sci = get_free_scientist(user_id)
                if not free_sci:
                    show_alert(cb_id, "❌ دانشمند آزاد نداری!", True)
                    return
                cost_coin = get_upgrade_cost(mn, lvl)
                cost_oil = get_upgrade_oil_cost(mn, lvl)
                if p.get("coins", 0) < cost_coin:
                    show_alert(cb_id, "❌ سکه کافی نیست!", True)
                    return
                if p.get("oil", 0) < cost_oil:
                    show_alert(cb_id, "❌ نفت کافی نیست!", True)
                    return
                base_time = get_upgrade_time(mn, lvl)
                duration = get_actual_upgrade_time(user_id, base_time)
                db[user_id]["coins"] -= cost_coin
                db[user_id]["oil"] -= cost_oil
                start_upgrade(user_id, mn, cat, cost_coin, duration, free_sci)
                show_alert(cb_id, f"✅ ارتقای {mn} شروع شد! ({duration} دقیقه)", True)
                edit_message(chat_id, msg_id, "⏳ در حال ارتقا...",
                    {"inline_keyboard": [[{"text": "🔙 بازگشت",
                                           "callback_data": "lab_back"}]]})
                return
        show_alert(cb_id, "❌ خطا در پارس دیتا", True)
        return

    if data.startswith("upg_back_"):
        cat = data.replace("upg_back_", "")
        res = build_missile_list_text(user_id, cat)
        if isinstance(res, tuple):
            edit_message(chat_id, msg_id, res[0], res[1])
        else:
            edit_message(chat_id, msg_id, res)
        return

    if data.startswith("upg_"):
        raw = data.replace("upg_", "")
        for cat in ("cruise", "ballistic", "hypersonic"):
            if raw.startswith(cat + "_"):
                mn = raw[len(cat) + 1:]
                txt, kb = build_upgrade_confirm_text(user_id, cat, mn)
                if not txt:
                    show_alert(cb_id, "❌ این موشک قابل ارتقا نیست!", True)
                    return
                edit_message(chat_id, msg_id, txt, kb)
                return
        return

    if data == "lab_scientists":
        edit_message(chat_id, msg_id, build_scientists_text(user_id),
                     build_scientists_keyboard(user_id))
        return

    if data == "buy_scientist":
        p = db.get(user_id, {})
        if p.get("scientists_count", 1) >= 2:
            show_alert(cb_id, "❌ قبلاً داری!", True)
            return
        if p.get("gems", 0) < SCIENTIST_2_COST:
            show_alert(cb_id, f"❌ به {SCIENTIST_2_COST} الماس نیاز داری!", True)
            return
        db[user_id]["gems"] -= SCIENTIST_2_COST
        db[user_id]["scientists_count"] = 2
        save_db()
        show_alert(cb_id, "✅ دانشمند دوم خریداری شد!", True)
        edit_message(chat_id, msg_id, build_scientists_text(user_id),
                     build_scientists_keyboard(user_id))
        return

    if data == "lab_boost":
        edit_message(chat_id, msg_id, build_boost_text(user_id),
                     build_boost_keyboard(user_id))
        return

    if data.startswith("buy_boost_"):
        btype = data.replace("buy_boost_", "")
        if btype not in BOOST_TYPES:
            show_alert(cb_id, "❌ بوست نامعتبر!", True)
            return
        p = db.get(user_id, {})
        b = BOOST_TYPES[btype]
        if p.get("gems", 0) < b["cost"]:
            show_alert(cb_id, f"❌ به {b['cost']} الماس نیاز داری!", True)
            return
        boost = p.get("active_boost")
        if boost and isinstance(boost, dict) and boost.get("expires_at", 0) > time.time():
            show_alert(cb_id, "⚠️ یک بوست فعال داری!", True)
            return
        db[user_id]["gems"] -= b["cost"]
        db[user_id]["active_boost"] = {
            "type": btype,
            "time_multiplier": b["time_multiplier"],
            "expires_at": time.time() + b["duration_seconds"],
            "started_at": time.time(),
        }
        save_db()
        show_alert(cb_id, f"✅ بوست {b['name']} فعال شد!", True)
        edit_message(chat_id, msg_id, build_scientists_text(user_id),
                     build_scientists_keyboard(user_id))
        return

    # ==================== رنکینگ ====================
    if data.startswith("rank_p_"):
        try:
            pg = int(data.replace("rank_p_", ""))
        except ValueError:
            pg = 0
        update_rank_today()
        txt, kb = build_players_ranking(pg, my_user_id=user_id)
        edit_message(chat_id, msg_id, txt, kb)
        return

    if data.startswith("rank_clan_p_"):
        try:
            pg = int(data.replace("rank_clan_p_", ""))
        except ValueError:
            pg = 0
        txt, kb = build_clans_ranking(pg, my_user_id=user_id)
        if txt:
            edit_message(chat_id, msg_id, txt, kb)
        else:
            show_alert(cb_id, "❌ هیچ کلنی نیست!", True)
        return

    if data == "rank_clan":
        txt, kb = build_clans_ranking(0, my_user_id=user_id)
        if txt:
            edit_message(chat_id, msg_id, txt, kb)
        else:
            show_alert(cb_id, "❌ هیچ کلنی نیست!", True)
        return

    if data == "rank_daily":
        txt, kb = build_daily_ranking(0, my_user_id=user_id)
        edit_message(chat_id, msg_id, txt, kb)
        return

    # ==================== حمله ====================
    if data == "battle_attack":
        p = db.get(user_id, {})
        tid = p.get("battle_target")
        tt = p.get("battle_target_time", 0)
        if not tid or tid not in db or time.time() - tt > 180:
            edit_message(chat_id, msg_id,
                "⏳ حریف منقضی شد. دوباره امتحان کن.",
                {"inline_keyboard": [[{"text": "🔙 بازگشت",
                                       "callback_data": "go_main"}]]})
            return
        db[user_id]["battle_action"] = "attack"
        save_db()
        t = db[tid]
        edit_message(chat_id, msg_id,
            f"⚔️ حمله به {t.get('name','کاربر')}\n\n"
            f"📝 اسم موشک رو بنویس (مثلاً: اطلس)\n"
            f"✨ می‌تونی طلسم همراهش کنی (مثلاً: اطلس آتش)\n\n"
            f"⏳ ۳ دقیقه فرصت داری",
            {"inline_keyboard": [[{"text": "❌ لغو",
                                   "callback_data": "battle_cancel"}]]})
        return

    if data == "battle_combo_start":
        p = db.get(user_id, {})
        tid = p.get("battle_target")
        tt = p.get("battle_target_time", 0)
        if not tid or tid not in db or time.time() - tt > 180:
            edit_message(chat_id, msg_id,
                "⏳ حریف منقضی شد.",
                {"inline_keyboard": [[{"text": "🔙 بازگشت",
                                       "callback_data": "go_main"}]]})
            return
        from handlers import calculate_combo_attack
        result = calculate_combo_attack(user_id)
        if not result:
            show_alert(cb_id, "❌ ترکیب نظامی نداری! اول ترکیب بساز.", True)
            return
        target = db[tid]

        for w in result["weapons"]:
            wn, wcat, used = w["name"], w["category"], w["used"]
            if used <= 0: continue
            if wcat in db[user_id] and wn in db[user_id][wcat]:
                cur = db[user_id][wcat][wn].get("count", 0)
                new = max(0, cur - used)
                if new <= 0:
                    del db[user_id][wcat][wn]
                else:
                    db[user_id][wcat][wn]["count"] = new

        fighter_bonus = result.get("fighter_bonus", 0)
        defense_pct = get_total_defense(target, "combo")
        total_dmg = result["damage"] + fighter_bonus
        defense_absorbed = int(total_dmg * defense_pct / 100)
        net_dmg = max(1, total_dmg - defense_absorbed)

        t_coins_before = target.get("coins", 0)
        t_oil_before = target.get("oil", 0)
        want_c = result["coins"]
        want_o = result["oil"]
        stolen_c = min(want_c, t_coins_before) if t_coins_before > 0 else 0
        stolen_o = min(want_o, t_oil_before) if t_oil_before > 0 else 0

        if target.get("sub_shield_until", 0) > time.time():
            stolen_c = int(stolen_c * 0.5)
            stolen_o = int(stolen_o * 0.5)

        db[tid]["coins"] = max(0, t_coins_before - stolen_c)
        db[user_id]["coins"] = db[user_id].get("coins", 0) + stolen_c
        if target.get("refinery_level", 0) > 0:
            db[tid]["oil"] = max(0, t_oil_before - stolen_o)
            db[user_id]["oil"] = db[user_id].get("oil", 0) + stolen_o

        from handlers import apply_rank_change
        rank_gain = result["rank"]
        if not is_moon_league(target.get("rank", 0)) and rank_gain > 0:
            apply_rank_change(user_id, tid, rank_gain)

        db[user_id]["total_damage"] = db[user_id].get("total_damage", 0) + 4
        db[user_id]["battle_action"] = None
        save_db()

        report = build_combo_attack_report(
            attacker=db[user_id], target=target,
            raw_dmg=total_dmg, defense_pct=defense_pct,
            stolen_c=stolen_c, stolen_o=stolen_o, rank_gain=rank_gain,
            weapons_used=result["weapons"],
            fighter_dmg=fighter_bonus,
            fighter_loot={"coins": 0, "oil": 0},
            fighter_note="",
            vernix_msgs=[], moon_note="",
            defender_had_coins=t_coins_before,
            defender_had_oil=t_oil_before,
            want_c=want_c, want_o=want_o,
        )
        send_message(chat_id, report)
        return

    if data == "battle_next":
        p = db.get(user_id, {})
        if p.get("coins", 0) < 10:
            show_alert(cb_id, "❌ به ۱۰ سکه نیاز داری!", True)
            return
        db[user_id]["coins"] -= 10
        db[user_id]["battle_target"] = None
        db[user_id]["battle_target_time"] = 0
        save_db()
        txt = build_battle_text(user_id)
        edit_message(chat_id, msg_id, txt, build_battle_keyboard())
        return

    if data == "battle_cancel":
        db[user_id]["battle_action"] = None
        save_db()
        show_alert(cb_id, "❌ لغو شد", False)
        return

    if data.startswith("revenge_"):
        target_id = data.replace("revenge_", "")
        if target_id not in db:
            show_alert(cb_id, "❌ کاربر پیدا نشد!", True)
            return
        if target_id == user_id:
            show_alert(cb_id, "❌ خودت!", True)
            return
        db[user_id]["battle_target"] = target_id
        db[user_id]["battle_target_time"] = time.time()
        save_db()
        txt = build_battle_text(user_id)
        edit_message(chat_id, msg_id, txt, build_battle_keyboard())
        return

    # ==================== گردونه‌ها ====================
    if data == "wheel_daily":
        txt, kb = build_wheel_daily_menu(user_id)
        edit_message(chat_id, msg_id, txt, kb)
        return

    if data == "wheel_daily_1":
        p = db.get(user_id, {})
        last = p.get("last_free_wheel", 0)
        if time.time() - last < 86400:
            show_alert(cb_id, "⏳ هنوز آماده نیست!", True)
            return
        prize = spin_daily_wheel()
        db[user_id]["last_free_wheel"] = time.time()
        if prize["type"] == "weapon":
            cat = prize["category"]
            wn = prize["weapon"]
            if cat not in db[user_id]:
                db[user_id][cat] = {}
            if wn not in db[user_id][cat]:
                db[user_id][cat][wn] = {"count": 0, "level": 1}
            db[user_id][cat][wn]["count"] += prize["amount"]
        elif prize["type"] == "coins":
            db[user_id]["coins"] = db[user_id].get("coins", 0) + prize["amount"]
        elif prize["type"] == "oil":
            db[user_id]["oil"] = db[user_id].get("oil", 0) + prize["amount"]
        elif prize["type"] == "iron":
            db[user_id]["iron"] = db[user_id].get("iron", 0) + prize["amount"]
        elif prize["type"] == "steel":
            db[user_id]["steel"] = db[user_id].get("steel", 0) + prize["amount"]
        save_db()
        txt, kb = build_wheel_daily_result(user_id, [prize])
        edit_message(chat_id, msg_id, txt, kb)
        return

    if data in ("wheel_legendary", "wheel_luck", "wheel_storm",
                "wheel_hunt", "wheel_fire", "wheel_dragon", "wheel_fighter"):
        _wheel_menu_route(data, chat_id, msg_id, user_id)
        return

    if data.startswith("wheel_legendary_"):
        n = 10 if data.endswith("_10") else 1
        _wheel_spin(user_id, cb_id, chat_id, msg_id, n, WHEEL_LEGENDARY_PRICE_1,
                    WHEEL_LEGENDARY_PRICE_10, spin_legendary_wheel,
                    build_wheel_legendary_result, "wheel_legendary")
        return

    if data.startswith("wheel_storm_"):
        n = 10 if data.endswith("_10") else 1
        _wheel_spin(user_id, cb_id, chat_id, msg_id, n, WHEEL_STORM_PRICE_1,
                    WHEEL_STORM_PRICE_10, spin_storm_wheel,
                    build_wheel_storm_result, "wheel_storm")
        return

    if data.startswith("wheel_hunt_"):
        n = 10 if data.endswith("_10") else 1
        _wheel_spin(user_id, cb_id, chat_id, msg_id, n, WHEEL_HUNT_PRICE_1,
                    WHEEL_HUNT_PRICE_10, spin_hunt_wheel,
                    build_wheel_hunt_result, "wheel_hunt")
        return

    if data.startswith("wheel_fire_"):
        n = 10 if data.endswith("_10") else 1
        _wheel_spin(user_id, cb_id, chat_id, msg_id, n, WHEEL_FIRE_PRICE_1,
                    WHEEL_FIRE_PRICE_10, spin_fire_wheel,
                    build_wheel_fire_result, "wheel_fire")
        return

    if data.startswith("wheel_dragon_"):
        n = 10 if data.endswith("_10") else 1
        _wheel_spin(user_id, cb_id, chat_id, msg_id, n, WHEEL_DRAGON_PRICE_1,
                    WHEEL_DRAGON_PRICE_10, spin_dragon_wheel,
                    build_wheel_dragon_result, "wheel_dragon")
        return

    if data.startswith("wheel_fighter_"):
        n = 10 if data.endswith("_10") else 1
        _wheel_spin(user_id, cb_id, chat_id, msg_id, n, WHEEL_FIGHTER_PRICE_1,
                    WHEEL_FIGHTER_PRICE_10, spin_fighter_wheel,
                    build_wheel_fighter_result, "wheel_fighter")
        return

    if data.startswith("wheel_luck_"):
        p = db.get(user_id, {})
        if p.get("coins", 0) < WHEEL_LUCK_PRICE_1:
            show_alert(cb_id, "❌ سکه کافی نیست!", True)
            return
        db[user_id]["coins"] -= WHEEL_LUCK_PRICE_1
        prize = spin_luck_wheel()
        if prize["type"] == "coins":
            db[user_id]["coins"] = db[user_id].get("coins", 0) + prize["amount"]
        elif prize["type"] == "multi":
            for r in prize["rewards"]:
                _apply_wheel_prize(user_id, r)
        save_db()
        txt, kb = build_wheel_luck_result(user_id, [prize])
        edit_message(chat_id, msg_id, txt, kb)
        return

    # ==================== 💥 تسلیحات خانه ====================
    if data == "upgrade_weapons_house":
        p = db.get(user_id, {})
        lvl = p.get("weapons_house_level", 1)
        if lvl >= 5:
            show_alert(cb_id, "🚫 حداکثر سطح!", True)
            return
        cost = ARSENAL_UPGRADE_COSTS.get(lvl, 0)
        if p.get("coins", 0) < cost:
            show_alert(cb_id, f"❌ به {cost:,} سکه نیاز داری!", True)
            return
        db[user_id]["coins"] -= cost
        db[user_id]["weapons_house_level"] = lvl + 1
        save_db()
        show_alert(cb_id, f"✅ تسلیحات خانه به سطح {lvl+1} ارتقا یافت!", True)
        edit_message(chat_id, msg_id, build_weapons_house_text(user_id),
                     build_weapons_house_keyboard(user_id))
        return

    if data == "upgrade_arsenal":
        p = db.get(user_id, {})
        lvl = p.get("weapons_house_level", 1)
        if lvl >= 5:
            show_alert(cb_id, "🚫 حداکثر سطح!", True)
            return
        cost = ARSENAL_UPGRADE_COSTS.get(lvl, 0)
        if p.get("coins", 0) < cost:
            show_alert(cb_id, f"❌ به {cost:,} سکه نیاز داری!", True)
            return
        db[user_id]["coins"] -= cost
        db[user_id]["weapons_house_level"] = lvl + 1
        save_db()
        show_alert(cb_id, f"✅ تسلیحات خانه به سطح {lvl+1} ارتقا یافت!", True)
        edit_message(chat_id, msg_id, build_weapons_house_text(user_id),
                     build_weapons_house_keyboard(user_id))
        return

    # ==================== پایگاه جنگنده ====================
    if data == "combo_fighter":
        edit_message(chat_id, msg_id, build_fighter_base_text(user_id),
                     build_fighter_base_keyboard(user_id))
        return

    if data == "fbase_build":
        p = db.get(user_id, {})
        ulvl, _, _ = get_level_info(p.get("total_damage", 0))
        if ulvl < 5:
            show_alert(cb_id, "❌ نیاز به لول 5!", True)
            return
        if p.get("coins", 0) < FIGHTER_BASE_BUILD_COST:
            show_alert(cb_id, f"❌ به {FIGHTER_BASE_BUILD_COST:,} سکه نیاز داری!", True)
            return
        db[user_id]["coins"] -= FIGHTER_BASE_BUILD_COST
        db[user_id]["fighter_base_level"] = 1
        save_db()
        show_alert(cb_id, "✅ پایگاه جنگنده ساخته شد!", True)
        edit_message(chat_id, msg_id, build_fighter_base_text(user_id),
                     build_fighter_base_keyboard(user_id))
        return

    if data == "fbase_upgrade":
        p = db.get(user_id, {})
        lvl = p.get("fighter_base_level", 0)
        if lvl <= 0:
            show_alert(cb_id, "❌ اول پایگاه بساز!", True)
            return
        if lvl >= FIGHTER_BASE_MAX_LEVEL:
            show_alert(cb_id, "🚫 حداکثر سطح!", True)
            return
        nxt = lvl + 1
        cost = FIGHTER_BASE_LEVELS[nxt]["upgrade_cost"]
        req = FIGHTER_BASE_LEVELS[nxt]["required_user_level"]
        ulvl, _, _ = get_level_info(p.get("total_damage", 0))
        if ulvl < req:
            show_alert(cb_id, f"❌ نیاز به لول {req}", True)
            return
        if p.get("coins", 0) < cost:
            show_alert(cb_id, f"❌ به {cost:,} سکه نیاز داری!", True)
            return
        db[user_id]["coins"] -= cost
        db[user_id]["fighter_base_level"] = nxt
        save_db()
        show_alert(cb_id, f"✅ پایگاه به سطح {nxt} ارتقا یافت!", True)
        edit_message(chat_id, msg_id, build_fighter_base_text(user_id),
                     build_fighter_base_keyboard(user_id))
        return

    if data == "fbase_buy":
        edit_message(chat_id, msg_id, build_fighter_buy_text(user_id),
                     build_fighter_buy_keyboard(user_id))
        return

    if data.startswith("fbase_buy_"):
        fname = data.replace("fbase_buy_", "")
        if fname not in HERO_FIGHTERS:
            show_alert(cb_id, "❌ جنگنده نامعتبر!", True)
            return
        fdata = HERO_FIGHTERS[fname]
        p = db.get(user_id, {})
        lvl = p.get("fighter_base_level", 0)
        if lvl < fdata.get("min_base_level", 1):
            show_alert(cb_id, f"❌ نیاز به پایگاه سطح {fdata['min_base_level']}", True)
            return
        cost = fdata["build_cost"]
        if p.get("coins", 0) < cost:
            show_alert(cb_id, f"❌ به {cost:,} سکه نیاز داری!", True)
            return
        used = get_used_fighter_slots(p)
        cap = FIGHTER_BASE_LEVELS.get(lvl, {}).get("slots", 0)
        if used + 1 > cap:
            show_alert(cb_id, f"❌ ظرفیت پایگاه پر است! ({used}/{cap})", True)
            return
        db[user_id]["coins"] -= cost
        if "fighters_hero" not in db[user_id]:
            db[user_id]["fighters_hero"] = {}
        if fname not in db[user_id]["fighters_hero"]:
            db[user_id]["fighters_hero"][fname] = {
                "count": 0, "hp_current": fdata.get("hp", 50), "level": 1,
            }
        db[user_id]["fighters_hero"][fname]["count"] += 1
        save_db()
        show_alert(cb_id, f"✅ {fname} خریداری شد!", True)
        edit_message(chat_id, msg_id, build_fighter_base_text(user_id),
                     build_fighter_base_keyboard(user_id))
        return

    if data == "phoenix_upgrade":
        p = db.get(user_id, {})
        phx = p.get("fighters_hero", {}).get("فونیکس", {})
        if phx.get("count", 0) <= 0:
            show_alert(cb_id, "❌ فونیکس نداری!", True)
            return
        cur_lvl = phx.get("level", 1)
        if cur_lvl >= PHOENIX_MAX_LEVEL:
            show_alert(cb_id, "🚫 حداکثر سطح!", True)
            return
        cost = (cur_lvl + 1) * 150000
        if p.get("coins", 0) < cost:
            show_alert(cb_id, f"❌ به {cost:,} سکه نیاز داری!", True)
            return
        db[user_id]["coins"] -= cost
        db[user_id]["fighters_hero"]["فونیکس"]["level"] = cur_lvl + 1
        save_db()
        show_alert(cb_id, f"✅ فونیکس به سطح {cur_lvl+1} ارتقا یافت!", True)
        edit_message(chat_id, msg_id, build_fighter_base_text(user_id),
                     build_fighter_base_keyboard(user_id))
        return

    if data == "fbase_repair":
        edit_message(chat_id, msg_id, build_repair_fighters_text(user_id),
                     build_repair_fighters_keyboard(user_id))
        return

    if data.startswith("fbase_repair_"):
        fname = data.replace("fbase_repair_", "")
        p = db.get(user_id, {})
        if fname not in p.get("fighters_hero", {}):
            show_alert(cb_id, "❌ نداری!", True)
            return
        fdata = HERO_FIGHTERS.get(fname, {})
        hp_m = fdata.get("hp", 50)
        finfo = p["fighters_hero"][fname]
        hp_c = finfo.get("hp_current", hp_m)
        need = hp_m - hp_c
        cost = need * 100
        if p.get("coins", 0) < cost:
            show_alert(cb_id, f"❌ به {cost:,} سکه نیاز داری!", True)
            return
        db[user_id]["coins"] -= cost
        db[user_id]["fighters_hero"][fname]["hp_current"] = hp_m
        save_db()
        show_alert(cb_id, f"✅ {fname} تعمیر شد!", True)
        edit_message(chat_id, msg_id, build_repair_fighters_text(user_id),
                     build_repair_fighters_keyboard(user_id))
        return

    # ==================== ترکیب نظامی ====================
    if data == "combo_new":
        db[user_id]["combo_action"] = "get_name"
        save_db()
        send_message(chat_id, "➕ ترکیب جدید\n\n📝 اسم ترکیب رو بنویس:",
            {"inline_keyboard": [[{"text": "❌ لغو",
                                   "callback_data": "combo_back"}]]})
        return

    if data == "combo_edit":
        p = db.get(user_id, {})
        combos = p.get("combos", {})
        if not combos:
            show_alert(cb_id, "❌ ترکیبی نداری!", True)
            return
        buttons = []
        for cn in combos:
            buttons.append([{"text": f"✏️ {cn}",
                             "callback_data": f"combo_edit_{cn}"}])
        buttons.append([{"text": "🔙 بازگشت", "callback_data": "combo_back"}])
        edit_message(chat_id, msg_id, "✏️ ترکیب‌های شما:",
                     {"inline_keyboard": buttons})
        return

    if data.startswith("combo_edit_"):
        cn = data.replace("combo_edit_", "")
        p = db.get(user_id, {})
        if cn not in p.get("combos", {}):
            show_alert(cb_id, "❌ ترکیب نیست!", True)
            return
        combo = p["combos"][cn]
        text = f"✏️ ترکیب «{cn}»\n\n📦 سلاح‌ها:\n"
        if not combo.get("weapons"):
            text += "❌ خالیه!\n"
        else:
            for w in combo["weapons"]:
                if w.get("count", 0) > 0:
                    text += f"• {w['name']}: {w['count']}\n"
        edit_message(chat_id, msg_id, text,
            {"inline_keyboard": [
                [{"text": "➕ اضافه سلاح", "callback_data": f"combo_add_{cn}"}],
                [{"text": "➖ حذف سلاح", "callback_data": f"combo_remove_{cn}"}],
                [{"text": "🗑️ حذف کل ترکیب", "callback_data": f"combo_del_{cn}"}],
                [{"text": "🔙 بازگشت", "callback_data": "combo_edit"}],
            ]})
        return

    if data.startswith("combo_add_"):
        cn = data.replace("combo_add_", "")
        db[user_id]["combo_action"] = f"add_weapon_{cn}"
        save_db()
        send_message(chat_id,
            f"➕ اضافه کردن سلاح به «{cn}»\n\n"
            f"📝 فرمت: `نام تعداد`\n"
            f"مثال: `اطلس 5`",
            {"inline_keyboard": [[{"text": "🔙 بازگشت",
                                   "callback_data": f"combo_edit_{cn}"}]]})
        return

    if data.startswith("combo_remove_"):
        cn = data.replace("combo_remove_", "")
        p = db.get(user_id, {})
        combo = p.get("combos", {}).get(cn, {})
        weapons = [(w["name"], w["count"]) for w in combo.get("weapons", [])
                   if w.get("count", 0) > 0]
        if not weapons:
            show_alert(cb_id, "❌ سلاحی نیست!", True)
            return
        buttons = []
        for wn, wc in weapons:
            buttons.append([{"text": f"➖ {wn} ({wc})",
                             "callback_data": f"combo_rmw_{cn}__{wn}"}])
        buttons.append([{"text": "🔙 بازگشت",
                         "callback_data": f"combo_edit_{cn}"}])
        edit_message(chat_id, msg_id, f"➖ حذف از «{cn}»:",
                     {"inline_keyboard": buttons})
        return

    if data.startswith("combo_rmw_"):
        rest = data.replace("combo_rmw_", "")
        if "__" not in rest:
            return
        cn, wn = rest.split("__", 1)
        db[user_id]["combo_remove_action"] = {"cn": cn, "wn": wn}
        save_db()
        send_message(chat_id,
            f"➖ حذف «{wn}»\n\n🔢 چند عدد کم کنم؟",
            {"inline_keyboard": [[{"text": "🔙 بازگشت",
                                   "callback_data": f"combo_remove_{cn}"}]]})
        return

    if data.startswith("combo_del_"):
        cn = data.replace("combo_del_", "")
        p = db.get(user_id, {})
        if cn in p.get("combos", {}):
            del db[user_id]["combos"][cn]
            save_db()
            show_alert(cb_id, f"✅ «{cn}» حذف شد!", True)
        edit_message(chat_id, msg_id, "🎯 ترکیب نظامی\n\n🔻 یکی:",
                     build_combo_menu(user_id))
        return

    if data == "combo_buildings":
        from handlers import get_buildings_text, get_buildings_keyboard
        edit_message(chat_id, msg_id, get_buildings_text(user_id),
                     get_buildings_keyboard(user_id))
        return

    if data.startswith("bld_"):
        bname = data.replace("bld_", "")
        if bname not in BUILDINGS:
            show_alert(cb_id, "❌ ساختمان نامعتبر!", True)
            return
        p = db.get(user_id, {})
        b = BUILDINGS[bname]
        cur_lvl = p.get("buildings", {}).get(bname, 0)
        arsenal_lvl = p.get("arsenal_level", 1)
        if cur_lvl == 0:
            if p.get("coins", 0) < b["price"]:
                show_alert(cb_id, f"❌ به {b['price']:,} سکه نیاز داری!", True)
                return
            db[user_id]["coins"] -= b["price"]
            if "buildings" not in db[user_id]:
                db[user_id]["buildings"] = {}
            db[user_id]["buildings"][bname] = 1
            save_db()
            show_alert(cb_id, f"✅ {bname} ساخته شد!", True)
        else:
            if cur_lvl >= BUILDING_MAX_LEVEL:
                show_alert(cb_id, "🚫 حداکثر سطح!", True)
                return
            if arsenal_lvl < cur_lvl + 1:
                show_alert(cb_id, f"❌ زرادخانه باید حداقل سطح {cur_lvl+1} باشد!", True)
                return
            if p.get("coins", 0) < b["upgrade"]:
                show_alert(cb_id, f"❌ به {b['upgrade']:,} سکه نیاز داری!", True)
                return
            db[user_id]["coins"] -= b["upgrade"]
            db[user_id]["buildings"][bname] = cur_lvl + 1
            save_db()
            show_alert(cb_id, f"✅ {bname} به سطح {cur_lvl+1} ارتقا یافت!", True)
        from handlers import get_buildings_text, get_buildings_keyboard
        edit_message(chat_id, msg_id, get_buildings_text(user_id),
                     get_buildings_keyboard(user_id))
        return

    # ==================== 🏰 زرادخانه ====================
    if data == "combo_armory":
        edit_message(chat_id, msg_id, build_combo_arsenal_text(user_id),
                     build_combo_arsenal_keyboard(user_id))
        return

    if data == "upgrade_arsenal_attack":
        p = db.get(user_id, {})
        lvl = p.get("arsenal_level", 1)
        if lvl >= ARSENAL_MAX_LEVEL:
            show_alert(cb_id, "🚫 حداکثر سطح!", True)
            return
        costs = ARSENAL_ATTACK_COSTS[lvl]
        if p.get("coins", 0) < costs["coins"]:
            show_alert(cb_id, f"❌ به {costs['coins']:,} سکه نیاز داری!", True)
            return
        if costs["oil"] > 0 and p.get("oil", 0) < costs["oil"]:
            show_alert(cb_id, f"❌ به {costs['oil']:,} نفت نیاز داری!", True)
            return
        db[user_id]["coins"] -= costs["coins"]
        if costs["oil"] > 0:
            db[user_id]["oil"] -= costs["oil"]
        db[user_id]["arsenal_level"] = lvl + 1
        save_db()
        new_cap = ARSENAL_LEVELS[lvl + 1]["capacity"]
        show_alert(cb_id,
            f"✅ زرادخانه به سطح {lvl+1} ارتقا یافت!\n"
            f"📦 ظرفیت جدید: {new_cap} موشک",
            True)
        edit_message(chat_id, msg_id, build_combo_arsenal_text(user_id),
                     build_combo_arsenal_keyboard(user_id))
        return

    # ==================== کلن ====================
    if data == "clan_buy":
        db[user_id]["clan_action"] = "buy_clan"
        save_db()
        send_message(chat_id,
            "🏰 خرید کلن\n\n💰 هزینه: 4,000 سکه\n\n"
            "📝 اسم کلن رو بنویس (حداقل 3 حرف):",
            {"inline_keyboard": [[{"text": "❌ لغو",
                                   "callback_data": "clan_back"}]]})
        return

    if data == "clan_search":
        txt, kb = build_clan_search(0)
        edit_message(chat_id, msg_id, txt, kb)
        return

    if data.startswith("clan_search_p_"):
        try:
            pg = int(data.replace("clan_search_p_", ""))
        except ValueError:
            pg = 0
        txt, kb = build_clan_search(pg)
        edit_message(chat_id, msg_id, txt, kb)
        return

    if data.startswith("clan_view_"):
        cid = data.replace("clan_view_", "")
        members = get_clan_members(cid)
        cname = get_clan_name(cid)
        is_full = len(members) >= CLAN_MAX_MEMBERS and cid != OFFICIAL_CLAN_ID
        text = (f"🏰 کلن {cname}\n\n"
                f"👥 اعضا: {len(members)}/{CLAN_MAX_MEMBERS}\n"
                f"🏆 رنک: {get_clan_rank_points(cid):,}\n")
        buttons = []
        if db[user_id].get("clan_id") != cid and not is_full:
            buttons.append([{"text": "📩 درخواست عضویت",
                             "callback_data": f"clan_joinreq_{cid}"}])
        buttons.append([{"text": "🔙 بازگشت", "callback_data": "clan_search"}])
        edit_message(chat_id, msg_id, text, {"inline_keyboard": buttons})
        return

    if data == "clan_members":
        txt, kb = build_clan_members_page(user_id, 0)
        edit_message(chat_id, msg_id, txt, kb)
        return

    if data.startswith("clan_members_p_"):
        try:
            pg = int(data.replace("clan_members_p_", ""))
        except ValueError:
            pg = 0
        txt, kb = build_clan_members_page(user_id, pg)
        edit_message(chat_id, msg_id, txt, kb)
        return

    if data == "clan_manage":
        p = db.get(user_id, {})
        if p.get("clan_role") not in ("leader", "officer"):
            show_alert(cb_id, "❌ دسترسی نداری!", True)
            return
        edit_message(chat_id, msg_id, "⚙️ مدیریت کلن:",
            {"inline_keyboard": [
                [{"text": "✏️ تغییر اسم (1,000 سکه)",
                  "callback_data": "clan_edit_name"}],
                [{"text": "🔙 بازگشت", "callback_data": "clan_back"}],
            ]})
        return

    if data == "clan_edit_name":
        p = db.get(user_id, {})
        if p.get("clan_role") != "leader":
            show_alert(cb_id, "❌ فقط رهبر!", True)
            return
        db[user_id]["clan_action"] = "edit_clan_name"
        save_db()
        send_message(chat_id, "✏️ اسم جدید کلن رو بنویس:",
            {"inline_keyboard": [[{"text": "❌ لغو",
                                   "callback_data": "clan_back"}]]})
        return

    if data == "clan_msg_all":
        p = db.get(user_id, {})
        if p.get("clan_role") not in ("leader", "officer"):
            show_alert(cb_id, "❌ دسترسی نداری!", True)
            return
        db[user_id]["clan_action"] = "broadcast"
        save_db()
        send_message(chat_id, "📢 پیام برای همه اعضای کلن:",
            {"inline_keyboard": [[{"text": "❌ لغو",
                                   "callback_data": "clan_back"}]]})
        return

    if data == "clan_leave":
        p = db.get(user_id, {})
        cid = p.get("clan_id")
        if not cid:
            show_alert(cb_id, "❌ کلن نداری!", True)
            return
        if p.get("clan_role") == "leader":
            show_alert(cb_id, "❌ رهبر نمی‌تونه خارج بشه! اول کلن رو حذف کن.", True)
            return
        db[user_id]["clan_id"] = None
        db[user_id]["clan"] = None
        db[user_id]["clan_role"] = None
        save_db()
        show_alert(cb_id, "✅ از کلن خارج شدی!", True)
        edit_message(chat_id, msg_id, "👥 کلن:",
                     build_clan_inline_keyboard(user_id))
        return

    if data == "clan_delete":
        p = db.get(user_id, {})
        if p.get("clan_role") != "leader":
            show_alert(cb_id, "❌ فقط رهبر!", True)
            return
        cid = p.get("clan_id")
        if not cid:
            show_alert(cb_id, "❌ کلن نداری!", True)
            return
        members = get_clan_members(cid)
        for muid, _ in members:
            db[muid]["clan_id"] = None
            db[muid]["clan"] = None
            db[muid]["clan_role"] = None
        if "clans" in db and cid in db["clans"]:
            del db["clans"][cid]
        save_db()
        show_alert(cb_id, "🗑️ کلن حذف شد!", True)
        edit_message(chat_id, msg_id, "👥 کلن:",
                     build_clan_inline_keyboard(user_id))
        return

    # ==================== جنگ کلن ====================
    if data == "clan_war":
        from clan_war import build_clan_war_select_text
        p = db.get(user_id, {})
        if not p.get("clan_id"):
            show_alert(cb_id, "❌ اول کلن بساز!", True)
            return
        if p.get("clan_role") != "leader":
            show_alert(cb_id, "❌ فقط رهبر می‌تواند جنگ را شروع کند!", True)
            return
        db[user_id]["clan_war_selection"] = []
        save_db()
        txt, kb = build_clan_war_select_text(user_id)
        if kb:
            edit_message(chat_id, msg_id, txt, kb)
        else:
            show_alert(cb_id, txt, True)
        return

    if data.startswith("cwar_toggle_"):
        from clan_war import (toggle_clan_war_member,
                              build_clan_war_select_text)
        mid = data.replace("cwar_toggle_", "")
        ok, msg = toggle_clan_war_member(user_id, mid)
        if not ok:
            show_alert(cb_id, msg, True)
            return
        txt, kb = build_clan_war_select_text(user_id)
        if kb:
            edit_message(chat_id, msg_id, txt, kb)
        return

    if data == "cwar_start_search":
        from clan_war import start_clan_war_search
        ok, msg = start_clan_war_search(user_id)
        show_alert(cb_id, msg, True)
        if ok:
            edit_message(chat_id, msg_id,
                f"⏳ {msg}\n\n🔄 وقتی رهبر کلن دیگری هم جنگ را شروع کند، اطلاع می‌دهم.",
                {"inline_keyboard": [[{"text": "❌ لغو جستجو",
                                       "callback_data": "cwar_cancel"}]]})
        return

    if data == "cwar_cancel":
        if "clan_war_requests" in db:
            for rid, req in list(db["clan_war_requests"].items()):
                if (req.get("leader_id") == user_id
                        and req.get("status") == "waiting"):
                    del db["clan_war_requests"][rid]
        db[user_id]["clan_war_selection"] = []
        save_db()
        show_alert(cb_id, "❌ لغو شد", False)
        edit_message(chat_id, msg_id, "❌ جستجوی جنگ لغو شد.",
            {"inline_keyboard": [[{"text": "🔙 بازگشت",
                                   "callback_data": "clan_war"}]]})
        return

    if data.startswith("cwar_attack_"):
        from clan_war import do_clan_war_attack
        wid = data.replace("cwar_attack_", "")
        ok, msg, _ = do_clan_war_attack(user_id, wid)
        if not ok:
            show_alert(cb_id, msg, True)
            return
        send_message(chat_id, msg)
        show_alert(cb_id, "✅ حمله انجام شد!", False)
        return

    if data.startswith("cwar_results_"):
        from clan_war import build_war_results_text
        wid = data.replace("cwar_results_", "")
        edit_message(chat_id, msg_id, build_war_results_text(wid),
            {"inline_keyboard": [[{"text": "🔙 بازگشت",
                                   "callback_data": "clan_war"}]]})
        return

    # ==================== ارتقای کلن ====================
    if data == "clan_upgrade":
        from clan_war import (build_clan_upgrade_text,
                              build_clan_upgrade_keyboard)
        p = db.get(user_id, {})
        cid = p.get("clan_id")
        if not cid:
            show_alert(cb_id, "❌ کلن نداری!", True)
            return
        edit_message(chat_id, msg_id, build_clan_upgrade_text(cid),
                     build_clan_upgrade_keyboard(cid))
        return

    if data == "clan_donate":
        db[user_id]["clan_action"] = "donate_coins"
        save_db()
        send_message(chat_id,
            "💰 *اهدا سکه به کلن*\n\n"
            "🔢 چند سکه می‌خواهی اهدا کنی؟\n"
            "(عدد بفرست یا /cancel برای لغو)",
            {"inline_keyboard": [[{"text": "❌ لغو",
                                   "callback_data": "clan_donate_cancel"}]]})
        return

    if data == "clan_donate_cancel":
        db[user_id]["clan_action"] = None
        save_db()
        edit_message(chat_id, msg_id, "❌ لغو شد.",
            {"inline_keyboard": [[{"text": "🔙 بازگشت",
                                   "callback_data": "clan_upgrade"}]]})
        return

    # ==================== مدیریت کلن ====================
    if data == "clan_invite":
        p = db.get(user_id, {})
        if p.get("clan_role") not in ("leader", "officer"):
            show_alert(cb_id, "❌ فقط رهبر یا افسر!", True)
            return
        cid = p.get("clan_id")
        if not cid:
            show_alert(cb_id, "❌ کلن نداری!", True)
            return
        members = get_clan_members(cid)
        if len(members) >= CLAN_MAX_MEMBERS and cid != OFFICIAL_CLAN_ID:
            show_alert(cb_id, f"❌ کلن پر است! ({len(members)}/{CLAN_MAX_MEMBERS})", True)
            return
        db[user_id]["clan_action"] = "invite_member"
        save_db()
        send_message(chat_id,
            f"📩 *دعوت به کلن*\n\n"
            f"👥 ظرفیت: {len(members)}/{CLAN_MAX_MEMBERS}\n\n"
            f"🆔 آیدی عددی کاربر موردنظر رو بفرست:\n"
            f"(یا /cancel برای لغو)",
            {"inline_keyboard": [[{"text": "❌ لغو",
                                   "callback_data": "clan_back"}]]})
        return

    if data.startswith("clan_inv_accept_"):
        inv_id = data.replace("clan_inv_accept_", "")
        if "clan_invites" not in db or inv_id not in db["clan_invites"]:
            show_alert(cb_id, "❌ دعوت پیدا نشد یا منقضی شده!", True)
            return
        inv = db["clan_invites"][inv_id]
        if inv.get("target_id") != user_id:
            show_alert(cb_id, "❌ این دعوت برای تو نیست!", True)
            return
        if time.time() > inv.get("expires_at", 0):
            del db["clan_invites"][inv_id]
            save_db()
            show_alert(cb_id, "⏱️ دعوت منقضی شده!", True)
            return
        p = db.get(user_id, {})
        if p.get("clan_id"):
            show_alert(cb_id, "❌ تو قبلاً عضو یه کلنی!", True)
            return
        cid = inv["clan_id"]
        members = get_clan_members(cid)
        if len(members) >= CLAN_MAX_MEMBERS and cid != OFFICIAL_CLAN_ID:
            show_alert(cb_id, "❌ کلن پر شد!", True)
            return
        cname = get_clan_name(cid)
        db[user_id]["clan_id"] = cid
        db[user_id]["clan"] = cname
        db[user_id]["clan_role"] = "member"
        del db["clan_invites"][inv_id]
        save_db()
        show_alert(cb_id, f"✅ عضو کلن «{cname}» شدی!", True)
        try:
            send_message(int(inv["inviter_id"]),
                f"✅ {p.get('name', 'کاربر')} دعوتت رو قبول کرد!\n"
                f"🏰 کلن: {cname}")
        except:
            pass
        edit_message(chat_id, msg_id, "👥 کلن:",
                     build_clan_inline_keyboard(user_id))
        return

    if data.startswith("clan_inv_reject_"):
        inv_id = data.replace("clan_inv_reject_", "")
        if "clan_invites" in db and inv_id in db["clan_invites"]:
            inv = db["clan_invites"][inv_id]
            if inv.get("target_id") == user_id:
                del db["clan_invites"][inv_id]
                save_db()
                try:
                    send_message(int(inv["inviter_id"]),
                        f"❌ دعوت کلن رد شد.")
                except:
                    pass
        show_alert(cb_id, "❌ رد شد", False)
        return

    if data.startswith("clan_joinreq_"):
        cid = data.replace("clan_joinreq_", "")
        if not cid or cid == "confirm":
            return
        p = db.get(user_id, {})
        if p.get("clan_id"):
            show_alert(cb_id, "❌ تو قبلاً عضو یه کلنی!", True)
            return
        members = get_clan_members(cid)
        if len(members) >= CLAN_MAX_MEMBERS and cid != OFFICIAL_CLAN_ID:
            show_alert(cb_id, "❌ کلن پر است!", True)
            return
        if cid == OFFICIAL_CLAN_ID:
            db[user_id]["clan_id"] = cid
            db[user_id]["clan"] = get_clan_name(cid)
            db[user_id]["clan_role"] = "member"
            save_db()
            show_alert(cb_id, "✅ عضو کلن رسمی شدی!", True)
            edit_message(chat_id, msg_id, "👥 کلن:",
                         build_clan_inline_keyboard(user_id))
            return
        db[user_id]["clan_join_target"] = cid
        save_db()
        send_message(chat_id,
            f"📩 *درخواست عضویت*\n\n"
            f"🏰 کلن: {get_clan_name(cid)}\n"
            f"👥 اعضا: {len(members)}/{CLAN_MAX_MEMBERS}\n\n"
            f"🔻 تأیید کن:",
            {"inline_keyboard": [
                [{"text": "✅ ارسال درخواست",
                  "callback_data": "clan_joinreq_confirm"}],
                [{"text": "❌ لغو", "callback_data": "clan_back"}],
            ]})
        return

    if data == "clan_joinreq_confirm":
        cid = db[user_id].get("clan_join_target")
        if not cid:
            show_alert(cb_id, "❌ خطا!", True)
            return
        p = db.get(user_id, {})
        members = get_clan_members(cid)
        if len(members) >= CLAN_MAX_MEMBERS and cid != OFFICIAL_CLAN_ID:
            show_alert(cb_id, "❌ کلن پر است!", True)
            db[user_id]["clan_action"] = None
            db[user_id]["clan_join_target"] = None
            save_db()
            return
        if "clan_requests" not in db:
            db["clan_requests"] = {}
        for rid, req in db["clan_requests"].items():
            if (req.get("user_id") == user_id
                    and req.get("clan_id") == cid
                    and req.get("status") == "pending"):
                show_alert(cb_id, "⏳ قبلاً درخواست دادی!", True)
                db[user_id]["clan_action"] = None
                db[user_id]["clan_join_target"] = None
                save_db()
                return
        req_id = f"REQ{int(time.time())}{random.randint(100, 999)}"
        db["clan_requests"][req_id] = {
            "clan_id": cid,
            "user_id": user_id,
            "user_name": p.get("name", "کاربر"),
            "created_at": time.time(),
            "status": "pending",
        }
        db[user_id]["clan_action"] = None
        db[user_id]["clan_join_target"] = None
        save_db()
        show_alert(cb_id, "✅ درخواست فرستاده شد!", True)
        leader_id = None
        if "clans" in db and cid in db["clans"]:
            leader_id = db["clans"][cid].get("leader_id")
        if not leader_id:
            for uid, d in db.items():
                if (isinstance(d, dict)
                        and d.get("clan_id") == cid
                        and d.get("clan_role") == "leader"):
                    leader_id = uid
                    break
        if leader_id:
            try:
                send_message(int(leader_id),
                    f"📥 *درخواست عضویت جدید*\n\n"
                    f"👤 کاربر: {p.get('name', 'کاربر')}\n"
                    f"🆔 آیدی: `{user_id}`",
                    {"inline_keyboard": [
                        [{"text": "✅ قبول",
                          "callback_data": f"clan_req_accept_{req_id}"}],
                        [{"text": "❌ رد",
                          "callback_data": f"clan_req_reject_{req_id}"}],
                    ]})
            except:
                pass
        return

    if data.startswith("clan_req_accept_"):
        req_id = data.replace("clan_req_accept_", "")
        if "clan_requests" not in db or req_id not in db["clan_requests"]:
            show_alert(cb_id, "❌ درخواست پیدا نشد!", True)
            return
        req = db["clan_requests"][req_id]
        if req.get("status") != "pending":
            show_alert(cb_id, "❌ قبلاً پردازش شده!", True)
            return
        cid = req["clan_id"]
        p = db.get(user_id, {})
        if p.get("clan_id") != cid or p.get("clan_role") != "leader":
            show_alert(cb_id, "❌ فقط رهبر این کلن می‌تونه!", True)
            return
        target_uid = req["user_id"]
        if target_uid not in db:
            show_alert(cb_id, "❌ کاربر نیست!", True)
            return
        if db[target_uid].get("clan_id"):
            show_alert(cb_id, "❌ کاربر دیگه عضو یه کلنه!", True)
            db["clan_requests"][req_id]["status"] = "rejected"
            save_db()
            return
        members = get_clan_members(cid)
        if len(members) >= CLAN_MAX_MEMBERS and cid != OFFICIAL_CLAN_ID:
            show_alert(cb_id, "❌ کلن پر است!", True)
            return
        cname = get_clan_name(cid)
        db[target_uid]["clan_id"] = cid
        db[target_uid]["clan"] = cname
        db[target_uid]["clan_role"] = "member"
        db["clan_requests"][req_id]["status"] = "accepted"
        save_db()
        show_alert(cb_id, f"✅ {db[target_uid].get('name','کاربر')} عضو شد!", True)
        try:
            send_message(int(target_uid),
                f"🎉 درخواستت قبول شد!\n\n"
                f"🏰 کلن: {cname}\n"
                f"👑 رهبر: {p.get('name', 'کاربر')}",
                {"inline_keyboard": [[
                    {"text": "👥 کلن من", "callback_data": "go_main"}
                ]]})
        except:
            pass
        return

    if data.startswith("clan_req_reject_"):
        req_id = data.replace("clan_req_reject_", "")
        if "clan_requests" not in db or req_id not in db["clan_requests"]:
            show_alert(cb_id, "❌ پیدا نشد!", True)
            return
        req = db["clan_requests"][req_id]
        cid = req["clan_id"]
        p = db.get(user_id, {})
        if p.get("clan_id") != cid or p.get("clan_role") != "leader":
            show_alert(cb_id, "❌ فقط رهبر!", True)
            return
        db["clan_requests"][req_id]["status"] = "rejected"
        save_db()
        show_alert(cb_id, "❌ رد شد", True)
        try:
            send_message(int(req["user_id"]),
                f"❌ درخواست عضویتت به کلن «{get_clan_name(cid)}» رد شد.")
        except:
            pass
        return

    # ==================== اخراج عضو ====================
    if data == "clan_kick_menu":
        p = db.get(user_id, {})
        if p.get("clan_role") != "leader":
            show_alert(cb_id, "❌ فقط رهبر!", True)
            return
        cid = p.get("clan_id")
        if not cid:
            show_alert(cb_id, "❌ کلن نداری!", True)
            return
        members = get_clan_members(cid)
        kickable = [(uid, m) for uid, m in members
                    if uid != user_id and m.get("clan_role") != "leader"]
        if not kickable:
            show_alert(cb_id, "❌ عضوی برای اخراج نیست!", True)
            return
        buttons = []
        row = []
        for uid, m in kickable:
            role_emoji = "🎖️" if m.get("clan_role") == "officer" else "👤"
            name = m.get("name", "کاربر")
            row.append({"text": f"{role_emoji} {name}",
                        "callback_data": f"clan_kick_{uid}"})
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
        buttons.append([{"text": "🔙 بازگشت", "callback_data": "clan_back"}])
        edit_message(chat_id, msg_id,
            "🚪 *اخراج عضو*\n\n🔻 کی رو اخراج کنم؟",
            {"inline_keyboard": buttons})
        return

    if data.startswith("clan_kick_"):
        target_uid = data.replace("clan_kick_", "")
        p = db.get(user_id, {})
        if p.get("clan_role") != "leader":
            show_alert(cb_id, "❌ فقط رهبر!", True)
            return
        cid = p.get("clan_id")
        if not cid:
            show_alert(cb_id, "❌ کلن نداری!", True)
            return
        if target_uid not in db:
            show_alert(cb_id, "❌ کاربر نیست!", True)
            return
        if db[target_uid].get("clan_id") != cid:
            show_alert(cb_id, "❌ عضو کلن تو نیست!", True)
            return
        if db[target_uid].get("clan_role") == "leader":
            show_alert(cb_id, "❌ رهبره!", True)
            return
        kicked_name = db[target_uid].get("name", "کاربر")
        db[target_uid]["clan_id"] = None
        db[target_uid]["clan"] = None
        db[target_uid]["clan_role"] = None
        save_db()
        show_alert(cb_id, f"✅ {kicked_name} اخراج شد!", True)
        try:
            send_message(int(target_uid),
                f"🚪 شما از کلن «{get_clan_name(cid)}» اخراج شدید!")
        except:
            pass
        edit_message(chat_id, msg_id, "👥 کلن:",
                     build_clan_inline_keyboard(user_id))
        return

    # ==================== ارتقا نقش ====================
    if data == "clan_promote_menu":
        p = db.get(user_id, {})
        if p.get("clan_role") != "leader":
            show_alert(cb_id, "❌ فقط رهبر!", True)
            return
        cid = p.get("clan_id")
        if not cid:
            show_alert(cb_id, "❌ کلن نداری!", True)
            return
        members = get_clan_members(cid)
        promotable = [(uid, m) for uid, m in members
                      if uid != user_id and m.get("clan_role") == "member"]
        if not promotable:
            show_alert(cb_id, "❌ هیچ عضو عادی‌ای نیست!", True)
            return
        buttons = []
        row = []
        for uid, m in promotable:
            name = m.get("name", "کاربر")
            row.append({"text": f"👤 {name}",
                        "callback_data": f"clan_promote_{uid}"})
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
        buttons.append([{"text": "🔙 بازگشت", "callback_data": "clan_back"}])
        edit_message(chat_id, msg_id,
            "⬆️ *ارتقا به افسر*\n\n🔻 کی رو افسر کنم؟",
            {"inline_keyboard": buttons})
        return

    if data.startswith("clan_promote_"):
        target_uid = data.replace("clan_promote_", "")
        p = db.get(user_id, {})
        if p.get("clan_role") != "leader":
            show_alert(cb_id, "❌ فقط رهبر!", True)
            return
        cid = p.get("clan_id")
        if not cid:
            show_alert(cb_id, "❌ کلن نداری!", True)
            return
        if target_uid not in db or db[target_uid].get("clan_id") != cid:
            show_alert(cb_id, "❌ عضو نیست!", True)
            return
        if db[target_uid].get("clan_role") != "member":
            show_alert(cb_id, "❌ فقط عضو عادی ارتقا می‌گیره!", True)
            return
        target_name = db[target_uid].get("name", "کاربر")
        db[target_uid]["clan_role"] = "officer"
        save_db()
        show_alert(cb_id, f"✅ {target_name} افسر شد!", True)
        try:
            send_message(int(target_uid),
                f"⬆️ شما به افسر کلن «{get_clan_name(cid)}» ارتقا یافتید!")
        except:
            pass
        edit_message(chat_id, msg_id, "👥 کلن:",
                     build_clan_inline_keyboard(user_id))
        return

    # ==================== تنزل نقش ====================
    if data == "clan_demote_menu":
        p = db.get(user_id, {})
        if p.get("clan_role") != "leader":
            show_alert(cb_id, "❌ فقط رهبر!", True)
            return
        cid = p.get("clan_id")
        if not cid:
            show_alert(cb_id, "❌ کلن نداری!", True)
            return
        members = get_clan_members(cid)
        demotable = [(uid, m) for uid, m in members
                     if m.get("clan_role") == "officer"]
        if not demotable:
            show_alert(cb_id, "❌ هیچ افسری نیست!", True)
            return
        buttons = []
        row = []
        for uid, m in demotable:
            name = m.get("name", "کاربر")
            row.append({"text": f"🎖️ {name}",
                        "callback_data": f"clan_demote_{uid}"})
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
        buttons.append([{"text": "🔙 بازگشت", "callback_data": "clan_back"}])
        edit_message(chat_id, msg_id,
            "⬇️ *تنزل به عضو عادی*\n\n🔻 کی رو تنزل بدم؟",
            {"inline_keyboard": buttons})
        return

    if data.startswith("clan_demote_"):
        target_uid = data.replace("clan_demote_", "")
        p = db.get(user_id, {})
        if p.get("clan_role") != "leader":
            show_alert(cb_id, "❌ فقط رهبر!", True)
            return
        cid = p.get("clan_id")
        if not cid:
            show_alert(cb_id, "❌ کلن نداری!", True)
            return
        if target_uid not in db or db[target_uid].get("clan_id") != cid:
            show_alert(cb_id, "❌ عضو نیست!", True)
            return
        if db[target_uid].get("clan_role") != "officer":
            show_alert(cb_id, "❌ افسر نیست!", True)
            return
        target_name = db[target_uid].get("name", "کاربر")
        db[target_uid]["clan_role"] = "member"
        save_db()
        show_alert(cb_id, f"✅ {target_name} به عضو عادی تنزل یافت!", True)
        try:
            send_message(int(target_uid),
                f"⬇️ شما از افسری به عضو عادی کلن تنزل یافتید.")
        except:
            pass
        edit_message(chat_id, msg_id, "👥 کلن:",
                     build_clan_inline_keyboard(user_id))
        return

    # ==================== انتقال مالکیت ====================
    if data == "clan_transfer_leader_menu":
        p = db.get(user_id, {})
        if p.get("clan_role") != "leader":
            show_alert(cb_id, "❌ فقط رهبر!", True)
            return
        cid = p.get("clan_id")
        if not cid:
            show_alert(cb_id, "❌ کلن نداری!", True)
            return
        members = get_clan_members(cid)
        transferable = [(uid, m) for uid, m in members
                        if uid != user_id and m.get("clan_role") != "leader"]
        if not transferable:
            show_alert(cb_id, "❌ عضو دیگه‌ای نیست!", True)
            return
        buttons = []
        row = []
        for uid, m in transferable:
            role_emoji = "🎖️" if m.get("clan_role") == "officer" else "👤"
            name = m.get("name", "کاربر")
            row.append({"text": f"{role_emoji} {name}",
                        "callback_data": f"clan_transfer_{uid}"})
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
        buttons.append([{"text": "🔙 بازگشت", "callback_data": "clan_back"}])
        edit_message(chat_id, msg_id,
            "👑 *انتقال مالکیت کلن*\n\n"
            "⚠️ بعد از انتقال، شما به عضو عادی تبدیل می‌شوید!\n\n"
            "🔻 به کی منتقل کنم؟",
            {"inline_keyboard": buttons})
        return

    if data.startswith("clan_transfer_confirm_"):
        target_uid = data.replace("clan_transfer_confirm_", "")
        p = db.get(user_id, {})
        if p.get("clan_role") != "leader":
            show_alert(cb_id, "❌ فقط رهبر!", True)
            return
        cid = p.get("clan_id")
        if not cid:
            show_alert(cb_id, "❌ کلن نداری!", True)
            return
        if target_uid not in db or db[target_uid].get("clan_id") != cid:
            show_alert(cb_id, "❌ عضو نیست!", True)
            return
        old_leader_name = p.get("name", "کاربر")
        new_leader_name = db[target_uid].get("name", "کاربر")
        db[user_id]["clan_role"] = "member"
        db[target_uid]["clan_role"] = "leader"
        if "clans" in db and cid in db["clans"]:
            db["clans"][cid]["leader_id"] = target_uid
        save_db()
        show_alert(cb_id, f"✅ مالکیت به {new_leader_name} منتقل شد!", True)
        try:
            send_message(int(target_uid),
                f"👑 *شما رهبر جدید کلن شدید!*\n\n"
                f"🏰 کلن: {get_clan_name(cid)}\n"
                f"👤 رهبر قبلی: {old_leader_name}")
        except:
            pass
        for muid, _ in get_clan_members(cid):
            if muid in (user_id, target_uid):
                continue
            try:
                send_message(int(muid),
                    f"👑 رهبر کلن تغییر کرد!\n"
                    f"رهبر جدید: {new_leader_name}")
            except:
                pass
        edit_message(chat_id, msg_id, "👥 کلن:",
                     build_clan_inline_keyboard(user_id))
        return

    if data.startswith("clan_transfer_"):
        target_uid = data.replace("clan_transfer_", "")
        p = db.get(user_id, {})
        if p.get("clan_role") != "leader":
            show_alert(cb_id, "❌ فقط رهبر!", True)
            return
        cid = p.get("clan_id")
        if not cid:
            show_alert(cb_id, "❌ کلن نداری!", True)
            return
        if target_uid not in db or db[target_uid].get("clan_id") != cid:
            show_alert(cb_id, "❌ عضو نیست!", True)
            return
        if target_uid == user_id:
            show_alert(cb_id, "❌ خودت رهبری!", True)
            return
        edit_message(chat_id, msg_id,
            f"👑 *تأیید انتقال مالکیت*\n\n"
            f"👤 رهبر جدید: {db[target_uid].get('name', 'کاربر')}\n\n"
            f"⚠️ *بعد از این، شما فقط عضو عادی هستید!*\n\n"
            f"🔻 مطمئنی؟",
            {"inline_keyboard": [
                [{"text": "✅ بله، انتقال بده",
                  "callback_data": f"clan_transfer_confirm_{target_uid}"}],
                [{"text": "❌ لغو", "callback_data": "clan_back"}],
            ]})
        return

    # ==================== تبادل سکه ====================
    if data == "other_transfer":
        db[user_id]["transfer_action"] = "get_id"
        db[user_id]["transfer_target"] = None
        db[user_id]["transfer_amount"] = None
        save_db()
        edit_message(chat_id, msg_id,
            "💳 تبادل سکه\n\n"
            "👤 آیدی را وارد کنید:",
            {"inline_keyboard": [[{"text": "🔙 بازگشت",
                                   "callback_data": "other_back"}]]})
        return

    if data == "other_back":
        db[user_id]["transfer_action"] = None
        db[user_id]["transfer_target"] = None
        db[user_id]["transfer_amount"] = None
        save_db()
        edit_message(chat_id, msg_id, "📁 سایر:\n\n🔻 یکی:",
                     get_other_inline_keyboard(user_id))
        return

    if data == "transfer_back_id":
        db[user_id]["transfer_action"] = "get_id"
        db[user_id]["transfer_target"] = None
        db[user_id]["transfer_amount"] = None
        save_db()
        edit_message(chat_id, msg_id,
            "💳 تبادل سکه\n\n"
            "👤 آیدی را وارد کنید:",
            {"inline_keyboard": [[{"text": "🔙 بازگشت",
                                   "callback_data": "other_back"}]]})
        return

    if data == "transfer_back_amount":
        tid = db[user_id].get("transfer_target")
        if not tid or tid not in db:
            show_alert(cb_id, "❌ خطا! دوباره شروع کن.", True)
            db[user_id]["transfer_action"] = None
            db[user_id]["transfer_target"] = None
            db[user_id]["transfer_amount"] = None
            save_db()
            return
        db[user_id]["transfer_action"] = "get_amount"
        db[user_id]["transfer_amount"] = None
        save_db()
        limit = SUB_TRANSFER_LIMIT if is_subscription_active(user_id) else 2000
        edit_message(chat_id, msg_id,
            f"💳 تبادل سکه\n\n"
            f"👤 گیرنده: {db[tid].get('name','کاربر')} ({tid})\n"
            f"🪙 موجودی: {db[user_id].get('coins',0):,}\n\n"
            f"💰 میزان سکه مورد نظر برای تبادل را وارد کنید (حداکثر {limit:,}):",
            {"inline_keyboard": [[{"text": "🔙 بازگشت",
                                   "callback_data": "transfer_back_id"}]]})
        return

    if data == "transfer_cancel":
        db[user_id]["transfer_action"] = None
        db[user_id]["transfer_target"] = None
        db[user_id]["transfer_amount"] = None
        save_db()
        edit_message(chat_id, msg_id, "📁 سایر:\n\n🔻 یکی:",
                     get_other_inline_keyboard(user_id))
        return

    if data == "transfer_confirm":
        p = db.get(user_id, {})
        amount = p.get("transfer_amount", 0)
        tid = p.get("transfer_target")
        if not tid or amount <= 0:
            show_alert(cb_id, "❌ خطا!", True)
            return
        if not check_daily_transfer_limit(user_id, amount):
            show_alert(cb_id, "❌ سقف روزانه رد شده!", True)
            return
        if p.get("coins", 0) < amount:
            show_alert(cb_id, "❌ میزان سکه شما کافی نیست!", True)
            return
        db[user_id]["coins"] -= amount
        db[tid]["coins"] = db[tid].get("coins", 0) + amount
        add_daily_transfer(user_id, amount)
        db[user_id]["transfer_action"] = None
        db[user_id]["transfer_target"] = None
        db[user_id]["transfer_amount"] = None
        save_db()
        show_alert(cb_id, f"✅ {amount:,} سکه فرستاده شد!", True)
        try:
            send_message(int(tid),
                f"💳 {amount:,} سکه از {p.get('name','کاربر')} دریافت کردی!")
        except Exception:
            pass
        edit_message(chat_id, msg_id, "📁 سایر:\n\n🔻 یکی:",
                     get_other_inline_keyboard(user_id))
        return

    # ==================== انتقال اکانت ====================
    if data == "transfer_copy":
        from handlers import generate_transfer_token
        token = generate_transfer_token(user_id, user_name)
        edit_message(chat_id, msg_id,
            f"📥 *توکن انتقال اکانت*\n\n"
            f"`{token}`\n\n"
            f"⏱️ اعتبار: 10 دقیقه\n\n"
            f"این کد رو به کسی که می‌خوای اکانتت رو بهش بدی بده.",
            {"inline_keyboard": [[{"text": "🔙 بازگشت",
                                   "callback_data": "go_main"}]]})
        return

    if data == "transfer_enter":
        db[user_id]["transfer_action"] = "enter_token"
        save_db()
        send_message(chat_id, "📤 توکن رو وارد کن:",
            {"inline_keyboard": [[{"text": "❌ لغو",
                                   "callback_data": "transfer_cancel"}]]})
        return

    if data.startswith("confirm_transfer_"):
        tid_t = data.replace("confirm_transfer_", "")
        from handlers import complete_pending_transfer
        complete_pending_transfer(tid_t)
        show_alert(cb_id, "✅ انتقال انجام شد!", True)
        return

    if data.startswith("reject_transfer_"):
        tid_t = data.replace("reject_transfer_", "")
        from handlers import cancel_pending_transfer
        cancel_pending_transfer(tid_t, "rejected")
        show_alert(cb_id, "❌ رد شد", True)
        return

    # ==================== پشتیبانی و سایر ====================
    if data == "support_cancel":
        db[user_id]["support_action"] = None
        save_db()
        edit_message(chat_id, msg_id, "📁 سایر:\n\n🔻 یکی:",
                     get_other_inline_keyboard(user_id))
        return

    if data == "other_support":
        db[user_id]["support_action"] = "ticket"
        save_db()
        send_message(chat_id,
            "🆘 پشتیبانی\n\n📝 پیامت رو بنویس:",
            {"inline_keyboard": [[{"text": "❌ لغو",
                                   "callback_data": "support_cancel"}]]})
        return

    if data == "other_gift":
        now = time.time()
        lg = db[user_id].get("last_gift", 0)
        diff = now - lg
        if diff >= 24 * 3600:
            from handlers import roll_daily_gift, apply_daily_gift_prize
            is_sub = is_subscription_active(user_id)
            prize = roll_daily_gift(is_subscriber=is_sub)
            db[user_id]["last_gift"] = now
            apply_daily_gift_prize(db[user_id], prize)
            save_db()
            show_alert(cb_id, f"🎉 {prize['emoji']} {prize['name']}!", True)
        else:
            from handlers import format_remaining_time
            rem = 24 * 3600 - diff
            show_alert(cb_id, f"⏳ {format_remaining_time(rem)} مونده", True)
        return

    if data == "other_admin":
        if not is_admin(user_id):
            show_alert(cb_id, "❌ دسترسی نداری!", True)
            return
        edit_message(chat_id, msg_id, "🔐 پنل ادمین:",
            {"inline_keyboard": [
                [{"text": "📊 آمار ربات", "callback_data": "admin_stats"}],
                [{"text": "🏵 رنکینگ کلن‌ها", "callback_data": "admin_clan_ranking"}],
                [{"text": "🪙 دادن سکه", "callback_data": "admin_give"},
                 {"text": "🪙 کم کردن سکه", "callback_data": "admin_take_coins"}],
                [{"text": "🎁 دادن پک", "callback_data": "admin_pack"}],
                [{"text": "🚫 مدیریت مسدودیت", "callback_data": "admin_ban"}],
                [{"text": "🔄 ریست رنک همه", "callback_data": "admin_reset"}],
                [{"text": "🔄 ریست لول همه", "callback_data": "admin_reset_levels"}],
                [{"text": "📢 پیام همگانی", "callback_data": "admin_broadcast"}],
            ]})
        return

    # ==================== ادمین ====================
    if data == "admin_stats":
        if not is_admin(user_id):
            show_alert(cb_id, "❌ دسترسی نداری!", True)
            return
        edit_message(chat_id, msg_id, build_admin_stats_text(),
            {"inline_keyboard": [[{"text": "🔙 بازگشت",
                                   "callback_data": "other_admin_back"}]]})
        return

    if data == "admin_clan_ranking":
        if not is_admin(user_id):
            show_alert(cb_id, "❌!", True)
            return
        txt, kb = build_admin_clans_ranking(0)
        if txt:
            edit_message(chat_id, msg_id, txt, kb)
        else:
            show_alert(cb_id, "❌ کلنی نیست!", True)
        return

    if data.startswith("admin_clan_ranking_p_"):
        if not is_admin(user_id):
            show_alert(cb_id, "❌!", True)
            return
        try:
            pg = int(data.replace("admin_clan_ranking_p_", ""))
        except ValueError:
            pg = 0
        txt, kb = build_admin_clans_ranking(pg)
        if txt:
            edit_message(chat_id, msg_id, txt, kb)
        return

    if data == "admin_give":
        if not is_admin(user_id):
            show_alert(cb_id, "❌!", True)
            return
        db[user_id]["admin_action"] = "give_coins"
        save_db()
        send_message(chat_id,
            "🪙 دادن سکه\n\nفرمت: `id amount`\nمثال: `123456789 1000`")
        return

    if data == "admin_take_coins":
        if not is_admin(user_id):
            show_alert(cb_id, "❌!", True)
            return
        db[user_id]["admin_action"] = "take_coins"
        save_db()
        send_message(chat_id,
            "🪙 کم کردن سکه\n\nفرمت: `id amount`")
        return

    if data == "admin_pack":
        if not is_admin(user_id):
            show_alert(cb_id, "❌!", True)
            return
        db[user_id]["admin_action"] = "give_pack"
        save_db()
        send_message(chat_id,
            "🎁 دادن پک\n\nفرمت: `id نوع مقدار`\n"
            "نوع: سکه، نفت، رنک، جم، یا اسم موشک/جنگنده\n"
            "مثال: `123456789 سکه 5000`")
        return

    if data == "admin_ban":
        if not is_admin(user_id):
            show_alert(cb_id, "❌!", True)
            return
        db[user_id]["admin_action"] = "ban_user"
        save_db()
        send_message(chat_id, "🚫 بن کردن کاربر\n\nآیدی عددی:")
        return

    if data == "admin_reset":
        if not is_admin(user_id):
            show_alert(cb_id, "❌!", True)
            return
        for uid, ud in db.items():
            if isinstance(ud, dict) and "user_id" in ud:
                ud["rank"] = 0
                ud["best_rank"] = 0
                ud["rank_today"] = 0
                ud["league"] = "🌱 تازه‌کار"
        save_db()
        show_alert(cb_id, "✅ همه رنک‌ها ریست شدند!", True)
        return

    if data == "admin_reset_levels":
        if not is_admin(user_id):
            show_alert(cb_id, "❌!", True)
            return
        for uid, ud in db.items():
            if isinstance(ud, dict) and "user_id" in ud:
                ud["total_damage"] = 0
        save_db()
        show_alert(cb_id, "✅ همه لول‌ها ریست شدند!", True)
        return

    if data == "admin_broadcast":
        if not is_admin(user_id):
            show_alert(cb_id, "❌!", True)
            return
        db[user_id]["admin_action"] = "broadcast"
        save_db()
        send_message(chat_id, "📢 پیام همگانی:\n\nمتن رو بفرست:")
        return

    # ==================== گاید ====================
    if data.startswith("guide_"):
        key = data.replace("guide_", "")
        guide = GUIDE_TEXT.get(key)
        if not guide:
            show_alert(cb_id, "❌ راهنما موجود نیست!", True)
            return
        from handlers import get_guide_keyboard
        edit_message(chat_id, msg_id, guide, get_guide_keyboard())
        return

    # ==================== Help shortcuts ====================
    if data == "help_shop":
        edit_message(chat_id, msg_id, GUIDE_TEXT["shop"],
            {"inline_keyboard": [[{"text": "🔙 بازگشت",
                                   "callback_data": "shop_back"}]]})
        return
    if data == "help_lab":
        edit_message(chat_id, msg_id, GUIDE_TEXT["lab"],
            {"inline_keyboard": [[{"text": "🔙 بازگشت",
                                   "callback_data": "lab_back"}]]})
        return
    if data == "help_defense":
        edit_message(chat_id, msg_id, GUIDE_TEXT["defense"],
            {"inline_keyboard": [[{"text": "🔙 بازگشت",
                                   "callback_data": "shop_back"}]]})
        return
    if data == "help_wheel":
        edit_message(chat_id, msg_id, GUIDE_TEXT["wheel"],
            {"inline_keyboard": [[{"text": "🔙 بازگشت",
                                   "callback_data": "go_wheel"}]]})
        return
    if data == "help_battle":
        edit_message(chat_id, msg_id, GUIDE_TEXT["battle"],
            {"inline_keyboard": [[{"text": "🔙 بازگشت",
                                   "callback_data": "go_main"}]]})
        return
    if data == "help_airport":
        edit_message(chat_id, msg_id, GUIDE_TEXT["airport"],
            {"inline_keyboard": [[{"text": "🔙 بازگشت",
                                   "callback_data": "go_main"}]]})
        return
    if data == "help_drone":
        edit_message(chat_id, msg_id, GUIDE_TEXT["drone"],
            {"inline_keyboard": [[{"text": "🔙 بازگشت",
                                   "callback_data": "shop_back"}]]})
        return
    if data == "help_arsenal":
        edit_message(chat_id, msg_id, GUIDE_TEXT["arsenal"],
            {"inline_keyboard": [[{"text": "🔙 بازگشت",
                                   "callback_data": "go_main"}]]})
        return
    if data == "help_fighter_base":
        edit_message(chat_id, msg_id, GUIDE_TEXT["fighter_base"],
            {"inline_keyboard": [[{"text": "🔙 بازگشت",
                                   "callback_data": "combo_fighter"}]]})
        return
    if data == "help_military":
        edit_message(chat_id, msg_id, GUIDE_TEXT["military"],
            {"inline_keyboard": [[{"text": "🔙 بازگشت",
                                   "callback_data": "combo_back"}]]})
        return

    # ==================== Box claim ====================
    if data.startswith("claimbox_"):
        box_id = data.replace("claimbox_", "")
        from handlers import claim_box
        ok, msg, winner = claim_box(user_id, box_id)
        if not ok:
            if winner:
                show_alert(cb_id, f"❌ {msg}\nبرنده: {winner}", True)
            else:
                show_alert(cb_id, msg, True)
        else:
            show_alert(cb_id, f"🎉 برنده شدی!\n{msg}", True)
        return

    # ==================== Fallback ====================
    print(f"⚠️ Unhandled callback: {data!r}")
    show_alert(cb_id, "⚠️ این دکمه منقضی شده یا نامعتبر است.", False)


# ==================== کمک‌کننده‌های گردونه ====================
def _apply_wheel_prize(user_id, prize):
    t = prize.get("type")
    if t == "coins":
        db[user_id]["coins"] = db[user_id].get("coins", 0) + prize.get("amount", 0)
    elif t == "oil":
        db[user_id]["oil"] = db[user_id].get("oil", 0) + prize.get("amount", 0)
    elif t == "weapon":
        cat = prize.get("category", "cruise")
        wn = prize.get("weapon")
        if cat not in db[user_id]:
            db[user_id][cat] = {}
        if wn not in db[user_id][cat]:
            db[user_id][cat][wn] = {"count": 0, "level": 1}
        db[user_id][cat][wn]["count"] += prize.get("amount", 0)
    elif t == "defense":
        dname = prize.get("defense")
        if "defense" not in db[user_id]:
            db[user_id]["defense"] = {}
        if dname not in db[user_id]["defense"]:
            db[user_id]["defense"][dname] = {"count": 0}
        db[user_id]["defense"][dname]["count"] += prize.get("amount", 0)
    elif t == "fighter":
        fname = prize.get("fighter")
        if "fighters_hero" not in db[user_id]:
            db[user_id]["fighters_hero"] = {}
        fdata = HERO_FIGHTERS.get(fname, {})
        if fname not in db[user_id]["fighters_hero"]:
            db[user_id]["fighters_hero"][fname] = {
                "count": 0,
                "hp_current": fdata.get("hp", 50),
                "level": 1,
            }
        db[user_id]["fighters_hero"][fname]["count"] += prize.get("amount", 0)


def _wheel_menu_route(data, chat_id, msg_id, user_id):
    routes = {
        "wheel_legendary": build_wheel_legendary_menu,
        "wheel_storm": build_wheel_storm_menu,
        "wheel_hunt": build_wheel_hunt_menu,
        "wheel_fire": build_wheel_fire_menu,
        "wheel_dragon": build_wheel_dragon_menu,
        "wheel_fighter": build_wheel_fighter_menu,
        "wheel_luck": build_wheel_luck_menu,
    }
    fn = routes.get(data)
    if fn:
        txt, kb = fn(user_id)
        edit_message(chat_id, msg_id, txt, kb)


def _wheel_spin(user_id, cb_id, chat_id, msg_id, n, price1, price10,
                spin_fn, result_fn, back_cb):
    cost = price10 if n == 10 else price1
    p = db.get(user_id, {})
    if p.get("coins", 0) < cost:
        show_alert(cb_id, f"❌ به {cost:,} سکه نیاز داری!", True)
        return
    db[user_id]["coins"] -= cost
    prizes = [spin_fn() for _ in range(n)]
    for pr in prizes:
        _apply_wheel_prize(user_id, pr)
    save_db()
    txt, kb = result_fn(user_id, prizes)
    edit_message(chat_id, msg_id, txt, kb)