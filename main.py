import time
import random
import threading
import requests
import urllib3
from config import *
from data import WORLD_PASS_TOTAL_DAYS
from core import db, save_db, save_db_now, load_offset, save_offset, send_message
from handlers import (check_expired_transfers, send_box_to_channel)
from handlers_callback import handle_callback
from handlers_message import handle_message
from handlers_payment import handle_pre_checkout_query, handle_successful_payment
from performance import init_performance, processor, get_stats
from web_panel import start_web_panel

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ==================== حذف Webhook ====================
def delete_webhook():
    try:
        r = requests.get(f"{API_URL}/deleteWebhook", verify=False, timeout=10)
        result = r.json()
        if result.get("ok"):
            print("✅ Webhook حذف شد")
        else:
            print(f"⚠️ deleteWebhook: {result}")
    except Exception as e:
        print(f"⚠️ deleteWebhook خطا: {e}")


# ==================== ساخت کلن رسمی ====================
def ensure_official_clan():
    if "clans" not in db:
        db["clans"] = {}

    if OFFICIAL_CLAN_ID not in db["clans"]:
        db["clans"][OFFICIAL_CLAN_ID] = {
            "name": OFFICIAL_CLAN_NAME,
            "rank_points": 0,
            "leader_id": str(ADMIN_ID),
            "created_at": time.time(),
            "level": 1,
            "donated_coins": 0,
            "is_official": True,
        }
        save_db_now()
        print(f"✅ کلن رسمی «{OFFICIAL_CLAN_NAME}» ساخته شد!")
    else:
        c = db["clans"][OFFICIAL_CLAN_ID]
        changed = False
        if "level" not in c:
            c["level"] = 1
            changed = True
        if "donated_coins" not in c:
            c["donated_coins"] = 0
            changed = True
        if "is_official" not in c:
            c["is_official"] = True
            changed = True
        if changed:
            save_db_now()


# ==================== مهاجرت ====================
def migrate_old_users():
    migrated = 0
    for uid, p in db.items():
        if not isinstance(p, dict):
            continue
        if "user_id" not in p:
            continue
        changed = False

        for k, v in [
            ("combo_daily_count", 0), ("combo_daily_date", ""),
            ("fighter_base_level", 0), ("fighters_hero", {}),
            ("last_wheel", 0), ("selected_defense", None),
            ("selected_talisman", None), ("selected_missile", None),
            ("nuclear", {}), ("gems", 0),
            ("battle_target", None), ("battle_target_time", 0),
            ("iron", 0), ("iron_mine_level", 1), ("iron_last_dig", 0),
            ("steel", 0), ("steel_factory_level", 0), ("steel_last_dig", 0),
            ("weapon", 0), ("weapon_factory_level", 0), ("weapon_last_dig", 0),
            ("world_pass_active", False), ("world_pass_purchased_at", 0),
            ("world_pass_days_claimed", 0), ("world_pass_last_claim_date", ""),
            ("world_pass_payment_id", ""), ("world_pass_pending_invoice", 0),
            ("clan_war_selection", []), ("clan_war_action", None),
            ("clan_join_target", None),
            ("subscription_active", False),
            ("subscription_started_at", 0),
            ("subscription_expires_at", 0),
            ("subscription_last_mission_claim", ""),
            ("subscription_pending_invoice", 0),
            ("sub_shield_until", 0),
            ("sub_shield_used_today", 0),
            ("sub_shield_date", ""),
            ("selected_item_pack", None),
            ("item_buy_pending_invoice", 0),
        ]:
            if k not in p:
                p[k] = v
                changed = True

        if "weapons_house_level" not in p:
            old_lvl = p.get("arsenal_level", 1)
            if old_lvl > 5:
                old_lvl = 5
            p["weapons_house_level"] = old_lvl
            p["arsenal_level"] = 1
            changed = True

        if isinstance(p.get("fighters_hero"), dict):
            for fname, finfo in p["fighters_hero"].items():
                if isinstance(finfo, dict):
                    if "level" not in finfo:
                        finfo["level"] = 1
                        changed = True
                    if "hp_current" not in finfo:
                        from data import HERO_FIGHTERS
                        f_data = HERO_FIGHTERS.get(fname, {})
                        finfo["hp_current"] = f_data.get("hp", 50)
                        changed = True

        if changed:
            migrated += 1

    if "clans" in db and isinstance(db["clans"], dict):
        for cid, cdata in db["clans"].items():
            if not isinstance(cdata, dict):
                continue
            if "level" not in cdata:
                cdata["level"] = 1
                migrated += 1
            if "donated_coins" not in cdata:
                cdata["donated_coins"] = 0
                migrated += 1

    for tname in ("clan_wars", "clan_war_requests",
                  "clan_invites", "clan_requests",
                  "known_groups", "active_boxes"):
        if tname not in db:
            db[tname] = {}

    ensure_official_clan()

    if migrated > 0:
        save_db_now()
        print(f"✅ {migrated} کاربر/کلن قدیمی مهاجرت شدند")


# ==================== اسکجولرها ====================
def box_scheduler():
    time.sleep(60)
    print("✅ box_scheduler شروع شد")

    while True:
        try:
            sleep_sec = random.randint(3600, 7200)
            mins = sleep_sec // 60
            print(f"⏰ باکس بعدی: {mins} دقیقه دیگه")
            time.sleep(sleep_sec)

            send_box_to_channel()

        except Exception as e:
            print(f"❌ box_scheduler: {e}")
            time.sleep(60)


def pending_transfer_scheduler():
    while True:
        try:
            check_expired_transfers()
        except Exception as e:
            print(f"خطا انتقال: {e}")
        time.sleep(30)


def check_rank_reset():
    from datetime import datetime
    import os
    now = datetime.now()
    if now.month == 1 and now.day == 1:
        if os.path.exists(RANK_RESET_FILE):
            with open(RANK_RESET_FILE, "r") as f:
                if f.read().strip() == str(now.year):
                    return
        for uid, ud in db.items():
            if isinstance(ud, dict):
                ud["rank"] = 0
                ud["best_rank"] = 0
                ud["league"] = "🏵 مبتدی"
        save_db()
        with open(RANK_RESET_FILE, "w") as f:
            f.write(str(now.year))


def rank_reset_scheduler():
    while True:
        try:
            check_rank_reset()
        except Exception as e:
            print(f"خطای reset رنک: {e}")
        time.sleep(24 * 60 * 60)


def check_expired_invoices():
    if not isinstance(db, dict):
        return
    now = time.time()
    changed = False
    for uid, p in list(db.items()):
        if not isinstance(p, dict) or "user_id" not in p:
            continue

        # ==================== World Shop ====================
        pending = p.get("world_pass_pending_invoice", 0)
        if pending and now - pending >= 600:
            active = p.get("world_pass_active", False)
            claimed = p.get("world_pass_days_claimed", 0)
            if active and claimed < WORLD_PASS_TOTAL_DAYS:
                db[uid]["world_pass_pending_invoice"] = 0
                changed = True
            else:
                try:
                    send_message(int(uid),
                        "❌ *پرداخت ناموفق!*\n"
                        "━━━━━━━━━━━━━━━━━\n\n"
                        "⏱️ فاکتور World Shop شما تا ۱۰ دقیقه تکمیل نشد و منقضی شد.\n\n"
                        "💡 اگه مبلغ از حسابتون کم شده، حداکثر تا ۲۴ ساعت آینده به حسابتون برمی‌گرده.\n\n"
                        "🔻 برای تلاش دوباره:",
                        {"inline_keyboard": [[
                            {"text": "⭐️ تلاش مجدد", "callback_data": "world_pass_open"}
                        ]]}
                    )
                except Exception:
                    pass
                db[uid]["world_pass_pending_invoice"] = 0
                changed = True

        # ==================== 💳 خرید آیتم ====================
        item_pending = p.get("item_buy_pending_invoice", 0)
        if item_pending and now - item_pending >= 600:
            try:
                send_message(int(uid),
                    "❌ *پرداخت ناموفق!*\n"
                    "━━━━━━━━━━━━━━━━━\n\n"
                    "⏱️ فاکتور خرید آیتم شما تا ۱۰ دقیقه تکمیل نشد و منقضی شد.\n\n"
                    "💡 اگه مبلغ از حسابتون کم شده، حداکثر تا ۲۴ ساعت آینده به حسابتون برمی‌گرده.\n\n"
                    "🔻 برای تلاش دوباره:",
                    {"inline_keyboard": [[
                        {"text": "💳 فروشگاه آیتم", "callback_data": "item_shop"}
                    ]]}
                )
            except Exception:
                pass
            db[uid]["item_buy_pending_invoice"] = 0
            changed = True

    if changed:
        save_db()


def invoice_checker():
    while True:
        try:
            check_expired_invoices()
        except Exception as e:
            print(f"❌ invoice_checker: {e}")
        time.sleep(30)


def clan_war_scheduler():
    try:
        from clan_war import check_clan_war_timeouts, init_clan_war_fields
        init_clan_war_fields()
        print("✅ clan_war_scheduler شروع شد")
    except Exception as e:
        print(f"⚠️ خطا در init جنگ کلن: {e}")
        return

    while True:
        try:
            check_clan_war_timeouts()
        except Exception as e:
            print(f"❌ clan_war_scheduler: {e}")
        time.sleep(20)


def subscription_checker():
    print("✅ subscription_checker شروع شد")
    while True:
        try:
            now = time.time()
            changed = False
            for uid, p in db.items():
                if not isinstance(p, dict) or "user_id" not in p:
                    continue
                if not p.get("subscription_active"):
                    continue
                if now < p.get("subscription_expires_at", 0):
                    continue
                p["subscription_active"] = False
                changed = True
                try:
                    send_message(int(uid),
                        "❌ *اشتراک ویژه شما منقضی شد!*\n\n"
                        "⏱️ مدت ۳۰ روزه به پایان رسید.\n\n"
                        "🔻 برای تمدید:",
                        {"inline_keyboard": [[
                            {"text": "⭐️ تمدید اشتراک",
                             "callback_data": "other_subscription"}
                        ]]})
                except Exception:
                    pass
            if changed:
                save_db_now()
        except Exception as e:
            print(f"❌ subscription_checker: {e}")
        time.sleep(60)


def start_background_threads():
    threading.Thread(target=box_scheduler, daemon=True).start()
    threading.Thread(target=pending_transfer_scheduler, daemon=True).start()
    threading.Thread(target=rank_reset_scheduler, daemon=True).start()
    threading.Thread(target=invoice_checker, daemon=True).start()
    threading.Thread(target=clan_war_scheduler, daemon=True).start()
    threading.Thread(target=subscription_checker, daemon=True).start()


# ==================== پردازش آپدیت ====================
def process_update(update):
    if "pre_checkout_query" in update:
        try:
            handle_pre_checkout_query(update)
        except Exception as e:
            print(f"❌ خطا در pre_checkout_query: {e}")
        return

    if "callback_query" in update:
        try:
            handle_callback(update)
        except Exception as e:
            print(f"❌ خطا در callback: {e}")
        return

    if "message" in update:
        msg = update["message"]
        if "successful_payment" in msg:
            try:
                handle_successful_payment(update)
            except Exception as e:
                print(f"❌ خطا در successful_payment: {e}")
            return
        try:
            handle_message(update)
        except Exception as e:
            print(f"❌ خطا در message: {e}")
        return

    print(f"⚠️ آپدیت ناشناخته: {list(update.keys())}")


# ==================== حلقه اصلی ====================
def main():
    offset = load_offset()
    print("⚜️ World War ⚜️ is online")

    # فقط performance (پایه)
    init_performance()
    processor.set_handler(process_update)

    # حذف Webhook
    print("🧹 حذف Webhook...")
    delete_webhook()
    time.sleep(1)

    # Migration
    try:
        migrate_old_users()
    except Exception as e:
        print(f"⚠️ خطای مهاجرت: {e}")

    # Background threads
    start_background_threads()

    # Main loop
    stats_counter = 0
    while True:
        try:
            response = requests.get(
                f"{API_URL}/getUpdates",
                params={"offset": offset, "timeout": 30},
                verify=False, timeout=35)
            updates = response.json()

            if updates.get("ok"):
                result = updates["result"]

                pcq_updates = [u for u in result if "pre_checkout_query" in u]
                other_updates = [u for u in result if "pre_checkout_query" not in u]

                # PCQ sync
                for update in pcq_updates:
                    offset = update["update_id"] + 1
                    save_offset(offset)
                    try:
                        process_update(update)
                        print(f"⚡ PCQ: {update['update_id']}")
                    except Exception as e:
                        print(f"❌ PCQ error: {e}")

                # بقیه async
                for update in other_updates:
                    offset = update["update_id"] + 1
                    save_offset(offset)
                    processor.submit(update)

                # آمار هر ۱۰ batch
                stats_counter += 1
                if stats_counter % 10 == 0 and len(other_updates) > 0:
                    s = processor.stats()
                    print(f"📊 active={s['active']} done={s['done']} "
                          f"drop={s['drop']} err={s['err']}")

            else:
                err = updates.get("description", "?")
                print(f"⚠️ getUpdates not ok: {err}")
                if "webhook" in str(err).lower():
                    print("🔄 تلاش برای حذف Webhook مجدد...")
                    delete_webhook()
                    time.sleep(2)

        except Exception as e:
            print(f"خطای حلقه اصلی: {e}")
            time.sleep(2)

        try:
            save_db()
        except:
            pass


if __name__ == "__main__":
    start_web_panel()
    main()