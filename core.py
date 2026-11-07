import os
import time
import threading
import atexit
import requests
import urllib3
import shutil
from datetime import datetime
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from config import *

# ============ JSON engine ============
_ORJSON_OK = False
try:
    import orjson
    _t = orjson.dumps({"t": 1})
    if orjson.loads(_t) == {"t": 1}:
        _ORJSON_OK = True
except Exception:
    _ORJSON_OK = False

if _ORJSON_OK:
    def _dumps_bytes(obj): return orjson.dumps(obj)
    def _loads_bytes(b): return orjson.loads(b)
    def _dumps_str(obj): return orjson.dumps(obj).decode()
    JSON_MODE = "orjson ⚡"
else:
    import json as _std_json
    def _dumps_bytes(obj):
        return _std_json.dumps(obj, ensure_ascii=False,
                               separators=(",", ":")).encode("utf-8")
    def _loads_bytes(b):
        return _std_json.loads(b)
    def _dumps_str(obj):
        return _std_json.dumps(obj, ensure_ascii=False,
                               separators=(",", ":"))
    JSON_MODE = "json-compact"


# ============ DB load ============
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "rb") as f:
                return _loads_bytes(f.read())
        except Exception as e:
            print(f"⚠️ DB load error: {e}")
            if os.path.exists(DB_FILE + ".bak"):
                try:
                    with open(DB_FILE + ".bak", "rb") as f:
                        data = _loads_bytes(f.read())
                    print("✅ بازیابی از بکاپ")
                    return data
                except Exception as e2:
                    print(f"❌ بکاپ هم خراب: {e2}")
            return {}
    return {}


db = load_db()


# ============ Async DB writer ============
_db_dirty = False
_db_shutdown = False
_last_backup = 0


def save_db(force=False):
    global _db_dirty
    _db_dirty = True
    if force:
        _flush_db(backup=True)


def save_db_now():
    _flush_db(backup=True)


def _flush_db(backup=False):
    global _db_dirty, _last_backup
    try:
        data = _dumps_bytes(db)
        tmp = DB_FILE + ".tmp"
        with open(tmp, "wb") as f:
            f.write(data)
            f.flush()
            try:
                os.fsync(f.fileno())
            except Exception:
                pass
        os.replace(tmp, DB_FILE)
        _db_dirty = False

        now = time.time()
        if backup or (now - _last_backup > 60):
            try:
                shutil.copy2(DB_FILE, DB_FILE + ".bak")
                _last_backup = now
            except Exception:
                pass
    except Exception as e:
        print(f"❌ _flush_db: {e}")


def _db_writer():
    global _db_dirty
    while not _db_shutdown:
        time.sleep(2)
        if _db_dirty:
            _flush_db()


threading.Thread(target=_db_writer, daemon=True).start()


def _shutdown():
    global _db_shutdown, _db_dirty
    _db_shutdown = True
    if _db_dirty:
        _flush_db(backup=True)


atexit.register(_shutdown)


# ============ Offset (async) ============
_offset_value = 0
_offset_dirty = False


def load_offset():
    global _offset_value
    if os.path.exists(OFFSET_FILE):
        try:
            with open(OFFSET_FILE, "r") as f:
                _offset_value = int(f.read().strip())
            return _offset_value
        except Exception:
            return 0
    return 0


def save_offset(off):
    global _offset_value, _offset_dirty
    _offset_value = off
    _offset_dirty = True


def _offset_writer():
    global _offset_dirty
    while not _db_shutdown:
        time.sleep(3)
        if _offset_dirty:
            try:
                with open(OFFSET_FILE, "w") as f:
                    f.write(str(_offset_value))
                _offset_dirty = False
            except Exception:
                pass


threading.Thread(target=_offset_writer, daemon=True).start()


# ============ HTTP session pool ============
_tls = threading.local()


def _session():
    if not hasattr(_tls, "s"):
        s = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=20, pool_maxsize=50,
            max_retries=1, pool_block=False,
        )
        s.mount("https://", adapter)
        s.mount("http://", adapter)
        _tls.s = s
    return _tls.s


def _post(method, data, timeout=4):
    """🆕 timeout=4 (به جای 6) + reject 5xx errors"""
    try:
        r = _session().post(f"{API_URL}/{method}", json=data,
                            verify=False, timeout=timeout)
        # 🆕 اگه کد HTTP خطای سرور بود، سریع fail
        if r.status_code >= 500:
            return {"ok": False}
        return r.json()
    except Exception:
        return {"ok": False}


# ============ Fast send/edit ============
def send_message(chat_id, text, reply_markup=None, reply_to_message_id=None):
    data = {"chat_id": chat_id, "text": text}
    if reply_markup:
        data["reply_markup"] = _dumps_str(reply_markup)
    if reply_to_message_id:
        data["reply_to_message_id"] = reply_to_message_id
    return _post("sendMessage", data)


def edit_message(chat_id, message_id, text, reply_markup=None):
    data = {"chat_id": chat_id, "message_id": message_id, "text": text}
    if reply_markup:
        data["reply_markup"] = _dumps_str(reply_markup)
    result = _post("editMessageText", data)
    if result.get("ok"):
        return result

    desc = result.get("description", "").lower()
    if "message is not modified" in desc:
        return {"ok": True, "skipped": True}
    if "no text" in desc or "can't be edited" in desc:
        cap_data = {"chat_id": chat_id, "message_id": message_id, "caption": text}
        if reply_markup:
            cap_data["reply_markup"] = _dumps_str(reply_markup)
        return _post("editMessageCaption", cap_data)
    return result


def send_photo(chat_id, photo, caption=None, reply_markup=None):
    try:
        if os.path.exists(photo):
            with open(photo, "rb") as f:
                files = {"photo": f}
                data = {"chat_id": chat_id}
                if caption:
                    data["caption"] = caption
                if reply_markup:
                    data["reply_markup"] = _dumps_str(reply_markup)
                r = _session().post(f"{API_URL}/sendPhoto",
                                    data=data, files=files,
                                    verify=False, timeout=15)
            return r.json()
        else:
            data = {"chat_id": chat_id, "photo": photo}
            if caption:
                data["caption"] = caption
            if reply_markup:
                data["reply_markup"] = _dumps_str(reply_markup)
            return _post("sendPhoto", data)
    except Exception:
        return {"ok": False}


def show_alert(callback_id, text, show_alert=True):
    return _post("answerCallbackQuery", {
        "callback_query_id": callback_id,
        "text": text,
        "show_alert": show_alert
    })


def is_admin(user_id):
    return str(user_id) == str(ADMIN_ID) or str(user_id) == str(PARTNER_ID)


# ============ ⭐️ اشتراک ویژه ============
def is_subscription_active(user_id):
    p = db.get(str(user_id), {})
    if not p.get("subscription_active"):
        return False
    if time.time() >= p.get("subscription_expires_at", 0):
        return False
    return True


def get_subscription_days_left(user_id):
    p = db.get(str(user_id), {})
    exp = p.get("subscription_expires_at", 0)
    if exp <= time.time():
        return 0
    return max(0, int((exp - time.time()) / 86400))


# ============ User helpers ============
_NON_USER_KEYS = {
    "pending_transfers", "clan_wars", "clan_war_requests",
    "transfer_tokens", "clans", "gifts", "active_boxes",
    "clan_invites", "clan_requests", "known_groups",
}


def create_user(user_id, user_name):
    if user_id in _NON_USER_KEYS:
        return
    db[user_id] = {
        "name": user_name, "user_id": user_id,
        "join_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "coins": 0, "gems": 0, "rank": 0, "best_rank": 0,
        "league": "🌱 تازه‌کار",
        "cruise": {}, "ballistic": {}, "hypersonic": {},
        "chemical": {}, "nuclear": {}, "drones": {}, "defense": {}, "fighters": {},
        "mine_level": 1, "mine_coins": 0, "mine_last_dig": 0,
        "refinery_level": 0, "oil": 0, "oil_last_dig": 0, "refinery_oil": 0,
        "research_level": 1, "talisman_money": 0, "talisman_damage": 0,
        "talisman_rank": 0, "magic": 0,
        "talisman_money_count": 0, "talisman_damage_count": 0,
        "talisman_rank_count": 0,
        "talisman_eye_count": 0, "talisman_fire_count": 0,
        "talisman_water_count": 0, "talisman_storm_count": 0,
        "talisman_lightning_count": 0, "talisman_shield_count": 0,
        "talisman_hunt_count": 0, "talisman_ice_count": 0,
        "tal_action": None, "selected_missile": None,
        "selected_defense": None, "selected_talisman": None,
        "last_gift": 0,
        "clan": None, "clan_rank": 0, "clan_action": None,
        "clan_role": None, "clan_treasury": 0,
        "clan_war_selection": [],
        "clan_war_action": None,
        "clan_join_target": None,
        "banned": False, "admin_action": None,
        "factory_level": 0, "factory_iron": 0, "factory_last_dig": 0,
        "iron": 0, "iron_mine_level": 1, "iron_last_dig": 0,
        "steel": 0, "steel_factory_level": 0, "steel_last_dig": 0,
        "weapon": 0, "weapon_factory_level": 0, "weapon_last_dig": 0,
        "buildings": {},
        "airport_level": 0,
        "powerplant_level": 0, "powerplant_power": 0,
        "powerplant_last_dig": 0,
        "fatah2_count": 0,
        "combo_action": None,
        "combos": {},
        "arsenal_level": 1,
        "weapons_house_level": 1,
        "combo_pending": None,
        "total_damage": 0,
        "last_active": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "upgrades": {},
        "scientists_count": 1,
        "active_boost": None,
        "combo_daily_count": 0,
        "combo_daily_date": "",
        "fighter_base_level": 0,
        "fighters_hero": {},
        "last_wheel": 0,
        "battle_target": None,
        "battle_target_time": 0,
        "world_pass_active": False,
        "world_pass_purchased_at": 0,
        "world_pass_days_claimed": 0,
        "world_pass_last_claim_date": "",
        "world_pass_payment_id": "",
        "world_pass_pending_invoice": 0,
        # ⭐️ اشتراک ویژه
        "subscription_active": False,
        "subscription_started_at": 0,
        "subscription_expires_at": 0,
        "subscription_last_mission_claim": "",
        "subscription_pending_invoice": 0,
        "sub_shield_until": 0,
        "sub_shield_used_today": 0,
        "sub_shield_date": "",
    }
    save_db()


def reset_user_account(user_id, user_name):
    old = db.get(user_id, {})
    join = old.get("join_date", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    create_user(user_id, user_name)
    db[user_id]["join_date"] = join
    save_db()


# ============ Membership (cached) ============
_membership_cache = {}
_membership_ttl = 300


def check_membership(user_id):
    now = time.time()
    key = str(user_id)
    cache = _membership_cache.get(key)
    if cache and now - cache[1] < _membership_ttl:
        return cache[0]

    try:
        res = _session().get(f"{API_URL}/getChatMember",
                             params={"chat_id": f"@{CHANNEL_ID}",
                                     "user_id": user_id},
                             verify=False, timeout=6)
        d = res.json()
        if not d.get("ok"):
            return True, "error"
        if d.get("result", {}).get("status", "") in ["left", "kicked", "restricted"]:
            _membership_cache[key] = ((False, "channel1"), now)
            return False, "channel1"

        res3 = _session().get(f"{API_URL}/getChatMember",
                              params={"chat_id": f"@{CHANNEL_ID_2}",
                                      "user_id": user_id},
                              verify=False, timeout=6)
        d3 = res3.json()
        if not d3.get("ok"):
            return True, "error"
        if d3.get("result", {}).get("status", "") in ["left", "kicked", "restricted"]:
            _membership_cache[key] = ((False, "channel2"), now)
            return False, "channel2"

        _membership_cache[key] = ((True, "ok"), now)
        return True, "ok"
    except Exception:
        return True, "error"


def send_join_message(chat_id):
    send_message(chat_id,
        "⚠️ عضویت اجباری ⚠️\n\n"
        "برای استفاده از ربات، ابتدا باید عضو این کانال‌ها بشید:\n\n"
        "1️⃣ کانال رسمی World War\n"
        "2️⃣ کانال ScoreZone\n\n"
        "🔻 بعد از عضویت، روی «✅ عضو شدم» بزن:",
        {"inline_keyboard": [
            [{"text": "📢 کانال World War",
              "url": f"https://ble.ir/{CHANNEL_ID}"}],
            [{"text": "🎯 کانال ScoreZone",
              "url": f"https://ble.ir/{CHANNEL_ID_2}"}],
            [{"text": "✅ عضو شدم", "callback_data": "check_join"}],
        ]})


# ============ Transfers ============
def check_daily_transfer_limit(user_id, amount):
    today = datetime.now().strftime("%Y-%m-%d")
    p = db.get(user_id, {})
    if p.get("transfer_daily_date") != today:
        db[user_id]["transfer_daily"] = 0
        db[user_id]["transfer_daily_date"] = today
        save_db()
    limit = SUB_TRANSFER_LIMIT if is_subscription_active(user_id) else 2000
    return (p.get("transfer_daily", 0) + amount) <= limit


def add_daily_transfer(user_id, amount):
    today = datetime.now().strftime("%Y-%m-%d")
    p = db.get(user_id, {})
    if p.get("transfer_daily_date") != today:
        db[user_id]["transfer_daily"] = amount
        db[user_id]["transfer_daily_date"] = today
    else:
        db[user_id]["transfer_daily"] = p.get("transfer_daily", 0) + amount
    save_db()


# ============ Payment ============
def send_invoice(chat_id, title, description, payload, amount,
                 currency="IRR", provider_token=None):
    if provider_token is None:
        provider_token = WALLET_TOKEN
    return _post("sendInvoice", {
        "chat_id": chat_id,
        "title": title,
        "description": description,
        "payload": payload,
        "provider_token": provider_token,
        "currency": currency,
        "prices": [{"label": title, "amount": amount}],
    })


def answer_pre_checkout_query(pre_checkout_query_id, ok, error_message=None):
    data = {
        "pre_checkout_query_id": pre_checkout_query_id,
        "ok": ok,
    }
    if error_message:
        data["error_message"] = error_message
    for _ in range(2):
        try:
            result = _post("answerPreCheckoutQuery", data, timeout=5)
            if result.get("ok"):
                return result
        except Exception:
            pass
    return {"ok": False}