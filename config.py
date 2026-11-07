# ⚙️ تنظیمات کلی ربات

TOKEN = "692461609:ywJtq7YooyShHcunMykaID8b3VWcx6z1gXk"
API_URL = f"https://tapi.bale.ai/bot{TOKEN}"

ADMIN_ID = 522059458
PARTNER_ID = 234775012

GAP_ID = "worldwar2037"
CHANNEL_ID = "worldwar2036"
CHANNEL_ID_2 = "scorezone"
SUPPORT_ID = "MohammadMahdi2037"
SHOP_URL = "https://ble.ir/MohammadMahdi2037"

DB_FILE = "players.json"
OFFSET_FILE = "offset.txt"
RANK_RESET_FILE = "last_rank_reset.txt"

BOT_USERNAME = "worldwar2037bot"
INVITE_REWARD = 2000
NEW_USER_REWARD = 500

# ==================== 👥 کلن ====================
OFFICIAL_CLAN_ID = "WorldWar2037"
OFFICIAL_CLAN_NAME = "⚜️WORLD WAR⚜️"
CLAN_MAX_MEMBERS = 10

# جنگ کلن
CLAN_WAR_MIN_PLAYERS = 3
CLAN_WAR_MAX_PLAYERS = 6
CLAN_WAR_DURATION = 15 * 60

# ارتقای کلن
CLAN_UPGRADE_BASE_COST = 1000
CLAN_MAX_LEVEL = 150

# ==================== 🎁 باکس شانسی ====================
# گروه‌ها به صورت خودکار از دیتابیس خونده می‌شن
BOX_SPLIT_DELAY_SECONDS = 300  # ۵ دقیقه بین نیمه اول و دوم

# ==================== ⚙️ تنظیمات ارتقا موشک ====================
MISSILE_MAX_LEVEL = 6

UPGRADE_TIME_PER_LEVEL = {1: 30, 2: 50, 3: 90, 4: 150, 5: 240}

UPGRADE_COST_MULTIPLIER = 0.5

FATAH2_DAMAGE = 100
FATAH2_REWARD = 500

COMBO_MAX_DAMAGE = 600
COMBO_MAX_COINS = 3000
COMBO_MAX_OIL = 1500
COMBO_MAX_RANK = 300

AUTO_REPAIR_TIME = 24 * 3600
HP_REPAIR_COST = 10

# 🖼️ عکس فروشگاه
SHOP_PHOTO = "234775012:-7269128521859195135:1:d71a0507c98b48f3933da630fd184fa14c3aef4d6d703360"

# 🖼️ عکس فرودگاه
AIRPORT_PHOTO = "234775012:7944302518436830976:1:d71a0507c98b48f30d07454e645acb613f188a170fc689f2"

# ==================== 💳 توکن پرداخت Bale ====================
WALLET_TOKEN = "WALLET-aXABdbTTIIA2AaDU"
WALLET_TEST_TOKEN = "WALLET-TEST-1111111111111111"
PAYMENT_CURRENCY = "IRR"

# ==================== 🛒 World Shop ====================
WORLD_PASS_PRICE_RIAL = 400000
WORLD_PASS_PRICE_TOMAN = 40000

# ==================== ⭐️ اشتراک ویژه (Subscription) ====================
SUBSCRIPTION_PRICE_RIAL = 500000
SUBSCRIPTION_PRICE_TOMAN = 50000
SUBSCRIPTION_DURATION_DAYS = 30

SUB_DISCOUNT_MISSILE = 10
SUB_TRANSFER_LIMIT = 5000
SUB_DAILY_CRUISE = 40
SUB_DAILY_BALLISTIC = 30
SUB_DAILY_HYPERSONIC = 20
SUB_SHIELD_MAX_SECONDS = 7200
SUB_GEMS_CHANCE = 10
SUB_DAILY_GEMS_AMOUNT = 3


# ==================== 💳 خرید آیتم (Item Packs) ====================
ITEM_PACKS = {
    "level": {
        "name": "پک لول",
        "emoji": "⭐",
        "price_per_unit": 20000,      # تومان — هر سطح
        "unit_name": "سطح",
        "reward_per_unit": 1,
        "reward_name": "سطح",
        "min_qty": 1,
        "max_qty": 30,
    },
    "oil": {
        "name": "پک نفت",
        "emoji": "🛢",
        "price_per_unit": 2000,       # تومان — هر ۱۰۰۰ نفت
        "unit_name": "هزار نفت",
        "reward_per_unit": 1000,
        "reward_name": "نفت",
        "min_qty": 1,
        "max_qty": 500,
    },
    "coins": {
        "name": "پک سکه",
        "emoji": "🪙",
        "price_per_unit": 2000,       # تومان — هر ۱۰۰۰ سکه
        "unit_name": "هزار سکه",
        "reward_per_unit": 1000,
        "reward_name": "سکه",
        "min_qty": 1,
        "max_qty": 500,
    },
    "gems": {
        "name": "پک الماس",
        "emoji": "💎",
        "price_per_unit": 1,          # تومان — هر ۱ الماس (۵۰ الماس = ۵۰ تومان)
        "unit_name": "الماس",
        "reward_per_unit": 1,
        "reward_name": "الماس",
        "min_qty": 1,
        "max_qty": 10000,
    },
}