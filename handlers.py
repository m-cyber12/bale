import time
import json
import random
import threading
import requests
from datetime import datetime
from config import *
from core import (db, save_db, save_db_now, send_message, edit_message,
                  show_alert, is_admin, create_user, check_membership,
                  send_join_message, check_daily_transfer_limit,
                  add_daily_transfer, is_subscription_active)
from data import *


# ==================== 🎁 باکس شانسی ====================
BOX_PRIZES = [
    {"name": "400 سکه", "type": "coins", "amount": 400, "chance": 14},
    {"name": "800 سکه", "type": "coins", "amount": 800, "chance": 14},
    {"name": "1 شیمیایی", "type": "weapon", "weapon": "شیمیایی",
     "category": "chemical", "amount": 1, "chance": 14},
    {"name": "5 راون", "type": "weapon", "weapon": "راون",
     "category": "ballistic", "amount": 5, "chance": 15},
    {"name": "1 چشم", "type": "talisman", "talisman_key": "talisman_eye_count",
     "talisman_name": "چشم", "amount": 1, "chance": 14},
    {"name": "1 باور", "type": "defense", "defense": "باور",
     "amount": 1, "chance": 15},
    {"name": "100 سکه", "type": "coins", "amount": 100, "chance": 14},
]

# 🆕 Lock برای جلوگیری از Race Condition در claim_box
_box_claim_lock = threading.Lock()


def get_random_box_prize():
    """انتخاب رندوم یک جایزه از لیست با وزن"""
    total = sum(p["chance"] for p in BOX_PRIZES)
    rand = random.randint(1, total)
    cur = 0
    for prize in BOX_PRIZES:
        cur += prize["chance"]
        if rand <= cur:
            return prize
    return BOX_PRIZES[0]


def _get_box_groups():
    """دریافت گروه‌های شناخته‌شده از دیتابیس (خودکار)"""
    known = db.get("known_groups", {})
    if not isinstance(known, dict):
        return []
    groups = []
    for gid in known.keys():
        try:
            groups.append(int(gid))
        except (ValueError, TypeError):
            continue
    return groups


def apply_box_prize(user_id, prize):
    """اعمال جایزه باکس به کاربر"""
    t = prize["type"]
    if t == "coins":
        db[user_id]["coins"] = db[user_id].get("coins", 0) + prize["amount"]
        return f"🪙 {prize['amount']:,} سکه"
    elif t == "oil":
        db[user_id]["oil"] = db[user_id].get("oil", 0) + prize["amount"]
        return f"🛢 {prize['amount']:,} نفت"
    elif t == "weapon":
        cat = prize["category"]
        wn = prize["weapon"]
        if cat not in db[user_id]:
            db[user_id][cat] = {}
        if wn not in db[user_id][cat]:
            db[user_id][cat][wn] = {"count": 0, "level": 1}
        db[user_id][cat][wn]["count"] += prize["amount"]
        emoji = MISSILES.get(wn, {}).get("emoji", "🚀")
        return f"{emoji} {wn} × {prize['amount']}"
    elif t == "talisman":
        key = prize.get("talisman_key")
        tname = prize.get("talisman_name", "طلسم")
        if key:
            current = db[user_id].get(key, 0)
            if current >= 20:
                # 🆕 اگه پر بود، به سکه تبدیل می‌شه
                db[user_id]["coins"] = db[user_id].get("coins", 0) + 200
                return f"🪙 200 سکه (طلسم {tname} پر بود)"
            new_val = current + prize["amount"]
            db[user_id][key] = new_val
            return f"✨ {prize['amount']} طلسم {tname} (مجموع: {new_val}/20)"
        return f"✨ طلسم"
    elif t == "defense":
        dname = prize.get("defense")
        if dname:
            if "defense" not in db[user_id]:
                db[user_id]["defense"] = {}
            if dname not in db[user_id]["defense"]:
                db[user_id]["defense"][dname] = {"count": 0}
            db[user_id]["defense"][dname]["count"] += prize["amount"]
            if not db[user_id].get("active_defense"):
                db[user_id]["active_defense"] = dname
            emoji = DEFENSES.get(dname, {}).get("emoji", "🛡️")
            return f"{emoji} {dname} × {prize['amount']}"
        return "🛡️ پدافند"
    return "🎁 آیتم ناشناخته"


def create_new_box(prize=None):
    """ساخت باکس جدید با جایزه از پیش تعیین‌شده (مخفی)"""
    if "active_boxes" not in db:
        db["active_boxes"] = {}

    now = time.time()
    # پاکسازی باکس‌های قدیمی (بیش از ۲ ساعت)
    old_boxes = [bid for bid, b in db["active_boxes"].items()
                 if now - b.get("created_at", 0) > 7200]
    for bid in old_boxes:
        del db["active_boxes"][bid]

    if prize is None:
        prize = get_random_box_prize()

    box_id = f"BOX{int(now)}{random.randint(100, 999)}"
    db["active_boxes"][box_id] = {
        "created_at": now,
        "prize": prize,
        "winner_id": None,
        "winner_name": None,
        "claimed_at": None,
    }
    save_db()
    return box_id, prize


def send_box_to_group(chat_id, box_id):
    """ارسال پیام باکس به یک گروه"""
    text = (
        f"🎁 باکس شانسی ⚜️WORLD WAR⚜️\n\n"
        f"اولین نفری که روی دکمه‌های زیر بزنه می‌تونه جعبه شانسی رو باز کنه و یک آیتم رندوم برنده بشه!"
    )

    keyboard = {
        "inline_keyboard": [
            [{"text": "🎁 دریافت جعبه شانسی 🎁",
              "callback_data": f"claimbox_{box_id}"}]
        ]
    }

    try:
        send_message(chat_id, text, keyboard)
        print(f"📦 جعبه فرستاده شد به {chat_id} → {box_id}")
        return True
    except Exception as e:
        print(f"❌ خطا در ارسال جعبه به {chat_id}: {e}")
        return False


def send_box_to_channel():
    """
    ارسال باکس به نصف گروه‌ها → ۵ دقیقه صبر → نصف دیگه
    گروه‌ها به صورت خودکار از دیتابیس خونده می‌شن
    """
    groups = _get_box_groups()
    if not groups:
        print("⚠️ هیچ گروه شناخته‌شده‌ای وجود نداره!")
        print("   💡 ربات باید اول توی یه گروه پیام ببینه (مثلاً کاربر /start بزنه)")
        return

    print(f"📋 تعداد گروه‌های شناخته‌شده: {len(groups)}")

    random.shuffle(groups)
    half = len(groups) // 2

    # اگه فقط ۱ گروه، همش یه بار می‌ره
    if half == 0:
        first_half = groups[:1]
        second_half = []
    else:
        first_half = groups[:half]
        second_half = groups[half:]

    # ==================== نیمه اول ====================
    print(f"🎁 ارسال باکس به {len(first_half)} گروه (نیمه اول)...")
    for gid in first_half:
        box_id, prize = create_new_box()
        send_box_to_group(gid, box_id)

    # ==================== نیمه دوم ====================
    if second_half:
        delay = BOX_SPLIT_DELAY_SECONDS
        print(f"⏳ صبر {delay // 60} دقیقه برای نیمه دوم...")
        time.sleep(delay)

        print(f"🎁 ارسال باکس به {len(second_half)} گروه (نیمه دوم)...")
        for gid in second_half:
            box_id, prize = create_new_box()
            send_box_to_group(gid, box_id)

    print("✅ ارسال باکس‌ها کامل شد!")


def claim_box(user_id, box_id):
    """کاربر روی باکس کلیک می‌کنه — فقط نفر اول جایزه می‌گیره (با Lock ضد Race Condition)"""
    if "active_boxes" not in db:
        db["active_boxes"] = {}

    if box_id not in db["active_boxes"]:
        return False, "❌ این باکس دیگه فعال نیست!", None

    # 🆕 قفل: فقط یک thread در لحظه می‌تونه چک/ثبت کنه
    with _box_claim_lock:
        box = db["active_boxes"].get(box_id)
        if not box:
            return False, "❌ این باکس دیگه فعال نیست!", None

        # چک: قبلاً کسی گرفته؟
        if box.get("winner_id"):
            winner_name = box.get("winner_name", "یه نفر")
            return False, "❌ این باکس قبلاً باز شده!", winner_name

        # چک: کاربر توی دیتابیس هست؟
        if user_id not in db or not isinstance(db.get(user_id), dict):
            return False, "❌ لطفاً اول /start بزنید!", None

        # استفاده از جایزه از پیش تعیین‌شده
        prize = box.get("prize")
        if not prize:
            prize = get_random_box_prize()

        # اعمال جایزه به موجودی کاربر
        result = apply_box_prize(user_id, prize)

        # ثبت برنده (داخل قفل)
        box["winner_id"] = user_id
        box["winner_name"] = db[user_id].get("name", "کاربر")
        box["prize_result"] = result
        box["claimed_at"] = time.time()

        # ذخیره فوری
        save_db_now()

        return True, result, box["winner_name"]


# ==================== توابع دعوت ====================
def generate_invite_link(user_id):
    return f"https://ble.ir/{BOT_USERNAME}?start=invite_{user_id}"


def handle_invite_start(user_id, inviter_id, user_name):
    if user_id in db:
        return False
    if inviter_id not in db:
        return False
    if str(inviter_id) == str(user_id):
        return False

    create_user(user_id, user_name)
    db[user_id]["coins"] = NEW_USER_REWARD

    db[inviter_id]["coins"] = db[inviter_id].get("coins", 0) + INVITE_REWARD
    db[inviter_id]["invited_count"] = db[inviter_id].get("invited_count", 0) + 1

    if "invited_users" not in db[inviter_id]:
        db[inviter_id]["invited_users"] = []
    db[inviter_id]["invited_users"].append(user_id)

    save_db()
    return True


def build_invite_page(user_id):
    p = db.get(user_id, {})
    invited_count = p.get("invited_count", 0)
    link = generate_invite_link(user_id)

    text = (
        f"🎁 دعوت از دوستان\n\n"
        f"🔗 لینک دعوت اختصاصی شما:\n"
        f"{link}\n\n"
        f"👥 تعداد دعوت شده: {invited_count}\n"
        f"🎁 جایزه هر دعوت: 2000 سکه"
    )
    kb = {
        "inline_keyboard": [
            [{"text": "❌ لغو", "callback_data": "invite_cancel"}],
        ]
    }
    return text, kb


# ==================== انتقال اکانت ====================
def generate_transfer_token(user_id, user_name):
    import secrets as _sec
    token = _sec.token_hex(8).upper()
    token = f"{token[:4]}-{token[4:8]}-{token[8:12]}-{token[12:16]}"

    if "transfer_tokens" not in db:
        db["transfer_tokens"] = {}

    for t, info in list(db["transfer_tokens"].items()):
        if info.get("user_id") == user_id:
            del db["transfer_tokens"][t]

    db["transfer_tokens"][token] = {
        "user_id": user_id,
        "user_name": user_name,
        "created_at": time.time(),
        "expires_at": time.time() + 600,
    }
    save_db()
    return token


def check_transfer_token(token):
    if "transfer_tokens" not in db:
        return None, "no_tokens"

    token = token.strip().upper()
    if token not in db["transfer_tokens"]:
        return None, "invalid"

    info = db["transfer_tokens"][token]
    if time.time() > info["expires_at"]:
        del db["transfer_tokens"][token]
        save_db()
        return None, "expired"

    return info, "valid"


def transfer_account(old_user_id, new_user_id, new_user_name):
    old_data = dict(db.get(old_user_id, {}))
    old_name = old_data.get("name", "کاربر")

    new_data = {}
    for key, value in old_data.items():
        if key in ["user_id", "name"]:
            continue
        if isinstance(value, dict):
            new_data[key] = dict(value)
        elif isinstance(value, list):
            new_data[key] = list(value)
        else:
            new_data[key] = value

    new_data["user_id"] = new_user_id
    new_data["name"] = new_user_name
    new_data["join_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    db[new_user_id] = new_data

    from core import reset_user_account
    reset_user_account(old_user_id, old_name)

    save_db()


def create_pending_transfer(old_user_id, old_user_name, new_user_id,
                             new_user_name, token):
    if "pending_transfers" not in db:
        db["pending_transfers"] = {}

    transfer_id = f"T{int(time.time())}{random.randint(100, 999)}"

    db["pending_transfers"][transfer_id] = {
        "old_user_id": old_user_id,
        "old_user_name": old_user_name,
        "new_user_id": new_user_id,
        "new_user_name": new_user_name,
        "token": token,
        "created_at": time.time(),
        "expires_at": time.time() + 600,
        "status": "pending",
    }
    save_db()
    return transfer_id


def cancel_pending_transfer(transfer_id, reason="rejected"):
    if "pending_transfers" not in db:
        return
    if transfer_id not in db["pending_transfers"]:
        return

    info = db["pending_transfers"][transfer_id]
    old_user_id = info["old_user_id"]
    new_user_id = info["new_user_id"]

    if reason == "rejected":
        msg = "❌ درخواست انتقال اکانت لغو شد"
    else:
        msg = "⏱️ زمان تأیید تموم شد. درخواست لغو شد."

    for uid in [new_user_id, old_user_id]:
        try:
            send_message(int(uid), msg)
        except:
            pass

    del db["pending_transfers"][transfer_id]
    save_db()


def complete_pending_transfer(transfer_id):
    if "pending_transfers" not in db:
        return
    if transfer_id not in db["pending_transfers"]:
        return

    info = db["pending_transfers"][transfer_id]
    old_user_id = info["old_user_id"]
    new_user_id = info["new_user_id"]
    new_user_name = info["new_user_name"]
    token = info["token"]

    transfer_account(old_user_id, new_user_id, new_user_name)

    if token in db.get("transfer_tokens", {}):
        del db["transfer_tokens"][token]

    del db["pending_transfers"][transfer_id]
    save_db()

    try:
        send_message(int(new_user_id), "✅ انتقال اکانت موفق")
    except:
        pass

    try:
        send_message(int(old_user_id),
                     f"⚠️ اکانت شما منتقل شد\n\n"
                     f"اکانت شما به {new_user_name} منتقل شد")
    except:
        pass


def check_expired_transfers():
    if "pending_transfers" not in db:
        return
    if not isinstance(db["pending_transfers"], dict):
        db["pending_transfers"] = {}
        return

    now = time.time()
    expired = []
    for tid, info in db["pending_transfers"].items():
        if not isinstance(info, dict):
            continue
        if info.get("status") == "pending" and now >= info.get("expires_at", 0):
            expired.append(tid)

    for tid in expired:
        cancel_pending_transfer(tid, reason="timeout")


def get_weapon_power(name, category, level):
    return get_missile_damage(name, level, category) + get_loot_coins(name, level)


# ==================== 🎯 ترکیب نظامی ====================
def calculate_combo_attack(user_id):
    """محاسبه حمله ترکیبی — با محدودیت‌های پویا بر اساس سطح زرادخانه"""
    p = db.get(user_id, {})
    combos = p.get("combos", {})
    if not combos:
        return None

    best_cn = None
    best_power = -1
    best_active = None

    for cn_key, cn_data in combos.items():
        ws_check = cn_data.get("weapons", [])
        active_check = []
        power = 0

        for w in ws_check:
            wn = w.get("name", "")
            wc = w.get("count", 0)
            wcat = w.get("category", "")

            if is_wheel_only(wn):
                continue
            if not is_combo_allowed(wn):
                continue
            if wc <= 0 or wn not in p.get(wcat, {}):
                continue

            inv_count = p[wcat][wn].get("count", 0)
            if inv_count <= 0:
                continue

            actual_count = min(wc, inv_count)
            level = p[wcat][wn].get("level", 1)
            weapon_power = get_weapon_power(wn, wcat, level) * actual_count

            active_check.append({
                "name": wn,
                "category": wcat,
                "max_count": actual_count,
                "level": level,
                "power": get_weapon_power(wn, wcat, level),
            })
            power += weapon_power

        if power > best_power and active_check:
            best_power = power
            best_cn = cn_key
            best_active = active_check

    if best_cn is None or not best_active:
        return None

    cn = best_cn
    active = best_active

    active.sort(key=lambda x: x["power"], reverse=True)
    for w in active:
        w["used"] = w["max_count"]

    arsenal_lvl = p.get("arsenal_level", 1)
    if arsenal_lvl > ARSENAL_MAX_LEVEL:
        arsenal_lvl = ARSENAL_MAX_LEVEL
    limits = COMBO_LIMITS_BY_ARSENAL.get(arsenal_lvl, COMBO_LIMITS_BY_ARSENAL[1])
    combo_max_dmg = limits["damage"]
    combo_max_coin = limits["coins"]
    combo_max_oil = limits["oil"]

    def calc_totals(weapons):
        dmg = coin = oil = rank = 0
        for w in weapons:
            c = w["used"]
            dmg += get_missile_damage(w["name"], w["level"], w["category"]) * c
            coin += get_loot_coins(w["name"], w["level"]) * c
            oil += get_loot_oil(w["name"], w["level"]) * c
            rank += get_loot_rank(w["name"], w["level"]) * c
        return dmg, coin, oil, rank

    dmg, coin, oil, rank = calc_totals(active)

    for w in active:
        if (dmg <= combo_max_dmg and coin <= combo_max_coin
                and oil <= combo_max_oil):
            break
        while w["used"] > 0:
            if (dmg <= combo_max_dmg and coin <= combo_max_coin
                    and oil <= combo_max_oil):
                break
            w["used"] -= 1
            dmg -= get_missile_damage(w["name"], w["level"], w["category"])
            coin -= get_loot_coins(w["name"], w["level"])
            oil -= get_loot_oil(w["name"], w["level"])
            rank -= get_loot_rank(w["name"], w["level"])

    dmg, coin, oil, rank = calc_totals(active)

    rank = min(rank, COMBO_MAX_RANK)

    fighter_bonus = get_fighter_hero_bonus(p)

    return {
        "combo_name": cn,
        "weapons": active,
        "damage": dmg,
        "coins": coin,
        "oil": oil,
        "rank": rank,
        "fighter_bonus": fighter_bonus,
    }


def get_combo_menu(user_id):
    p = db.get(user_id, {})
    combos = p.get("combos", {})
    buttons = []
    if combos:
        buttons.append([{"text": "✏️ ویرایش ترکیب",
                         "callback_data": "combo_edit"}])
    else:
        buttons.append([{"text": "➕️ ساخت ترکیب جدید",
                         "callback_data": "combo_new"}])
    buttons.append([
        {"text": "🏗️ ساختمان‌ها", "callback_data": "combo_buildings"},
        {"text": "🏰 زرادخانه", "callback_data": "combo_armory"},
    ])
    buttons.append([
        {"text": "✈️ پایگاه جنگنده", "callback_data": "combo_fighter"},
    ])
    buttons.append([
        {"text": "📖 راهنما", "callback_data": "help_military"},
    ])
    buttons.append([{"text": "🔙 بازگشت به منوی اصلی", "callback_data": "shop_back"}])
    return {"inline_keyboard": buttons}


# ==================== 📖 راهنمای اصلی ====================
def get_guide_keyboard():
    return {"inline_keyboard": [
        [{"text": "🪙 معدن سکه", "callback_data": "guide_mine"},
         {"text": "🏭 پالایشگاه", "callback_data": "guide_refinery"}],
        [{"text": "🏭 کارخانه", "callback_data": "guide_factory"},
         {"text": "🏪 فروشگاه", "callback_data": "guide_shop"}],
        [{"text": "🧪 آزمایشگاه", "callback_data": "guide_lab"},
         {"text": "⚔️ تسلیحات خانه", "callback_data": "guide_arsenal"}],
        [{"text": "🎯 مدیریت ترکیب", "callback_data": "guide_military"},
         {"text": "✈️ پایگاه جنگنده", "callback_data": "guide_fighter_base"}],
        [{"text": "🎰 گردونه‌ها", "callback_data": "guide_wheel"},
         {"text": "🔮 طلسم", "callback_data": "guide_magic"}],
        [{"text": "🛩 فرودگاه", "callback_data": "guide_airport"},
         {"text": "🛡 پدافند", "callback_data": "guide_defense"}],
        [{"text": "🛩 پهباد", "callback_data": "guide_drone"},
         {"text": "🌐 حمله جهانی", "callback_data": "guide_battle"}],
        [{"text": "⚔️ حمله در گپ", "callback_data": "guide_attack"},
         {"text": "📊 رنکینگ", "callback_data": "guide_ranking"}],
        [{"text": "👥 کلن", "callback_data": "guide_clan"},
         {"text": "🏅 لیگ‌ها", "callback_data": "guide_league"}],
        [{"text": "🎁 جایزه روزانه", "callback_data": "guide_gift"},
         {"text": "💳 تبادل سکه", "callback_data": "guide_transfer"}],
        [{"text": "📥 انتقال اکانت", "callback_data": "guide_account_transfer"},
         {"text": "🎁 دعوت", "callback_data": "guide_invite"}],
        [{"text": "🪪 دارایی", "callback_data": "guide_profile"}],
        [{"text": "🔙 بازگشت به منوی اصلی", "callback_data": "go_main"}],
    ]}


def get_other_inline_keyboard(user_id):
    is_sub = is_subscription_active(user_id)
    base = [
        [{"text": "💬 گپ رسمی", "url": f"https://ble.ir/{GAP_ID}"}],
        [{"text": "📞 پشتیبانی", "callback_data": "other_support"},
         {"text": "🎁 جایزه روزانه", "callback_data": "other_gift"}],
        [{"text": "💰 تبادل سکه", "callback_data": "other_transfer"}],
        [{"text": f"⭐️ اشتراک ویژه{' ✅' if is_sub else ''}",
          "callback_data": "other_subscription"}],
    ]
    if is_admin(user_id):
        base.append([{"text": "🔐 پنل ادمین",
                      "callback_data": "other_admin"}])
    base.append([{"text": "🔙 بازگشت به منوی اصلی",
                  "callback_data": "go_main"}])
    return {"inline_keyboard": base}


def get_other_keyboard(user_id):
    if is_admin(user_id):
        return {"keyboard": [
            [{"text": "📢 گپ رسمی"}, {"text": "📢 کانال رسمی"}],
            [{"text": "🔐 پنل ادمین"}],
            [{"text": "🔙 بازگشت"}],
        ], "resize_keyboard": True}
    return {"keyboard": [
        [{"text": "📢 گپ رسمی"}],
        [{"text": "🔙 بازگشت"}],
    ], "resize_keyboard": True}


def get_buildings_keyboard(user_id):
    p = db.get(user_id, {})
    buildings = p.get("buildings", {})
    items = []
    for name, info in BUILDINGS.items():
        if name in buildings:
            items.append({"text": f"{info['emoji']} {name} (سطح {buildings[name]})",
                          "callback_data": f"bld_{name}"})
        else:
            items.append({"text": f"{info['emoji']} خرید {name} ({info['price']} سکه)",
                          "callback_data": f"bld_{name}"})
    buttons = []
    for i in range(0, len(items), 2):
        buttons.append(items[i:i + 2])
    buttons.append([{"text": "🔙 بازگشت به منوی اصلی", "callback_data": "go_main"}])
    return {"inline_keyboard": buttons}


def get_buildings_text(user_id):
    p = db.get(user_id, {})
    buildings = p.get("buildings", {})
    arsenal_level = p.get("arsenal_level", 1)

    text = "🎯 ترکیب نظامی\n\n🏗️ ساختمون‌های شما:\n\n"
    text += f"🏰 سطح زرادخانه: *{arsenal_level}/{ARSENAL_MAX_LEVEL}*\n"
    text += "⚠️ برای ارتقای هر ساختمان، سطح زرادخانه باید از سطح جدید ساختمان بالاتر یا برابر باشد\n\n"

    if not buildings:
        text += "❌ هنوز هیچ ساختمونی نساختی!\n"
    else:
        total = 0
        for name, level in buildings.items():
            if name in BUILDINGS:
                per = BUILDINGS[name]["per_level"]
                defense = level * per
                total += defense
                text += (f"{BUILDINGS[name]['emoji']} {name}: سطح {level} "
                         f"— 🛡️ {defense}٪ دفاع\n")
        if total > 100:
            total = 100
        text += f"\n📊 کل دفاع: {total}٪ (دمیج جنگنده کم می‌شه)"
    return text


# ==================== کیبوردهای اصلی ====================
reply_keyboard = {
    "keyboard": [
        [{"text": "🌐 حمله جهانی"}, {"text": "🎯 مدیریت ترکیب"}],
        [{"text": "📊 رنکینگ"}, {"text": "🪪 دارایی"}, {"text": "🏪 فروشگاه"}],
        [{"text": "💥 تسلیحات"}, {"text": "🛩 فرودگاه"}, {"text": "🏦 منابع"}],
        [{"text": "❓ راهنما"}, {"text": "🧪 آزمایشگاه"},
         {"text": "🎁 جایزه روزانه"}, {"text": "🎰 گردونه"}],
        [{"text": "👥 کلن"}, {"text": "🛒 World Shop"}, {"text": "📁 سایر"}],
        [{"text": "💳 خرید آیتم"}],
    ],
    "resize_keyboard": True,
}

admin_keyboard = {
    "keyboard": [
        [{"text": "📊 آمار ربات"}],
        [{"text": "🪙 دادن سکه"}, {"text": "🚫 بن کاربر"}],
        [{"text": "🔄 ریست رنک‌ها"}, {"text": "📢 پیام همگانی"}],
        [{"text": "🔙 بازگشت"}],
    ],
    "resize_keyboard": True,
}

inline_keyboard = {
    "inline_keyboard": [
        [{"text": "📢 کانال رسمی", "url": f"https://ble.ir/{CHANNEL_ID}"}],
        [{"text": "💬 گپ رسمی", "url": f"https://ble.ir/{GAP_ID}"}],
        [{"text": "🆘 پشتیبانی", "url": f"https://ble.ir/{SUPPORT_ID}"}],
        [{"text": "⚖️ قوانین ربات", "callback_data": "show_rules"}],
    ]
}

gap_inline_keyboard = {
    "inline_keyboard": [
        [{"text": "📢 کانال رسمی", "url": f"https://ble.ir/{CHANNEL_ID}"}],
        [{"text": "💬 گپ رسمی", "url": f"https://ble.ir/{GAP_ID}"}],
        [{"text": "🆘 پشتیبانی", "url": f"https://ble.ir/{SUPPORT_ID}"}],
        [{"text": "⚖️ قوانین ربات", "callback_data": "show_rules"}],
    ]
}

channel_inline_keyboard = {
    "inline_keyboard": [
        [{"text": "📢 ورود به کانال رسمی",
          "url": f"https://ble.ir/{CHANNEL_ID}"}]
    ]
}

shop_inline_keyboard = {
    "inline_keyboard": [
        [{"text": "🏪 ورود به فروشگاه", "url": SHOP_URL}]
    ]
}

talisman_keyboard = {
    "inline_keyboard": [
        [{"text": "🪙 طلسم پول", "callback_data": "talisman_money"}],
        [{"text": "⚡ طلسم دمیج", "callback_data": "talisman_damage"}],
        [{"text": "🥇 طلسم رنک", "callback_data": "talisman_rank"}],
        [{"text": "🔙 بازگشت به منوی اصلی", "callback_data": "go_main"}],
    ]
}

buy_keyboard = {
    "inline_keyboard": [
        [{"text": "❌ لغو", "callback_data": "buy_cancel"}],
    ]
}


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


def send_ticket_to_admins(user_id, user_name, message):
    for admin_id in [ADMIN_ID, PARTNER_ID]:
        try:
            requests.post(f"{API_URL}/sendMessage", json={
                "chat_id": admin_id,
                "text": (f"🎫 تیکت جدید\n\n"
                         f"👤 کاربر: {user_name}\n"
                         f"🆔 آیدی: {user_id}\n"
                         f"📝 پیام:\n\n{message}"),
            }, verify=False, timeout=10)
        except:
            pass
    return True


def give_pack(admin_id, target_id, pack_type, amount):
    if str(admin_id) not in [str(ADMIN_ID), str(PARTNER_ID)]:
        return "❌ شما ادمین نیستید!"

    if target_id not in db or not isinstance(db.get(target_id), dict):
        return "❌ کاربر پیدا نشد!"

    p = db[target_id]
    name = p.get("name", "کاربر")

    if pack_type == "سکه":
        p["coins"] = p.get("coins", 0) + amount
        save_db()
        return f"✅ {amount} سکه به {name} داده شد!"
    elif pack_type == "نفت":
        p["oil"] = p.get("oil", 0) + amount
        save_db()
        return f"✅ {amount} نفت به {name} داده شد!"
    elif pack_type == "رنک":
        p["rank"] = p.get("rank", 0) + amount
        if p["rank"] > p.get("best_rank", 0):
            p["best_rank"] = p["rank"]
        save_db()
        return f"✅ {amount} رنک به {name} داده شد!"
    elif pack_type == "جم":
        p["gems"] = p.get("gems", 0) + amount
        save_db()
        return f"✅ {amount} جم به {name} داده شد!"

    if pack_type in MISSILES:
        cat = MISSILES[pack_type]["category"]
        if cat not in p:
            db[target_id][cat] = {}
        if pack_type not in p[cat]:
            db[target_id][cat][pack_type] = {"count": 0, "level": 1}
        p[cat][pack_type]["count"] = p[cat][pack_type].get("count", 0) + amount
        save_db()
        return f"✅ {amount} عدد {pack_type} به {name} داده شد!"

    if pack_type in HERO_FIGHTERS:
        give_fighter(p, pack_type, amount)
        save_db()
        return f"✅ {amount} عدد {pack_type} (جنگنده) به {name} داده شد!"

    return "❌ نوع پک نامعتبر!"


# ==================== 🎁 جایزه روزانه ====================
DAILY_GIFT_PRIZES = [
    {"name": "4 عدد راون", "type": "weapon", "weapon": "راون",
     "category": "ballistic", "amount": 4, "chance": 8, "emoji": "⚔️"},
    {"name": "10 عدد اطلس", "type": "weapon", "weapon": "اطلس",
     "category": "cruise", "amount": 10, "chance": 20, "emoji": "🚀"},
    {"name": "500 سکه", "type": "coins", "amount": 500,
     "chance": 55, "emoji": "🪙"},
    {"name": "200 سکه", "type": "coins", "amount": 200,
     "chance": 100, "emoji": "🪙"},
]

DAILY_GIFT_PRIZES_SUB = [
    {"name": f"{SUB_DAILY_GEMS_AMOUNT} الماس", "type": "gems",
     "amount": SUB_DAILY_GEMS_AMOUNT, "chance": 10, "emoji": "💎"},
    {"name": "4 عدد راون", "type": "weapon", "weapon": "راون",
     "category": "ballistic", "amount": 4, "chance": 18, "emoji": "⚔️"},
    {"name": "10 عدد اطلس", "type": "weapon", "weapon": "اطلس",
     "category": "cruise", "amount": 10, "chance": 30, "emoji": "🚀"},
    {"name": "500 سکه", "type": "coins", "amount": 500,
     "chance": 65, "emoji": "🪙"},
    {"name": "200 سکه", "type": "coins", "amount": 200,
     "chance": 100, "emoji": "🪙"},
]


def roll_daily_gift(is_subscriber=False):
    prizes = DAILY_GIFT_PRIZES_SUB if is_subscriber else DAILY_GIFT_PRIZES
    roll = random.randint(1, 100)
    for prize in prizes:
        if roll <= prize["chance"]:
            return prize
    return prizes[-1]


def apply_daily_gift_prize(p, prize):
    t = prize.get("type")
    if t == "coins":
        p["coins"] = p.get("coins", 0) + prize["amount"]
    elif t == "gems":
        p["gems"] = p.get("gems", 0) + prize["amount"]
    elif t == "weapon":
        cat = prize["category"]
        wn = prize["weapon"]
        if cat not in p:
            p[cat] = {}
        if wn not in p[cat]:
            p[cat][wn] = {"count": 0, "level": 1}
        p[cat][wn]["count"] = p[cat][wn].get("count", 0) + prize["amount"]
    return True


def format_remaining_time(seconds):
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0 and m > 0:
        return f"{h} ساعت و {m} دقیقه"
    elif h > 0:
        return f"{h} ساعت و {m} دقیقه"
    elif m > 0:
        return f"{m} دقیقه و {s} ثانیه"
    else:
        return f"{s} ثانیه"


def apply_rank_change(attacker_id, defender_id, rank_gain):
    today_str = datetime.now().strftime("%Y-%m-%d")
    attacker_id = str(attacker_id)
    defender_id = str(defender_id)

    if db[attacker_id].get("rank_date") != today_str:
        db[attacker_id]["rank_today"] = 0
    db[attacker_id]["rank"] = db[attacker_id].get("rank", 0) + rank_gain
    if db[attacker_id]["rank"] > db[attacker_id].get("best_rank", 0):
        db[attacker_id]["best_rank"] = db[attacker_id]["rank"]
    db[attacker_id]["rank_today"] = db[attacker_id].get("rank_today", 0) + rank_gain
    db[attacker_id]["rank_date"] = today_str

    if defender_id and defender_id in db:
        if db[defender_id].get("rank_date") != today_str:
            db[defender_id]["rank_today"] = 0
        db[defender_id]["rank"] = max(0, db[defender_id].get("rank", 0) - rank_gain)
        db[defender_id]["rank_today"] = db[defender_id].get("rank_today", 0) - rank_gain
        db[defender_id]["rank_date"] = today_str