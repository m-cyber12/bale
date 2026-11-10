import time
from datetime import datetime
from config import *
from core import (db, save_db, save_db_now, send_message,
                  answer_pre_checkout_query, is_subscription_active)
from data import *


def get_today_str():
    return datetime.now().strftime("%Y-%m-%d")


# ==================== Pre-Checkout Query ====================
def handle_pre_checkout_query(update):
    """
    وقتی کاربر روی دکمه پرداخت می‌زنه، Bale این آپدیت رو می‌فرسته
    و منتظر تأیید یا رد ما می‌مونه.
    """
    pcq = update.get("pre_checkout_query", {})
    pcq_id = pcq.get("id")
    payload = pcq.get("invoice_payload", "")
    total = pcq.get("total_amount", 0)
    currency = pcq.get("currency", "")

    from_user = pcq.get("from", {})
    user_id = str(from_user.get("id", ""))
    user_name = from_user.get("first_name", "کاربر")

    print(f"💰 PRE_CHECKOUT → user={user_id} | payload={payload} | "
          f"amount={total} {currency}")

    if currency != PAYMENT_CURRENCY:
        answer_pre_checkout_query(pcq_id, False, "❌ واحد پول نامعتبر است.")
        return

    # Payloads created by the bot contain the buyer ID and timestamp.
    if payload.startswith(("world_pass_", "subscription_")):
        prefix = "world_pass_" if payload.startswith("world_pass_") else "subscription_"
        parts = payload[len(prefix):].split("_")
        if len(parts) != 2 or parts[0] != user_id or not parts[1].isdigit():
            answer_pre_checkout_query(pcq_id, False, "❌ اطلاعات خریدار نامعتبر است.")
            return

    # ==================== تشخیص نوع پرداخت ====================
    if payload.startswith("world_pass_"):
        expected = WORLD_PASS_PRICE_RIAL
        ptype = "world_pass"
    elif payload.startswith("subscription_"):
        expected = SUBSCRIPTION_PRICE_RIAL
        ptype = "subscription"
    elif payload.startswith("item_"):
        parts = payload.split("_")
        if len(parts) != 5 or not parts[4].isdigit():
            answer_pre_checkout_query(pcq_id, False, "❌ داده نامعتبر.")
            print(f"❌ Invalid item payload: {payload}")
            return
        try:
            key = parts[1]
            qty = int(parts[2])
            buyer_uid = parts[3]
        except (ValueError, IndexError):
            answer_pre_checkout_query(pcq_id, False, "❌ داده نامعتبر.")
            print(f"❌ Invalid item payload parts: {payload}")
            return

        if key not in ITEM_PACKS:
            answer_pre_checkout_query(pcq_id, False, "❌ پک نامعتبر.")
            print(f"❌ Unknown item key: {key}")
            return

        if buyer_uid != user_id:
            answer_pre_checkout_query(pcq_id, False, "❌ کاربر نامعتبر.")
            print(f"❌ Buyer mismatch: {buyer_uid} != {user_id}")
            return

        pack = ITEM_PACKS[key]
        if not pack["min_qty"] <= qty <= pack["max_qty"]:
            answer_pre_checkout_query(pcq_id, False, "❌ تعداد نامعتبر است.")
            return
        expected = pack["price_per_unit"] * qty * 10  # تومان → ریال
        ptype = "item"
    else:
        answer_pre_checkout_query(
            pcq_id, False,
            "❌ نوع پرداخت نامعتبر است."
        )
        print(f"❌ Invalid payload: {payload}")
        return

    # ==================== اعتبارسنجی مبلغ ====================
    try:
        total_int = int(total)
    except (ValueError, TypeError):
        answer_pre_checkout_query(
            pcq_id, False,
            "❌ مبلغ پرداخت نامعتبر است."
        )
        print(f"❌ Invalid amount type: {total!r}")
        return

    if total_int != expected:
        answer_pre_checkout_query(
            pcq_id, False,
            f"❌ مبلغ پرداخت اشتباه است.\n"
            f"انتظار: {expected:,} ریال\n"
            f"دریافت: {total_int:,} {currency}"
        )
        print(f"❌ Wrong amount: {total_int} != {expected}")
        return

    # ==================== بررسی کاربر ====================
    if not user_id:
        answer_pre_checkout_query(
            pcq_id, False,
            "❌ خطا در شناسایی کاربر. لطفاً دوباره تلاش کنید."
        )
        print(f"❌ No user_id in pre_checkout_query")
        return

    if user_id not in db or not isinstance(db.get(user_id), dict):
        answer_pre_checkout_query(
            pcq_id, False,
            "❌ لطفاً ابتدا /start بزنید و پروفایل بسازید."
        )
        print(f"❌ User not found: {user_id}")
        return

    p = db[user_id]

    # ==================== بررسی پرداخت تکراری ====================
    if ptype == "world_pass":
        active = p.get("world_pass_active", False)
        claimed = p.get("world_pass_days_claimed", 0)
        if active and claimed < WORLD_PASS_TOTAL_DAYS:
            answer_pre_checkout_query(
                pcq_id, False,
                "⚠️ شما یک World Shop فعال دارید!\n"
                "ابتدا جوایز فعلی رو دریافت کنید."
            )
            print(f"❌ User already has active world_pass: {user_id}")
            return

    elif ptype == "subscription":
        if is_subscription_active(user_id):
            answer_pre_checkout_query(
                pcq_id, False,
                "⚠️ شما یک اشتراک ویژه فعال دارید!\n"
                "بعد از پایان مدت، دوباره تلاش کنید."
            )
            print(f"❌ User already has active subscription: {user_id}")
            return

    # ptype == "item" → چک تکراری لازم نداره (هر خرید جدید مجازه)

    # ==================== همه چیز اوکی ====================
    answer_pre_checkout_query(pcq_id, True)
    print(f"✅ Pre-checkout confirmed → user={user_id} | "
          f"type={ptype} | amount={total_int}")


# ==================== Successful Payment ====================
def handle_successful_payment(update):
    """
    وقتی پرداخت موفق می‌شه، Bale یه پیام با successful_payment می‌فرسته.
    """
    msg = update.get("message", {})
    sp = msg.get("successful_payment", {})
    user_id = str(msg.get("from", {}).get("id", ""))
    chat_id = msg.get("chat", {}).get("id", user_id)
    user_name = msg.get("from", {}).get("first_name", "کاربر")

    payload = sp.get("invoice_payload", "")
    total = sp.get("total_amount", 0)
    currency = sp.get("currency", "")
    charge_id = sp.get("telegram_payment_charge_id", "")
    provider_charge = sp.get("provider_payment_charge_id", "")

    print(f"🎉 SUCCESSFUL PAYMENT → user={user_id} | "
          f"amount={total} {currency} | payload={payload} | charge={charge_id}")

    if not user_id:
        print(f"❌ No user_id in successful_payment")
        return

    if user_id not in db or not isinstance(db.get(user_id), dict):
        try:
            send_message(chat_id,
                "⚠️ پرداخت دریافت شد ولی پروفایل شما پیدا نشد.\n"
                "لطفاً به پشتیبانی پیام بدید.")
        except:
            pass
        print(f"❌ User not found on payment: {user_id}")
        return

    p = db[user_id]

    # ==================== ⭐️ اشتراک ویژه ====================
    if payload.startswith("subscription_"):
        if is_subscription_active(user_id):
            db[user_id]["subscription_pending_invoice"] = 0
            save_db_now()

            try:
                send_message(chat_id,
                    "⚠️ شما قبلاً یک اشتراک فعال دارید.\n"
                    "پرداخت شما دریافت شد ولی نیازی به فعال‌سازی مجدد نیست.\n\n"
                    f"🔑 کد پرداخت: `{charge_id}`\n"
                    "📞 برای پیگیری به پشتیبانی پیام بدید.")
            except:
                pass
            print(f"⚠️ Double subscription payment: {user_id} | charge={charge_id}")

            try:
                for admin_id in [ADMIN_ID, PARTNER_ID]:
                    if str(admin_id) != user_id:
                        send_message(int(admin_id),
                            f"⚠️ *پرداخت تکراری اشتراک!*\n"
                            f"━━━━━━━━━━━━━━━━━\n\n"
                            f"👤 کاربر: {p.get('name', user_name)}\n"
                            f"🆔 آیدی: `{user_id}`\n"
                            f"💰 مبلغ: {total:,} {currency}\n"
                            f"🔑 Charge ID: `{charge_id}`\n\n"
                            f"⚠️ کاربر دوبار پرداخت کرده ولی اشتراک فعال داشته.\n"
                            f"💡 لطفاً دستی بررسی کنید.")
            except:
                pass
            return

        now = time.time()
        expires_at = now + (SUBSCRIPTION_DURATION_DAYS * 86400)

        db[user_id]["subscription_active"] = True
        db[user_id]["subscription_started_at"] = now
        db[user_id]["subscription_expires_at"] = expires_at
        db[user_id]["subscription_last_mission_claim"] = ""
        db[user_id]["subscription_pending_invoice"] = 0
        db[user_id]["sub_shield_until"] = 0
        db[user_id]["sub_shield_used_today"] = 0
        db[user_id]["sub_shield_date"] = ""
        save_db_now()

        print(f"✅ Subscription activated → user={user_id} | "
              f"expires={datetime.fromtimestamp(expires_at).strftime('%Y-%m-%d %H:%M')}")

        exp_str = datetime.fromtimestamp(expires_at).strftime("%Y-%m-%d")
        success_text = (
            f"🎉 *پرداخت موفق!*\n"
            f"━━━━━━━━━━━━━━━━━\n\n"
            f"⭐️ *اشتراک ویژه شما فعال شد!*\n\n"
            f"📅 مدت: *{SUBSCRIPTION_DURATION_DAYS} روز*\n"
            f"⏰ انقضا: *{exp_str}*\n\n"
            f"🎁 *مزایای فعال‌شده:*\n"
            f"• 🚀 {SUB_DISCOUNT_MISSILE}٪ تخفیف روی همه موشک‌ها\n"
            f"• 💎 الماس در جایزه روزانه (شانس {SUB_GEMS_CHANCE}٪)\n"
            f"• 💰 انتقال سکه تا {SUB_TRANSFER_LIMIT:,}\n"
            f"• 🚀 {SUB_DAILY_CRUISE} کروز + {SUB_DAILY_BALLISTIC} بالستیک + {SUB_DAILY_HYPERSONIC} هایپرسونیک روزانه\n"
            f"• 🛡 سپر تا {SUB_SHIELD_MAX_SECONDS//3600} ساعت در روز\n\n"
            f"━━━━━━━━━━━━━━━━━\n"
            f"🔻 از منوی «📁 سایر → ⭐️ اشتراک ویژه» استفاده کن:"
        )
        try:
            send_message(chat_id, success_text, {
                "inline_keyboard": [
                    [{"text": "⭐️ مشاهده اشتراک",
                      "callback_data": "other_subscription"}],
                    [{"text": "🎁 دریافت موشک‌های روزانه",
                      "callback_data": "sub_claim_missiles"}],
                ]
            })
        except Exception as e:
            print(f"⚠️ Failed to send success: {e}")

        try:
            a_name = db[user_id].get("name", user_name)
            admin_msg = (
                f"💳 *پرداخت اشتراک جدید*\n"
                f"━━━━━━━━━━━━━━━━━\n\n"
                f"👤 کاربر: {a_name}\n"
                f"🆔 آیدی: `{user_id}`\n"
                f"💰 مبلغ: {total:,} {currency}\n"
                f"📦 محصول: اشتراک ویژه {SUBSCRIPTION_DURATION_DAYS} روزه\n"
                f"🔑 Charge ID: `{charge_id}`\n"
                f"🕒 زمان: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            for admin_id in [ADMIN_ID, PARTNER_ID]:
                if str(admin_id) != user_id:
                    try:
                        send_message(int(admin_id), admin_msg)
                    except Exception as e:
                        print(f"⚠️ Failed to notify admin {admin_id}: {e}")
        except Exception as e:
            print(f"⚠️ Admin notification error: {e}")

        return

    # ==================== 💳 خرید آیتم ====================
    if payload.startswith("item_"):
        parts = payload.split("_")
        if len(parts) != 5 or not parts[4].isdigit():
            print(f"❌ Invalid item payload on success: {payload}")
            return
        try:
            key = parts[1]
            qty = int(parts[2])
            buyer_uid = parts[3]
        except (ValueError, IndexError):
            print(f"❌ Invalid item payload parts on success: {payload}")
            return

        if key not in ITEM_PACKS or buyer_uid != user_id:
            print(f"❌ Item success validation failed: key={key} buyer={buyer_uid} vs {user_id}")
            return

        pack = ITEM_PACKS[key]
        if (not pack["min_qty"] <= qty <= pack["max_qty"]
                or currency != PAYMENT_CURRENCY
                or total != pack["price_per_unit"] * qty * 10):
            print(f"❌ Invalid item payment details for user {user_id}; manual review required")
            return
        payment_id = charge_id or provider_charge
        if payment_id and payment_id in p.get("processed_item_payments", []):
            print(f"⚠️ Duplicate item payment ignored: {payment_id}")
            return
        if not payment_id:
            print(f"⚠️ Item payment has no charge ID; cannot deduplicate user {user_id}")
        reward = pack["reward_per_unit"] * qty
        db[user_id]["item_buy_pending_invoice"] = 0

        # ==================== اعمال جایزه ====================
        if key == "level":
            from data import get_level_info
            cur_dmg = p.get("total_damage", 0)
            cur_lvl, _, _ = get_level_info(cur_dmg)
            target_lvl = cur_lvl + qty
            # XP لازم برای رسیدن به target_lvl:
            # total_damage برای level n = 50 * n * (n-1)
            target_xp = 50 * target_lvl * (target_lvl - 1)
            if cur_dmg < target_xp:
                db[user_id]["total_damage"] = target_xp
            success_msg = (f"🎉 *{qty} سطح* اضافه شد!\n"
                           f"📊 سطح جدید: *{target_lvl}*")

        elif key == "oil":
            db[user_id]["oil"] = p.get("oil", 0) + reward
            success_msg = f"🎉 *{reward:,} نفت* اضافه شد!"

        elif key == "coins":
            db[user_id]["coins"] = p.get("coins", 0) + reward
            success_msg = f"🎉 *{reward:,} سکه* اضافه شد!"

        elif key == "gems":
            db[user_id]["gems"] = p.get("gems", 0) + reward
            success_msg = f"🎉 *{reward:,} الماس* اضافه شد!"

        else:
            success_msg = f"🎉 جایزه اضافه شد!"

        if payment_id:
            p.setdefault("processed_item_payments", []).append(payment_id)
        save_db_now()

        try:
            send_message(chat_id,
                f"✅ *پرداخت موفق!*\n"
                f"━━━━━━━━━━━━━━━━━\n\n"
                f"{pack['emoji']} *{pack['name']}*\n\n"
                f"{success_msg}\n\n"
                f"🔑 کد پرداخت: `{charge_id}`")
        except Exception as e:
            print(f"⚠️ item success send: {e}")

        # اطلاع به ادمین
        try:
            admin_msg = (
                f"💳 *خرید آیتم جدید*\n"
                f"━━━━━━━━━━━━━━━━━\n\n"
                f"👤 کاربر: {p.get('name', user_name)}\n"
                f"🆔 آیدی: `{user_id}`\n"
                f"📦 محصول: {pack['name']} × {qty}\n"
                f"💰 مبلغ: {total:,} {currency}\n"
                f"🔑 Charge ID: `{charge_id}`\n"
                f"🕒 زمان: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            for admin_id in [ADMIN_ID, PARTNER_ID]:
                if str(admin_id) != user_id:
                    try:
                        send_message(int(admin_id), admin_msg)
                    except Exception:
                        pass
        except Exception as e:
            print(f"⚠️ item admin notify error: {e}")
        return

    # ==================== 🛒 World Shop ====================
    if payload.startswith("world_pass_"):
        if p.get("world_pass_active") and p.get("world_pass_days_claimed", 0) < WORLD_PASS_TOTAL_DAYS:
            db[user_id]["world_pass_pending_invoice"] = 0
            save_db_now()

            try:
                send_message(chat_id,
                    "⚠️ شما قبلاً یک World Shop فعال دارید.\n"
                    "پرداخت شما دریافت شد ولی نیازی به فعال‌سازی مجدد نیست.\n\n"
                    f"🔑 کد پرداخت: `{charge_id}`\n"
                    "📞 برای پیگیری به پشتیبانی پیام بدید.")
            except:
                pass
            print(f"⚠️ Double world_pass payment: {user_id} | charge={charge_id}")

            try:
                for admin_id in [ADMIN_ID, PARTNER_ID]:
                    if str(admin_id) != user_id:
                        send_message(int(admin_id),
                            f"⚠️ *پرداخت تکراری World Shop!*\n"
                            f"━━━━━━━━━━━━━━━━━\n\n"
                            f"👤 کاربر: {p.get('name', user_name)}\n"
                            f"🆔 آیدی: `{user_id}`\n"
                            f"💰 مبلغ: {total:,} {currency}\n"
                            f"🔑 Charge ID: `{charge_id}`")
            except:
                pass
            return

        db[user_id]["world_pass_active"] = True
        db[user_id]["world_pass_purchased_at"] = time.time()
        db[user_id]["world_pass_days_claimed"] = 0
        db[user_id]["world_pass_last_claim_date"] = ""
        db[user_id]["world_pass_payment_id"] = charge_id
        db[user_id]["world_pass_pending_invoice"] = 0
        save_db_now()

        print(f"✅ World Shop activated → user={user_id} | charge={charge_id}")

        success_text = (
            f"🎉 *پرداخت موفق!*\n"
            f"━━━━━━━━━━━━━━━━━\n\n"
            f"✅ *World Shop شما فعال شد!*\n\n"
            f"📦 *جوایز این فصل:*\n"
        )
        for r in WORLD_PASS_REWARDS:
            success_text += f"روز {r['day']} → {r['text']}\n"

        success_text += (
            f"\n━━━━━━━━━━━━━━━━━\n"
            f"🎁 *هر روز فقط یک جایزه* می‌تونی بگیری!\n"
            f"🔔 برای دریافت جایزه اول، دکمه زیر رو بزن:"
        )
        try:
            send_message(chat_id, success_text, {
                "inline_keyboard": [
                    [{"text": "🎁 دریافت جایزه روز 1",
                      "callback_data": "world_pass_claim"}],
                    [{"text": "⭐️ پنل World Shop",
                      "callback_data": "world_pass_open"}],
                ]
            })
        except Exception as e:
            print(f"⚠️ Failed to send success: {e}")

        try:
            a_name = db[user_id].get("name", user_name)
            admin_msg = (
                f"💳 *پرداخت World Shop جدید*\n"
                f"━━━━━━━━━━━━━━━━━\n\n"
                f"👤 کاربر: {a_name}\n"
                f"🆔 آیدی: `{user_id}`\n"
                f"💰 مبلغ: {total:,} {currency}\n"
                f"📦 محصول: World Shop (10 روز)\n"
                f"🔑 Charge ID: `{charge_id}`\n"
                f"🕒 زمان: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            for admin_id in [ADMIN_ID, PARTNER_ID]:
                if str(admin_id) != user_id:
                    try:
                        send_message(int(admin_id), admin_msg)
                    except Exception as e:
                        print(f"⚠️ Failed to notify admin {admin_id}: {e}")
        except Exception as e:
            print(f"⚠️ Admin notification error: {e}")

        return

    # ==================== payload ناشناخته ====================
    print(f"⚠️ Unknown payload in successful_payment: {payload}")
    try:
        send_message(chat_id,
            "⚠️ پرداخت دریافت شد ولی نوع آن نامشخص است.\n"
            f"🔑 کد پرداخت: `{charge_id}`\n"
            "📞 لطفاً به پشتیبانی پیام بدید.")
    except:
        pass