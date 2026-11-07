import random

# ==================== موشک‌های جدید استاروار ====================
MISSILES = {
    # ==================== کروز ====================
    "اطلس": {"price": 30, "level": 1, "min_dmg": 3, "max_dmg": 6,
             "category": "cruise", "shop": True, "emoji": "🚀"},
    "هویزه": {"price": 40, "level": 2, "min_dmg": 4, "max_dmg": 7,
              "category": "cruise", "shop": True, "emoji": "🏹"},
    "فالکون": {"price": 55, "level": 4, "min_dmg": 5, "max_dmg": 9,
               "category": "cruise", "shop": True, "emoji": "🦅"},
    "اسپکترا": {"price": 70, "level": 7, "min_dmg": 7, "max_dmg": 10,
                "category": "cruise", "shop": True, "emoji": "💠"},

    # ==================== بالستیک ====================
    "عماد": {"price": 100, "level": 3, "min_dmg": 10, "max_dmg": 13,
             "category": "ballistic", "shop": True, "emoji": "🗡️"},
    "ونگارد": {"price": 120, "level": 6, "min_dmg": 11, "max_dmg": 15,
               "category": "ballistic", "shop": True, "emoji": "⚔️"},
    "ذوالفقار": {"price": 140, "level": 9, "min_dmg": 12, "max_dmg": 17,
                 "category": "ballistic", "shop": True, "emoji": "🗡️"},
    "رپتور": {"price": 170, "level": 11, "min_dmg": 15, "max_dmg": 25,
              "category": "ballistic", "shop": True, "emoji": "🦖"},
    "راون": {"price": 220, "level": 14, "min_dmg": 23, "max_dmg": 30,
             "category": "ballistic", "shop": True, "emoji": "🦅",
             "special": "steal_coins_per_level"},

    # ==================== هایپرسونیک ====================
    "بلیزارد": {"price": 250, "level": 7, "min_dmg": 25, "max_dmg": 29,
                "category": "hypersonic", "shop": True, "emoji": "❄️"},
    "فتاح": {"price": 280, "level": 10, "min_dmg": 28, "max_dmg": 35,
             "category": "hypersonic", "shop": True, "emoji": "⚡"},
    "زفیکس": {"price": 300, "level": 13, "min_dmg": 30, "max_dmg": 40,
              "category": "hypersonic", "shop": True, "emoji": "🌀"},
    "خرمشهر": {"price": 340, "level": 15, "min_dmg": 35, "max_dmg": 45,
               "category": "hypersonic", "shop": True, "emoji": "🏙️"},
    "آذرخش": {"price": 370, "level": 20, "min_dmg": 40, "max_dmg": 50,
              "category": "hypersonic", "shop": True, "emoji": "🌩️"},

    # ==================== شیمیایی ====================
    "شیمیایی": {"price": 400, "level": 10, "min_dmg": 25, "max_dmg": 40,
                "category": "chemical", "shop": True, "emoji": "☣️"},

    # ==================== هسته‌ای ====================
    "هسته‌ای": {"price": 3000, "level": 20, "min_dmg": 100, "max_dmg": 300,
                "category": "nuclear", "shop": True, "emoji": "☢️",
                "gems": 5, "unblockable": True},

    # ==================== کروز قدیمی ====================
    "تاماهاک": {"price": 30, "level": 1, "min_dmg": 3, "max_dmg": 6,
                "category": "cruise", "shop": False, "emoji": "🎯"},
    "پاوه": {"price": 50, "level": 2, "min_dmg": 5, "max_dmg": 8,
             "category": "cruise", "shop": False, "emoji": "⚔️"},
    "قدر": {"price": 70, "level": 3, "min_dmg": 6, "max_dmg": 9,
            "category": "cruise", "shop": False, "emoji": "💪"},
    "وایپر": {"price": 80, "level": 3, "min_dmg": 7, "max_dmg": 11,
              "category": "cruise", "shop": False, "emoji": "🐍"},
    "ایگل": {"price": 90, "level": 4, "min_dmg": 8, "max_dmg": 12,
             "category": "cruise", "shop": False, "emoji": "🦅"},
    "تایتان": {"price": 100, "level": 4, "min_dmg": 9, "max_dmg": 13,
               "category": "cruise", "shop": False, "emoji": "⚙️"},

    # ==================== بالستیک قدیمی ====================
    "شهاب 3": {"price": 100, "level": 1, "min_dmg": 10, "max_dmg": 13,
               "category": "ballistic", "shop": False, "emoji": "☄️"},
    "قدر ب": {"price": 120, "level": 1, "min_dmg": 11, "max_dmg": 14,
              "category": "ballistic", "shop": False, "emoji": "🔱"},
    "خیبرشکن": {"price": 160, "level": 1, "min_dmg": 13, "max_dmg": 16,
                "category": "ballistic", "shop": False, "emoji": "🔥"},
    "فتاح 110": {"price": 180, "level": 2, "min_dmg": 14, "max_dmg": 18,
                 "category": "ballistic", "shop": False, "emoji": "⚡"},
    "اسکندر": {"price": 260, "level": 4, "min_dmg": 18, "max_dmg": 22,
               "category": "ballistic", "shop": False, "emoji": "🏹"},
    "رعد": {"price": 280, "level": 4, "min_dmg": 19, "max_dmg": 25,
            "category": "ballistic", "shop": False, "emoji": "⚡"},

    # ==================== هایپرسونیک قدیمی ====================
    "آوانگارد": {"price": 400, "level": 20, "min_dmg": 42, "max_dmg": 52,
                 "category": "hypersonic", "shop": False, "emoji": "🎯"},
    "کینژال": {"price": 420, "level": 20, "min_dmg": 44, "max_dmg": 55,
               "category": "hypersonic", "shop": False, "emoji": "❄️"},
    "سیمرغ": {"price": 550, "level": 25, "min_dmg": 55, "max_dmg": 70,
              "category": "hypersonic", "shop": False, "emoji": "🦅"},
    "ققنوس": {"price": 580, "level": 28, "min_dmg": 58, "max_dmg": 75,
              "category": "hypersonic", "shop": False, "emoji": "🦅"},

    # ==================== گردونه طوفان — کروز انحصاری ====================
    "موج": {"price": 100, "level": 1, "min_dmg": 8, "max_dmg": 12,
            "category": "cruise", "shop": False, "emoji": "🌊",
            "wheel_only": True, "upgradeable": False, "combo_allowed": False,
            "rank_override": 4},
    "افعی": {"price": 150, "level": 1, "min_dmg": 12, "max_dmg": 18,
             "category": "cruise", "shop": False, "emoji": "🐍",
             "wheel_only": True, "upgradeable": False, "combo_allowed": False,
             "rank_override": 5},
    "عقرب": {"price": 225, "level": 1, "min_dmg": 18, "max_dmg": 25,
             "category": "cruise", "shop": False, "emoji": "🦂",
             "wheel_only": True, "upgradeable": False, "combo_allowed": False,
             "rank_override": 7},

    # ==================== گردونه شکار — بالستیک انحصاری ====================
    "اسنایپر": {"price": 375, "level": 1, "min_dmg": 30, "max_dmg": 40,
                "category": "ballistic", "shop": False, "emoji": "🎯",
                "wheel_only": True, "upgradeable": False, "combo_allowed": False,
                "rank_override": 11},
    "هایدرا": {"price": 500, "level": 1, "min_dmg": 40, "max_dmg": 55,
               "category": "ballistic", "shop": False, "emoji": "☠️",
               "wheel_only": True, "upgradeable": False, "combo_allowed": False,
               "rank_override": 13},
    "اژدها": {"price": 650, "level": 1, "min_dmg": 50, "max_dmg": 70,
              "category": "ballistic", "shop": False, "emoji": "🐉",
              "wheel_only": True, "upgradeable": False, "combo_allowed": False,
              "rank_override": 15},

    # ==================== گردونه آتش — هایپرسونیک انحصاری ====================
    "شهاب": {"price": 800, "level": 1, "min_dmg": 60, "max_dmg": 80,
             "category": "hypersonic", "shop": False, "emoji": "🔥",
             "wheel_only": True, "upgradeable": False, "combo_allowed": False,
             "rank_override": 20},
    "ستاره": {"price": 1400, "level": 1, "min_dmg": 100, "max_dmg": 140,
              "category": "hypersonic", "shop": False, "emoji": "🌟",
              "wheel_only": True, "upgradeable": False, "combo_allowed": False,
              "rank_override": 28},
    "ابرنواختر": {"price": 2000, "level": 1, "min_dmg": 150, "max_dmg": 200,
                  "category": "hypersonic", "shop": False, "emoji": "💥",
                  "wheel_only": True, "upgradeable": False, "combo_allowed": False,
                  "rank_override": 35},
}

MISSILE_PRICES = {n: d["price"] for n, d in MISSILES.items()}
MISSILE_UNLOCK_LEVEL = {n: d["level"] for n, d in MISSILES.items()}
HYPERSONIC_DAMAGE = {n: d["max_dmg"] for n, d in MISSILES.items()}
WEAPON_LEVELS = {n: d["level"] for n, d in MISSILES.items()}

COMBO_MAX_RANK = 40   # ← سقف رنک همیشه ۴۰ (دست نمی‌خوره)

# 🆕 محدودیت‌های حمله ترکیبی بر اساس سطح زرادخانه
COMBO_LIMITS_BY_ARSENAL = {
    1: {"damage": 600,   "coins": 3000,   "oil": 1500},
    2: {"damage": 1200,  "coins": 6000,   "oil": 3000},
    3: {"damage": 2500,  "coins": 12000,  "oil": 6000},
    4: {"damage": 5000,  "coins": 25000,  "oil": 12000},
    5: {"damage": 10000, "coins": 50000,  "oil": 25000},
    6: {"damage": 20000, "coins": 100000, "oil": 50000},
}


# ==================== تنظیمات آزمایشگاه ====================
LAB_MAX_LEVEL = 6

LAB_UPGRADE_COSTS = {
    1: 10000,
    2: 25000,
    3: 45000,
    4: 70000,
    5: 100000,
}

LAB_UPGRADE_USER_LEVELS = {
    1: 2,
    2: 5,
    3: 10,
    4: 15,
    5: 20,
}

LAB_MISSILE_UPGRADE_REQUIREMENTS = {
    1: 2,
    2: 3,
    3: 4,
    4: 5,
    5: 6,
}

LAB_ALLOWED_CATEGORIES = ["cruise", "ballistic", "hypersonic"]
LAB_BLOCKED_MISSILES = ["تاماهاک"]


# ==================== پژوهشگران و بوست ====================
DEFAULT_SCIENTISTS_COUNT = 1
MAX_SCIENTISTS_COUNT = 2
SCIENTIST_2_COST = 200

BOOST_TYPES = {
    "20": {"cost": 15, "time_multiplier": 0.8,
           "duration_seconds": 3600, "name": "20%"},
    "50": {"cost": 40, "time_multiplier": 0.5,
           "duration_seconds": 3600, "name": "50%"},
    "100": {"cost": 80, "time_multiplier": 0.5,
            "duration_seconds": 7200, "name": "2x"},
}


# ==================== ضرایب هزینه ارتقا ====================
CATEGORY_UPGRADE_MULTIPLIER = {
    "cruise": 1.0,
    "ballistic": 1.2,
    "hypersonic": 1.5,
}

LEVEL_UPGRADE_MULTIPLIER = {
    1: 1,
    2: 2.5,
    3: 5,
    4: 8,
    5: 14,
}


# ==================== توابع کمکی موشک ====================
def get_missile_data(name):
    return MISSILES.get(name)


def is_missile_purchasable(name):
    data = MISSILES.get(name)
    return data and data.get("shop", False)


def is_wheel_only(name):
    return MISSILES.get(name, {}).get("wheel_only", False)


def is_upgradeable(name):
    data = MISSILES.get(name, {})
    if data.get("upgradeable") is False:
        return False
    return True


def is_combo_allowed(name):
    data = MISSILES.get(name, {})
    if data.get("combo_allowed") is False:
        return False
    return True


def get_missiles_by_category(cat, only_shop=False):
    result = []
    for name, data in MISSILES.items():
        if data["category"] != cat:
            continue
        if only_shop and not data.get("shop", False):
            continue
        result.append(name)
    return result


def get_missile_category(missile_name):
    data = MISSILES.get(missile_name)
    if data:
        return data["category"]
    return "cruise"


def get_missile_damage(name, level, category=None):
    data = MISSILES.get(name)
    if not data:
        return 5
    lo = data["min_dmg"]
    hi = data["max_dmg"]
    mult = 1 + (level - 1) * 0.2
    min_d = int(lo * mult)
    max_d = int(hi * mult)
    if max_d <= min_d:
        return min_d
    return random.randint(min_d, max_d)


def get_hypersonic_damage(name, level):
    return get_missile_damage(name, level, "hypersonic")


# ==================== غارت سکه و نفت ====================
def get_loot_coins(missile_name, level):
    data = MISSILES.get(missile_name)
    if not data:
        return 10
    price = data["price"]
    cat = data["category"]

    base = max(5, int(price * 0.2))

    if cat == "cruise":
        return base + (level - 1) * 5
    elif cat == "ballistic":
        return base + (level - 1) * 15
    elif cat == "hypersonic":
        return base + (level - 1) * 25
    elif cat == "chemical":
        return base + (level - 1) * 20
    elif cat == "nuclear":
        return base + (level - 1) * 50
    return base


def get_loot_oil(missile_name, level):
    return max(1, get_loot_coins(missile_name, level) // 2)


# ==================== رنک ====================
def get_loot_rank(missile_name, level, combo=False):
    data = MISSILES.get(missile_name)
    if not data:
        return 1

    if "rank_override" in data:
        return data["rank_override"]

    cat = data["category"]
    lo = data["min_dmg"]
    hi = data["max_dmg"]

    if cat == "nuclear":
        return 100

    if level <= 5:
        per_level = (hi - lo) / 4
        base_rank = lo + (level - 1) * per_level
    else:
        base_rank = hi + (level - 5) * (hi * 0.2)

    result = max(1, round(base_rank))

    if cat in ["ballistic", "chemical"]:
        result = min(result, 30)

    return result


# ==================== هزینه ارتقای موشک ====================
def get_missile_upgrade_base_cost(missile_name):
    price = MISSILE_PRICES.get(missile_name, 100)
    cat = get_missile_category(missile_name)
    base = 5000 + (price - 30) * 50
    if base < 1000:
        base = 1000
    mult = CATEGORY_UPGRADE_MULTIPLIER.get(cat, 1.0)
    return int(base * mult)


def get_upgrade_cost(missile_name, current_level):
    base = get_missile_upgrade_base_cost(missile_name)
    mult = LEVEL_UPGRADE_MULTIPLIER.get(current_level, 14)
    return int(base * mult)


def get_upgrade_oil_cost(missile_name, current_level):
    if current_level < 3:
        return 0
    cost = get_upgrade_cost(missile_name, current_level)
    return cost // 20


def get_upgrade_time(missile_name, current_level):
    from config import UPGRADE_TIME_PER_LEVEL
    return UPGRADE_TIME_PER_LEVEL.get(current_level, 240)


# ==================== کاهش غارت ترکیبی ====================
def calc_combo_defense_penalty(defender, attacker_fighter_count):
    buildings = defender.get("buildings", {})
    phoenix = defender.get("fighters_hero", {}).get("فونیکس", {})
    phoenix_count = phoenix.get("count", 0)
    phoenix_level = phoenix.get("level", 1)

    total_reduction = 0
    maxed_count = 0
    half_count = 0

    for bname, blvl in buildings.items():
        if blvl <= 0:
            continue
        if blvl >= 7:
            total_reduction += 0.15
            maxed_count += 1
        elif blvl >= 4:
            total_reduction += 0.07
            half_count += 1
        elif blvl >= 1:
            total_reduction += 0.02

    total_buildings = len(BUILDINGS)
    phoenix_maxed = (phoenix_count > 0 and phoenix_level >= PHOENIX_MAX_LEVEL)

    if (maxed_count >= total_buildings and phoenix_maxed
            and attacker_fighter_count > 0):
        return (0.0, -2,
                "🛡 مدافع کاملاً مکس — غارت صفر، ۲ رنک از مهاجم کم شد")

    if phoenix_maxed and maxed_count < total_buildings:
        total_reduction += 0.10

    total_reduction = min(0.95, total_reduction)
    loot_pct = max(0.05, 1.0 - total_reduction)

    if total_reduction > 0:
        note = (f"🛡 کاهش غارت: {int(total_reduction * 100)}% "
                f"({maxed_count} مکس + {half_count} نیمه)")
    else:
        note = ""

    return loot_pct, 0, note


# ==================== ساختمون‌ها ====================
BUILDINGS_HP = {
    "پادزون": 50, "مگالیر": 80, "ورنیکس": 120,
    "فونیکس": 180, "آشیانه": 250, "سپر آهنی": 400,
}

BUILDINGS = {
    "پادزون": {"emoji": "🏠", "price": 10000, "upgrade": 5000, "per_level": 5},
    "مگالیر": {"emoji": "🏠", "price": 20000, "upgrade": 10000, "per_level": 7},
    "ورنیکس": {"emoji": "🏠", "price": 30000, "upgrade": 15000, "per_level": 10},
    "فونیکس": {"emoji": "🏠", "price": 50000, "upgrade": 25000, "per_level": 12},
    "آشیانه": {"emoji": "⚔️", "price": 100000, "upgrade": 50000, "per_level": 15},
    "سپر آهنی": {"emoji": "🛡️", "price": 200000, "upgrade": 100000, "per_level": 20},
}

# 🆕 زرادخانه — ظرفیت حمله ترکیبی (جدا از تسلیحات خانه)
ARSENAL_LEVELS = {
    1: {"capacity": 5},    # 5 موشک
    2: {"capacity": 10},   # 10 موشک
    3: {"capacity": 20},   # 20 موشک
    4: {"capacity": 35},   # 35 موشک
    5: {"capacity": 50},   # 50 موشک
    6: {"capacity": 75},   # 75 موشک
}

ARSENAL_ATTACK_COSTS = {
    1: {"coins": 10000,  "oil": 0},       # 1→2
    2: {"coins": 25000,  "oil": 0},       # 2→3
    3: {"coins": 50000,  "oil": 0},       # 3→4
    4: {"coins": 65000,  "oil": 0},       # 4→5
    5: {"coins": 100000, "oil": 5000},    # 5→6
}

ARSENAL_MAX_LEVEL = 6

BUILDING_MAX_LEVEL = 7

FIGHTER_BASE_LEVELS = {
    1: {"upgrade_cost": 0,      "slots": 3,  "required_user_level": 5},
    2: {"upgrade_cost": 50000,  "slots": 5,  "required_user_level": 10},
    3: {"upgrade_cost": 100000, "slots": 8,  "required_user_level": 15},
    4: {"upgrade_cost": 200000, "slots": 12, "required_user_level": 20},
    5: {"upgrade_cost": 450000, "slots": 18, "required_user_level": 30},
}

FIGHTER_BASE_MAX_LEVEL = 5
FIGHTER_BASE_BUILD_COST = 100000

HERO_FIGHTERS = {
    "فونیکس": {"tier": 1, "damage": 20, "speed": 20, "hp": 50,
               "build_cost": 50000, "min_base_level": 1, "source": "build"},
    "رعد": {"tier": 2, "damage": 35, "speed": 25, "hp": 90,
            "build_cost": 100000, "min_base_level": 2, "source": "build"},
    "سیمرغ": {"tier": 3, "damage": 55, "speed": 30, "hp": 140,
              "build_cost": 200000, "min_base_level": 3, "source": "build"},
    "آذرخش": {"tier": 4, "damage": 80, "speed": 35, "hp": 200,
              "build_cost": 400000, "min_base_level": 4, "source": "build"},
    "تایتان": {"tier": 5, "damage": 120, "speed": 40, "hp": 300,
               "build_cost": 800000, "min_base_level": 5, "source": "build"},
    "F-16": {"tier": 1, "damage": 40, "speed": 22, "hp": 80, "source": "wheel"},
    "میگ 29": {"tier": 1, "damage": 45, "speed": 24, "hp": 85, "source": "wheel"},
    "F-22": {"tier": 2, "damage": 60, "speed": 28, "hp": 120, "source": "wheel"},
    "سوخو 35": {"tier": 2, "damage": 70, "speed": 30, "hp": 130, "source": "wheel"},
    "F-35": {"tier": 3, "damage": 90, "speed": 34, "hp": 180, "source": "wheel"},
    "سوخو 57": {"tier": 3, "damage": 100, "speed": 36, "hp": 190, "source": "wheel"},
    "میگ 31": {"tier": 4, "damage": 130, "speed": 40, "hp": 240, "source": "wheel"},
    "F-15": {"tier": 4, "damage": 140, "speed": 42, "hp": 260, "source": "wheel"},
    "رافال": {"tier": 5, "damage": 175, "speed": 46, "hp": 320, "source": "wheel"},
    "تایفون": {"tier": 6, "damage": 220, "speed": 52, "hp": 420, "source": "wheel"},
    "اژدهای سیاه": {"tier": 6, "damage": 260, "speed": 55, "hp": 500, "source": "wheel"},
}


def get_fighter_base_slots(level):
    return FIGHTER_BASE_LEVELS.get(level, {}).get("slots", 0)


def get_used_fighter_slots(p):
    fighters = p.get("fighters_hero", {})
    return sum(f.get("count", 0) for f in fighters.values())


def get_fighter_hero_bonus(p):
    fighters = p.get("fighters_hero", {})
    bonus = 0
    for fname, finfo in fighters.items():
        if finfo.get("count", 0) > 0:
            f_data = HERO_FIGHTERS.get(fname, {})
            bonus += f_data.get("damage", 0) * finfo["count"]
    return bonus


def get_fighter_loot_bonus(fighter_bonus):
    return {
        "coins": int(fighter_bonus * 4),
        "oil": int(fighter_bonus * 2),
    }


PHOENIX_REDUCTION = {1: 0, 2: 25, 3: 50, 4: 60, 5: 75, 6: 100}
PHOENIX_MAX_LEVEL = 6


def get_phoenix_reduction(target):
    fighters = target.get("fighters_hero", {})
    phoenix = fighters.get("فونیکس", {})
    if phoenix.get("count", 0) <= 0:
        return 0
    lvl = phoenix.get("level", 1)
    return PHOENIX_REDUCTION.get(lvl, 0)


def apply_vernix_damage_to_fighters(p, target):
    target_buildings = target.get("buildings", {})
    if "ورنیکس" not in target_buildings:
        return []
    vernix_level = target_buildings["ورنیکس"]
    if vernix_level <= 0:
        return []
    damage_per_fighter = vernix_level * 5
    messages = []
    fighters = p.get("fighters_hero", {})
    for fname, finfo in fighters.items():
        if finfo.get("count", 0) > 0 and finfo.get("hp_current", 0) > 0:
            old_hp = finfo["hp_current"]
            finfo["hp_current"] = max(0, old_hp - damage_per_fighter)
            messages.append(f"⚠️ {fname}: {old_hp} → {finfo['hp_current']} HP")
    return messages


# ==================== گردونه جنگنده ====================
WHEEL_FIGHTER_PRICE_1 = 6000
WHEEL_FIGHTER_PRICE_10 = 60000

WHEEL_FIGHTER_PRIZES = [
    {"name": "F-16", "chance": 18},
    {"name": "میگ 29", "chance": 15},
    {"name": "F-22", "chance": 14},
    {"name": "سوخو 35", "chance": 12},
    {"name": "F-35", "chance": 10},
    {"name": "سوخو 57", "chance": 8},
    {"name": "میگ 31", "chance": 7},
    {"name": "F-15", "chance": 6},
    {"name": "رافال", "chance": 5},
    {"name": "تایفون", "chance": 3},
    {"name": None, "chance": 2, "type": "coins", "amount": 15000},
]


def spin_fighter_wheel():
    total = sum(p["chance"] for p in WHEEL_FIGHTER_PRIZES)
    rand = random.randint(1, total)
    cur = 0
    for prize in WHEEL_FIGHTER_PRIZES:
        cur += prize["chance"]
        if rand <= cur:
            return prize
    return WHEEL_FIGHTER_PRIZES[0]


# ==================== گردونه روزانه ====================
WHEEL_DAILY_PRIZES = [
    {"name": "اطلس × 2", "type": "weapon", "weapon": "اطلس",
     "category": "cruise", "amount": 2, "chance": 3},
    {"name": "هویزه × 1", "type": "weapon", "weapon": "هویزه",
     "category": "cruise", "amount": 1, "chance": 5},
    {"name": "1000 سکه", "type": "coins", "amount": 1000, "chance": 7},
    {"name": "500 سکه", "type": "coins", "amount": 500, "chance": 20},
    {"name": "200 سکه", "type": "coins", "amount": 200, "chance": 25},
    {"name": "50 نفت", "type": "oil", "amount": 50, "chance": 15},
    {"name": "10 آهن", "type": "iron", "amount": 10, "chance": 15},
    {"name": "5 فولاد", "type": "steel", "amount": 5, "chance": 10},
]


def spin_daily_wheel():
    roll = random.randint(1, 100)
    cur = 0
    for prize in WHEEL_DAILY_PRIZES:
        cur += prize["chance"]
        if roll <= cur:
            return prize
    return WHEEL_DAILY_PRIZES[-1]


# ==================== گردونه افسانه‌ای ====================
WHEEL_LEGENDARY_PRICE_1 = 15000
WHEEL_LEGENDARY_PRICE_10 = 150000

WHEEL_LEGENDARY_PRIZES = [
    {"name": "هسته‌ای × 1", "type": "weapon", "weapon": "هسته‌ای",
     "category": "nuclear", "amount": 1, "chance": 1},
    {"name": "فتاح × 2", "type": "weapon", "weapon": "فتاح",
     "category": "hypersonic", "amount": 2, "chance": 5},
    {"name": "خرمشهر × 1", "type": "weapon", "weapon": "خرمشهر",
     "category": "hypersonic", "amount": 1, "chance": 9},
    {"name": "F-35 × 1", "type": "fighter", "fighter": "F-35",
     "amount": 1, "chance": 10},
    {"name": "رافال × 1", "type": "fighter", "fighter": "رافال",
     "amount": 1, "chance": 8},
    {"name": "تاد × 1", "type": "defense", "defense": "تاد",
     "amount": 1, "chance": 12},
    {"name": "S-400 × 1", "type": "defense", "defense": "S-400",
     "amount": 1, "chance": 15},
    {"name": "2000 سکه", "type": "coins", "amount": 2000, "chance": 20},
    {"name": "1000 سکه", "type": "coins", "amount": 1000, "chance": 20},
]


def spin_legendary_wheel():
    roll = random.randint(1, 100)
    cur = 0
    for prize in WHEEL_LEGENDARY_PRIZES:
        cur += prize["chance"]
        if roll <= cur:
            return prize
    return WHEEL_LEGENDARY_PRIZES[-1]


# ==================== گردونه بخت ====================
WHEEL_LUCK_PRICE_1 = 20000

WHEEL_LUCK_PRIZES = [
    {"name": "🏆 جکپات کامل", "type": "multi", "rewards": [
        {"type": "weapon", "weapon": "هسته‌ای", "category": "nuclear", "amount": 2},
        {"type": "weapon", "weapon": "فتاح", "category": "hypersonic", "amount": 5},
        {"type": "fighter", "fighter": "تایفون", "amount": 1},
    ], "chance": 2},
    {"name": "🛡 پک پدافند", "type": "multi", "rewards": [
        {"type": "defense", "defense": "تاد", "amount": 1},
        {"type": "defense", "defense": "S-400", "amount": 1},
        {"type": "defense", "defense": "گاردین", "amount": 1},
    ], "chance": 6},
    {"name": "✈️ پک جنگنده", "type": "multi", "rewards": [
        {"type": "fighter", "fighter": "F-15", "amount": 1},
        {"type": "fighter", "fighter": "F-22", "amount": 1},
    ], "chance": 7},
    {"name": "50,000 سکه", "type": "coins", "amount": 50000, "chance": 10},
    {"name": "20,000 سکه", "type": "coins", "amount": 20000, "chance": 25},
    {"name": "هیچی", "type": "nothing", "chance": 50},
]


def spin_luck_wheel():
    roll = random.randint(1, 100)
    cur = 0
    for prize in WHEEL_LUCK_PRIZES:
        cur += prize["chance"]
        if roll <= cur:
            return prize
    return WHEEL_LUCK_PRIZES[-1]


# ==================== گردونه طوفان ====================
WHEEL_STORM_PRICE_1 = 2500
WHEEL_STORM_PRICE_10 = 25000

WHEEL_STORM_PRIZES = [
    {"name": "عقرب", "type": "weapon", "weapon": "عقرب",
     "category": "cruise", "amount": 1, "chance": 4},
    {"name": "افعی × 2", "type": "weapon", "weapon": "افعی",
     "category": "cruise", "amount": 2, "chance": 5},
    {"name": "افعی × 1", "type": "weapon", "weapon": "افعی",
     "category": "cruise", "amount": 1, "chance": 8},
    {"name": "موج × 3", "type": "weapon", "weapon": "موج",
     "category": "cruise", "amount": 3, "chance": 10},
    {"name": "موج × 1", "type": "weapon", "weapon": "موج",
     "category": "cruise", "amount": 1, "chance": 15},
    {"name": "1000 سکه", "type": "coins", "amount": 1000, "chance": 10},
    {"name": "500 سکه", "type": "coins", "amount": 500, "chance": 18},
    {"name": "300 سکه", "type": "coins", "amount": 300, "chance": 15},
    {"name": "150 سکه", "type": "coins", "amount": 150, "chance": 15},
]


def spin_storm_wheel():
    roll = random.randint(1, 100)
    cur = 0
    for prize in WHEEL_STORM_PRIZES:
        cur += prize["chance"]
        if roll <= cur:
            return prize
    return WHEEL_STORM_PRIZES[-1]


# ==================== گردونه شکار ====================
WHEEL_HUNT_PRICE_1 = 5000
WHEEL_HUNT_PRICE_10 = 50000

WHEEL_HUNT_PRIZES = [
    {"name": "اژدها", "type": "weapon", "weapon": "اژدها",
     "category": "ballistic", "amount": 1, "chance": 3},
    {"name": "هایدرا", "type": "weapon", "weapon": "هایدرا",
     "category": "ballistic", "amount": 1, "chance": 6},
    {"name": "اسنایپر", "type": "weapon", "weapon": "اسنایپر",
     "category": "ballistic", "amount": 1, "chance": 10},
    {"name": "S-400", "type": "defense", "defense": "S-400",
     "amount": 1, "chance": 6},
    {"name": "5000 سکه", "type": "coins", "amount": 5000, "chance": 10},
    {"name": "3000 سکه", "type": "coins", "amount": 3000, "chance": 15},
    {"name": "2000 سکه", "type": "coins", "amount": 2000, "chance": 20},
    {"name": "1000 سکه", "type": "coins", "amount": 1000, "chance": 20},
    {"name": "500 سکه", "type": "coins", "amount": 500, "chance": 10},
]


def spin_hunt_wheel():
    roll = random.randint(1, 100)
    cur = 0
    for prize in WHEEL_HUNT_PRIZES:
        cur += prize["chance"]
        if roll <= cur:
            return prize
    return WHEEL_HUNT_PRIZES[-1]


# ==================== گردونه آتش ====================
WHEEL_FIRE_PRICE_1 = 15000
WHEEL_FIRE_PRICE_10 = 150000

WHEEL_FIRE_PRIZES = [
    {"name": "ابرنواختر", "type": "weapon", "weapon": "ابرنواختر",
     "category": "hypersonic", "amount": 1, "chance": 2},
    {"name": "ستاره", "type": "weapon", "weapon": "ستاره",
     "category": "hypersonic", "amount": 1, "chance": 5},
    {"name": "شهاب", "type": "weapon", "weapon": "شهاب",
     "category": "hypersonic", "amount": 1, "chance": 10},
    {"name": "تاد", "type": "defense", "defense": "تاد",
     "amount": 1, "chance": 5},
    {"name": "10,000 سکه", "type": "coins", "amount": 10000, "chance": 10},
    {"name": "5,000 سکه", "type": "coins", "amount": 5000, "chance": 18},
    {"name": "3,000 سکه", "type": "coins", "amount": 3000, "chance": 20},
    {"name": "1,500 سکه", "type": "coins", "amount": 1500, "chance": 20},
    {"name": "500 سکه", "type": "coins", "amount": 500, "chance": 10},
]


def spin_fire_wheel():
    roll = random.randint(1, 100)
    cur = 0
    for prize in WHEEL_FIRE_PRIZES:
        cur += prize["chance"]
        if roll <= cur:
            return prize
    return WHEEL_FIRE_PRIZES[-1]


# ==================== گردونه اژدها ====================
WHEEL_DRAGON_PRICE_1 = 25000
WHEEL_DRAGON_PRICE_10 = 250000

WHEEL_DRAGON_PRIZES = [
    {"name": "اژدهای سیاه", "type": "fighter", "fighter": "اژدهای سیاه",
     "amount": 1, "chance": 1},
    {"name": "صاعقه", "type": "fighter", "fighter": "صاعقه",
     "amount": 1, "chance": 4},
    {"name": "شاهین", "type": "fighter", "fighter": "شاهین",
     "amount": 1, "chance": 10},
    {"name": "30,000 سکه", "type": "coins", "amount": 30000, "chance": 5},
    {"name": "15,000 سکه", "type": "coins", "amount": 15000, "chance": 10},
    {"name": "8,000 سکه", "type": "coins", "amount": 8000, "chance": 15},
    {"name": "5,000 سکه", "type": "coins", "amount": 5000, "chance": 20},
    {"name": "3,000 سکه", "type": "coins", "amount": 3000, "chance": 20},
    {"name": "1,500 سکه", "type": "coins", "amount": 1500, "chance": 15},
]


def spin_dragon_wheel():
    roll = random.randint(1, 100)
    cur = 0
    for prize in WHEEL_DRAGON_PRIZES:
        cur += prize["chance"]
        if roll <= cur:
            return prize
    return WHEEL_DRAGON_PRIZES[-1]


def give_fighter(p, fname, count=1):
    if "fighters_hero" not in p:
        p["fighters_hero"] = {}
    f_data = HERO_FIGHTERS.get(fname, {})
    if fname not in p["fighters_hero"]:
        p["fighters_hero"][fname] = {
            "count": 0,
            "hp_current": f_data.get("hp", 50),
            "level": 1,
        }
    p["fighters_hero"][fname]["count"] += count
    return True


WEAPON_SPACE = {
    "cruise": 1, "ballistic": 2, "hypersonic": 3, "chemical": 4,
    "nuclear": 5,
    "drones": 1, "fighters": 3, "defense": 1, "custom": 10,
}

DEFENSES = {
    "تیربار": {"price": 50, "block_chance": 10, "required_level": 1,
               "emoji": "🔫", "type": "block", "advanced": False},
    "گنبد آهنین": {"price": 150, "block_chance": 25, "required_level": 2,
                    "emoji": "🔵", "type": "block", "advanced": False},
    "باور": {"price": 800, "block_chance": 40, "required_level": 5,
             "emoji": "🛡️", "type": "block", "advanced": False},
    "پاتریوت": {"price": 1500, "block_chance": 50, "required_level": 8,
                 "emoji": "🛡️", "type": "block", "advanced": False},
    "S-400": {"price": 2500, "block_chance": 60, "required_level": 10,
              "emoji": "🛡️", "type": "block", "advanced": True},
    "گاردین": {"price": 4000, "block_chance": 70, "required_level": 13,
                "emoji": "💠", "type": "damage_reduce", "advanced": False},
    "تاد": {"price": 5000, "block_chance": 80, "required_level": 13,
            "emoji": "🛡️", "type": "block", "advanced": True},
}


def get_defense_block_chance(defense_name, missile_category="cruise",
                              missile_level=1):
    defense = DEFENSES.get(defense_name)
    if not defense:
        return 0
    if defense.get("type") != "block":
        return 0

    base = defense["block_chance"]

    if missile_category == "hypersonic":
        return base // 2

    if missile_category == "nuclear":
        return 0

    if defense.get("advanced"):
        if missile_category == "ballistic" and missile_level >= 3:
            base = min(100, base + 10)
        elif missile_category == "cruise":
            base = max(0, base - 10)

    return min(base, 100)


def get_guardian_reduction(target):
    active = target.get("active_defense")
    if not active:
        return 0
    defense = DEFENSES.get(active)
    if not defense:
        return 0
    if defense.get("type") != "damage_reduce":
        return 0
    return defense["block_chance"]


def try_defense_block(target, missile_category="cruise", missile_level=1):
    if missile_category == "nuclear":
        return False, 0, None

    active = target.get("active_defense")
    if not active:
        return False, 0, None

    if active not in DEFENSES:
        return False, 0, None

    user_defenses = target.get("defense", {})
    if active not in user_defenses or user_defenses[active].get("count", 0) <= 0:
        return False, 0, None

    defense = DEFENSES[active]

    if defense.get("type") == "damage_reduce":
        return False, 0, None

    chance = get_defense_block_chance(active, missile_category, missile_level)

    if random.randint(1, 100) <= chance:
        return True, chance, active
    return False, chance, active


AIRPORT_LEVELS = {
    1: {"fighter_cap": 50, "drone_cap": 25, "upgrade_cost": 0},
    2: {"fighter_cap": 100, "drone_cap": 50, "upgrade_cost": 5000},
    3: {"fighter_cap": 200, "drone_cap": 100, "upgrade_cost": 10000},
    4: {"fighter_cap": 400, "drone_cap": 200, "upgrade_cost": 20000},
    5: {"fighter_cap": 800, "drone_cap": 400, "upgrade_cost": 40000},
    6: {"fighter_cap": 1400, "drone_cap": 700, "upgrade_cost": 80000},
    7: {"fighter_cap": 2000, "drone_cap": 1000, "upgrade_cost": 150000},
}

DRONES = {
    "شاهد": {"price": 200, "required_level": 3, "effect": "rank", "value": 1.5, "desc": "👑 رنک بیشتر"},
    "کرار": {"price": 300, "required_level": 3, "effect": "rank", "value": 1.8, "desc": "👑 رنک بیشتر"},
    "مهاجر": {"price": 400, "required_level": 3, "effect": "rank", "value": 2.2, "desc": "👑 رنک بیشتر"},
    "ابابیل": {"price": 500, "required_level": 3, "effect": "rank", "value": 2.5, "desc": "👑 رنک بیشتر"},
    "حماسه": {"price": 300, "required_level": 3, "effect": "defense", "value": 2, "desc": "💥 نابودی ۲ پدافند"},
    "یاسر": {"price": 400, "required_level": 3, "effect": "defense", "value": 2, "desc": "💥 نابودی ۲ پدافند"},
    "معراج": {"price": 500, "required_level": 3, "effect": "defense", "value": 2, "desc": "💥 نابودی ۲ پدافند"},
    "مهاجر 6": {"price": 600, "required_level": 3, "effect": "defense", "value": 2, "desc": "💥 نابودی ۲ پدافند"},
    "شاهد 136": {"price": 500, "required_level": 3, "effect": "coins", "value": 1.8, "desc": "💰 غارت سکه بیشتر"},
    "کرار 2": {"price": 600, "required_level": 3, "effect": "coins", "value": 2.2, "desc": "💰 غارت سکه بیشتر"},
}

FIGHTERS = {}

PACKS = {
    "start": {"name": "پک شروع", "price": "100,000 تومان",
              "items": ["10000 سکه", "5000 نفت", "5 موشک اطلس"],
              "emoji": "📦"},
    "war": {"name": "پک جنگی", "price": "250,000 تومان",
            "items": ["25000 سکه", "10000 نفت", "10 موشک اطلس",
                      "5 موشک عماد", "1 جنگنده F-16"],
            "emoji": "⚔️"},
    "legend": {"name": "پک افسانه‌ای", "price": "500,000 تومان",
               "items": ["50000 سکه", "25000 نفت", "10 موشک اطلس",
                         "10 موشک فتاح", "5 موشک آذرخش",
                         "1 جنگنده F-35", "1 پدافند S-400"],
               "emoji": "💎"},
    "god": {"name": "پک خدا", "price": "1,000,000 تومان",
            "items": ["100000 سکه", "50000 نفت", "20 موشک اطلس",
                      "20 موشک فتاح", "10 موشک خرمشهر", "5 جنگنده F-22",
                      "5 پدافند S-500", "نشان ویژه"],
            "emoji": "👑"},
}

BOX_PRIZES = [
    {"name": "300 سکه", "type": "coins", "amount": 300, "chance": 40},
    {"name": "اطلس × 3", "type": "weapon", "weapon": "اطلس",
     "category": "cruise", "amount": 3, "chance": 35},
    {"name": "فتاح × 1", "type": "weapon", "weapon": "فتاح",
     "category": "hypersonic", "amount": 1, "chance": 25},
]

LEVEL_REQUIREMENTS = {
    "shop_missile": 1, "shop_ballistic": 1, "shop_drone": 3,
    "shop_hypersonic": 20, "shop_defense": 15, "shop_talisman": 25,
    "shop_nuclear": 20,
}

RANK_LEAGUES = [
    ("🌙 ماه", 100000, 999999999),
    ("🔮 کریستال", 28000, 100000),
    ("⚔️ تایتان", 20000, 28000),
    ("⭐ طوفان", 17000, 20000),
    ("❄️ آیس", 12000, 17000),
    ("🐉 دراگون", 8000, 12000),
    ("👻 ارواح", 5000, 8000),
    ("💠 پلاتینیوم", 3000, 5000),
    ("🥇 طلایی", 1500, 3000),
    ("🥈 نقره‌ای", 800, 1500),
    ("🥉 برنزی", 200, 800),
    ("🌱 تازه‌کار", 0, 200),
]


def get_level_info(total_damage):
    level = 1
    xp_used = 0
    while True:
        xp_needed = level * 100
        if total_damage < xp_used + xp_needed:
            return level, total_damage - xp_used, xp_needed
        xp_used += xp_needed
        level += 1
        if level > 1000:
            return level, 0, 1000


def get_league(rank):
    for name, mn, mx in RANK_LEAGUES:
        if mn <= rank < mx:
            return name
    return "🌱 تازه‌کار"


def make_bar(value, max_value, length=10):
    if max_value <= 0:
        return "░" * length, 0
    percent = min(int((value / max_value) * 100), 100)
    filled = int((percent / 100) * length)
    return "▓" * filled + "░" * (length - filled), percent


def get_category_name(cat_key):
    return {
        "cruise": "کروز", "ballistic": "بالستیک", "hypersonic": "هایپرسونیک",
        "chemical": "شیمیایی", "nuclear": "هسته‌ای",
        "drones": "پهباد", "fighters": "جنگنده", "defense": "پدافند",
    }.get(cat_key, cat_key)


def get_arsenal_capacity(p):
    """ظرفیت حمله ترکیبی بر اساس زرادخانه"""
    level = p.get("arsenal_level", 1)
    if level > ARSENAL_MAX_LEVEL:
        level = ARSENAL_MAX_LEVEL
    return ARSENAL_LEVELS.get(level, ARSENAL_LEVELS[1])["capacity"]


def get_used_space(p):
    combos = p.get("combos", {})
    used = 0
    for _, combo_data in combos.items():
        for weapon in combo_data.get("weapons", []):
            cat = weapon.get("category", "")
            count = weapon.get("count", 0)
            used += WEAPON_SPACE.get(cat, 1) * count
    return used


def get_refinery_cap(level):
    return level * 40 * 4


def get_refinery_rate(level):
    return level * 40


def get_random_box_prize():
    total = sum(p["chance"] for p in BOX_PRIZES)
    rand = random.randint(1, total)
    cur = 0
    for prize in BOX_PRIZES:
        cur += prize["chance"]
        if rand <= cur:
            return prize
    return BOX_PRIZES[0]


def get_buildings_defense(buildings, attack_type="normal"):
    if attack_type == "chemical":
        return 0
    chances = {
        "پادزون": 30, "مگالیر": 40, "ورنیکس": 50,
        "فونیکس": 50, "آشیانه": 70, "سپر آهنی": 80,
    }
    total = 0
    for name in buildings:
        if name in chances and random.randint(1, 100) <= chances[name]:
            total += chances[name]
    return min(total, 100)


def get_total_defense(p, attack_type="normal"):
    if attack_type == "chemical":
        return 0
    buildings = p.get("buildings", {})
    arsenal_level = p.get("arsenal_level", 1)
    total = 0
    for name, level in buildings.items():
        if name in BUILDINGS and level > 0:
            per = BUILDINGS[name].get("per_level", 0)
            total += per * level
    total += arsenal_level * 4
    if attack_type == "hypersonic":
        total = total // 2
    return min(total, 100)


def is_moon_league(rank):
    return rank >= 100000


def apply_defense_to_attack(bdef, damage, coins, oil, rank):
    if bdef <= 0:
        return damage, coins, oil, rank
    factor = (100 - bdef) / 100
    new_dmg = max(1, int(damage * factor))
    new_coins = int(coins * factor)
    new_oil = int(oil * factor)
    new_rank = max(1, int(rank * factor)) if rank > 0 else 0
    return new_dmg, new_coins, new_oil, new_rank


# ==================== 📖 راهنمای کامل همه بخش‌ها ====================
GUIDE_TEXT = {
    "mine": (
        "⛏️ *راهنمای معدن سکه*\n\n"
        "📊 *سطوح:* 1 تا 40\n"
        "⚙️ *تولید:* سطح × 100 سکه در ساعت\n"
        "📦 *سقف:* سطح × 300 سکه (3 ساعت)\n"
        "💰 *هزینه ارتقا:* (سطح + 1) × 1,000 سکه\n\n"
        "📝 *نکات مهم:*\n"
        "• هر چند ساعت یکبار بیا برداشت کن\n"
        "• اگه پر بشه تولید متوقف می‌شه\n"
        "• ارتقا هم تولید و هم سقف رو زیاد می‌کنه\n\n"
        "🔻 *دکمه‌ها:*\n"
        "• 🪙 برداشت سکه → گرفتن سکه‌های آماده\n"
        "• 🔼 ارتقا معدن → افزایش سطح"
    ),
    "refinery": (
        "🏭 *راهنمای پالایشگاه نفت*\n\n"
        "💰 *هزینه خرید:* 10,000 سکه\n"
        "🎯 *لول لازم:* 10\n"
        "📊 *سطوح:* 1 تا 10\n"
        "⚙️ *تولید:* سطح × 40 نفت در ساعت\n"
        "📦 *سقف:* 4 ساعت تولید (سطح × 160)\n\n"
        "📝 *نکات:*\n"
        "• برای برداشت، روی «🛢️ برداشت نفت» بزن\n"
        "• نفت برای ارتقا موشک و خرید فرودگاه لازمه\n"
        "• بعد از سطح 10 دیگه ارتقا نمی‌شه\n\n"
        "🔻 *دکمه‌ها:*\n"
        "• 🛢️ برداشت نفت → گرفتن نفت آماده\n"
        "• 🔼 ارتقا پالایشگاه → افزایش سطح"
    ),
    "lab": (
        "🧪 *راهنمای آزمایشگاه*\n\n"
        "📊 *سطح آزمایشگاه:* 1 تا 6\n"
        "💰 *هزینه ارتقا:* 10K تا 100K سکه\n\n"
        "👤 *لول کاربر لازم:*\n"
        "• 1→2: لول 2\n"
        "• 2→3: لول 5\n"
        "• 3→4: لول 10\n"
        "• 4→5: لول 15\n"
        "• 5→6: لول 20\n\n"
        "🔓 *قفل ارتقای موشک (بر اساس لول آزمایشگاه):*\n"
        "• موشک 1→2: لاب 2\n"
        "• موشک 2→3: لاب 3\n"
        "• موشک 3→4: لاب 4\n"
        "• موشک 4→5: لاب 5\n"
        "• موشک 5→6: لاب 6\n\n"
        "🔬 *دانشمندان:*\n"
        "• اول: 1 دانشمند داری\n"
        "• دومی: 200 الماس (همزمان 2 موشک ارتقا)\n"
        "• زمان ارتقا: 30 تا 240 دقیقه\n\n"
        "🟢 *بوست‌ها (الماس):*\n"
        "• 20% کاهش زمان: 15 الماس (1 ساعت)\n"
        "• 50% کاهش زمان: 40 الماس (1 ساعت)\n"
        "• 2x سرعت: 80 الماس (2 ساعت)\n\n"
        "🔻 *دکمه‌ها:*\n"
        "• 🚀 ارتقا موشک → کروز/بالستیک/هایپر\n"
        "• 🔼 ارتقا آزمایشگاه → سطح بعدی\n"
        "• 🔬 دانشمندان → مدیریت و خرید"
    ),
    "shop": (
        "🏪 *راهنمای فروشگاه*\n\n"
        "🚀 *موشک‌ها (بر اساس لول باز می‌شن):*\n"
        "• کروز: اطلس، هویزه، فالکون، اسپکترا\n"
        "• بالستیک: عماد، ونگارد، ذوالفقار، رپتور، راون\n"
        "• هایپرسونیک: بلیزارد، فتاح، زفیکس، خرمشهر، آذرخش\n"
        "• شیمیایی: فقط شیمیایی (لول 10)\n"
        "• هسته‌ای: لول 20 + 5 الماس هر عدد\n\n"
        "🛡️ *پدافندها:*\n"
        "• تیربار (لول 1، 10% بلاک)\n"
        "• گنبد آهنین (لول 2، 25%)\n"
        "• باور (لول 5، 40%)\n"
        "• پاتریوت (لول 8، 50%)\n"
        "• S-400 (لول 10، 60%)\n"
        "• گاردین (لول 13، 70% کاهش)\n"
        "• تاد (لول 13، 80%)\n\n"
        "🔮 *طلسم‌ها (لول 5 تا 25):*\n"
        "• چشم، آتش، آب، طوفان، صاعقه، سپر، شکار، یخ\n\n"
        "🛩 *پهبادها (لول 3+):*\n"
        "• شاهد، کرار، مهاجر، ابابیل، حماسه، یاسر...\n"
        "• نیاز به فرودگاه\n\n"
        "⭐ *World Shop:*\n"
        "• از منوی اصلی\n"
        "• ۴۰,۰۰۰ تومان - ۱۰ روز جایزه اختصاصی\n\n"
        "⚠️ *ظرفیت:* قبل خرید موشک، ظرفیت تسلیحات خانه چک می‌شه"
    ),
    "wheel": (
        "🎰 *راهنمای گردونه‌ها*\n\n"
        "🎁 *گردونه روزانه* — رایگان (هر 24 ساعت)\n"
        "• سکه، نفت، آهن، فولاد، 2 اطلس، هویزه\n\n"
        "🎡 *گردونه افسانه‌ای* — 15,000 سکه\n"
        "• هسته‌ای، فتاح، خرمشهر، F-35، رافال، تاد، S-400\n\n"
        "🎰 *گردونه بخت* — 20,000 سکه\n"
        "• 50% هیچی، 25% 20K سکه، 10% 50K سکه، جکپات و پک‌ها\n\n"
        "🌊 *گردونه طوفان* — 2,500 سکه\n"
        "• موشک کروز انحصاری: عقرب، افعی، موج\n\n"
        "🐉 *گردونه شکار* — 5,000 سکه\n"
        "• موشک بالستیک انحصاری: اژدها، هایدرا، اسنایپر + S-400\n\n"
        "🔥 *گردونه آتش* — 15,000 سکه\n"
        "• موشک هایپر انحصاری: ابرنواختر، ستاره، شهاب + تاد\n\n"
        "🐲 *گردونه اژدها* — 25,000 سکه\n"
        "• جنگنده انحصاری: اژدهای سیاه، صاعقه، شاهین\n\n"
        "🎡 *گردونه جنگنده* — 6,000 سکه\n"
        "• از بخش مدیریت ترکیب → پایگاه جنگنده\n\n"
        "⚠️ موشک‌های گردونه فقط در حمله عادی قابل استفاده هستند\n"
        "❌ قابل ارتقا نیستند"
    ),
    "magic": (
        "🔮 *راهنمای طلسم*\n\n"
        "📌 *طلسم‌های پایه (قدیمی):*\n"
        "• 🪙 طلسم پول: +50 سکه (200 سکه، مکس 20)\n"
        "• ⚡ طلسم دمیج: +25 دمیج (200 سکه، مکس 20)\n"
        "• 🥇 طلسم رنک: +5 رنک (200 سکه، مکس 20)\n\n"
        "📌 *طلسم‌های حمله:*\n"
        "• 🧿 چشم (لول 5): 25% نادیده گرفتن پدافند\n"
        "• 🔥 آتش (لول 8): 20% دمیج بیشتر\n"
        "• 🌪 طوفان (لول 14): 2 موشک اضافه\n"
        "• ⚡ صاعقه (لول 17): حریف 60 ثانیه فلج\n"
        "• 👁 شکار (لول 23): حریف 40% ضعیف‌تر\n"
        "• ❄️ یخ (لول 25): حریف 30 ثانیه فلج\n\n"
        "📌 *طلسم‌های دفاعی (خودکار):*\n"
        "• 💧 آب (لول 10): 30% کاهش دمیج و غارت\n"
        "• 🛡 سپر (لول 20): 50% کاهش غارت\n\n"
        "📝 *نحوه استفاده در حمله:*\n"
        "• مثال: `حمله اطلس آتش`\n"
        "• فقط 1 طلسم در هر حمله"
    ),
    "ranking": (
        "📊 *راهنمای کامل رنکینگ*\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        "🏅 *۳ بخش رنکینگ:*\n\n"
        "1️⃣ *🏅 برترین بازیکن‌ها*\n"
        "   • رنک کل همه بازیکن‌ها\n"
        "   • صفحه‌بندی ۱۰ نفر در هر صفحه\n"
        "   • رتبه خودت هم پایین نشون داده می‌شه\n\n"
        "2️⃣ *👥 برترین کلن‌ها*\n"
        "   • مجموع رنک همه اعضای کلن\n"
        "   • تعداد اعضا / حداکثر ۱۰ نفر\n"
        "   • کلن‌های برتر اول نمایش داده می‌شن\n\n"
        "3️⃣ *📆 رنکینگ روزانه*\n"
        "   • امتیاز امروز هر بازیکن\n"
        "   • هر روز ساعت ۰۰:۰۰ صفر می‌شه\n"
        "   • رقابت روزانه برای جایزه\n\n"
        "━━━━━━━━━━━━━━━━━\n"
        "🎯 *چطور رنک بگیرم؟*\n"
        "• حمله به بازیکن‌های دیگه\n"
        "• حمله ترکیبی > حمله موشکی\n"
        "• هرچه دمیج بیشتر → رنک بیشتر\n\n"
        "📝 *نکته‌های مهم:*\n"
        "• بازیکن لیگ ماه رنک نمی‌گیره\n"
        "• به بازیکن لیگ ماه حمله کنی → رنک نمی‌گیری\n"
        "• هر ماه اول ریست می‌شه\n"
        "• بالاترین رنک ذخیره می‌شه\n\n"
        "💡 *صفحه‌بندی:* با دکمه‌های ⬅️ قبل / بعدی ➡️"
    ),
    "clan": (
        "👥 *راهنمای کلن*\n\n"
        "💰 *خرید کلن:* 4,000 سکه\n"
        "👥 *حداکثر اعضا:* 10 نفر\n\n"
        "📌 *نقش‌ها:*\n"
        "• 👑 رهبر → همه‌کاره\n"
        "• 🎖️ افسر → مدیریت، پیام، دعوت\n"
        "• 👤 عضو → فقط دیدن\n\n"
        "📋 *امکانات:*\n"
        "• 🔍 جستجو → پیدا کردن کلن\n"
        "• 📩 درخواست عضویت (بدون نیاز به متن)\n"
        "• 📋 لیست اعضا\n"
        "• ⚙️ مدیریت (رهبر/افسر):\n"
        "  - ✏️ تغییر اسم (1,000 سکه)\n"
        "  - 📢 پیام به همه اعضا\n"
        "  - 📩 دعوت عضو\n"
        "• 🚪 اخراج/ارتقا/تنزل (فقط رهبر)\n"
        "• 👑 انتقال مالکیت (فقط رهبر)\n"
        "• 🗑️ حذف کلن (فقط رهبر)\n\n"
        "⚔️ *جنگ کلن‌ها:* ۳ تا ۶ نفر، ۱۵ دقیقه\n"
        "🔧 *ارتقای کلن:* با اهدای سکه"
    ),
    "battle": (
        "🌐 *راهنمای کامل حمله جهانی*\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        "🎯 *سیستم پیشنهاد حریف:*\n"
        "• اول تو لیگ خودت دنبال حریف می‌گرده\n"
        "• اگه نبود، از لیگ‌های پایین‌تر پیشنهاد می‌ده\n"
        "• پیشنهاد ۳۰ ثانیه معتبره\n"
        "• دکمه «➡️ بعدی» با هزینه ۱۰ سکه حریف عوض می‌کنه\n\n"
        "⚔️ *دو نوع حمله:*\n\n"
        "1️⃣ *حمله موشکی (عادی):*\n"
        "   • فقط ۱ موشک / پهباد مصرف می‌شه\n"
        "   • می‌تونی ۱ طلسم (چشم، آتش، شکار...) همراهش کنی\n"
        "   • دمیج کمتر، ولی موشک کمتر مصرف می‌شه\n\n"
        "2️⃣ *حمله ترکیبی:*\n"
        "   • کل ترکیب نظامی رو شلیک می‌کنه\n"
        "   • دمیج بالا، غارت بالا، رنک بالا\n"
        "   • ظرفیت: طبق سطح زرادخانه\n"
        "   • در لیگ ماه: روزی ۱۲ بار مجاز\n\n"
        "━━━━━━━━━━━━━━━━━\n"
        "📦 *غارت چی می‌بری؟*\n"
        "• 🪙 سکه از حریف (اگه داشته باشه)\n"
        "• 🛢 نفت از حریف (اگه پالایشگاه داشته باشه)\n"
        "• 🏆 رنک +برای مهاجم، -برای مدافع\n\n"
        "🛡 *دفاع حریف:*\n"
        "• پدافند فعال: شانس بلاک کردن حمله\n"
        "• ساختمون‌ها: کاهش دمیج\n"
        "• طلسم آب/سپر: کاهش دمیج و غارت (خودکار)\n"
        "• فونیکس: کاهش حمله جنگنده دشمن\n\n"
        "⏱ *محدودیت زمانی:*\n"
        "• ۵ ثانیه بین هر دو حمله صبر کن\n"
        "• پیشنهاد حریف ۳۰ ثانیه معتبره\n\n"
        "⚠️ *در لیگ ماه:*\n"
        "• حمله ترکیبی رنک نمی‌ده\n"
        "• حمله عادی رنک نمی‌ده\n"
        "• حداکثر ۱۲ حمله ترکیبی در روز"
    ),
    "attack": (
        "⚔️ *راهنمای کامل حمله در گپ*\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        "📝 *نحوه حمله:*\n"
        "1. روی پیام حریف ریپلای بزن\n"
        "2. بنویس: `حمله [اسم موشک]`\n\n"
        "📌 *مثال‌ها:*\n"
        "• `حمله اطلس` → حمله با موشک اطلس\n"
        "• `حمله اطلس آتش` → با طلسم آتش\n"
        "• `حمله عماد چشم` → با طلسم چشم\n"
        "• `حمله شاهد` → حمله پهبادی\n"
        "• `حمله ترکیبی` → حمله با کل ترکیب\n\n"
        "━━━━━━━━━━━━━━━━━\n"
        "✨ *طلسم‌های قابل استفاده در حمله:*\n"
        "• 🧿 چشم → ۲۵٪ نادیده گرفتن پدافند\n"
        "• 🔥 آتش → ۲۰٪ دمیج بیشتر\n"
        "• 🌪 طوفان → ۲ موشک اضافه\n"
        "• ⚡ صاعقه → حریف ۶۰ ثانیه فلج\n"
        "• 👁 شکار → ۴۰٪ دمیج بیشتر\n"
        "• ❄️ یخ → حریف ۳۰ ثانیه فلج\n\n"
        "⚠️ *فقط ۱ طلسم در هر حمله!*\n\n"
        "━━━━━━━━━━━━━━━━━\n"
        "🚫 *خطاهای رایج:*\n"
        "• ❌ نام موشک اشتباه → موشک وجود نداره\n"
        "• ❌ این موشک در لیست دارایی شما نیست → نداریش\n"
        "• ❌ روی پیام حریف ریپلای کن → ریپلای نزدی\n"
        "• ❌ خودت! → به خودت نمی‌تونی حمله کنی\n"
        "• ❌ مالک! → به ادمین نمی‌تونی حمله کنی\n"
        "• ⛔ شما فلج هستید → صبر کن یا طلسم دفع کن\n\n"
        "⏱ *محدودیت:* ۵ ثانیه بین حملات"
    ),
    "military": (
        "🎯 *راهنمای مدیریت ترکیب*\n\n"
        "📝 *چهار بخش اصلی:*\n\n"
        "1️⃣ *ترکیب‌ها:*\n"
        "• ➕ ساخت ترکیب جدید (اسم بده)\n"
        "• ✏️ ویرایش (اضافه/حذف سلاح)\n"
        "• 🗑️ حذف کل ترکیب\n"
        "⚠️ فقط موشک‌های عادی (نه گردونه)\n"
        "⚠️ ظرفیت زرادخانه چک می‌شه\n\n"
        "2️⃣ *🏗️ ساختمان‌ها (6 نوع):*\n"
        "• 🏠 پادزون → قیمت 10K، 5%/سطح\n"
        "• 🏠 مگالیر → 20K، 7%/سطح\n"
        "• 🏠 ورنیکس → 30K، 10%/سطح (به جنگنده دشمن آسیب می‌زنه)\n"
        "• 🏠 فونیکس → 50K، 12%/سطح (حمله جنگنده دشمن رو کم می‌کنه)\n"
        "• ⚔️ آشیانه → 100K، 15%/سطح\n"
        "• 🛡️ سپر آهنی → 200K، 20%/سطح\n"
        "🎯 مکس: لول 7\n"
        "⚠️ زرادخانه باید هم‌سطح یا بالاتر باشه\n\n"
        "3️⃣ *🏰 زرادخانه (ظرفیت حمله ترکیبی):*\n"
        "• 📊 سطح: 1 تا 6\n"
        "• 📦 ظرفیت: 5/10/20/35/50/75 موشک\n"
        "• 💰 هزینه: 10K/25K/50K/65K/100K + 5K نفت\n"
        "• 🎯 فقط برای حمله ترکیبی\n"
        "• 🔒 شرط ارتقای ساختمان‌ها\n\n"
        "4️⃣ *✈️ پایگاه جنگنده:*\n"
        "• 💰 ساخت: 100,000 سکه (لول 5+)\n"
        "• 📊 سطح 1 تا 5\n"
        "• 🎯 ظرفیت: 3 تا 18 جنگنده\n"
        "• 🛠 خرید جنگنده (فونیکس، رعد، سیمرغ، آذرخش، تایتان)\n"
        "• ⬆️ ارتقا فونیکس (تا لول 6)\n"
        "• 🔧 تعمیر جنگنده‌ها\n"
        "• 🎡 گردونه جنگنده (6K سکه)"
    ),
    "profile": (
        "🪪 *راهنمای کامل دارایی*\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        "📊 *اطلاعات نمایش داده شده:*\n\n"
        "👤 *پروفایل شخصی:*\n"
        "• نام و آیدی عددی\n"
        "• تاریخ عضویت\n"
        "• سطح و تجربه فعلی\n"
        "• 🪙 سکه، 🛢 نفت، 💎 الماس\n\n"
        "🏆 *رنک و لیگ:*\n"
        "• رنک فعلی\n"
        "• بالاترین رنک (best_rank)\n"
        "• لیگ فعلی (تازه‌کار تا ماه)\n\n"
        "🛡 *سپر فعال:*\n"
        "• اگه سپر داشته باشی، فعال نشون داده می‌شه\n\n"
        "📦 *دارایی‌های نظامی:*\n"
        "• 🧨 کروز، 🚀 بالستیک، ⚡ هایپر\n"
        "• ☣️ شیمیایی، ☢️ هسته‌ای\n"
        "• ✈️ جنگنده‌های هیرو\n"
        "• 🛡 پدافندها و 🛩 پهبادها\n"
        "• ✨ طلسم‌ها\n"
        "• ⚡ فتاح ۲ (موشک ویژه)\n\n"
        "━━━━━━━━━━━━━━━━━\n"
        "🔢 *کپی آیدی:* دکمه «🔢 کپی کردن آیدی» بالای پروفایل\n\n"
        "💡 *نکته:* اگه هیچ دارایی نداشته باشی، «هیچ دارایی نداری!» نشون می‌ده"
    ),
    "gift": (
        "🎁 *راهنمای کامل جایزه روزانه*\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        "🕒 *زمان:*\n"
        "• هر ۲۴ ساعت یکبار\n"
        "• از آخرین دریافتی حساب می‌شه\n\n"
        "📊 *جوایز احتمالی:*\n\n"
        "• ⚔️ ۴ عدد راون → شانس ۸٪\n"
        "• 🚀 ۱۰ عدد اطلس → شانس ۲۰٪\n"
        "• 🪙 ۵۰۰ سکه → شانس ۵۵٪\n"
        "• 🪙 ۲۰۰ سکه → شانس ۱۰۰٪ (تضمینی)\n\n"
        "⚠️ *نکته مهم:* هیچ الماسی نمی‌ده!\n\n"
        "🔔 *برای دریافت:*\n"
        "از منوی «🎁 جایزه روزانه» استفاده کن\n\n"
        "💡 *چرا؟* برای تعادل بازی، الماس فقط از رویدادهای خاص"
    ),
    "transfer": (
        "💳 *راهنمای کامل تبادل سکه*\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        "📤 *چطور بفرستم:*\n"
        "1. از منوی «💰 تبادل سکه» گزینه رو بزن\n"
        "2. آیدی عددی طرف مقابل رو بده\n"
        "3. مقدار سکه رو وارد کن\n"
        "4. تأیید کن\n\n"
        "📥 *چطور بگیرم:*\n"
        "• طرف مقابل برات می‌فرسته\n"
        "• خودکار به موجودیت اضافه می‌شه\n\n"
        "⚠️ *محدودیت‌های مهم:*\n"
        "• سقف روزانه: ۲,۰۰۰ سکه برای هر نفر\n"
        "• حداقل مقدار: ۱ سکه\n"
        "• فقط در پیوی کار می‌کنه\n"
        "• به خودت نمی‌تونی بفرستی\n"
        "• به کاربر غیرموجود نمی‌شه فرستاد\n\n"
        "🔒 *سقف روزانه چطور ریست می‌شه؟*\n"
        "• هر روز ساعت ۰۰:۰۰\n"
        "• ۲,۰۰۰ سکه در ۲۴ ساعت\n\n"
        "💡 *دلیل محدودیت:* جلوگیری از انتقال انبوه سکه"
    ),
    "account_transfer": (
        "📥 *راهنمای کامل انتقال اکانت*\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        "⚠️ *انتقال کامل اطلاعات!*\n"
        "همه دارایی، رنک، آیدی و... منتقل می‌شه\n\n"
        "📤 *مرحله ۱: توکن بگیر (تو بده):*\n"
        "• روی «📥 دریافت توکن» بزن\n"
        "• یه کد ۱۰ دقیقه‌ای تولید می‌شه\n"
        "• کد رو به طرف مقابل بده\n\n"
        "📥 *مرحله ۲: توکن وارد کن (تو بگیر):*\n"
        "• روی «📤 وارد کردن توکن» بزن\n"
        "• کد رو وارد کن\n"
        "• صاحب اکانت باید تأیید کنه\n"
        "• بعد از تأیید، انتقال انجام می‌شه\n\n"
        "━━━━━━━━━━━━━━━━━\n"
        "⚠️ *بعد از انتقال:*\n"
        "• 📤 فرستنده: اکانتش صفر می‌شه (پروفایل جدید، بدون دارایی)\n"
        "• 📥 گیرنده: همه دارایی و رنک و آیدی رو می‌گیره\n\n"
        "⏱ *اعتبار توکن:* ۱۰ دقیقه\n"
        "🔒 *تأیید:* صاحب اکانت باید حتماً تأیید کنه"
    ),
    "invite": (
        "🎁 *راهنمای دعوت دوستان*\n\n"
        "🔗 *لینک اختصاصی:*\n"
        "• دکمه /invite یا از «سایر» → لینک بگیر\n"
        "• لینک رو برای دوستان بفرست\n\n"
        "💰 *جایزه‌ها:*\n"
        "• تو: 2,000 سکه\n"
        "• دوستت: 500 سکه\n\n"
        "📊 *شرایط:*\n"
        "• فقط کاربر جدید (اولین بار وارد می‌شه)\n"
        "• خودت رو دعوت نکنی\n"
        "• لینک نامحدود"
    ),
    "factory": (
        "🏭 *راهنمای کارخانه*\n\n"
        "📌 *سه بخش:*\n\n"
        "1️⃣ *⛏️ معدن آهن:*\n"
        "• تولید: سطح × 100 آهن/ساعت\n"
        "• سقف: سطح × 500 آهن\n"
        "• ارتقا: تا 10 سطح\n\n"
        "2️⃣ *🏭 کارخانه فولاد (لول 25+):*\n"
        "• ساخت: 50,000 سکه + 500 آهن\n"
        "• تولید: سطح × 50 فولاد/ساعت\n"
        "• سقف: سطح × 250 فولاد\n\n"
        "3️⃣ *⚔️ کارخانه سلاح (لول 40+):*\n"
        "• ساخت: 100,000 سکه + 500 فولاد\n"
        "• تولید: سطح × 10 سلاح/ساعت\n"
        "• سقف: سطح × 50 سلاح\n\n"
        "💰 *فروش (دکمه فروشگاه کارخانه):*\n"
        "• آهن: 10 سکه\n"
        "• فولاد: 50 سکه\n"
        "• سلاح: 500 سکه"
    ),
    "league": (
        "🏅 *راهنمای کامل لیگ‌ها*\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        "📊 *۱۲ لیگ بر اساس رنک:*\n\n"
        "1️⃣ 🌱 *تازه‌کار* → رنک 0 تا 199\n"
        "2️⃣ 🥉 *برنزی* → رنک 200 تا 799\n"
        "3️⃣ 🥈 *نقره‌ای* → رنک 800 تا 1,499\n"
        "4️⃣ 🥇 *طلایی* → رنک 1,500 تا 2,999\n"
        "5️⃣ 💠 *پلاتینیوم* → رنک 3,000 تا 4,999\n"
        "6️⃣ 👻 *ارواح* → رنک 5,000 تا 7,999\n"
        "7️⃣ 🐉 *دراگون* → رنک 8,000 تا 11,999\n"
        "8️⃣ ❄️ *آیس* → رنک 12,000 تا 16,999\n"
        "9️⃣ ⭐ *طوفان* → رنک 17,000 تا 19,999\n"
        "🔟 ⚔️ *تایتان* → رنک 20,000 تا 27,999\n"
        "1️⃣1️⃣ 🔮 *کریستال* → رنک 28,000 تا 99,999\n"
        "1️⃣2️⃣ 🌙 *ماه* → رنک 100,000 و بالاتر\n\n"
        "━━━━━━━━━━━━━━━━━\n"
        "🎯 *چطور رنک بگیرم؟*\n"
        "• هر حمله موفق به حریف (به هر میزانی) رنک می‌ده\n"
        "• هرچه دمیج بیشتر → رنک بیشتر\n"
        "• حمله ترکیبی رنک بیشتری از حمله عادی می‌ده\n"
        "• مدافع همون مقدار رنک از دست می‌ده\n\n"
        "━━━━━━━━━━━━━━━━━\n"
        "⚠️ *نکات مهم:*\n"
        "• 🚫 وقتی به لیگ *🌙 ماه* برسی:\n"
        "   → حمله ترکیبی دیگه رنک نمی‌ده\n"
        "   → فقط روزی ۱۲ حمله ترکیبی مجاز داری\n"
        "• 🚫 اگه حریف در لیگ ماه باشه:\n"
        "   → حمله بهش رنک نمی‌ده\n"
        "• 🔄 هر ماه اول سال میلادی، رنک همه ریست می‌شه\n"
        "• 💾 بالاترین رنک همیشه ذخیره می‌مونه (best_rank)\n\n"
        "━━━━━━━━━━━━━━━━━\n"
        "💡 *برای دیدن لیگ فعلیت:*\n"
        "از منوی «🪪 دارایی» یا «📊 رنکینگ» استفاده کن"
    ),
    "arsenal": (
        "⚔️ *راهنمای تسلیحات خانه*\n\n"
        "📊 *سطوح:* 1 تا 5\n\n"
        "📦 *ظرفیت موشک‌های قابل خرید:*\n"
        "• سطح 1: کروز 200 / بالستیک 100 / هایپر 50 / شیمیایی 20 / هسته‌ای 1\n"
        "• سطح 2: 400 / 200 / 100 / 45 / 3\n"
        "• سطح 3: 800 / 400 / 250 / 120 / 10\n"
        "• سطح 4: 1400 / 700 / 450 / 250 / 40\n"
        "• سطح 5: 2000 / 1000 / 700 / 500 / 100\n\n"
        "💰 *هزینه ارتقا:*\n"
        "• 1→2: 20,000 سکه\n"
        "• 2→3: 40,000 سکه\n"
        "• 3→4: 65,000 سکه\n"
        "• 4→5: 100,000 سکه\n\n"
        "⚠️ *مهم:*\n"
        "• موقع خرید موشک، ظرفیت چک می‌شه\n"
        "• اگه پر باشه نمی‌تونی بخری\n"
        "• این جدا از زرادخانه است!\n"
        "• زرادخانه برای ظرفیت حمله ترکیبی است"
    ),
    "airport": (
        "🛩 *راهنمای فرودگاه*\n\n"
        "💰 *هزینه خرید:* 5,000 سکه\n"
        "🎯 *لول لازم:* 10\n\n"
        "📊 *سطوح:* 1 تا 7\n\n"
        "📦 *ظرفیت‌ها (سطح: جنگنده / پهباد):*\n"
        "• 1: 50 / 25\n"
        "• 2: 100 / 50 (5K نفت)\n"
        "• 3: 200 / 100 (10K)\n"
        "• 4: 400 / 200 (20K)\n"
        "• 5: 800 / 400 (40K)\n"
        "• 6: 1400 / 700 (80K)\n"
        "• 7: 2000 / 1000 (150K)\n\n"
        "🛩 *پهبادها (با نفت):*\n"
        "• شاهد (200) → رنک +1.5x\n"
        "• کرار (300) → رنک +1.8x\n"
        "• مهاجر (400) → رنک +2.2x\n"
        "• ابابیل (500) → رنک +2.5x\n"
        "• حماسه/یاسر/معراج/مهاجر6 (300-600) → 2 پدافند نابود\n"
        "• شاهد 136 / کرار 2 (500-600) → غارت بیشتر"
    ),
    "fighter_base": (
        "✈️ *راهنمای پایگاه جنگنده*\n\n"
        "💰 *ساخت پایگاه:* 100,000 سکه (لول 5+)\n\n"
        "📊 *سطوح پایگاه:*\n"
        "• 1: 3 اسلات\n"
        "• 2: 5 اسلات (50K + لول 10)\n"
        "• 3: 8 اسلات (100K + لول 15)\n"
        "• 4: 12 اسلات (200K + لول 20)\n"
        "• 5: 18 اسلات (450K + لول 30)\n\n"
        "🛠 *جنگنده‌های ساختنی:*\n"
        "• فونیکس: 50K، دمیج 20 (لول 1)\n"
        "• رعد: 100K، دمیج 35 (لول 2)\n"
        "• سیمرغ: 200K، دمیج 55 (لول 3)\n"
        "• آذرخش: 400K، دمیج 80 (لول 4)\n"
        "• تایتان: 800K، دمیج 120 (لول 5)\n\n"
        "🎡 *گردونه جنگنده (6K سکه):*\n"
        "• F-16, میگ 29, F-22, سوخو 35, F-35, سوخو 57, میگ 31, F-15, رافال, تایفون\n\n"
        "🛡 *فونیکس:*\n"
        "• کاهش حمله جنگنده دشمن\n"
        "• لول 1-6 → 0 تا 100%"
    ),
    "defense": (
        "🛡 *راهنمای کامل پدافند*\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        "📌 *۷ پدافند بر اساس لول:*\n\n"
        "1️⃣ 🔫 *تیربار* — لول ۱ — ۵۰ سکه\n"
        "   └ ۱۰٪ شانس بلاک\n\n"
        "2️⃣ 🔵 *گنبد آهنین* — لول ۲ — ۱۵۰ سکه\n"
        "   └ ۲۵٪ شانس بلاک\n\n"
        "3️⃣ 🛡️ *باور* — لول ۵ — ۸۰۰ سکه\n"
        "   └ ۴۰٪ شانس بلاک\n\n"
        "4️⃣ 🛡️ *پاتریوت* — لول ۸ — ۱,۵۰۰ سکه\n"
        "   └ ۵۰٪ شانس بلاک\n\n"
        "5️⃣ 🛡️ *S-400* — لول ۱۰ — ۲,۵۰۰ سکه\n"
        "   └ ۶۰٪ شانس بلاک (+۱۰٪ مقابل بالستیک سطح ۳+)\n\n"
        "6️⃣ 💠 *گاردین* — لول ۱۳ — ۴,۰۰۰ سکه\n"
        "   └ ۷۰٪ کاهش دمیج (بلاک نمی‌کنه، فقط کم می‌کنه)\n\n"
        "7️⃣ 🛡️ *تاد* — لول ۱۳ — ۵,۰۰۰ سکه\n"
        "   └ ۸۰٪ شانس بلاک\n\n"
        "━━━━━━━━━━━━━━━━━\n"
        "🎯 *نحوه کار:*\n"
        "• فقط ۱ پدافند می‌تونه فعال باشه\n"
        "• اگه چند تا داشته باشی، یکی رو انتخاب می‌کنی\n"
        "• پدافند فعال هنگام حمله حریف شانس بلاک داره\n\n"
        "⚠️ *استثناها:*\n"
        "• 🚀 هسته‌ای → پدافند اثر نداره (Unblockable)\n"
        "• ⚡ هایپرسونیک → شانس بلاک نصف می‌شه\n"
        "• ☣️ شیمیایی → ساختمون‌ها و پدافند اثر ندارن\n\n"
        "💡 *نکته:* پدافند رو با دکمه «انتخاب پدافند فعال» عوض کن"
    ),
    "drone": (
        "🛩 *راهنمای پهبادها*\n\n"
        "💰 *خرید:* با نفت\n"
        "🎯 *لول لازم:* 3\n"
        "⚠️ *نیاز:* فرودگاه\n\n"
        "📌 *3 دسته:*\n\n"
        "1️⃣ *رنک بیشتر:*\n"
        "• شاهد (200) → 1.5x\n"
        "• کرار (300) → 1.8x\n"
        "• مهاجر (400) → 2.2x\n"
        "• ابابیل (500) → 2.5x\n\n"
        "2️⃣ *نابودی پدافند:*\n"
        "• حماسه، یاسر، معراج، مهاجر 6 (300-600)\n"
        "• نابودی 2 پدافند حریف\n\n"
        "3️⃣ *غارت بیشتر:*\n"
        "• شاهد 136 (500) → 1.8x\n"
        "• کرار 2 (600) → 2.2x"
    ),
    "clan_war": (
        "⚔️ *راهنمای جنگ کلن‌ها*\n\n"
        "👑 *فقط رهبر* می‌تونه جنگ رو شروع کنه\n"
        "👥 حداقل ۳ نفر، حداکثر ۶ نفر\n\n"
        "📝 *مراحل:*\n"
        "1. رهبر اعضا رو انتخاب می‌کنه\n"
        "2. روی «شروع جستجو» می‌زنه\n"
        "3. منتظر می‌مونه رهبر کلن دیگه‌ای هم شروع کنه\n"
        "4. وقتی حریف پیدا شد → جنگ شروع می‌شه\n\n"
        "🎯 *نحوه جنگ:*\n"
        "• رهبر با رهبر می‌افته\n"
        "• بقیه اعضا رندوم با هم\n"
        "• هر نفر فقط *یک بار* می‌تونه حمله کنه\n"
        "• حمله ترکیبی\n\n"
        "⏱ *زمان:* ۱۵ دقیقه\n\n"
        "⭐ *امتیازدهی:*\n"
        "• ۳ ستاره: تخریب ۸۰٪+\n"
        "• ۲ ستاره: تخریب ۵۰٪+\n"
        "• ۱ ستاره: تخریب ۲۰٪+\n"
        "• ۰ ستاره: کمتر\n\n"
        "🏆 کلنی که امتیاز بیشتری بگیره برنده‌ست\n"
        "📈 رنک کلن برنده = مجموع امتیازاتش"
    ),
    "clan_upgrade": (
        "🔧 *راهنمای ارتقای کلن*\n\n"
        "📊 *سطح کلن:* 1 تا 150\n\n"
        "💰 *هزینه ارتقا:*\n"
        "• سطح 1→2: ۱,۰۰۰ سکه\n"
        "• سطح 2→3: ۲,۰۰۰ سکه\n"
        "• سطح 3→4: ۳,۰۰۰ سکه\n"
        "• و همینطور... (سطح × 1000)\n\n"
        "👥 *هر عضوی* می‌تونه اهدا کنه\n"
        "🎯 وقتی مجموع به هدف رسید → خودکار ارتقا می‌یابه\n\n"
        "🔔 *اطلاع‌رسانی:*\n"
        "بعد از ارتقا، به *همه اعضا* پیام داده می‌شه\n\n"
        "💡 *نکته:* اگه ارتقا نیمه‌کاره بمونه (مثلاً ۵۰۰/۱۰۰۰)، اون مقدار ذخیره می‌شه و دفعه بعد ادامه می‌دید"
    ),
}

# ==================== تسلیحات خانه (مستقل از زرادخانه) ====================
ARSENAL_CAPACITIES = {
    1: {"cruise": 200, "ballistic": 100, "hypersonic": 50, "chemical": 20, "nuclear": 1},
    2: {"cruise": 400, "ballistic": 200, "hypersonic": 100, "chemical": 45, "nuclear": 3},
    3: {"cruise": 800, "ballistic": 400, "hypersonic": 250, "chemical": 120, "nuclear": 10},
    4: {"cruise": 1400, "ballistic": 700, "hypersonic": 450, "chemical": 250, "nuclear": 40},
    5: {"cruise": 2000, "ballistic": 1000, "hypersonic": 700, "chemical": 500, "nuclear": 100}
}

ARSENAL_UPGRADE_COSTS = {
    1: 20000,
    2: 40000,
    3: 65000,
    4: 100000
}


# ==================== ایموجی پدافند ====================
DEFENSE_EMOJI_MAP = {
    "تیربار": "🔫", "گنبد آهنین": "🛡️", "باور": "🛡️",
    "پاتریوت": "🎯", "S-400": "💥", "گاردین": "💎", "تاد": "⚡",
}


# ==================== 🛒 World Shop (قبلاً World Pass) ====================
WORLD_PASS_TITLE = "⚜️ WORLD SHOP ⚜️"

WORLD_PASS_DESCRIPTION = (
    "⭐️ WORLD SHOP ⭐️\n\n"
    "با خرید امکانات ویژه‌ای دریافت می‌کنید:\n"
    "• دسترسی به جوایز روزانه اختصاصی\n"
    "• دریافت بج اختصاصی\n\n"
    "📦 جوایز این فصل (۱۰ روز):\n"
    "روز 1 → 15 باور\n"
    "روز 2 → 10 ونگارد\n"
    "روز 3 → 5000 سکه\n"
    "روز 4 → 10 الماس\n"
    "روز 5 → 5 راون\n"
    "روز 6 → 10 تاد\n"
    "روز 7 → 10 قدر\n"
    "روز 8 → 10 آذرخش\n"
    "روز 9 → 10 الماس\n"
    "روز 10 → 10000 سکه\n\n"
    "🔔 هر روز فقط یک جایزه می‌تونی بگیری!"
)

WORLD_PASS_TOTAL_DAYS = 10

WORLD_PASS_REWARDS = [
    {"day": 1, "type": "defense", "name": "باور", "amount": 15,
     "text": "🛡 15 عدد باور"},
    {"day": 2, "type": "weapon", "name": "ونگارد", "amount": 10,
     "text": "⚔️ 10 عدد ونگارد"},
    {"day": 3, "type": "coins", "amount": 5000,
     "text": "🪙 5,000 سکه"},
    {"day": 4, "type": "gems", "amount": 10,
     "text": "💎 10 الماس"},
    {"day": 5, "type": "weapon", "name": "راون", "amount": 5,
     "text": "🦅 5 عدد راون"},
    {"day": 6, "type": "defense", "name": "تاد", "amount": 10,
     "text": "🛡 10 عدد تاد"},
    {"day": 7, "type": "weapon", "name": "قدر", "amount": 10,
     "text": "💪 10 عدد قدر"},
    {"day": 8, "type": "weapon", "name": "آذرخش", "amount": 10,
     "text": "🌩️ 10 عدد آذرخش"},
    {"day": 9, "type": "gems", "amount": 10,
     "text": "💎 10 الماس"},
    {"day": 10, "type": "coins", "amount": 10000,
     "text": "🪙 10,000 سکه"},
]


def get_world_pass_reward(day):
    for r in WORLD_PASS_REWARDS:
        if r["day"] == day:
            return r
    return None


def validate_world_pass_reward(reward):
    if not reward:
        return False, "❌ جایزه پیدا نشد"

    rtype = reward.get("type")
    if rtype in ("coins", "gems"):
        return True, None

    if rtype == "weapon":
        if not MISSILES.get(reward.get("name")):
            return False, f"❌ آیتم {reward.get('name')} تعریف نشده"
        return True, None

    if rtype == "defense":
        if reward.get("name") not in DEFENSES:
            return False, f"❌ پدافند {reward.get('name')} تعریف نشده"
        return True, None

    return False, "❌ نوع جایزه نامعتبر"


def apply_world_pass_reward(p, reward):
    rtype = reward["type"]

    if rtype == "coins":
        p["coins"] = p.get("coins", 0) + reward["amount"]
        return f"🪙 {reward['amount']:,} سکه"

    elif rtype == "gems":
        p["gems"] = p.get("gems", 0) + reward["amount"]
        return f"💎 {reward['amount']} الماس"

    elif rtype == "weapon":
        wname = reward["name"]
        mdata = MISSILES.get(wname)
        if not mdata:
            return f"❌ آیتم {wname} پیدا نشد"
        cat = mdata["category"]
        if cat not in p:
            p[cat] = {}
        if wname not in p[cat]:
            p[cat][wname] = {"count": 0, "level": 1}
        p[cat][wname]["count"] += reward["amount"]
        emoji = mdata.get("emoji", "🚀")
        return f"{emoji} {reward['amount']} عدد {wname}"

    elif rtype == "defense":
        dname = reward["name"]
        if "defense" not in p:
            p["defense"] = {}
        if dname not in p["defense"]:
            p["defense"][dname] = {"count": 0}
        p["defense"][dname]["count"] += reward["amount"]
        if not p.get("active_defense"):
            p["active_defense"] = dname
        emoji = DEFENSE_EMOJI_MAP.get(dname, "🛡️")
        return f"{emoji} {reward['amount']} عدد {dname}"

    return "❌ نوع جایزه نامعتبر"