import time
import requests
import random
from datetime import datetime
from config import *
from core import (db, save_db, save_db_now, send_message, edit_message,
                  send_photo, show_alert, is_admin, create_user, check_membership,
                  send_join_message, check_daily_transfer_limit,
                  add_daily_transfer, is_subscription_active,
                  send_invoice)
from data import *
from builders import *
from handlers import (calculate_combo_attack, build_invite_page,
                      handle_invite_start, get_combo_menu,
                      get_guide_keyboard, get_other_inline_keyboard,
                      get_other_keyboard, get_buildings_keyboard,
                      get_buildings_text, generate_transfer_token,
                      check_transfer_token, create_pending_transfer,
                      complete_pending_transfer, cancel_pending_transfer,
                      send_ticket_to_admins, give_pack,
                      reply_keyboard, inline_keyboard,
                      gap_inline_keyboard, channel_inline_keyboard,
                      talisman_keyboard, buy_keyboard,
                      roll_daily_gift, apply_daily_gift_prize,
                      format_remaining_time, apply_rank_change)


def build_attack_loot_section(stolen_c, stolen_o, had_coins, had_oil, target):
    """بخش نمودار غارت رنگارنگ برای حمله عادی"""
    text = ""
    text += "📊 *نمودار غارت*\n"
    text += "━━━━━━━━━━━━━━━━━\n"

    text += "🪙 *سکه*\n"
    if had_coins <= 0:
        text += "⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜  0%\n"
        text += "❌ مدافع سکه‌ای نداشت\n\n"
    else:
        bar, pct = make_loot_chart(stolen_c, had_coins)
        text += f"{bar}  {pct}%\n"
        text += f"📦 {stolen_c:,} از {had_coins:,}\n\n"

    text += "🛢 *نفت*\n"
    if target.get("refinery_level", 0) <= 0:
        text += "⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜  0%\n"
        text += "❌ پالایشگاه ندارد\n"
    elif had_oil <= 0:
        text += "⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜  0%\n"
        text += "❌ مدافع نفتی نداشت\n"
    else:
        bar, pct = make_loot_chart(stolen_o, had_oil)
        text += f"{bar}  {pct}%\n"
        text += f"📦 {stolen_o:,} از {had_oil:,}\n"

    text += "━━━━━━━━━━━━━━━━━\n\n"
    return text


def find_missile_category(missile_name):
    data = MISSILES.get(missile_name)
    if data:
        return data["category"]
    return None


def handle_message(update):
    message = update["message"]
    chat_id = message["chat"]["id"]
    user_id = str(message.get("from", {}).get("id", 0))
    text = message.get("text", "")
    user_name = message.get("from", {}).get("first_name", "کاربر")
    chat_type = message.get("chat", {}).get("type", "private")

    if text:
        text = text.replace("\uFE0F", "")

    # 🆕 ذخیره خودکار گروه‌ها برای باکس شانسی
    if chat_type in ["group", "supergroup"]:
        if "known_groups" not in db:
            db["known_groups"] = {}
        gid = str(chat_id)
        if gid not in db["known_groups"]:
            db["known_groups"][gid] = {
                "title": message.get("chat", {}).get("title", "گروه"),
                "added_at": time.time(),
            }
            save_db()

    if user_id not in db or not isinstance(db.get(user_id), dict):
        create_user(user_id, user_name)
    elif db[user_id].get("name") != user_name:
        db[user_id]["name"] = user_name
        save_db()

    if db[user_id].get("banned"):
        return

    db[user_id]["last_active"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if chat_type in ["group", "supergroup"]:
        is_attack = (text.startswith("حمله ")
                     or text == "حمله ترکیبی"
                     or text.startswith("حمله ترکیبی "))
        is_guide = text in ("راهنما", "راهنمای بازی") or text.lower() == "/help"
        if not (is_attack or is_guide):
            return

    # ==================== /start ====================
    if text.lower().startswith("/start"):
        is_member, _ = check_membership(user_id)
        if not is_member:
            send_join_message(chat_id)
            return

        if "invite_" in text:
            try:
                inviter = text.split("invite_")[1].strip().split()[0]
                if handle_invite_start(user_id, inviter, user_name):
                    send_message(chat_id,
                        "🎉 تبریک!\n\n🪙 500 سکه هدیه گرفتی!")
                    try:
                        send_message(int(inviter),
                            f"🎁 یه نفر با لینک دعوتت اومد!\n"
                            f"👤 {user_name}\n🪙 +2000 سکه")
                    except:
                        pass
            except Exception as e:
                print(f"خطای دعوت: {e}")

        send_message(chat_id,
            f"⚜️WORLD WAR⚜️\nخوش اومدی {user_name}\n"
            f"🔥 اینجا میدان جنگه 🔥\n"
            f"⚔️ بجنگ غارت کن افسانه شو ⚔️\n"
            f"از دکمه های پایین استفاده کن👇",
            reply_markup=inline_keyboard)
        send_message(chat_id, "🔻 منوی اصلی:", reply_markup=reply_keyboard)
        return

    # ==================== /transfer ====================
    if text.lower() == "/transfer":
        send_message(chat_id,
            "📥 انتقال اکانت\n\n⚠️ تمام اطلاعات اکانت منتقل می‌شود\n\n"
            "🔻 یکی:",
            {"inline_keyboard": [
                [{"text": "📥 دریافت توکن",
                  "callback_data": "transfer_copy"}],
                [{"text": "📤 وارد کردن توکن",
                  "callback_data": "transfer_enter"}],
                [{"text": "❌ لغو", "callback_data": "go_main"}],
            ]})
        return

    # ==================== /invite ====================
    if text.lower() == "/invite":
        t, k = build_invite_page(user_id)
        send_message(chat_id, t, reply_markup=k)
        return

    # ==================== /help ====================
    if text in ["❓ راهنما", "❓️ راهنما", "راهنما", "راهنمای بازی"] \
            or text.lower() == "/help":
        send_message(chat_id, "📖 راهنما\n\n🔻 یکی از بخش‌ها:",
                     reply_markup=get_guide_keyboard())
        return

    # ==================== دکمه‌های اصلی ====================
    if text == "🪪 دارایی":
        send_message(chat_id, build_profile(chat_id, user_name),
            {"inline_keyboard": [[{"text": "🔢 کپی کردن آیدی",
                                   "copy_text": {"text": str(user_id)}}]]})
        return

    if text == "🏦 منابع":
        send_message(chat_id, build_resources_text(user_id),
                     reply_markup=build_resources_keyboard())
        return

    if text == "🪙 معدن سکه":
        update_mine_coins(user_id)
        send_message(chat_id, build_mine_text(user_id),
                     reply_markup=build_mine_keyboard())
        return

    if text == "🏭 پالایشگاه":
        p = db.get(user_id, {})
        if p.get("refinery_level", 0) == 0:
            send_message(chat_id,
                "🏭 پالایشگاه\n\n❌ ندارید!\n🪙 10,000 سکه\n"
                "🎯 لول 10\n\n🔻 خرید:",
                {"inline_keyboard": [
                    [{"text": "🛒 خرید", "callback_data": "refinery_buy"}],
                    [{"text": "🔙", "callback_data": "go_main"}],
                ]})
        else:
            update_refinery_oil(user_id)
            send_message(chat_id, build_refinery_text(user_id),
                         reply_markup=build_refinery_keyboard())
        return

    if text == "🏭 کارخانه":
        update_factory_iron(user_id)
        update_factory_steel(user_id)
        update_factory_weapon(user_id)
        send_message(chat_id, build_factory_text(user_id),
                     reply_markup=build_factory_keyboard())
        return

    if text == "🧪 آزمایشگاه":
        send_message(chat_id, build_lab_text(user_id),
                     reply_markup=build_lab_keyboard(user_id))
        return

    if text == "🔮 طلسم":
        send_message(chat_id, build_talisman_text(user_id),
                     reply_markup=build_talisman_inline_keyboard(user_id))
        return

    if text == "🏪 فروشگاه":
        shop_text = build_shop_text(user_id)
        shop_kb = build_shop_keyboard()

        # Inline menus are edited as text; keep the decorative photo separate.
        if SHOP_PHOTO:
            send_photo(chat_id, SHOP_PHOTO)
        send_message(chat_id, shop_text, reply_markup=shop_kb)
        return

    if text in ["🛒 World Shop", "World Shop", "world shop"]:
        send_message(chat_id, build_world_pass_text(user_id),
                     reply_markup=build_world_pass_keyboard(user_id))
        return

    # ==================== 💳 خرید آیتم ====================
    if text == "💳 خرید آیتم":
        send_message(chat_id, build_item_shop_text(),
                     reply_markup=build_item_shop_keyboard())
        return

    if text == "🎰 گردونه":
        send_message(chat_id, "🎰 گردونه شانس\n\n🔻 یکی:",
                     reply_markup=build_wheel_keyboard())
        return

    if text == "📊 رنکینگ":
        update_rank_today()
        t, k = build_players_ranking(0, my_user_id=user_id)
        send_message(chat_id, t, reply_markup=k)
        return

    if text in ["📁 سایر", "🗄 سایر", "🗂 سایر"]:
        send_message(chat_id, "📁 سایر:\n\n🔻 یکی:",
                     reply_markup=get_other_inline_keyboard(user_id))
        return

    if text in ["📛 گپ رسمی", "💬 گپ رسمی"]:
        send_message(chat_id, "📛 گپ رسمی:",
                     reply_markup=gap_inline_keyboard)
        return
    if text in ["📢 کانال رسمی", "📣 کانال رسمی"]:
        send_message(chat_id, "📢 کانال رسمی:",
                     reply_markup=channel_inline_keyboard)
        return

    if text == "👥 کلن":
        p = db.get(user_id, {})
        if p.get("clan_id"):
            cid = p["clan_id"]
            clan_name = get_clan_name(cid)
            members = get_clan_members(cid)
            total_rank = get_clan_rank_points(cid)
            text_clan = (f"👥 کلن شما: {clan_name}\n\n"
                         f"📝 آیدی کلن: {cid}\n"
                         f"👥 اعضا: {len(members)}/{CLAN_MAX_MEMBERS}\n"
                         f"🏆 رنک کلن: {total_rank:,}\n\n"
                         f"🔻 از دکمه‌ها استفاده کن:")
            send_message(chat_id, text_clan,
                         reply_markup=build_clan_inline_keyboard(user_id))
        else:
            send_message(chat_id, "👥 کلن\n\n❌ کلن ندارید!",
                         reply_markup=build_clan_inline_keyboard(user_id))
        return

    if text == "🌐 حمله جهانی":
        send_message(chat_id, build_battle_text(user_id),
                     reply_markup=build_battle_keyboard())
        return

    if text in ["🎯 ترکیب نظامی", "🎯 مدیریت ترکیب"]:
        send_message(chat_id, "🎯 ترکیب نظامی\n\n🔻 یکی:",
                     reply_markup=get_combo_menu(user_id))
        return

    # ==================== 🎁 جایزه روزانه ====================
    if text == "🎁 جایزه روزانه":
        now = time.time()
        lg = db[user_id].get("last_gift", 0)
        diff = now - lg

        if diff >= 24 * 3600:
            is_sub = is_subscription_active(user_id)
            prize = roll_daily_gift(is_subscriber=is_sub)
            db[user_id]["last_gift"] = now
            apply_daily_gift_prize(db[user_id], prize)
            save_db()

            balance_line = ""
            if prize["type"] == "coins":
                balance_line = f"🪙 موجودی سکه: *{db[user_id].get('coins', 0):,}*"
            elif prize["type"] == "gems":
                balance_line = f"💎 موجودی الماس: *{db[user_id].get('gems', 0):,}*"
            elif prize["type"] == "weapon":
                wn = prize["weapon"]
                cat = prize["category"]
                cnt = db[user_id].get(cat, {}).get(wn, {}).get("count", 0)
                balance_line = f"📦 تعداد {wn}: *{cnt:,}*"

            sub_badge = " ⭐️" if is_sub else ""
            msg = (
                f"🎁✨ *جایزه روزانه*{sub_badge} ✨🎁\n"
                "━━━━━━━━━━━━━━━━━\n"
                "🎉 *تبریک!* جایزه امروزت:\n\n"
                f"   {prize['emoji']} *{prize['name']}*\n\n"
                f"✅ به داراییت اضافه شد!\n"
                f"{balance_line}\n"
                "━━━━━━━━━━━━━━━━━\n"
                "⏰ جایزه بعدی: *۲۴ ساعت* دیگه\n"
                "🔔 سر ساعت بیا و جایت رو بگیر!"
            )
            send_message(chat_id, msg)
        else:
            rem = 24 * 3600 - diff
            time_str = format_remaining_time(rem)
            msg = (
                "⏳ *جایزه روزانه بعدی*\n"
                "━━━━━━━━━━━━━━━━━\n"
                f"🕒 *{time_str}* مونده\n"
                "━━━━━━━━━━━━━━━━━\n"
                "💡 سر ساعت بیا و جایت رو بگیر!\n"
                "🎁 جایزه‌های خفن منتظرته"
            )
            send_message(chat_id, msg)
        return

    if text == "🛩 فرودگاه":
        air_text = build_airport_text(user_id)
        air_kb = build_airport_keyboard(user_id)

        if AIRPORT_PHOTO:
            result = send_photo(chat_id, AIRPORT_PHOTO, caption=air_text, reply_markup=air_kb)
            if not result.get("ok"):
                send_message(chat_id, air_text, reply_markup=air_kb)
        else:
            send_message(chat_id, air_text, reply_markup=air_kb)
        return

    if text == "💥 تسلیحات":
        send_message(chat_id, build_weapons_house_text(user_id),
                     reply_markup=build_weapons_house_keyboard(user_id))
        return

    if text in ["🆘 پشتیبانی", "📞 پشتیبانی"]:
        db[user_id]["support_action"] = "ticket"
        save_db()
        send_message(chat_id,
            "📤 ارسال پیام به پشتیبانی\n\n📝 پیامت رو بنویس:",
            {"inline_keyboard": [[{"text": "❌ لغو",
                                   "callback_data": "support_cancel"}]]})
        return

    if text in ["📞 پیوی مدیریت", "📞 پیوی مالک"]:
        send_message(chat_id,
            f"📞 برای ارتباط با مدیریت:\n@{SUPPORT_ID}",
            {"inline_keyboard": [[{"text": "💬 پیوی مالک",
                                   "url": f"https://ble.ir/{SUPPORT_ID}"}]]})
        return

    if text == "🔙 بازگشت":
        send_message(chat_id, "🔻 منوی اصلی:",
                     reply_markup=reply_keyboard)
        return

    if text == "🔐 پنل ادمین" and is_admin(user_id):
        send_message(chat_id, "🔐 پنل ادمین:",
            {"inline_keyboard": [
                [{"text": "📊 آمار ربات", "callback_data": "admin_stats"}],
                [{"text": "🏵 رنکینگ کلن‌ها", "callback_data": "admin_clan_ranking"}],
                [{"text": "🪙 دادن سکه", "callback_data": "admin_give"},
                 {"text": "🪙 کم کردن سکه", "callback_data": "admin_take_coins"}],
                [{"text": "🎁 دادن پک", "callback_data": "admin_pack"}],
                [{"text": "🚫 مدیریت مسدودیت", "callback_data": "admin_ban"}],
                [{"text": "🔄 ریست رنک همه", "callback_data": "admin_reset"}],
                [{"text": "🔄 ریست لول و تجربه همه",
                  "callback_data": "admin_reset_levels"}],
                [{"text": "📢 پیام همگانی",
                  "callback_data": "admin_broadcast"}],
            ]})
        return

    # ==================== 💳 خرید آیتم — گرفتن تعداد ====================
    if db[user_id].get("selected_item_pack"):
        key = db[user_id]["selected_item_pack"]

        if text.strip() in ("❌ لغو", "/cancel"):
            db[user_id]["selected_item_pack"] = None
            save_db()
            send_message(chat_id, "❌ لغو شد", reply_markup=reply_keyboard)
            return

        try:
            qty = int(text.strip())
            if qty <= 0:
                raise ValueError
        except:
            send_message(chat_id, "❌ یه عدد مثبت بفرست!",
                {"inline_keyboard": [[{"text": "❌ لغو",
                                       "callback_data": "item_buy_cancel"}]]})
            return

        pack = ITEM_PACKS.get(key)
        if not pack:
            db[user_id]["selected_item_pack"] = None
            save_db()
            return

        if qty < pack["min_qty"] or qty > pack["max_qty"]:
            send_message(chat_id,
                f"❌ مقدار باید بین {pack['min_qty']} و {pack['max_qty']} باشه!",
                {"inline_keyboard": [[{"text": "❌ لغو",
                                       "callback_data": "item_buy_cancel"}]]})
            return

        total_toman = pack["price_per_unit"] * qty
        total_rial = total_toman * 10
        reward = pack["reward_per_unit"] * qty

        payload = f"item_{key}_{qty}_{user_id}_{int(time.time())}"

        db[user_id]["selected_item_pack"] = None
        db[user_id]["item_buy_pending_invoice"] = time.time()
        save_db()

        res = send_invoice(
            chat_id=chat_id,
            title=f"{pack['emoji']} {pack['name']}",
            description=(f"{qty} × {pack['unit_name']}  |  "
                         f"جایزه: {reward:,} {pack['reward_name']}"),
            payload=payload,
            amount=total_rial,
            currency="IRR",
        )
        if not res.get("ok"):
            # 🆕 اگه فاکتور ساخته نشد، pending رو پاک کن
            db[user_id]["item_buy_pending_invoice"] = 0
            save_db()
            send_message(chat_id,
                "❌ خطا در ساخت فاکتور. لطفاً دوباره تلاش کن.",
                reply_markup=reply_keyboard)
        return

    # ==================== تبادل سکه (از بخش سایر) ====================
    if db[user_id].get("transfer_action") == "get_id":
        tid = text.strip()
        if not tid.isdigit():
            send_message(chat_id, "❌ آیدی باید عدد باشه!",
                {"inline_keyboard": [[{"text": "🔙 بازگشت",
                                       "callback_data": "other_back"}]]})
            return
        if tid == user_id:
            send_message(chat_id, "❌ نمی‌تونی به خودت سکه بفرستی!",
                {"inline_keyboard": [[{"text": "🔙 بازگشت",
                                       "callback_data": "other_back"}]]})
            return
        if tid not in db or not isinstance(db.get(tid), dict):
            send_message(chat_id, "❌ کاربر پیدا نشد!",
                {"inline_keyboard": [[{"text": "🔙 بازگشت",
                                       "callback_data": "other_back"}]]})
            return
        db[user_id]["transfer_target"] = tid
        db[user_id]["transfer_action"] = "get_amount"
        save_db()
        limit = SUB_TRANSFER_LIMIT if is_subscription_active(user_id) else 2000
        send_message(chat_id,
            f"💳 تبادل سکه\n\n"
            f"👤 گیرنده: {db[tid].get('name','کاربر')} ({tid})\n"
            f"🪙 موجودی: {db[user_id].get('coins',0):,}\n\n"
            f"💰 میزان سکه مورد نظر برای تبادل را وارد کنید (حداکثر {limit:,}):",
            {"inline_keyboard": [
                [{"text": "🔙 بازگشت", "callback_data": "transfer_back_id"}],
            ]})
        return

    if db[user_id].get("transfer_action") == "get_amount":
        try:
            amount = int(text.strip())
        except:
            send_message(chat_id, "❌ یه عدد بفرست!",
                {"inline_keyboard": [[{"text": "🔙 بازگشت",
                                       "callback_data": "transfer_back_id"}]]})
            return
        if amount <= 0:
            send_message(chat_id, "❌ مقدار باید مثبت باشه!",
                {"inline_keyboard": [[{"text": "🔙 بازگشت",
                                       "callback_data": "transfer_back_id"}]]})
            return

        limit = SUB_TRANSFER_LIMIT if is_subscription_active(user_id) else 2000
        if amount > limit:
            send_message(chat_id, f"❌ حداکثر {limit:,} سکه!",
                {"inline_keyboard": [[{"text": "🔙 بازگشت",
                                       "callback_data": "transfer_back_id"}]]})
            return

        if db[user_id].get("coins", 0) < amount:
            send_message(chat_id,
                f"❌ میزان سکه شما کافی نیست!\n\n"
                f"🪙 موجودی شما: {db[user_id].get('coins',0):,}\n"
                f"💰 درخواست: {amount:,}\n\n"
                f"🔻 دوباره امتحان کن:",
                {"inline_keyboard": [[{"text": "🔙 بازگشت",
                                       "callback_data": "transfer_back_id"}]]})
            return

        tid = db[user_id].get("transfer_target")
        if not tid or tid not in db:
            send_message(chat_id, "❌ خطا! دوباره شروع کن.",
                {"inline_keyboard": [[{"text": "🔙 بازگشت",
                                       "callback_data": "other_back"}]]})
            db[user_id]["transfer_action"] = None
            save_db()
            return

        db[user_id]["transfer_amount"] = amount
        db[user_id]["transfer_action"] = "confirm"
        save_db()
        send_message(chat_id,
            f"🪙 تأیید تبادل\n\n"
            f"👤 {db[user_id].get('name','کاربر')} → "
            f"{db[tid].get('name','کاربر')}\n"
            f"🪙 {amount:,} سکه\n\n🔻 مطمئنی؟",
            {"inline_keyboard": [
                [{"text": "✅ تأیید", "callback_data": "transfer_confirm"}],
                [{"text": "🔙 بازگشت", "callback_data": "transfer_back_amount"}],
            ]})
        return

    # انتقال اکانت (توکن)
    if db[user_id].get("transfer_action") == "enter_token":
        token = text.strip()
        info, status = check_transfer_token(token)
        if status == "no_tokens":
            send_message(chat_id, "❌ توکنی نیست!")
        elif status == "invalid":
            send_message(chat_id, "❌ توکن نامعتبر!")
        elif status == "expired":
            send_message(chat_id, "❌ توکن منقضی شده!")
        else:
            old_id = info["user_id"]
            old_name = info["user_name"]
            if old_id == user_id:
                send_message(chat_id, "❌ خودت!")
            else:
                tid = create_pending_transfer(old_id, old_name, user_id,
                                              user_name, token)
                send_message(chat_id,
                    "⏳ در انتظار تأیید صاحب اکانت...\n"
                    "اگه 10 دقیقه بگذره لغو می‌شه.")
                try:
                    send_message(int(old_id),
                        f"⚠️ درخواست انتقال اکانت\n\n"
                        f"کاربر {user_name} قصد داره اکانتت رو منتقل کنه\n\n"
                        f"⏱️ 10 دقیقه",
                        {"inline_keyboard": [
                            [{"text": "✅ تأیید",
                              "callback_data": f"confirm_transfer_{tid}"}],
                            [{"text": "❌ رد",
                              "callback_data": f"reject_transfer_{tid}"}],
                        ]})
                except:
                    pass
        db[user_id]["transfer_action"] = None
        save_db()
        return

    # ==================== طلسم ====================
    if db[user_id].get("selected_talisman"):
        key = db[user_id]["selected_talisman"]
        if text == "❌ لغو":
            db[user_id]["selected_talisman"] = None
            save_db()
            send_message(chat_id, "❌ لغو شد.", reply_markup=reply_keyboard)
            return
        try:
            cnt = int(text.strip())
        except:
            send_message(chat_id, "❌ یه عدد بفرست.")
            return
        if cnt <= 0:
            send_message(chat_id, "❌ عدد مثبت باشه!")
            db[user_id]["selected_talisman"] = None
            save_db()
            return
        if key not in TALISMAN_INFO:
            db[user_id]["selected_talisman"] = None
            save_db()
            send_message(chat_id, "❌ طلسم نامعتبر!")
            return
        info = TALISMAN_INFO[key]
        current = db[user_id].get(info["count_key"], 0)
        if current + cnt > 20:
            send_message(chat_id,
                f"❌ حداکثر 20 عدد!\n📦 الان داری: {current}")
            db[user_id]["selected_talisman"] = None
            save_db()
            return
        total_cost = info["price"] * cnt
        if info["currency"] == "coins":
            if db[user_id].get("coins", 0) < total_cost:
                send_message(chat_id, f"❌ به {total_cost:,} سکه نیاز داری!")
                db[user_id]["selected_talisman"] = None
                save_db()
                return
            db[user_id]["coins"] -= total_cost
            balance_txt = f"🪙 سکه باقی‌مونده: {db[user_id]['coins']:,}"
        else:
            if db[user_id].get("oil", 0) < total_cost:
                send_message(chat_id, f"❌ به {total_cost:,} نفت نیاز داری!")
                db[user_id]["selected_talisman"] = None
                save_db()
                return
            db[user_id]["oil"] -= total_cost
            balance_txt = f"🛢 نفت باقی‌مونده: {db[user_id]['oil']:,}"
        db[user_id][info["count_key"]] = current + cnt
        save_db()
        send_message(chat_id,
            f"✅ {cnt:,} عدد {info['emoji']} طلسم {info['name']} خریداری شد!\n\n"
            f"{balance_txt}\n"
            f"📦 تعداد کل: {db[user_id][info['count_key']]:,}/20",
            reply_markup=reply_keyboard)
        db[user_id]["selected_talisman"] = None
        save_db()
        return

    # ==================== پدافند ====================
    if db[user_id].get("selected_defense"):
        name = db[user_id]["selected_defense"]
        if text == "❌ لغو":
            db[user_id]["selected_defense"] = None
            save_db()
            send_message(chat_id, "❌ لغو شد.", reply_markup=reply_keyboard)
            return
        try:
            cnt = int(text.strip())
        except:
            send_message(chat_id, "❌ یه عدد بفرست.")
            return
        if cnt <= 0:
            send_message(chat_id, "❌ عدد مثبت باشه!")
            db[user_id]["selected_defense"] = None
            save_db()
            return
        if name not in DEFENSES:
            db[user_id]["selected_defense"] = None
            save_db()
            send_message(chat_id, "❌ پدافند نامعتبر!")
            return
        info = DEFENSES[name]
        total_cost = info["price"] * cnt
        if db[user_id].get("coins", 0) < total_cost:
            send_message(chat_id, f"❌ به {total_cost:,} سکه نیاز داری!")
            db[user_id]["selected_defense"] = None
            save_db()
            return
        db[user_id]["coins"] -= total_cost
        if "defense" not in db[user_id]:
            db[user_id]["defense"] = {}
        if name not in db[user_id]["defense"]:
            db[user_id]["defense"][name] = {"count": 0}
        db[user_id]["defense"][name]["count"] += cnt
        if not db[user_id].get("active_defense"):
            db[user_id]["active_defense"] = name
        save_db()
        emoji = get_defense_emoji(name)
        send_message(chat_id,
            f"✅ {cnt:,} عدد {emoji} {name} خریداری شد!\n\n"
            f"🪙 سکه باقی‌مونده: {db[user_id].get('coins', 0):,}\n"
            f"📦 تعداد کل {name}: {db[user_id]['defense'][name]['count']:,}",
            reply_markup=reply_keyboard)
        db[user_id]["selected_defense"] = None
        save_db()
        return

    if db[user_id].get("tal_action"):
        action = db[user_id]["tal_action"]
        try:
            cnt = int(text.strip())
        except:
            send_message(chat_id, "❌ یه عدد بفرست.")
            return
        if cnt <= 0:
            send_message(chat_id, "❌ عدد مثبت باشه!")
            db[user_id]["tal_action"] = None
            save_db()
            return
        cost = cnt * 200
        if db[user_id].get("coins", 0) < cost:
            send_message(chat_id, f"❌ {cost} سکه لازمه.")
        else:
            if action == "buy_money":
                cur = db[user_id].get("talisman_money_count", 0)
                if cur + cnt > 20:
                    send_message(chat_id, f"❌ حداکثر 20! الان {cur}")
                else:
                    db[user_id]["coins"] -= cost
                    db[user_id]["talisman_money_count"] = cur + cnt
                    if db[user_id].get("talisman_money", 0) == 0:
                        db[user_id]["talisman_money"] = 1
                    save_db()
                    send_message(chat_id,
                                 f"✅ {cnt} طلسم پول خریداری شد!")
            elif action == "buy_damage":
                cur = db[user_id].get("talisman_damage_count", 0)
                if cur + cnt > 20:
                    send_message(chat_id, "❌ حداکثر 20!")
                else:
                    db[user_id]["coins"] -= cost
                    db[user_id]["talisman_damage_count"] = cur + cnt
                    if db[user_id].get("talisman_damage", 0) == 0:
                        db[user_id]["talisman_damage"] = 1
                    save_db()
                    send_message(chat_id,
                                 f"✅ {cnt} طلسم دمیج خریداری شد!")
            elif action == "buy_rank":
                cur = db[user_id].get("talisman_rank_count", 0)
                if cur + cnt > 20:
                    send_message(chat_id, "❌ حداکثر 20!")
                else:
                    db[user_id]["coins"] -= cost
                    db[user_id]["talisman_rank_count"] = cur + cnt
                    if db[user_id].get("talisman_rank", 0) == 0:
                        db[user_id]["talisman_rank"] = 1
                    save_db()
                    send_message(chat_id,
                                 f"✅ {cnt} طلسم رنک خریداری شد!")
        db[user_id]["tal_action"] = None
        save_db()
        send_message(chat_id, build_talisman_text(user_id),
                     reply_markup=build_talisman_inline_keyboard(user_id))
        return

    # ==================== خرید موشک ====================
    if db[user_id].get("selected_missile"):
        mn = db[user_id].get("selected_missile")
        if text == "❌ لغو":
            db[user_id]["selected_missile"] = None
            save_db()
            send_message(chat_id, "❌ لغو شد.", reply_markup=reply_keyboard)
            return
        try:
            cnt = int(text)
        except:
            send_message(chat_id, "❌ یه عدد بفرست.")
            return
        if cnt <= 0:
            send_message(chat_id, "❌ عدد مثبت باشه!")
            db[user_id]["selected_missile"] = None
            save_db()
            return

        if mn not in MISSILES:
            send_message(chat_id, "❌ موشک نامعتبر!")
            db[user_id]["selected_missile"] = None
            save_db()
            return

        data_m = MISSILES[mn]
        req = data_m["level"]
        price = data_m["price"]
        gem_cost = data_m.get("gems", 0)
        cat = data_m["category"]

        ulvl, _, _ = get_level_info(db[user_id].get("total_damage", 0))
        if ulvl < req:
            send_message(chat_id,
                f"❌ برای «{mn}» باید سطح {req} باشی!\n"
                f"سطح تو: {ulvl}")
            db[user_id]["selected_missile"] = None
            save_db()
            return

        total_coin = price * cnt
        total_gem = gem_cost * cnt

        is_sub = is_subscription_active(user_id)
        if is_sub:
            total_coin = int(total_coin * (100 - SUB_DISCOUNT_MISSILE) / 100)

        if db[user_id].get("coins", 0) < total_coin:
            send_message(chat_id, f"❌ به {total_coin:,} سکه نیاز داری.")
            db[user_id]["selected_missile"] = None
            save_db()
            return

        if total_gem > 0 and db[user_id].get("gems", 0) < total_gem:
            send_message(chat_id, f"❌ به {total_gem} الماس هم نیاز داری.")
            db[user_id]["selected_missile"] = None
            save_db()
            return

        wh_lvl = db[user_id].get("weapons_house_level", 1)
        if wh_lvl > 5:
            wh_lvl = 5
        max_cap = ARSENAL_CAPACITIES[wh_lvl].get(cat, 0)

        current_count = sum(m.get("count", 0)
                            for m in db[user_id].get(cat, {}).values())

        if current_count + cnt > max_cap:
            cat_name_map = {"cruise": "کروز", "ballistic": "بالستیک",
                            "hypersonic": "هایپرسونیک",
                            "chemical": "شیمیایی", "nuclear": "هسته‌ای"}
            send_message(chat_id,
                f"❌ ظرفیت تسلیحات خانه کافی نیست!\n\n"
                f"📊 بخش: **{cat_name_map.get(cat, cat)}**\n"
                f"📦 ظرفیت فعلی: {current_count:,}/{max_cap:,}\n"
                f"🔢 درخواست خرید: {cnt:,} عدد\n\n"
                f"💡 برای خرید موشک بیشتر، ابتدا از منوی «💥 تسلیحات» "
                f"تسلیحات خانه را ارتقا دهید.")
            db[user_id]["selected_missile"] = None
            save_db()
            return

        db[user_id]["coins"] -= total_coin
        if total_gem > 0:
            db[user_id]["gems"] -= total_gem

        if cat not in db[user_id]:
            db[user_id][cat] = {}
        if mn not in db[user_id][cat]:
            db[user_id][cat][mn] = {"count": 0, "level": 1}
        db[user_id][cat][mn]["count"] += cnt
        save_db()
        emoji = data_m["emoji"]
        gem_txt = f" و {total_gem}💎" if total_gem > 0 else ""
        sub_txt = f"\n⭐️ {SUB_DISCOUNT_MISSILE}٪ تخفیف اشتراک اعمال شد!" if is_sub else ""
        send_message(chat_id,
            f"✅ {cnt} عدد {emoji} {mn} خریداری شد!\n"
            f"🪙 سکه‌ات: {db[user_id]['coins']:,}{gem_txt}{sub_txt}",
            reply_markup=reply_keyboard)
        db[user_id]["selected_missile"] = None
        save_db()
        return

    # ==================== خرید پهباد ====================
    if db[user_id].get("selected_drone"):
        d_name = db[user_id]["selected_drone"]
        if text == "❌ لغو":
            db[user_id]["selected_drone"] = None
            save_db()
            send_message(chat_id, "❌ لغو شد.", reply_markup=reply_keyboard)
            return
        try:
            cnt = int(text.strip())
        except:
            send_message(chat_id, "❌ یه عدد بفرست.")
            return
        if cnt <= 0:
            send_message(chat_id, "❌ عدد مثبت باشه!")
            db[user_id]["selected_drone"] = None
            save_db()
            return
        if d_name not in DRONES:
            db[user_id]["selected_drone"] = None
            save_db()
            send_message(chat_id, "❌ پهباد نامعتبر!")
            return

        price = DRONES[d_name]["price"]
        total_cost = price * cnt

        if db[user_id].get("coins", 0) < total_cost:
            send_message(chat_id, f"❌ به {total_cost:,} سکه نیاز داری!")
            db[user_id]["selected_drone"] = None
            save_db()
            return

        db[user_id]["coins"] -= total_cost
        if "drones" not in db[user_id]:
            db[user_id]["drones"] = {}
        if d_name not in db[user_id]["drones"]:
            db[user_id]["drones"][d_name] = {"count": 0, "level": 1}
        db[user_id]["drones"][d_name]["count"] += cnt
        save_db()

        send_message(chat_id,
            f"✅ {cnt:,} عدد {d_name} خریداری شد!\n"
            f"🪙 سکه باقی‌مونده: {db[user_id]['coins']:,}",
            reply_markup=reply_keyboard)
        db[user_id]["selected_drone"] = None
        save_db()
        return

    # ==================== ترکیب نظامی ====================
    if db[user_id].get("combo_action") == "get_name":
        nm = text.strip()
        if len(nm) < 2:
            send_message(chat_id, "❌ حداقل 2 حرف!",
                {"inline_keyboard": [[{"text": "❌ لغو",
                                       "callback_data": "combo_back"}]]})
            return
        if "combos" not in db[user_id]:
            db[user_id]["combos"] = {}
        db[user_id]["combos"][nm] = {"name": nm, "weapons": []}
        db[user_id]["combo_action"] = None
        save_db()
        send_message(chat_id, f"✅ ترکیب «{nm}» ساخته شد!",
            {"inline_keyboard": [
                [{"text": "✏️ ویرایش",
                  "callback_data": f"combo_edit_{nm}"}],
                [{"text": "🔙", "callback_data": "combo_back"}],
            ]})
        return

    if (db[user_id].get("combo_action") or "").startswith("add_weapon_"):
        cn = db[user_id]["combo_action"].replace("add_weapon_", "")
        parts = text.strip().split()
        if len(parts) < 2:
            send_message(chat_id, "❌ فرمت: نام تعداد",
                {"inline_keyboard": [[{"text": "🔙",
                                       "callback_data": f"combo_edit_{cn}"}]]})
            return
        wn = " ".join(parts[:-1])
        try:
            cnt = int(parts[-1])
        except:
            send_message(chat_id, "❌ تعداد عدد باشه!",
                {"inline_keyboard": [[{"text": "🔙",
                                       "callback_data": f"combo_edit_{cn}"}]]})
            return

        if is_wheel_only(wn):
            send_message(chat_id,
                "❌ موشک‌های گردونه فقط در حمله عادی قابل استفاده هستند!",
                {"inline_keyboard": [[{"text": "🔙",
                                       "callback_data": f"combo_edit_{cn}"}]]})
            return

        p = db.get(user_id, {})
        fnd = False
        wcat = None
        for c in ["cruise", "ballistic", "hypersonic", "chemical",
                  "nuclear", "drones", "fighters", "defense"]:
            if wn in p.get(c, {}):
                fnd = True
                wcat = c
                break
        if not fnd:
            send_message(chat_id, f"❌ «{wn}» رو نداری!",
                {"inline_keyboard": [[{"text": "🔙",
                                       "callback_data": f"combo_edit_{cn}"}]]})
            return
        spc = WEAPON_SPACE.get(wcat, 1) * cnt
        cap = get_arsenal_capacity(p)
        used = get_used_space(p)
        if used + spc > cap:
            send_message(chat_id,
                f"❌ ظرفیت زرادخانه کافی نیست! ({used}+{spc} > {cap})\n"
                f"💡 برای افزایش ظرفیت، از منوی «🎯 مدیریت ترکیب → 🏰 زرادخانه» استفاده کن.",
                {"inline_keyboard": [[{"text": "🔙",
                                       "callback_data": f"combo_edit_{cn}"}]]})
            return
        if cn not in db[user_id].get("combos", {}):
            db[user_id]["combos"][cn] = {"name": cn, "weapons": []}
        wl = db[user_id]["combos"][cn].get("weapons", [])
        ex = next((w for w in wl if w.get("name") == wn), None)
        if ex:
            ex["count"] = ex.get("count", 0) + cnt
        else:
            wl.append({"name": wn, "count": cnt, "category": wcat})
        db[user_id]["combos"][cn]["weapons"] = wl
        db[user_id]["combo_action"] = None
        save_db()
        send_message(chat_id, f"✅ {cnt} عدد «{wn}» اضافه شد!",
            {"inline_keyboard": [[{"text": "🔙",
                                   "callback_data": f"combo_edit_{cn}"}]]})
        return

    if db[user_id].get("combo_remove_action"):
        action = db[user_id]["combo_remove_action"]
        cn = action["cn"]
        wn = action["wn"]
        try:
            cnt = int(text.strip())
        except:
            send_message(chat_id, "❌ یه عدد بفرست!",
                {"inline_keyboard": [[{"text": "🔙",
                                       "callback_data": f"combo_remove_{cn}"}]]})
            return
        if cnt <= 0:
            send_message(chat_id, "❌ مثبت باشه!",
                {"inline_keyboard": [[{"text": "🔙",
                                       "callback_data": f"combo_remove_{cn}"}]]})
            return
        p = db.get(user_id, {})
        combos = p.get("combos", {})
        if cn not in combos:
            db[user_id]["combo_remove_action"] = None
            save_db()
            send_message(chat_id, "❌ پیدا نشد!")
            return
        ws = combos[cn].get("weapons", [])
        target = next((w for w in ws if w.get("name") == wn), None)
        if not target:
            db[user_id]["combo_remove_action"] = None
            save_db()
            send_message(chat_id, f"❌ «{wn}» نیست!")
            return
        cur = target.get("count", 0)
        if cnt >= cur:
            target["count"] = 0
            send_message(chat_id, f"✅ «{wn}» کلاً حذف شد!")
        else:
            target["count"] = cur - cnt
            send_message(chat_id,
                         f"✅ {cnt} عدد کم شد! الان: {target['count']}")
        db[user_id]["combo_remove_action"] = None
        save_db()
        return

    # ==================== کلن ====================
    if db[user_id].get("clan_action") == "buy_clan":
        clan_name = text.strip()
        if len(clan_name) < 3:
            send_message(chat_id, "❌ حداقل 3 حرف!")
            return
        exists = any(isinstance(d, dict) and d.get("clan") == clan_name
                     for d in db.values())
        if exists:
            send_message(chat_id, "❌ این اسم گرفته شده!")
            return
        cost = 4000
        if db[user_id].get("coins", 0) < cost:
            send_message(chat_id, f"❌ {cost} سکه لازمه!")
            return
        new_cid = generate_clan_id()
        db[user_id]["coins"] -= cost
        db[user_id]["clan"] = clan_name
        db[user_id]["clan_id"] = new_cid
        db[user_id]["clan_role"] = "leader"
        db[user_id]["clan_action"] = None
        if "clans" not in db:
            db["clans"] = {}
        db["clans"][new_cid] = {"name": clan_name, "rank_points": 0,
                                "leader_id": user_id,
                                "created_at": time.time(),
                                "level": 1,
                                "donated_coins": 0}
        save_db()
        send_message(chat_id,
            f"✅ کلن «{clan_name}» ساخته شد!\n"
            f"📝 آیدی: {new_cid}\n👑 شما رهبر هستید.")
        send_message(chat_id, f"👥 کلن شما: {clan_name}",
                     reply_markup=build_clan_inline_keyboard(user_id))
        return

    if db[user_id].get("clan_action") == "edit_clan_name":
        new_name = text.strip()
        if len(new_name) < 3:
            send_message(chat_id, "❌ حداقل 3 حرف!")
            db[user_id]["clan_action"] = None
            save_db()
            return
        p = db.get(user_id, {})
        cid = p.get("clan_id")
        if not cid:
            send_message(chat_id, "❌ کلن نداری!")
            db[user_id]["clan_action"] = None
            save_db()
            return
        cost = 1000
        if db[user_id].get("coins", 0) < cost:
            send_message(chat_id, f"❌ {cost} سکه لازمه!")
            db[user_id]["clan_action"] = None
            save_db()
            return
        exists = any(isinstance(d, dict) and d.get("clan_id") != cid
                     and d.get("clan") == new_name for d in db.values())
        if exists:
            send_message(chat_id, "❌ گرفته شده!")
            db[user_id]["clan_action"] = None
            save_db()
            return
        old = get_clan_name(cid)
        db[user_id]["coins"] -= cost
        for uid, d in db.items():
            if isinstance(d, dict) and d.get("clan_id") == cid:
                d["clan"] = new_name
        if "clans" in db and cid in db["clans"]:
            db["clans"][cid]["name"] = new_name
        db[user_id]["clan_action"] = None
        save_db()
        send_message(chat_id,
                     f"✅ از «{old}» به «{new_name}» تغییر کرد!")
        return

    if db[user_id].get("clan_action") == "broadcast":
        p = db.get(user_id, {})
        cid = p.get("clan_id")
        if not cid:
            send_message(chat_id, "❌ کلن نداری!")
            db[user_id]["clan_action"] = None
            save_db()
            return
        members = get_clan_members(cid)
        count = 0
        for uid, _ in members:
            if uid == user_id:
                continue
            try:
                send_message(int(uid), f"📢 پیام کلن:\n\n{text}")
                count += 1
            except:
                pass
        db[user_id]["clan_action"] = None
        save_db()
        send_message(chat_id, f"✅ به {count} عضو ارسال شد!")
        return

    if db[user_id].get("clan_action") == "donate_coins":
        if text.strip() == "/cancel":
            db[user_id]["clan_action"] = None
            save_db()
            send_message(chat_id, "❌ لغو شد.", reply_markup=reply_keyboard)
            return
        try:
            amt = int(text.strip())
        except:
            send_message(chat_id, "❌ یه عدد بفرست!\n(یا /cancel برای لغو)")
            return
        from clan_war import donate_to_clan
        ok, msg = donate_to_clan(user_id, amt)
        db[user_id]["clan_action"] = None
        save_db()
        send_message(chat_id, msg, reply_markup=reply_keyboard)
        return

    if db[user_id].get("clan_action") == "transfer_leadership":
        p = db.get(user_id, {})
        if p.get("clan_role") != "leader":
            send_message(chat_id, "❌ فقط رهبر می‌تونه انتقال بده!")
            db[user_id]["clan_action"] = None
            save_db()
            return
        cid = p.get("clan_id")
        if not cid:
            send_message(chat_id, "❌ کلن نداری!")
            db[user_id]["clan_action"] = None
            save_db()
            return
        if text.strip() == "/cancel":
            db[user_id]["clan_action"] = None
            save_db()
            send_message(chat_id, "❌ لغو شد.", reply_markup=reply_keyboard)
            return
        new_leader_id = text.strip()
        if not new_leader_id.isdigit():
            send_message(chat_id, "❌ آیدی باید عدد باشه!\n(یا /cancel)")
            return
        if new_leader_id == user_id:
            send_message(chat_id, "❌ خودت رهبری!")
            return
        if new_leader_id not in db or not isinstance(db.get(new_leader_id), dict):
            send_message(chat_id, "❌ کاربر پیدا نشد!")
            return
        if db[new_leader_id].get("clan_id") != cid:
            send_message(chat_id, "❌ این کاربر عضو کلن تو نیست!")
            return
        old_leader_name = p.get("name", "کاربر")
        new_leader_name = db[new_leader_id].get("name", "کاربر")
        db[user_id]["clan_role"] = "member"
        db[new_leader_id]["clan_role"] = "leader"
        if "clans" in db and cid in db["clans"]:
            db["clans"][cid]["leader_id"] = new_leader_id
        db[user_id]["clan_action"] = None
        save_db()
        send_message(chat_id,
            f"👑 مالکیت کلن به {new_leader_name} منتقل شد!\n\n"
            f"اکنون شما عضو عادی هستید.",
            reply_markup=build_clan_inline_keyboard(user_id))
        try:
            send_message(int(new_leader_id),
                f"👑 *شما رهبر جدید کلن شدید!*\n\n"
                f"🏰 کلن: {get_clan_name(cid)}\n"
                f"👤 رهبر قبلی: {old_leader_name}",
                {"inline_keyboard": [[
                    {"text": "⚙️ مدیریت کلن", "callback_data": "clan_manage"}
                ]]})
        except:
            pass
        for muid, _ in get_clan_members(cid):
            if muid in (user_id, new_leader_id):
                continue
            try:
                send_message(int(muid),
                    f"👑 رهبر کلن تغییر کرد!\n\n"
                    f"رهبر جدید: {new_leader_name}")
            except:
                pass
        return

    if db[user_id].get("clan_action") == "invite_member":
        p = db.get(user_id, {})
        if p.get("clan_role") not in ("leader", "officer"):
            send_message(chat_id, "❌ فقط رهبر یا افسر!")
            db[user_id]["clan_action"] = None
            save_db()
            return
        cid = p.get("clan_id")
        if not cid:
            send_message(chat_id, "❌ کلن نداری!")
            db[user_id]["clan_action"] = None
            save_db()
            return
        if text.strip() == "/cancel":
            db[user_id]["clan_action"] = None
            save_db()
            send_message(chat_id, "❌ لغو شد.", reply_markup=reply_keyboard)
            return
        target_id = text.strip()
        if not target_id.isdigit():
            send_message(chat_id, "❌ آیدی باید عدد باشه!\n(یا /cancel)")
            return
        if target_id == user_id:
            send_message(chat_id, "❌ خودت!")
            return
        if target_id not in db or not isinstance(db.get(target_id), dict):
            send_message(chat_id, "❌ کاربر پیدا نشد!")
            return
        if db[target_id].get("clan_id"):
            send_message(chat_id,
                f"❌ {db[target_id].get('name','کاربر')} قبلاً عضو یه کلنه!")
            return
        members = get_clan_members(cid)
        if len(members) >= CLAN_MAX_MEMBERS and cid != OFFICIAL_CLAN_ID:
            send_message(chat_id, f"❌ کلن پر است! ({len(members)}/{CLAN_MAX_MEMBERS})")
            return
        if "clan_invites" not in db:
            db["clan_invites"] = {}
        inv_id = f"INV{int(time.time())}{random.randint(100, 999)}"
        db["clan_invites"][inv_id] = {
            "clan_id": cid,
            "inviter_id": user_id,
            "inviter_name": p.get("name", "کاربر"),
            "target_id": target_id,
            "created_at": time.time(),
            "expires_at": time.time() + 3600,
        }
        db[user_id]["clan_action"] = None
        save_db()
        send_message(chat_id,
            f"✅ دعوت برای {db[target_id].get('name','کاربر')} فرستاده شد!\n"
            f"⏱️ اعتبار: ۱ ساعت",
            reply_markup=reply_keyboard)
        try:
            send_message(int(target_id),
                f"📩 *دعوت به کلن*\n\n"
                f"🏰 کلن: {get_clan_name(cid)}\n"
                f"👤 دعوت‌کننده: {p.get('name', 'کاربر')}\n"
                f"👥 اعضا: {len(members)}/{CLAN_MAX_MEMBERS}\n"
                f"⏱️ اعتبار: ۱ ساعت",
                {"inline_keyboard": [
                    [{"text": "✅ قبول دعوت",
                      "callback_data": f"clan_inv_accept_{inv_id}"}],
                    [{"text": "❌ رد", "callback_data": f"clan_inv_reject_{inv_id}"}],
                ]})
        except:
            pass
        return

    if db[user_id].get("clan_action") == "request_join":
        target_cid = db[user_id].get("clan_join_target")
        if not target_cid:
            db[user_id]["clan_action"] = None
            save_db()
            return
        p = db.get(user_id, {})
        if p.get("clan_id"):
            send_message(chat_id, "❌ تو قبلاً عضو یه کلنی!")
            db[user_id]["clan_action"] = None
            db[user_id]["clan_join_target"] = None
            save_db()
            return
        members = get_clan_members(target_cid)
        if len(members) >= CLAN_MAX_MEMBERS and target_cid != OFFICIAL_CLAN_ID:
            send_message(chat_id, "❌ کلن پر است!")
            db[user_id]["clan_action"] = None
            db[user_id]["clan_join_target"] = None
            save_db()
            return
        if "clan_requests" not in db:
            db["clan_requests"] = {}
        for rid, req in db["clan_requests"].items():
            if (req.get("user_id") == user_id
                    and req.get("clan_id") == target_cid
                    and req.get("status") == "pending"):
                send_message(chat_id, "⏳ قبلاً درخواست دادی! منتظر بمون.")
                db[user_id]["clan_action"] = None
                db[user_id]["clan_join_target"] = None
                save_db()
                return
        req_id = f"REQ{int(time.time())}{random.randint(100, 999)}"
        db["clan_requests"][req_id] = {
            "clan_id": target_cid,
            "user_id": user_id,
            "user_name": p.get("name", "کاربر"),
            "created_at": time.time(),
            "status": "pending",
        }
        db[user_id]["clan_action"] = None
        db[user_id]["clan_join_target"] = None
        save_db()
        send_message(chat_id,
            f"✅ درخواست عضویت به «{get_clan_name(target_cid)}» ارسال شد!\n"
            f"⏳ منتظر تأیید رهبر باش.",
            reply_markup=reply_keyboard)
        leader_id = None
        if "clans" in db and target_cid in db["clans"]:
            leader_id = db["clans"][target_cid].get("leader_id")
        if not leader_id:
            for uid, d in db.items():
                if (isinstance(d, dict)
                        and d.get("clan_id") == target_cid
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

    if db[user_id].get("clan_action") == "kick_member":
        p = db.get(user_id, {})
        if p.get("clan_role") != "leader":
            send_message(chat_id, "❌ فقط رهبر!")
            db[user_id]["clan_action"] = None
            save_db()
            return
        cid = p.get("clan_id")
        if not cid:
            db[user_id]["clan_action"] = None
            save_db()
            return
        if text.strip() == "/cancel":
            db[user_id]["clan_action"] = None
            save_db()
            send_message(chat_id, "❌ لغو شد.", reply_markup=reply_keyboard)
            return
        target_id = text.strip()
        if not target_id.isdigit():
            send_message(chat_id, "❌ آیدی باید عدد باشه!\n(یا /cancel)")
            return
        if target_id == user_id:
            send_message(chat_id, "❌ خودت رهبری! برای خروج، کلن رو حذف کن.")
            return
        if target_id not in db or not isinstance(db.get(target_id), dict):
            send_message(chat_id, "❌ کاربر پیدا نشد!")
            return
        if db[target_id].get("clan_id") != cid:
            send_message(chat_id, "❌ این کاربر عضو کلن تو نیست!")
            return
        kicked_name = db[target_id].get("name", "کاربر")
        db[target_id]["clan_id"] = None
        db[target_id]["clan"] = None
        db[target_id]["clan_role"] = None
        db[user_id]["clan_action"] = None
        save_db()
        send_message(chat_id,
            f"🚪 {kicked_name} از کلن اخراج شد!",
            reply_markup=reply_keyboard)
        try:
            send_message(int(target_id),
                f"🚪 شما از کلن «{get_clan_name(cid)}» اخراج شدید!")
        except:
            pass
        return

    if db[user_id].get("clan_action") == "promote_member":
        p = db.get(user_id, {})
        if p.get("clan_role") != "leader":
            send_message(chat_id, "❌ فقط رهبر!")
            db[user_id]["clan_action"] = None
            save_db()
            return
        cid = p.get("clan_id")
        if not cid:
            db[user_id]["clan_action"] = None
            save_db()
            return
        if text.strip() == "/cancel":
            db[user_id]["clan_action"] = None
            save_db()
            send_message(chat_id, "❌ لغو شد.", reply_markup=reply_keyboard)
            return
        target_id = text.strip()
        if not target_id.isdigit():
            send_message(chat_id, "❌ آیدی باید عدد باشه!\n(یا /cancel)")
            return
        if target_id == user_id:
            send_message(chat_id, "❌ خودت رهبری!")
            return
        if target_id not in db or not isinstance(db.get(target_id), dict):
            send_message(chat_id, "❌ کاربر پیدا نشد!")
            return
        if db[target_id].get("clan_id") != cid:
            send_message(chat_id, "❌ عضو کلن تو نیست!")
            return
        if db[target_id].get("clan_role") == "leader":
            send_message(chat_id, "❌ رهبره!")
            return
        if db[target_id].get("clan_role") == "officer":
            send_message(chat_id, "❌ قبلاً افسره!")
            return
        target_name = db[target_id].get("name", "کاربر")
        db[target_id]["clan_role"] = "officer"
        db[user_id]["clan_action"] = None
        save_db()
        send_message(chat_id,
            f"⬆️ {target_name} به افسر ارتقا یافت!",
            reply_markup=reply_keyboard)
        try:
            send_message(int(target_id),
                f"⬆️ شما به افسر کلن «{get_clan_name(cid)}» ارتقا یافتید!\n\n"
                f"اکنون می‌توانید به اعضا پیام بدهید و اعضای جدید دعوت کنید.")
        except:
            pass
        return

    if db[user_id].get("clan_action") == "demote_member":
        p = db.get(user_id, {})
        if p.get("clan_role") != "leader":
            send_message(chat_id, "❌ فقط رهبر!")
            db[user_id]["clan_action"] = None
            save_db()
            return
        cid = p.get("clan_id")
        if not cid:
            db[user_id]["clan_action"] = None
            save_db()
            return
        if text.strip() == "/cancel":
            db[user_id]["clan_action"] = None
            save_db()
            send_message(chat_id, "❌ لغو شد.", reply_markup=reply_keyboard)
            return
        target_id = text.strip()
        if not target_id.isdigit():
            send_message(chat_id, "❌ آیدی باید عدد باشه!\n(یا /cancel)")
            return
        if target_id not in db or not isinstance(db.get(target_id), dict):
            send_message(chat_id, "❌ کاربر پیدا نشد!")
            return
        if db[target_id].get("clan_id") != cid:
            send_message(chat_id, "❌ عضو کلن تو نیست!")
            return
        if db[target_id].get("clan_role") != "officer":
            send_message(chat_id, "❌ افسر نیست!")
            return
        target_name = db[target_id].get("name", "کاربر")
        db[target_id]["clan_role"] = "member"
        db[user_id]["clan_action"] = None
        save_db()
        send_message(chat_id,
            f"⬇️ {target_name} به عضو عادی تنزل یافت!",
            reply_markup=reply_keyboard)
        try:
            send_message(int(target_id),
                f"⬇️ شما از افسری به عضو عادی کلن تنزل یافتید.")
        except:
            pass
        return

    # ==================== پنل ادمین ====================
    if is_admin(user_id) and db[user_id].get("admin_action") == "give_coins":
        parts = text.split()
        if len(parts) == 2:
            try:
                tid = parts[0]
                amount = int(parts[1])
                if tid in db and isinstance(db[tid], dict):
                    db[tid]["coins"] = db[tid].get("coins", 0) + amount
                    save_db()
                    send_message(chat_id,
                        f"✅ {amount} سکه به {db[tid]['name']} داده شد!")
                    send_message(int(tid),
                                 f"🎁 {amount} سکه از طرف ادمین!")
                else:
                    send_message(chat_id, "❌ کاربر نیست!")
            except:
                send_message(chat_id, "❌ فرمت: id amount")
        db[user_id]["admin_action"] = None
        save_db()
        return

    if is_admin(user_id) and db[user_id].get("admin_action") == "take_coins":
        parts = text.split()
        if len(parts) == 2:
            try:
                tid = parts[0]
                amount = int(parts[1])
                if amount <= 0:
                    send_message(chat_id, "❌ مقدار باید مثبت باشه!")
                elif tid in db and isinstance(db[tid], dict):
                    cur = db[tid].get("coins", 0)
                    if cur < amount:
                        send_message(chat_id,
                            f"❌ کاربر «{db[tid].get('name','کاربر')}» فقط {cur:,} سکه داره!\n"
                            f"نمی‌تونی {amount:,} تا ازش کم کنی.")
                    else:
                        db[tid]["coins"] = cur - amount
                        save_db()
                        send_message(chat_id,
                            f"✅ {amount:,} سکه از «{db[tid]['name']}» کم شد!\n\n"
                            f"🪙 موجودی قبلی: {cur:,}\n"
                            f"🪙 موجودی جدید: {db[tid]['coins']:,}")
                        try:
                            send_message(int(tid),
                                f"⚠️ {amount:,} سکه از طرف ادمین ازت کم شد!\n\n"
                                f"🪙 موجودی جدید: {db[tid]['coins']:,}")
                        except:
                            pass
                else:
                    send_message(chat_id, "❌ کاربر پیدا نشد!")
            except:
                send_message(chat_id, "❌ فرمت اشتباه!\nفرمت: `ایدی مقدار`")
        else:
            send_message(chat_id, "❌ فرمت اشتباه!\nفرمت: `ایدی مقدار`")
        db[user_id]["admin_action"] = None
        save_db()
        return

    if is_admin(user_id) and db[user_id].get("admin_action") == "give_pack":
        parts = text.split()
        if len(parts) == 3:
            tid = parts[0]
            ptype = parts[1]
            try:
                amount = int(parts[2])
                res = give_pack(user_id, tid, ptype, amount)
                send_message(chat_id, res)
            except Exception as e:
                send_message(chat_id, f"❌ خطا: {e}")
        else:
            send_message(chat_id, "❌ فرمت: id نوع مقدار")
        db[user_id]["admin_action"] = None
        save_db()
        return

    if is_admin(user_id) and db[user_id].get("admin_action") == "ban_user":
        tid = text.strip()
        if tid in db and isinstance(db[tid], dict):
            db[tid]["banned"] = True
            save_db()
            send_message(chat_id, f"🚫 {db[tid]['name']} بن شد!")
            try:
                send_message(int(tid), "🚫 توسط ادمین بن شدید!")
            except:
                pass
        else:
            send_message(chat_id, "❌ کاربر نیست!")
        db[user_id]["admin_action"] = None
        save_db()
        return

    if is_admin(user_id) and db[user_id].get("admin_action") == "unban_user":
        tid = text.strip()
        if tid in db and isinstance(db[tid], dict):
            db[tid]["banned"] = False
            save_db()
            send_message(chat_id,
                         f"✅ {db[tid]['name']} رفع مسدودیت شد!")
            try:
                send_message(int(tid), "✅ رفع مسدودیت شدید!")
            except:
                pass
        else:
            send_message(chat_id, "❌ کاربر نیست!")
        db[user_id]["admin_action"] = None
        save_db()
        return

    if is_admin(user_id) and db[user_id].get("admin_action") == "broadcast":
        count = 0
        for uid, d in db.items():
            if isinstance(d, dict) and not d.get("banned"):
                try:
                    send_message(int(uid), f"📢 پیام ادمین:\n\n{text}")
                    count += 1
                    time.sleep(0.5)
                except:
                    pass
        db[user_id]["admin_action"] = None
        save_db()
        send_message(chat_id, f"✅ به {count} کاربر ارسال شد!")
        return

    # ==================== پشتیبانی ====================
    if db[user_id].get("support_action") == "ticket":
        if chat_type != "private":
            return
        if len(text.strip()) < 5:
            send_message(chat_id, "❌ پیام خیلی کوتاهه!")
            return
        send_ticket_to_admins(user_id,
                              db[user_id].get("name", "کاربر"),
                              text.strip())
        db[user_id]["support_action"] = None
        save_db_now()
        send_message(chat_id, "✅ پیام به پشتیبانی ارسال شد!",
            {"inline_keyboard": [[{"text": "🔙",
                                   "callback_data": "go_main"}]]})
        return

    # ==================== battle_action (حمله عادی خصوصی) ====================
    if db[user_id].get("battle_action"):
        action = db[user_id].get("battle_action")
        target_id = db[user_id].get("battle_target")

        if text == "❌ لغو":
            db[user_id]["battle_action"] = None
            save_db()
            send_message(chat_id, "❌ لغو شد.", reply_markup=reply_keyboard)
            return

        if db[user_id].get("paralyzed_until", 0) > time.time():
            rem = int(db[user_id]["paralyzed_until"] - time.time())
            send_message(chat_id, f"⛔️ شما فلج هستید! ({rem} ثانیه دیگر صبر کنید)")
            return

        target_time = db[user_id].get("battle_target_time", 0)
        now_check = time.time()

        if not target_id or target_id not in db:
            send_message(chat_id,
                "❌ *حریفی وجود نداره!*\n\n"
                "💡 هنوز بازیکن دیگه‌ای تو لیگت نیست.",
                {"inline_keyboard": [
                    [{"text": "🔙 بازگشت به منوی اصلی",
                      "callback_data": "go_main"}],
                ]})
            db[user_id]["battle_action"] = None
            save_db()
            return

        if now_check - target_time > 180:
            send_message(chat_id,
                "⏳ *زمان تموم شد!*\n\n"
                "💡 ۳ دقیقه فرصت داشتی. دوباره امتحان کن:",
                {"inline_keyboard": [
                    [{"text": "⚔️ حمله موشکی", "callback_data": "battle_attack"}],
                    [{"text": "🚀 حمله ترکیبی", "callback_data": "battle_combo_start"}],
                    [{"text": "🔙 بازگشت به منوی اصلی", "callback_data": "go_main"}],
                ]})
            db[user_id]["battle_action"] = None
            save_db()
            return

        use_talismans = []
        weapon_parts = []
        valid_tal_mans = {
            "چشم": "talisman_eye_count",
            "آتش": "talisman_fire_count",
            "طوفان": "talisman_storm_count",
            "صاعقه": "talisman_lightning_count",
            "شکار": "talisman_hunt_count",
            "یخ": "talisman_ice_count"
        }
        for w in text.strip().split():
            if w in valid_tal_mans:
                use_talismans.append(w)
            else:
                weapon_parts.append(w)
        weapon_name = " ".join(weapon_parts)

        if len(use_talismans) > 1:
            missing = [t for t in use_talismans if db[user_id].get(valid_tal_mans[t], 0) <= 0]
            if missing:
                send_message(chat_id, f"❌ شما طلسم {'، '.join(missing)} ندارید!")
            else:
                send_message(chat_id, "❌ حداکثر استفاده از طلسم در هر حمله 1 عدد است!")
            return
        elif len(use_talismans) == 1:
            t_name = use_talismans[0]
            if db[user_id].get(valid_tal_mans[t_name], 0) <= 0:
                send_message(chat_id, f"❌ شما طلسم {t_name} ندارید!")
                return

        is_drone = weapon_name in DRONES

        if not is_drone and weapon_name not in MISSILES:
            send_message(chat_id, "❌ نام موشک اشتباه است!")
            return

        if not is_drone:
            weapon_found = None
            weapon_category = None
            for cat in ["cruise", "ballistic", "hypersonic",
                        "chemical", "nuclear", "drones", "fighters"]:
                if weapon_name in db[user_id].get(cat, {}):
                    weapon_found = db[user_id][cat][weapon_name]
                    weapon_category = cat
                    break

            if not weapon_found:
                send_message(chat_id, "❌ این موشک در لیست دارایی شما نیست!")
                return

            cur = db[user_id][weapon_category][weapon_name].get("count", 0)
            new = max(0, cur - 1)
            if new <= 0:
                del db[user_id][weapon_category][weapon_name]
                if not db[user_id][weapon_category]:
                    db[user_id][weapon_category] = {}
            else:
                db[user_id][weapon_category][weapon_name]["count"] = new

        target = db[target_id]
        m_level = 1
        if not is_drone:
            m_level = weapon_found.get("level", 1)
            damage = get_missile_damage(weapon_name, m_level, weapon_category)
        else:
            d_info = DRONES[weapon_name]
            m_level = db[user_id].get("drones", {}).get(weapon_name, {}).get("level", 1)
            damage = int((d_info["price"] / 2) * (1 + (m_level - 1) * 0.2))
            weapon_category = "drones"

        bypass_defense = False
        tal_msgs = []

        for tal_name in use_talismans:
            tal_key = None
            for k, v in TALISMAN_INFO.items():
                if v["name"] == tal_name:
                    tal_key = k
                    break
            if not tal_key: continue

            count_key = TALISMAN_INFO[tal_key]["count_key"]
            db[user_id][count_key] -= 1

            if tal_key == "eye":
                if random.randint(1, 100) <= 25:
                    bypass_defense = True
                    tal_msgs.append("🧿 چشم: پدافند نادیده گرفته شد!")
                else:
                    tal_msgs.append("🧿 چشم: فعال نشد.")
            elif tal_key == "fire":
                damage = int(damage * 1.2)
                tal_msgs.append("🔥 آتش: ۲۰٪ دمیج بیشتر")
            elif tal_key == "storm":
                if not is_drone and weapon_category in db[user_id] and weapon_name in db[user_id][weapon_category]:
                    if db[user_id][weapon_category][weapon_name].get("count", 0) >= 2:
                        db[user_id][weapon_category][weapon_name]["count"] -= 2
                        extra_dmg = get_missile_damage(weapon_name, m_level, weapon_category) * 2
                        damage += extra_dmg
                        tal_msgs.append("🌪 طوفان: ۲ موشک اضافه شلیک شد")
                    else:
                        tal_msgs.append("🌪 طوفان: موشک کافی نداشتی")
                else:
                    tal_msgs.append("🌪 طوفان: موشک نداشتی")
            elif tal_key == "hunt":
                damage = int(damage * 1.4)
                tal_msgs.append("👁 شکار: ۴۰٪ دمیج بیشتر")
            elif tal_key == "lightning":
                db[target_id]["paralyzed_until"] = time.time() + 60
                tal_msgs.append("⚡ صاعقه: حریف ۶۰ ثانیه فلج شد")
            elif tal_key == "ice":
                db[target_id]["paralyzed_until"] = time.time() + 30
                tal_msgs.append("❄️ یخ: حریف ۳۰ ثانیه فلج شد")

        if is_drone:
            d_info = DRONES[weapon_name]
            base_c = int(d_info["price"] * 0.3 * m_level)
            base_o = int(base_c / 2)
            base_r = int(d_info["price"] * 0.1 * m_level)

            if d_info["effect"] == "rank": base_r = int(base_r * d_info["value"])
            elif d_info["effect"] == "coins": base_c = int(base_c * d_info["value"])
            elif d_info["effect"] == "defense": bypass_defense = True
        else:
            base_c = get_loot_coins(weapon_name, m_level)
            base_o = get_loot_oil(weapon_name, m_level)
            base_r = get_loot_rank(weapon_name, m_level)

        want_c = base_c
        want_o = base_o
        want_r = base_r

        from handlers_callback import apply_defense_block_to_attack
        defense_result = apply_defense_block_to_attack(
            user_id, target_id, target,
            weapon_name, weapon_category, m_level,
            damage, want_c, want_o, want_r)

        if bypass_defense:
            defense_result["blocked"] = False
            defense_result["guardian_reduce"] = 0
            defense_result["damage"] = damage

        target_coins_before = target.get("coins", 0)
        target_oil_before = target.get("oil", 0)
        target_rank_before = target.get("rank", 0)

        if defense_result["blocked"]:
            db[user_id]["battle_action"] = None
            db[user_id]["last_battle_attack"] = time.time()
            save_db()

            a_name = db[user_id].get("name", "کاربر")
            t_name = target.get("name", "کاربر")
            a_league = get_league(db[user_id].get("rank", 0))
            t_league = get_league(target.get("rank", 0))

            title = "🛩️🛡 *حمله پهبادی دفع شد!*" if is_drone else "🚀🛡 *حمله موشکی دفع شد!*"

            block_msg = (
                f"{title}\n\n"
                f"👤 مهاجم: {a_name} ({a_league})\n"
                f"🛡️ مدافع: {t_name} ({t_league})\n\n"
                f"🚀 سلاح: *{weapon_name}*\n"
                f"⚡ پدافند فعال: *{defense_result['defense_name']}*\n"
                f"🎯 شانس بلاک: *{defense_result['block_chance']}%*\n"
                f"💥 دمیج واردشده: *0*\n"
                f"🪙 غارت: *0*\n"
                f"🏅 رنک: *بدون تغییر*\n\n"
                f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            send_message(chat_id, block_msg)
            send_message(chat_id, "🔻 منوی حمله:",
                         reply_markup=build_battle_keyboard())

            try:
                send_message(int(target_id),
                    f"🛡 *حمله دفع شد!*\n\n"
                    f"👤 مهاجم: {a_name}\n"
                    f"🚀 سلاح: {weapon_name}\n"
                    f"⚡ پدافند: {defense_result['defense_name']}",
                    {"inline_keyboard": [[
                        {"text": "⚔️ انتقام",
                         "callback_data": f"revenge_{user_id}"}
                    ]]})
            except:
                pass
            return

        damage = defense_result["damage"]
        if defense_result["guardian_reduce"] > 0:
            factor = (100 - defense_result["guardian_reduce"]) / 100
            damage = max(1, int(damage * factor))

        if target_coins_before <= 0:
            stolen_c = 0
        else:
            stolen_c = min(want_c, target_coins_before)

        if target.get("refinery_level", 0) <= 0 or target_oil_before <= 0:
            stolen_o = 0
        else:
            stolen_o = min(want_o, target_oil_before)

        rank_gain = want_r

        def_msgs = []
        target_water = target.get("talisman_water_count", 0)
        target_shield = target.get("talisman_shield_count", 0)

        if target_water > 0:
            db[target_id]["talisman_water_count"] -= 1
            damage = int(damage * 0.7)
            stolen_c = int(stolen_c * 0.7)
            stolen_o = int(stolen_o * 0.7)
            def_msgs.append("💧 مدافع از طلسم آب استفاده کرد: 30% کاهش دمیج و غارت")

        if target_shield > 0:
            db[target_id]["talisman_shield_count"] -= 1
            stolen_c = int(stolen_c * 0.5)
            stolen_o = int(stolen_o * 0.5)
            def_msgs.append("🛡 مدافع از طلسم سپر استفاده کرد: 50% کاهش غارت")

        if target.get("sub_shield_until", 0) > time.time():
            stolen_c = int(stolen_c * 0.5)
            stolen_o = int(stolen_o * 0.5)
            def_msgs.append("⭐️ مدافع سپر اشتراک ویژه فعال داشت: 50% کاهش غارت")

        defense_msg = ""
        if defense_result["guardian_reduce"] > 0:
            defense_msg += f"\n💠 گاردین فعال! کاهش دمیج: {defense_result['guardian_reduce']}%\n"
        if def_msgs:
            defense_msg += "\n" + "\n".join(def_msgs) + "\n"

        db[target_id]["coins"] = max(0, target_coins_before - stolen_c)
        db[user_id]["coins"] = db[user_id].get("coins", 0) + stolen_c
        if target.get("refinery_level", 0) > 0:
            db[target_id]["oil"] = max(0, target_oil_before - stolen_o)
            db[user_id]["oil"] = db[user_id].get("oil", 0) + stolen_o

        if is_moon_league(target_rank_before):
            rank_gain = 0
            moon_note = ("\n⚠️ این بازیکن در لیگ ماه است.\n"
                         "حمله عادی روی او تاثیری ندارد.")
        else:
            moon_note = ""
            if rank_gain > 0:
                apply_rank_change(user_id, target_id, rank_gain)

        db[user_id]["total_damage"] = db[user_id].get("total_damage", 0) + 2
        db[user_id]["last_battle_attack"] = time.time()
        db[user_id]["battle_action"] = None
        db[target_id]["last_attacker"] = user_id

        vernix_msgs = apply_vernix_damage_to_fighters(db[user_id], target)

        if is_drone:
            if db[user_id]["drones"][weapon_name]["count"] <= 1:
                del db[user_id]["drones"][weapon_name]
            else:
                db[user_id]["drones"][weapon_name]["count"] -= 1

        save_db()

        title = "🚀💥 حمله موشکی موفق 💥🚀" if not is_drone else "🛩️💥 حمله پهبادی موفق 💥🛩️"

        loot_section = build_attack_loot_section(
            stolen_c, stolen_o, target_coins_before, target_oil_before, target)

        a_league = get_league(db[user_id].get("rank", 0))
        t_league = get_league(target.get("rank", 0))

        if is_drone:
            weapon_line = f"🛩 سلاح: {weapon_name}"
        elif weapon_category in ["cruise", "ballistic", "hypersonic", "nuclear"]:
            if is_wheel_only(weapon_name):
                weapon_line = f"🚀 سلاح: {weapon_name} (🎡 گردونه)"
            else:
                weapon_line = f"🚀 سلاح: {weapon_name} (📊 سطح {m_level})"
        else:
            weapon_line = f"🚀 سلاح: {weapon_name}"

        talisman_block = ""
        if tal_msgs:
            talisman_block = "\n✨ طلسم‌های مهاجم:\n"
            for tm in tal_msgs:
                talisman_block += f"   {tm}\n"

        vernix_block = ""
        if vernix_msgs:
            vernix_block = "\n🔥 آسیب ورنیکس به جنگنده‌ها:\n"
            for vm in vernix_msgs:
                vernix_block += f"   {vm}\n"

        msg = (
            f"{title}\n\n"
            f"⚔️ مهاجم: {db[user_id].get('name','کاربر')} ({a_league})\n"
            f"🛡️ مدافع: {target.get('name','کاربر')} ({t_league})\n\n"
            f"{weapon_line}\n"
            f"💥 دمیج واردشده: {damage}\n\n"
            f"{defense_msg}"
            f"{talisman_block}"
            f"{vernix_block}"
            f"\n{loot_section}"
            f"🏅 رنک: {rank_gain if rank_gain > 0 else '🚫 بدون تغییر'}{moon_note}\n\n"
            f"🕒 تاریخ و ساعت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        send_message(chat_id, msg)

        try:
            send_message(int(target_id),
                f"⛔️ بهت حمله شد ⛔️\n\n"
                f"⚔️ مهاجم: {db[user_id].get('name','کاربر')}\n"
                f"🚀 سلاح: {weapon_name}\n"
                f"💥 دمیج: {damage}\n"
                f"🪙 سکه: -{stolen_c}"
                f"{defense_msg}",
                {"inline_keyboard": [[{"text": "⚔️ انتقام",
                                       "callback_data": f"revenge_{user_id}"}]]},
                reply_to_message_id=message["message_id"])
        except:
            pass
        return

    # ==================== حمله ترکیبی در گپ ====================
    if text == "حمله ترکیبی":
        if chat_type not in ["group", "supergroup"]:
            return
        if db[user_id].get("paralyzed_until", 0) > time.time():
            rem = int(db[user_id]["paralyzed_until"] - time.time())
            send_message(chat_id, f"⛔️ شما فلج هستید! ({rem} ثانیه دیگر صبر کنید)")
            return
        now = time.time()
        if now - db[user_id].get("last_combo_attack", 0) < 5:
            rem = int(5 - (now - db[user_id].get("last_combo_attack", 0)))
            send_message(chat_id,
                         f"⛔️ شما تازه حمله کردید!\n⏳ {rem} ثانیه دیگر صبر کنید")
            return
        if not message.get("reply_to_message"):
            send_message(chat_id, "❌ روی پیام حریف ریپلای کن!")
            return
        target_id = str(message["reply_to_message"].get("from", {}).get("id", 0))
        if target_id == user_id:
            send_message(chat_id, "❌ خودت!")
            return
        if target_id == str(ADMIN_ID) or target_id == str(PARTNER_ID):
            send_message(chat_id, "❌ مالک!")
            return
        if target_id not in db or not isinstance(db.get(target_id), dict):
            send_message(chat_id, "❌ حریف نیست!")
            return
        result = calculate_combo_attack(user_id)
        if not result:
            send_message(chat_id, "❌ ترکیبی نداری!")
            return
        attacker = db[user_id]
        target = db[target_id]

        for w in result["weapons"]:
            wn = w["name"]
            wcat = w["category"]
            used = w["used"]
            if used <= 0:
                continue
            if wcat in db[user_id] and wn in db[user_id][wcat]:
                cur = db[user_id][wcat][wn].get("count", 0)
                new = max(0, cur - used)
                if new <= 0:
                    del db[user_id][wcat][wn]
                    if not db[user_id][wcat]:
                        db[user_id][wcat] = {}
                else:
                    db[user_id][wcat][wn]["count"] = new

        phoenix_red = get_phoenix_reduction(target)
        fighter_bonus = result.get("fighter_bonus", 0)

        if phoenix_red >= 100:
            fighter_dmg = 0
            fighter_loot = {"coins": 0, "oil": 0}
            fighter_note = ("\n🛡 حریف فونیکس سطح 6 دارد!\n"
                            "✈️ جنگنده‌های شما کاملاً بی‌اثر شدند.")
        elif phoenix_red > 0:
            fighter_dmg = int(fighter_bonus * (100 - phoenix_red) / 100)
            fighter_loot = get_fighter_loot_bonus(fighter_dmg)
            fighter_note = (f"\n🛡 فونیکس حریف ({phoenix_red}% کاهش)\n"
                            f"✈️ دمیج جنگنده‌های شما کاهش یافت.")
        else:
            fighter_dmg = fighter_bonus
            fighter_loot = get_fighter_loot_bonus(fighter_bonus)
            fighter_note = ""

        defense_pct = get_total_defense(target, "combo")

        target_coins_before = target.get("coins", 0)
        target_oil_before = target.get("oil", 0)
        target_rank_before = target.get("rank", 0)

        total_dmg = result["damage"] + fighter_dmg
        defense_absorbed = int(total_dmg * defense_pct / 100)
        net_dmg = total_dmg - defense_absorbed
        if net_dmg < 1:
            net_dmg = 1

        want_c = result["coins"] + fighter_loot["coins"]
        want_o = result["oil"] + fighter_loot["oil"]

        attacker_fighters = sum(
            f.get("count", 0)
            for f in attacker.get("fighters_hero", {}).values()
        )
        loot_pct, rank_penalty, defense_note = calc_combo_defense_penalty(
            target, attacker_fighters)

        want_c = int(want_c * loot_pct)
        want_o = int(want_o * loot_pct)

        if target_coins_before <= 0:
            stolen_c = 0
        else:
            stolen_c = min(want_c, target_coins_before)

        if target.get("refinery_level", 0) <= 0 or target_oil_before <= 0:
            stolen_o = 0
        else:
            stolen_o = min(want_o, target_oil_before)

        sub_shield_note = ""
        if target.get("sub_shield_until", 0) > time.time():
            stolen_c = int(stolen_c * 0.5)
            stolen_o = int(stolen_o * 0.5)
            sub_shield_note = "\n⭐️ مدافع سپر اشتراک ویژه داشت: 50% کاهش غارت"

        db[target_id]["coins"] = max(0, target_coins_before - stolen_c)
        db[user_id]["coins"] = attacker.get("coins", 0) + stolen_c
        if target.get("refinery_level", 0) > 0:
            db[target_id]["oil"] = max(0, target_oil_before - stolen_o)
            db[user_id]["oil"] = attacker.get("oil", 0) + stolen_o

        attacker_rank_before = attacker.get("rank", 0)
        if is_moon_league(attacker_rank_before):
            rank_gain = 0
            moon_note = ("\n⚠️ شما در لیگ ماه هستید.\n"
                         "ترکیبی در گپ رنک نمی‌دهد.")
        elif is_moon_league(target_rank_before):
            rank_gain = 0
            moon_note = ("\n⚠️ این بازیکن در لیگ ماه است.\n"
                         "حمله ترکیبی روی او رنک اثر ندارد.")
        else:
            rank_gain = result["rank"]
            moon_note = ""
            if rank_gain > 0:
                apply_rank_change(user_id, target_id, rank_gain)

        if rank_penalty < 0:
            today_str = datetime.now().strftime("%Y-%m-%d")
            db[user_id]["rank"] = max(0, db[user_id].get("rank", 0) + rank_penalty)
            if db[user_id].get("rank_date") == today_str:
                db[user_id]["rank_today"] = db[user_id].get("rank_today", 0) + rank_penalty
            rank_gain = rank_penalty

        db[user_id]["total_damage"] = attacker.get("total_damage", 0) + 4
        db[user_id]["last_combo_attack"] = now

        vernix_msgs = apply_vernix_damage_to_fighters(db[user_id], target)
        save_db()

        full_note = moon_note
        if defense_note:
            full_note = (full_note + "\n" + defense_note) if full_note else defense_note
        if sub_shield_note:
            full_note = (full_note + "\n" + sub_shield_note) if full_note else sub_shield_note

        report = build_combo_attack_report(
            attacker=attacker,
            target=target,
            raw_dmg=total_dmg,
            defense_pct=defense_pct,
            stolen_c=stolen_c,
            stolen_o=stolen_o,
            rank_gain=rank_gain,
            weapons_used=result["weapons"],
            fighter_dmg=fighter_dmg,
            fighter_loot=fighter_loot,
            fighter_note=fighter_note,
            vernix_msgs=vernix_msgs,
            moon_note=full_note,
            defender_had_coins=target_coins_before,
            defender_had_oil=target_oil_before,
            want_c=want_c,
            want_o=want_o,
        )

        send_message(chat_id, report,
                     reply_to_message_id=message["message_id"])

        try:
            db[target_id]["last_attacker"] = user_id
            db[target_id]["last_attack_time"] = time.time()
            save_db()
            a_name = attacker.get("name", "کاربر")
            send_message(int(target_id),
                f"⛔️ *بهت حمله ترکیبی شد* ⛔️\n\n"
                f"👤 حمله‌کننده: {a_name}\n"
                f"📦 {result['combo_name']}\n"
                f"💢 دمیج: {net_dmg:,}\n"
                f"سکه: {stolen_c:,}\nنفت: {stolen_o:,}",
                {"inline_keyboard": [[{"text": "⚔️ انتقام",
                                       "callback_data": f"revenge_{user_id}"}]]},
                reply_to_message_id=message["message_id"])
        except:
            pass
        return

    # ==================== حمله عادی در گپ ====================
    if text.startswith("حمله ") and chat_type in ["group", "supergroup"]:
        cmd = text.replace("حمله", "").strip()

        if db[user_id].get("paralyzed_until", 0) > time.time():
            rem = int(db[user_id]["paralyzed_until"] - time.time())
            send_message(chat_id, f"⛔️ شما فلج هستید! ({rem} ثانیه دیگر صبر کنید)")
            return

        use_talismans = []
        weapon_parts = []
        valid_tal_mans = {
            "چشم": "talisman_eye_count",
            "آتش": "talisman_fire_count",
            "طوفان": "talisman_storm_count",
            "صاعقه": "talisman_lightning_count",
            "شکار": "talisman_hunt_count",
            "یخ": "talisman_ice_count"
        }
        for w in cmd.strip().split():
            if w in valid_tal_mans:
                use_talismans.append(w)
            else:
                weapon_parts.append(w)
        cmd = " ".join(weapon_parts)

        if len(use_talismans) > 1:
            missing = [t for t in use_talismans if db[user_id].get(valid_tal_mans[t], 0) <= 0]
            if missing:
                send_message(chat_id, f"❌ شما طلسم {'، '.join(missing)} ندارید!")
            else:
                send_message(chat_id, "❌ حداکثر استفاده از طلسم در هر حمله 1 عدد است!")
            return
        elif len(use_talismans) == 1:
            t_name = use_talismans[0]
            if db[user_id].get(valid_tal_mans[t_name], 0) <= 0:
                send_message(chat_id, f"❌ شما طلسم {t_name} ندارید!")
                return

        if cmd == "شیمیایی":
            missile_name = "شیمیایی"
        else:
            for w in ["موشکی", "پهبادی", "هوایی", "هسته‌ای"]:
                if cmd.startswith(w):
                    cmd = cmd.replace(w, "", 1).strip()
            missile_name = cmd.strip()

        is_drone = missile_name in DRONES
        if not is_drone and missile_name not in MISSILES:
            send_message(chat_id, "❌ نام موشک اشتباه است!")
            return

        now = time.time()
        if now - db[user_id].get("last_gap_attack", 0) < 5:
            rem = int(5 - (now - db[user_id].get("last_gap_attack", 0)))
            send_message(chat_id,
                         f"⛔️ شما تازه حمله کردید!\n⏳ {rem} ثانیه دیگر صبر کنید")
            return
        db[user_id]["last_gap_attack"] = now
        save_db()

        if not message.get("reply_to_message"):
            send_message(chat_id, "❌ روی پیام حریف ریپلای کن!")
            return
        target_user = message["reply_to_message"].get("from", {})
        target_id = str(target_user.get("id", 0))
        if target_id == user_id:
            send_message(chat_id, "❌ خودت!")
            return
        if target_user.get("is_bot"):
            send_message(chat_id, "❌ بات!")
            return
        if target_id == str(ADMIN_ID) or target_id == str(PARTNER_ID):
            send_message(chat_id, "❌ مالک!")
            return
        if target_id not in db or not isinstance(db.get(target_id), dict):
            send_message(chat_id, "❌ حریف نیست!")
            return

        attacker = db[user_id]
        target = db[target_id]

        missile_found = None
        missile_category = None
        if not is_drone:
            for category in ["cruise", "ballistic", "hypersonic",
                             "chemical", "nuclear", "drones", "fighters"]:
                if missile_name in attacker.get(category, {}):
                    missile_found = attacker[category][missile_name]
                    missile_category = category
                    break
            if not missile_found:
                send_message(chat_id, "❌ این موشک در لیست دارایی شما نیست!")
                return
            if missile_found.get("count", 0) <= 0:
                send_message(chat_id, f"❌ «{missile_name}» تموم شده!")
                return

        missile_level = missile_found.get("level", 1) if not is_drone else 1
        if not is_drone:
            damage = get_missile_damage(missile_name, missile_level, missile_category)
        else:
            d_info = DRONES[missile_name]
            missile_level = attacker.get("drones", {}).get(missile_name, {}).get("level", 1)
            damage = int((d_info["price"] / 2) * (1 + (missile_level - 1) * 0.2))
            missile_category = "drones"

        bypass_defense = False
        tal_msgs = []

        for tal_name in use_talismans:
            tal_key = None
            for k, v in TALISMAN_INFO.items():
                if v["name"] == tal_name:
                    tal_key = k
                    break
            if not tal_key: continue

            count_key = TALISMAN_INFO[tal_key]["count_key"]
            db[user_id][count_key] -= 1

            if tal_key == "eye":
                if random.randint(1, 100) <= 25:
                    bypass_defense = True
                    tal_msgs.append("🧿 چشم: پدافند نادیده گرفته شد!")
                else:
                    tal_msgs.append("🧿 چشم: فعال نشد.")
            elif tal_key == "fire":
                damage = int(damage * 1.2)
                tal_msgs.append("🔥 آتش: ۲۰٪ دمیج بیشتر")
            elif tal_key == "storm":
                if not is_drone and missile_category in db[user_id] and missile_name in db[user_id][missile_category]:
                    if db[user_id][missile_category][missile_name].get("count", 0) >= 2:
                        db[user_id][missile_category][missile_name]["count"] -= 2
                        extra_dmg = get_missile_damage(missile_name, missile_level, missile_category) * 2
                        damage += extra_dmg
                        tal_msgs.append("🌪 طوفان: ۲ موشک اضافه شلیک شد")
                    else:
                        tal_msgs.append("🌪 طوفان: موشک کافی نداشتی")
                else:
                    tal_msgs.append("🌪 طوفان: موشک نداشتی")
            elif tal_key == "hunt":
                damage = int(damage * 1.4)
                tal_msgs.append("👁 شکار: ۴۰٪ دمیج بیشتر")
            elif tal_key == "lightning":
                db[target_id]["paralyzed_until"] = time.time() + 60
                tal_msgs.append("⚡ صاعقه: حریف ۶۰ ثانیه فلج شد")
            elif tal_key == "ice":
                db[target_id]["paralyzed_until"] = time.time() + 30
                tal_msgs.append("❄️ یخ: حریف ۳۰ ثانیه فلج شد")

        from handlers_callback import apply_defense_block_to_attack

        if not is_drone:
            base_c = get_loot_coins(missile_name, missile_level)
            base_o = get_loot_oil(missile_name, missile_level)
            base_r = get_loot_rank(missile_name, missile_level)
        else:
            d_info = DRONES[missile_name]
            base_c = int(d_info["price"] * 0.3 * missile_level)
            base_o = int(base_c / 2)
            base_r = int(d_info["price"] * 0.1 * missile_level)
            if d_info["effect"] == "rank": base_r = int(base_r * d_info["value"])
            elif d_info["effect"] == "coins": base_c = int(base_c * d_info["value"])
            elif d_info["effect"] == "defense": bypass_defense = True

        defense_result = apply_defense_block_to_attack(
            user_id, target_id, target,
            missile_name, missile_category, missile_level,
            damage, base_c, base_o, base_r)

        if bypass_defense:
            defense_result["blocked"] = False
            defense_result["guardian_reduce"] = 0
            defense_result["damage"] = damage

        if defense_result["blocked"]:
            db[user_id]["last_gap_attack"] = now
            save_db()

            a_name = attacker.get("name", "کاربر")
            t_name = target.get("name", "کاربر")
            a_league = get_league(attacker.get("rank", 0))
            t_league = get_league(target.get("rank", 0))

            title = "🛩️🛡 *حمله پهبادی دفع شد!*" if is_drone else "🚀🛡 *حمله موشکی دفع شد!*"

            block_msg = (
                f"{title}\n\n"
                f"👤 مهاجم: {a_name} ({a_league})\n"
                f"🛡️ مدافع: {t_name} ({t_league})\n\n"
                f"🚀 سلاح: *{missile_name}* (سطح {missile_level})\n"
                f"⚡ پدافند فعال: *{defense_result['defense_name']}*\n"
                f"🎯 شانس بلاک: *{defense_result['block_chance']}%*\n"
                f"💥 دمیج واردشده: *0*\n"
                f"🪙 غارت: *0*\n"
                f"🏅 رنک: *بدون تغییر*\n\n"
                f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            send_message(chat_id, block_msg,
                         reply_to_message_id=message["message_id"])

            try:
                db[target_id]["last_attacker"] = user_id
                db[target_id]["last_attack_time"] = time.time()
                save_db()
                send_message(int(target_id),
                    f"🛡 *حمله دفع شد!*\n\n"
                    f"👤 مهاجم: {a_name}\n"
                    f"🚀 سلاح: {missile_name}\n"
                    f"⚡ پدافند: {defense_result['defense_name']}\n"
                    f"🎯 شانس بلاک: {defense_result['block_chance']}%",
                    {"inline_keyboard": [[
                        {"text": "⚔️ انتقام",
                         "callback_data": f"revenge_{user_id}"}
                    ]]},
                    reply_to_message_id=message["message_id"])
            except:
                pass
            return

        target_coins_before = target.get("coins", 0)
        target_oil_before = target.get("oil", 0)
        target_rank_before = target.get("rank", 0)

        damage = defense_result["damage"]
        if defense_result["guardian_reduce"] > 0:
            factor = (100 - defense_result["guardian_reduce"]) / 100
            damage = max(1, int(damage * factor))

        if target_coins_before <= 0:
            stolen_c = 0
        else:
            stolen_c = min(base_c, target_coins_before)

        if target.get("refinery_level", 0) <= 0 or target_oil_before <= 0:
            stolen_o = 0
        else:
            stolen_o = min(base_o, target_oil_before)

        rank_gain = base_r

        def_msgs = []
        target_water = target.get("talisman_water_count", 0)
        target_shield = target.get("talisman_shield_count", 0)

        if target_water > 0:
            db[target_id]["talisman_water_count"] -= 1
            damage = int(damage * 0.7)
            stolen_c = int(stolen_c * 0.7)
            stolen_o = int(stolen_o * 0.7)
            def_msgs.append("💧 مدافع از طلسم آب استفاده کرد: 30% کاهش دمیج و غارت")

        if target_shield > 0:
            db[target_id]["talisman_shield_count"] -= 1
            stolen_c = int(stolen_c * 0.5)
            stolen_o = int(stolen_o * 0.5)
            def_msgs.append("🛡 مدافع از طلسم سپر استفاده کرد: 50% کاهش غارت")

        if target.get("sub_shield_until", 0) > time.time():
            stolen_c = int(stolen_c * 0.5)
            stolen_o = int(stolen_o * 0.5)
            def_msgs.append("⭐️ مدافع سپر اشتراک ویژه فعال داشت: 50% کاهش غارت")

        defense_msg = ""
        if defense_result["guardian_reduce"] > 0:
            defense_msg += f"\n💠 گاردین فعال! کاهش دمیج: {defense_result['guardian_reduce']}%\n"
        if def_msgs:
            defense_msg += "\n" + "\n".join(def_msgs) + "\n"

        db[target_id]["coins"] = max(0, target_coins_before - stolen_c)
        db[user_id]["coins"] = attacker.get("coins", 0) + stolen_c
        if target.get("refinery_level", 0) > 0:
            db[target_id]["oil"] = max(0, target_oil_before - stolen_o)
            db[user_id]["oil"] = attacker.get("oil", 0) + stolen_o

        attacker_rank_before = attacker.get("rank", 0)
        if is_moon_league(attacker_rank_before):
            rank_gain = 0
            moon_note = ("\n⚠️ شما در لیگ ماه هستید.\n"
                         "حمله عادی در گپ رنک نمی‌دهد.")
        elif is_moon_league(target_rank_before):
            rank_gain = 0
            moon_note = ("\n⚠️ این بازیکن در لیگ ماه است.\n"
                         "حمله عادی روی او تاثیری ندارد.")
        else:
            moon_note = ""
            if rank_gain > 0:
                apply_rank_change(user_id, target_id, rank_gain)

        db[user_id]["total_damage"] = attacker.get("total_damage", 0) + 2

        if is_drone:
            if db[user_id]["drones"][missile_name]["count"] <= 1:
                del db[user_id]["drones"][missile_name]
            else:
                db[user_id]["drones"][missile_name]["count"] -= 1
        else:
            new = max(0, missile_found.get("count", 0) - 1)
            if new <= 0:
                del db[user_id][missile_category][missile_name]
                if not db[user_id][missile_category]:
                    db[user_id][missile_category] = {}
            else:
                db[user_id][missile_category][missile_name]["count"] = new

        vernix_msgs = apply_vernix_damage_to_fighters(db[user_id], target)

        save_db()

        a_league = get_league(attacker.get("rank", 0))
        t_league = get_league(target.get("rank", 0))

        title = "🛩️💥 حمله پهبادی موفق 💥🛩️" if is_drone else "🚀💥 حمله موشکی موفق 💥🚀"

        loot_section = build_attack_loot_section(
            stolen_c, stolen_o, target_coins_before, target_oil_before, target)

        if is_drone:
            weapon_line = f"🛩 سلاح: {missile_name}"
        elif missile_category in ["cruise", "ballistic", "hypersonic", "nuclear"]:
            if is_wheel_only(missile_name):
                weapon_line = f"🚀 سلاح: {missile_name} (🎡 گردونه)"
            else:
                weapon_line = f"🚀 سلاح: {missile_name} (📊 سطح {missile_level})"
        else:
            weapon_line = f"🚀 سلاح: {missile_name}"

        talisman_block = ""
        if tal_msgs:
            talisman_block = "\n✨ طلسم‌های مهاجم:\n"
            for tm in tal_msgs:
                talisman_block += f"   {tm}\n"

        vernix_block = ""
        if vernix_msgs:
            vernix_block = "\n🔥 آسیب ورنیکس به جنگنده‌ها:\n"
            for vm in vernix_msgs:
                vernix_block += f"   {vm}\n"

        msg = (
            f"{title}\n\n"
            f"⚔️ مهاجم: {attacker.get('name','کاربر')} ({a_league})\n"
            f"🛡️ مدافع: {target.get('name','کاربر')} ({t_league})\n\n"
            f"{weapon_line}\n"
            f"💥 دمیج واردشده: {damage}\n\n"
            f"{defense_msg}"
            f"{talisman_block}"
            f"{vernix_block}"
            f"\n{loot_section}"
            f"🏅 رنک: {rank_gain if rank_gain > 0 else '🚫 بدون تغییر'}{moon_note}\n\n"
            f"🕒 تاریخ و ساعت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        send_message(chat_id, msg, reply_to_message_id=message["message_id"])

        try:
            db[target_id]["last_attacker"] = user_id
            db[target_id]["last_attack_time"] = time.time()
            save_db()
            warn = (f"⛔️ بهت حمله شد ⛔️\n\n"
                    f"⚔️ مهاجم: {attacker.get('name','کاربر')} ({a_league})\n"
                    f"🛡️ مدافع: {target.get('name','کاربر')} ({t_league})\n\n")
            if is_drone:
                warn += f"🛩 سلاح: {missile_name}\n"
            elif missile_category in ["cruise", "ballistic", "hypersonic", "nuclear"]:
                warn += f"🚀 سلاح: {missile_name} (📊 سطح {missile_level})\n"
            else:
                warn += f"🚀 سلاح: {missile_name}\n"
            warn += f"💥 دمیج: {damage}\n"
            warn += f"🪙 سکه از دست رفته: {stolen_c}\n"
            warn += f"{defense_msg}"
            warn += f"\n🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            send_message(int(target_id), warn,
                {"inline_keyboard": [[{"text": "⚔️ انتقام",
                                       "callback_data": f"revenge_{user_id}"}]]},
                reply_to_message_id=message["message_id"])
        except:
            pass
        return