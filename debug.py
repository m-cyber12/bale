# debug.py — تست خام دریافت آپدیت‌ها
import requests
import urllib3
import time
import json
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

TOKEN = "692461609:ywJtq7YooyShHcunMykaID8b3VWcx6z1gXk"
API_URL = f"https://tapi.bale.ai/bot{TOKEN}"

# 1️⃣ اول Webhook رو پاک کن
print("🧹 حذف WebHook...")
r = requests.get(f"{API_URL}/deleteWebhook", verify=False, timeout=10)
print(f"نتیجه: {r.text}\n")

time.sleep(2)

# 2️⃣ offset رو صفر کن تا همه آپدیت‌ها بیان
print("📥 شروع دریافت آپدیت‌ها...")
print("🔘 حالا روی یه دکمه ربات بزن!\n")
print("=" * 50)

offset = 0
while True:
    try:
        r = requests.get(f"{API_URL}/getUpdates",
                        params={"offset": offset, "timeout": 30,
                                "allowed_updates": json.dumps(["message", "callback_query"])},
                        verify=False, timeout=35)
        data = r.json()
        print(f"\n📡 Raw response: {json.dumps(data, ensure_ascii=False, indent=2)[:2000]}")
        if data.get("ok"):
            for upd in data["result"]:
                offset = upd["update_id"] + 1
                print(f"\n{'='*50}")
                print(f"🆔 Update ID: {upd['update_id']}")
                print(f"📦 Keys: {list(upd.keys())}")
                if "callback_query" in upd:
                    print(f"✅ CALLBACK FOUND!")
                    print(f"   Data: {upd['callback_query'].get('data')}")
                    print(f"   From: {upd['callback_query'].get('from', {}).get('id')}")
                elif "message" in upd:
                    print(f"💬 MESSAGE")
                    print(f"   Text: {upd['message'].get('text', '')[:50]}")
                else:
                    print(f"⚠️ Unknown update type!")
                print(f"{'='*50}\n")
    except Exception as e:
        print(f"❌ Error: {e}")
    time.sleep(1)