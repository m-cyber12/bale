# clan_war.py — جنگ کلن‌ها + ارتقای کلن
import time
import random
from datetime import datetime
from config import *
from core import (db, save_db, save_db_now, send_message, show_alert)
from data import *
from builders import get_clan_name, get_clan_members


# ==================== تنظیمات ====================
CLAN_WAR_MIN_PLAYERS = 3
CLAN_WAR_MAX_PLAYERS = 6
CLAN_WAR_DURATION = 15 * 60          # ۱۵ دقیقه
CLAN_UPGRADE_BASE_COST = 1000        # سطح 1→2 = 1000، 2→3 = 2000، ...
CLAN_MAX_LEVEL = 150


# ==================== init ====================
def init_clan_war_fields():
    if "clan_wars" not in db:
        db["clan_wars"] = {}
    if "clan_war_requests" not in db:
        db["clan_war_requests"] = {}


def get_clan_data(clan_id):
    if "clans" not in db or clan_id not in db["clans"]:
        return None
    c = db["clans"][clan_id]
    c.setdefault("level", 1)
    c.setdefault("donated_coins", 0)
    return c


def get_clan_level_cost(level):
    return CLAN_UPGRADE_BASE_COST * level


# ==================== UI انتخاب اعضا ====================
def build_clan_war_select_text(user_id):
    p = db.get(user_id, {})
    cid = p.get("clan_id")
    if not cid:
        return "❌ شما کلن ندارید!", None

    members = get_clan_members(cid)
    if len(members) < CLAN_WAR_MIN_PLAYERS:
        return (f"❌ کلن شما فقط {len(members)} عضو دارد!\n"
                f"برای جنگ حداقل {CLAN_WAR_MIN_PLAYERS} نفر لازم است."), None

    selected = p.get("clan_war_selection", [])
    text = (f"⚔️ *جنگ کلن‌ها - {get_clan_name(cid)}*\n\n"
            f"👥 اعضای کلن: {len(members)}\n"
            f"👑 رهبر (خودکار): {p.get('name')}\n\n"
            f"🔻 بازیکنان موردنظر رو انتخاب کن:\n"
            f"• حداقل: {CLAN_WAR_MIN_PLAYERS-1} نفر + خودت = {CLAN_WAR_MIN_PLAYERS}\n"
            f"• حداکثر: {CLAN_WAR_MAX_PLAYERS-1} نفر + خودت = {CLAN_WAR_MAX_PLAYERS}\n\n"
            f"📊 انتخاب‌شده: {len(selected)+1} نفر")
    return text, build_clan_war_select_keyboard(user_id, members, selected)


def build_clan_war_select_keyboard(user_id, members, selected):
    buttons = []
    row = []
    for uid, m in members:
        name = m.get("name", "کاربر")
        is_leader = m.get("clan_role") == "leader"
        if is_leader:
            mark = "👑"
        elif uid in selected:
            mark = "✅"
        else:
            mark = "⬜"
        row.append({"text": f"{mark} {name}", "callback_data": f"cwar_toggle_{uid}"})
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([{"text": f"🚀 شروع جستجو ({len(selected)+1} نفر)",
                     "callback_data": "cwar_start_search"}])
    buttons.append([{"text": "❌ لغو", "callback_data": "cwar_cancel"}])
    return {"inline_keyboard": buttons}


def toggle_clan_war_member(leader_id, member_id):
    p = db.get(leader_id, {})
    cid = p.get("clan_id")
    if not cid:
        return False, "❌ کلن ندارید!"
    m = db.get(member_id, {})
    if m.get("clan_id") != cid:
        return False, "❌ این عضو کلن شما نیست!"
    if m.get("clan_role") == "leader":
        return False, "👑 رهبر خودکار انتخاب می‌شود!"

    selected = list(p.get("clan_war_selection", []))
    if member_id in selected:
        selected.remove(member_id)
    else:
        if len(selected) >= CLAN_WAR_MAX_PLAYERS - 1:
            return False, f"❌ حداکثر {CLAN_WAR_MAX_PLAYERS} نفر!"
        selected.append(member_id)

    db[leader_id]["clan_war_selection"] = selected
    save_db()
    return True, "✅"


# ==================== شروع جستجو ====================
def start_clan_war_search(leader_id):
    p = db.get(leader_id, {})
    cid = p.get("clan_id")
    if not cid:
        return False, "❌ کلن ندارید!"
    if p.get("clan_role") != "leader":
        return False, "❌ فقط رهبر می‌تواند جنگ را شروع کند!"

    selected = p.get("clan_war_selection", [])
    total = len(selected) + 1
    if total < CLAN_WAR_MIN_PLAYERS:
        return False, f"❌ حداقل {CLAN_WAR_MIN_PLAYERS} نفر لازم است!"

    # کلن در حال جنگ فعال نباشد
    for wid, war in db.get("clan_wars", {}).items():
        if war.get("status") == "active" and cid in (war["clan1_id"], war["clan2_id"]):
            return False, "❌ کلن شما در حال جنگ است!"

    # درخواست تکراری
    for rid, req in db.get("clan_war_requests", {}).items():
        if req.get("leader_id") == leader_id and req.get("status") == "waiting":
            return False, "⏳ شما قبلاً درخواست داده‌اید!"

    req_id = f"CW{int(time.time())}{random.randint(100, 999)}"
    db["clan_war_requests"][req_id] = {
        "req_id": req_id,
        "clan_id": cid,
        "clan_name": get_clan_name(cid),
        "leader_id": leader_id,
        "members": [leader_id] + selected,
        "status": "waiting",
        "created_at": time.time(),
    }
    db[leader_id]["clan_war_selection"] = []
    save_db()

    if try_match_clan_wars(req_id):
        return True, "🎉 حریف پیدا شد! جنگ شروع می‌شود..."
    return True, "⏳ در انتظار کلن! (رهبر کلن دیگری هم باید جنگ را شروع کند)"


def try_match_clan_wars(my_req_id):
    my_req = db["clan_war_requests"].get(my_req_id)
    if not my_req:
        return False
    for other_rid, other in db["clan_war_requests"].items():
        if other_rid == my_req_id:
            continue
        if other.get("status") != "waiting":
            continue
        if other.get("clan_id") == my_req["clan_id"]:
            continue
        start_clan_war(my_req, other)
        return True
    return False


def start_clan_war(req1, req2):
    war_id = f"WAR{int(time.time())}{random.randint(100, 999)}"
    now = time.time()

    leader1, leader2 = req1["leader_id"], req2["leader_id"]
    other1 = [m for m in req1["members"] if m != leader1]
    other2 = [m for m in req2["members"] if m != leader2]
    random.shuffle(other1)
    random.shuffle(other2)

    # رهبر vs رهبر + بقیه رندوم
    pairs = [(leader1, leader2)]
    for i, m1 in enumerate(other1):
        pairs.append((m1, other2[i] if i < len(other2) else None))
    for i in range(len(other1), len(other2)):
        pairs.append((None, other2[i]))

    war = {
        "war_id": war_id,
        "clan1_id": req1["clan_id"], "clan2_id": req2["clan_id"],
        "clan1_name": req1["clan_name"], "clan2_name": req2["clan_name"],
        "clan1_members": req1["members"], "clan2_members": req2["members"],
        "matches": pairs,
        "scores": {},
        "status": "active",
        "created_at": now, "started_at": now,
        "ends_at": now + CLAN_WAR_DURATION,
        "clan1_total": 0, "clan2_total": 0,
    }
    db["clan_wars"][war_id] = war
    db["clan_war_requests"][req1["req_id"]]["status"] = "matched"
    db["clan_war_requests"][req2["req_id"]]["status"] = "matched"
    save_db()

    for uid in req1["members"] + req2["members"]:
        notify_clan_war_start(uid, war)


def notify_clan_war_start(uid, war):
    p = db.get(uid, {})
    cid = p.get("clan_id")
    opp_clan = war["clan2_name"] if cid == war["clan1_id"] else war["clan1_name"]

    opp_uid = None
    for a, b in war["matches"]:
        if a == uid: opp_uid = b; break
        if b == uid: opp_uid = a; break
    opp_name = db.get(opp_uid, {}).get("name", "نامشخص") if opp_uid else "—"

    text = (f"🚀 *جنگ کلن شروع شد* 🚀\n\n"
            f"⚔️ کلن شما: {get_clan_name(cid)}\n"
            f"🛡 حریف: {opp_clan}\n\n"
            f"🎯 حریف شما: {opp_name}\n"
            f"⏰ مدت: ۱۵ دقیقه\n\n"
            f"👑 وقت صدرت نماییه! پس سریع باش و حمله کن\n\n"
            f"🔻 فقط حمله ترکیبی مجاز است:")
    try:
        send_message(int(uid), text, {"inline_keyboard": [
            [{"text": "⚔️ حمله ترکیبی", "callback_data": f"cwar_attack_{war['war_id']}"}],
            [{"text": "📊 دیدن نتایج", "callback_data": f"cwar_results_{war['war_id']}"}],
        ]})
    except Exception as e:
        print(f"⚠️ notify {uid}: {e}")


# ==================== حمله در جنگ ====================
def do_clan_war_attack(uid, war_id):
    war = db.get("clan_wars", {}).get(war_id)
    if not war:
        return False, "❌ جنگ پیدا نشد!", None
    if war["status"] != "active":
        return False, "❌ جنگ به پایان رسیده!", None
    if time.time() > war["ends_at"]:
        return False, "❌ زمان جنگ تمام شده!", None
    if uid in war["scores"]:
        return False, "❌ شما قبلاً حمله کرده‌اید!", None

    opp_uid = None
    for a, b in war["matches"]:
        if a == uid: opp_uid = b; break
        if b == uid: opp_uid = a; break
    if not opp_uid or opp_uid not in db:
        return False, "❌ حریف پیدا نشد!", None

    from handlers import calculate_combo_attack
    from builders import build_combo_attack_report

    result = calculate_combo_attack(uid)
    if not result:
        return False, "❌ ترکیب نظامی نداری! اول ترکیب بساز.", None

    p = db[uid]
    target = db[opp_uid]

    # مصرف سلاح‌ها
    for w in result["weapons"]:
        wn, wcat, used = w["name"], w["category"], w["used"]
        if used <= 0: continue
        if wcat in p and wn in p[wcat]:
            cur = p[wcat][wn].get("count", 0)
            new = max(0, cur - used)
            if new <= 0:
                del p[wcat][wn]
            else:
                p[wcat][wn]["count"] = new

    fighter_bonus = result.get("fighter_bonus", 0)
    defense_pct = get_total_defense(target, "combo")

    total_dmg = result["damage"] + fighter_bonus
    defense_absorbed = int(total_dmg * defense_pct / 100)
    net_dmg = max(1, total_dmg - defense_absorbed)

    # HP پایه مدافع
    base_hp = 100 + target.get("arsenal_level", 1) * 50
    for bname, blvl in target.get("buildings", {}).items():
        base_hp += BUILDINGS_HP.get(bname, 100) + (blvl - 1) * 20

    destruction = min(100, int((net_dmg / base_hp) * 100)) if base_hp else 0
    if destruction >= 80:   stars = 3
    elif destruction >= 50: stars = 2
    elif destruction >= 20: stars = 1
    else:                   stars = 0

    war["scores"][uid] = {
        "points": stars, "stars": stars,
        "damage": net_dmg, "destruction": destruction,
        "opponent": opp_uid, "attacked_at": time.time(),
    }
    if p.get("clan_id") == war["clan1_id"]:
        war["clan1_total"] += stars
    else:
        war["clan2_total"] += stars
    save_db()

    # گزارش (مثل حمله ترکیبی معمولی)
    fake_loot = {"coins": 0, "oil": 0}
    report = build_combo_attack_report(
        attacker=p, target=target,
        raw_dmg=total_dmg, defense_pct=defense_pct,
        stolen_c=0, stolen_o=0,
        rank_gain=stars,
        weapons_used=result["weapons"],
        fighter_dmg=fighter_bonus,
        fighter_loot=fake_loot,
        fighter_note="",
        vernix_msgs=[], moon_note="",
        defender_had_coins=target.get("coins", 0),
        defender_had_oil=target.get("oil", 0),
        want_c=0, want_o=0,
    )
    report += f"\n\n━━━━━━━━━━━━━━━━━\n🏆 *امتیاز این حمله*: {stars} ستاره"
    return True, report, war_id


# ==================== پایان جنگ ====================
def finish_clan_war(war_id):
    war = db.get("clan_wars", {}).get(war_id)
    if not war or war["status"] == "finished":
        return
    war["status"] = "finished"
    war["finished_at"] = time.time()

    c1, c2 = war["clan1_total"], war["clan2_total"]

    if c1 > c2:
        winner, winner_id, rank_change = war["clan1_name"], war["clan1_id"], c1
    elif c2 > c1:
        winner, winner_id, rank_change = war["clan2_name"], war["clan2_id"], c2
    else:
        winner, winner_id, rank_change = "مساوی", None, 0

    if winner_id and "clans" in db and winner_id in db["clans"]:
        db["clans"][winner_id]["rank_points"] = (
            db["clans"][winner_id].get("rank_points", 0) + rank_change)
    save_db()

    best1 = _best_player(war["clan1_members"], war["scores"])
    best2 = _best_player(war["clan2_members"], war["scores"])

    for uid in war["clan1_members"] + war["clan2_members"]:
        my_cid = db.get(uid, {}).get("clan_id")
        is_c1 = my_cid == war["clan1_id"]
        sc = war["scores"].get(uid, {})
        my_pts, my_stars = sc.get("points", 0), sc.get("stars", 0)
        best = best1 if is_c1 else best2
        best_name = db.get(best, {}).get("name", "کاربر") if best else "—"
        best_pts = war["scores"].get(best, {}).get("points", 0) if best else 0

        text = (f"🏁 *نتیجه جنگ کلن‌ها*\n\n"
                f"⚔️ {war['clan1_name']}: *{c1}* امتیاز\n"
                f"⚔️ {war['clan2_name']}: *{c2}* امتیاز\n\n"
                f"🏆 برنده: *{winner}*\n")
        if rank_change > 0:
            text += f"📈 +{rank_change} رنک به کلن برنده\n"
        text += (f"\n━━━━━━━━━━━━━━━━━\n"
                 f"📊 *نتیجه شما:*\n"
                 f"⭐ ستاره: {'⭐'*my_stars if my_stars else '—'}\n"
                 f"🏆 امتیاز: {my_pts}\n\n"
                 f"👑 بهترین بازیکن کلن شما: {best_name} ({best_pts} امتیاز)")
        try:
            send_message(int(uid), text, {"inline_keyboard": [
                [{"text": "📊 نتایج کامل", "callback_data": f"cwar_results_{war_id}"}],
                [{"text": "🔙 بازگشت", "callback_data": "clan_war"}],
            ]})
        except: pass


def _best_player(members, scores):
    best, best_pts = None, -1
    for uid in members:
        pts = scores.get(uid, {}).get("points", 0)
        if pts > best_pts:
            best, best_pts = uid, pts
    return best


def check_clan_war_timeouts():
    if "clan_wars" not in db:
        return
    now = time.time()
    for wid, war in list(db["clan_wars"].items()):
        if war.get("status") == "active" and now >= war.get("ends_at", 0):
            finish_clan_war(wid)


# ==================== نمایش نتایج ====================
def build_war_results_text(war_id):
    war = db.get("clan_wars", {}).get(war_id)
    if not war:
        return "❌ جنگ پیدا نشد!"
    text = (f"📊 *نتایج جنگ کلن‌ها*\n\n"
            f"⚔️ {war['clan1_name']}: *{war['clan1_total']}*\n"
            f"⚔️ {war['clan2_name']}: *{war['clan2_total']}*\n\n"
            f"━━━━━━━━━━━━━━━━━\n")
    for i, (a, b) in enumerate(war["matches"], 1):
        an = db.get(a, {}).get("name", "—") if a else "—"
        bn = db.get(b, {}).get("name", "—") if b else "—"
        ast = war["scores"].get(a, {}).get("stars") if a else None
        bst = war["scores"].get(b, {}).get("stars") if b else None
        ad = '⭐'*ast if isinstance(ast, int) and ast > 0 else '—'
        bd = '⭐'*bst if isinstance(bst, int) and bst > 0 else '—'
        text += f"{i}. {an} {ad} vs {bn} {bd}\n"
    if war["status"] == "active":
        rem = max(0, int(war["ends_at"] - time.time()))
        text += f"\n⏰ باقی‌مانده: {rem//60}:{rem%60:02d}"
    else:
        text += "\n🏁 به پایان رسیده"
    return text


# ==================== ارتقای کلن ====================
def build_clan_upgrade_text(clan_id):
    c = get_clan_data(clan_id)
    if not c:
        return "❌ کلن پیدا نشد!"
    lvl = c.get("level", 1)
    if lvl >= CLAN_MAX_LEVEL:
        return f"🔧 *ارتقای کلن*\n\n📊 سطح: {lvl}/{CLAN_MAX_LEVEL}\n\n🚫 حداکثر سطح!"
    cost = get_clan_level_cost(lvl)
    donated = c.get("donated_coins", 0)
    rem = max(0, cost - donated)
    pct = min(100, int((donated / cost) * 100)) if cost else 100
    bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
    return (f"🔧 *ارتقای کلن*\n\n"
            f"🏰 {c['name']}\n"
            f"📊 سطح: *{lvl}* → *{lvl+1}*\n\n"
            f"💰 هزینه: {cost:,} سکه\n"
            f"💵 اهدا شده: {donated:,}/{cost:,}\n"
            f"⏳ باقی: {rem:,}\n\n"
            f"{bar} {pct}%\n\n"
            f"🔻 هر عضو می‌تواند اهدا کند:")


def build_clan_upgrade_keyboard(clan_id):
    c = get_clan_data(clan_id)
    if not c or c.get("level", 1) >= CLAN_MAX_LEVEL:
        return {"inline_keyboard": [[{"text": "🔙 بازگشت", "callback_data": "clan_back"}]]}
    return {"inline_keyboard": [
        [{"text": "💰 اهدای سکه", "callback_data": "clan_donate"}],
        [{"text": "🔙 بازگشت", "callback_data": "clan_back"}],
    ]}


def donate_to_clan(uid, amount):
    p = db.get(uid, {})
    cid = p.get("clan_id")
    if not cid:
        return False, "❌ کلن ندارید!"
    if amount <= 0:
        return False, "❌ مقدار باید مثبت باشد!"
    if p.get("coins", 0) < amount:
        return False, f"❌ فقط {p.get('coins', 0):,} سکه داری!"

    c = get_clan_data(cid)
    if not c:
        return False, "❌ کلن پیدا نشد!"
    lvl = c.get("level", 1)
    if lvl >= CLAN_MAX_LEVEL:
        return False, "🚫 حداکثر سطح!"

    cost = get_clan_level_cost(lvl)
    donated = c.get("donated_coins", 0)
    actual = min(amount, cost - donated)
    if actual <= 0:
        return False, "❌ هزینه این سطح کامل شده!"

    db[uid]["coins"] -= actual
    c["donated_coins"] = donated + actual

    leveled = False
    if c["donated_coins"] >= cost:
        old = lvl
        c["level"] = lvl + 1
        c["donated_coins"] = 0
        leveled = True

    save_db()

    if leveled:
        for muid, _ in get_clan_members(cid):
            try:
                send_message(int(muid),
                    f"🎉 *کلن با موفقیت ارتقا یافت!*\n\n"
                    f"📊 از سطح {old} به {c['level']}\n"
                    f"🏰 {c['name']}")
            except: pass
        return True, f"🎉 کلن به سطح {c['level']} ارتقا یافت!"
    return True, (f"✅ {actual:,} سکه اهدا شد!\n\n"
                  f"💰 اهدایی: {c['donated_coins']:,}/{cost:,}")