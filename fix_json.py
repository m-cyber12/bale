import json
from config import DB_FILE

with open(DB_FILE, "r", encoding="utf-8") as f:
    content = f.read()

print(f"📊 طول فایل: {len(content):,}\n")

def save_fixed(data):
    users = [k for k, v in data.items() if isinstance(v, dict) and "user_id" in v]
    print(f"✅ تعمیر موفق! کلیدها: {len(data)} | کاربران: {len(users)}")
    with open(DB_FILE + ".fixed", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"💾 ذخیره شد: {DB_FILE}.fixed")

# ====== روش ۱: پیدا کردن آخرین کاربر کامل ======
# دنبال الگوی "\n  },\n" می‌گردیم (بسته شدن کاربر با indent=2)
print("🔍 روش ۱: آخرین کاربر کامل...")
idx = content.rfind("\n  },\n")
while idx > 0:
    new_content = content[:idx] + "\n  }\n}"
    try:
        data = json.loads(new_content)
        save_fixed(data)
        exit(0)
    except json.JSONDecodeError:
        # یه کم عقب‌تر برو
        idx = content.rfind("\n  },\n", 0, idx)
print("❌ روش ۱ جواب نداد\n")

# ====== روش ۲: حذف آخرین کاربر ناقص ======
# خط به خط از آخر می‌ریم تا به یه "  }" کامل برسیم
print("🔍 روش ۲: حذف کاربر ناقص...")
lines = content.split("\n")
for i in range(len(lines) - 1, 0, -1):
    line = lines[i]
    # خطی که کاربر رو با indent=2 می‌بنده
    if line == "  }," or line == "  }":
        truncated = "\n".join(lines[:i+1])
        # اگه با , تموم شده، حذفش کن
        if truncated.rstrip().endswith(","):
            truncated = truncated.rstrip()[:-1]
        if not truncated.rstrip().endswith("}"):
            truncated = truncated.rstrip() + "\n}"
        else:
            truncated = truncated.rstrip() + "\n}"
        try:
            data = json.loads(truncated)
            save_fixed(data)
            exit(0)
        except json.JSONDecodeError:
            continue
print("❌ روش ۲ جواب نداد\n")

# ====== روش ۳: پارس دستی، همه کاربران کامل رو استخراج کن ======
print("🔍 روش ۳: استخراج دستی کاربران...")
# پیدا کردن مرز بین کاربران با regex
import re
# الگو: "\n  \"user_id\": \"ID\"" رو می‌گردیم
# ولی بهتره با یه پارسر دستی ساده چک کنیم
users = {}
# هر کاربر با `  "ID": {` شروع میشه
pattern = re.compile(r'\n  "(\d+)": \{')
positions = [(m.start(), m.group(1)) for m in pattern.finditer(content)]
print(f"👥 {len(positions)} کاربر پیدا شد")

if positions:
    # از اول تا آخرین کاربر، هر کدوم رو جدا بااستخراج کن
    for j in range(len(positions) - 1, -1, -1):
        start, uid = positions[j]
        # از این کاربر تا کاربر بعدی یا آخر
        if j + 1 < len(positions):
            end = positions[j + 1][0]
        else:
            end = len(content)
        chunk = content[start:end].rstrip()
        # چک کنیم این chunk کامل یه کاربر باشه
        candidate = "{" + chunk.rstrip(",")
        if not candidate.endswith("}"):
            # شاید آخرش ناقصه
            continue
        try:
            user_data = json.loads(candidate)
            # شاید چند تا key داشته باشه اگر کاما اضافه مونده باشه
            if isinstance(user_data, dict) and uid in user_data:
                users[uid] = user_data[uid]
                print(f"   ✅ {uid} - {user_data[uid].get('name', '?')}")
        except:
            continue

if users:
    save_fixed(users)
    exit(0)

print("❌ همه روش‌ها شکست خورد!")
print("⚠️ باید فایل رو پاک کنی.")