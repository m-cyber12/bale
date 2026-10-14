# 🚀 راه‌اندازی روی Render

راهنمای گام‌به‌گام. همه‌ی توکن‌ها در **Environment** می‌روند — هیچ‌چیزی داخل کد نیست.

---

## ۰) قبل از شروع

مطمئن شو این‌ها را داری:

| چه | از کجا |
|---|---|
| توکن ربات بله | BotFather بله |
| توکن ربات تلگرام *(اختیاری)* | [@BotFather](https://t.me/BotFather) |
| کلید OpenRouter *(اختیاری — برای هوش مصنوعی)* | [openrouter.ai/keys](https://openrouter.ai/keys) |
| آیدی عددی خودت | پیوی ربات بله یا [@userinfobot](https://t.me/userinfobot) |

---

## ۱) ساخت سرویس (روش Blueprint — ساده‌تر)

1. وارد [dashboard.render.com](https://dashboard.render.com) شو (با گیت‌هاب ثبت‌نام کن).
2. **New +** → **Blueprint**.
3. ریپوی `m-cyber12/bale` را انتخاب کن.
4. Render فایل `render.yaml` را می‌خواند و سرویس `alpha-group-bot` را می‌سازد.
5. در مرحله‌ی **Environment** این‌ها را بگذار (مقدارها را خودت وارد کن):

```
BALE_TOKEN          = 123456:ABC...        ← توکن ربات بله
TELEGRAM_TOKEN      = 789:XYZ...           ← اگر تلگرام هم می‌خواهی
OPENROUTER_API_KEY  = sk-or-v1-...         ← برای هوش مصنوعی
OWNER_ID            = 234775012            ← آیدی عددی خودت
PLATFORMS           = bale,telegram        ← خالی بگذاری، خودکار تشخیص می‌دهد
```

6. **Apply** → بیلد و دیپلوی شروع می‌شود (۲–۴ دقیقه).

### روش دستی (اگر Blueprint نخواستی)

**New +** → **Web Service** → ریپو را وصل کن و این‌ها را تنظیم کن:

| فیلد | مقدار |
|---|---|
| **Language / Runtime** | `Python 3` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `python3 -u main.py` |
| **Health Check Path** | `/healthz` |
| **Root Directory** | خالی بگذار |
| Instance Type | Free (برای تست) / Starter (برای جدی) |

**چرا این‌ها؟**

- `pip install -r requirements.txt` — ربات وابستگی اجباری ندارد، پس این خط
  در چند ثانیه تمام می‌شود. اگر بعداً کتابخانه‌ای لازم شد، فقط به
  `requirements.txt` اضافه کن؛ لازم نیست دستور را عوض کنی.
  (اگر ترجیح می‌دهی بیلد کاملاً بی‌کار باشد: `echo no-deps` هم کار می‌کند.)
- `python3 -u main.py` — `-u` یعنی لاگ‌ها **بی‌درنگ** در تب Logs ظاهر شوند
  (وگرنه بافر می‌شوند و فکر می‌کنی ربات کار نمی‌کند). حتماً همین را بزن.
- Health Check Path را `/healthz` بگذار؛ Render با آن می‌فهمد سرویس سالم است.
- اگر روزی خواستی گیف اختصاصی هم داشته باشی: در `requirements.txt` خط
  `Pillow>=10.0.0` را از کامنت دربیار (پیش‌فرض کامنت است تا بیلد سبک بماند).

---

## ۲) بررسی سلامت

بعد از دیپلوی، این آدرس را باز کن:

```
https://<اسم-سرویس>.onrender.com/healthz
```

باید چیزی شبیه این ببینی:

```json
{
  "ok": true,
  "platforms": [{"key": "bale", "configured": true, "api_host": "tapi.bale.ai"}],
  "ai": {"enabled": true, "key_set": true, "models_total": 14}
}
```

در **Logs** هم باید این خطوط را ببینی:

```
📡 پیام‌رسان فعال: بله (bale) — توکن از BALE_TOKEN
🧠 موتور هوش مصنوعی: روشن (OpenRouter) — کلید از env
🌐 وب‌سرور روی http://0.0.0.0:10000 بالا آمد
✅ متصل به بله (@alpha_bot) — شناسه: 1234
```

> `api_host` فقط دامنه است — خودِ توکن هیچ‌وقت در لاگ/health نشان داده نمی‌شود.

---

## ۳) ⚠️ نکته‌ی حیاتی: خواب رفتن Free

سرویس **رایگان** Render بعد از ۱۵ دقیقه بی‌کاری می‌خوابد. برای ربات
Long-polling این یعنی ربات از کار می‌افتد تا وقتی یک درخواست HTTP بیاید.

**سه راه‌حل:**

| راه | هزینه | توضیح |
|---|---|---|
| ✅ پینگر بیرونی | رایگان | یک سرویس مثل [cron-job.org](https://cron-job.org) یا UptimeRobot را بگذار هر **۵ دقیقه** `https://<سرویس>.onrender.com/healthz` را بزند → ربات بیدار می‌ماند |
| 💳 پلن Starter | ~۷$ ماه | Web Service دیگر نمی‌خوابد — بهترین گزینه برای ربات واقعی |
| 💳 Background Worker | ~۷$ ماه | فقط polling (بدون وب‌سرور) — اگر پورت لازم نداری |

در نبود پینگر، ربات فقط وقتی بیدار می‌شود که کسی سایت را باز کند؛
پیام‌های گروه در آن فاصله دریافت نمی‌شوند (توسط خودِ بله فقط ۲۴ ساعت
نگه داشته می‌شوند و بعد از بیدار شدن دوباره تحویل داده می‌شوند).

---

## ۴) ذخیره‌ی داده‌ها (گروه‌ها، اخطارها، پرونده‌های AI)

روی پلن رایگان **دیسک وجود ندارد**؛ یعنی با هر دیپلوی/ری‌استارت، پوشه‌ی
`data/` از صفر شروع می‌شود (تنظیمات گروه‌ها و آمار پاک می‌شوند).

اگر می‌خواهی داده‌ها بمانند:

1. پلن را به Starter تغییر بده.
2. **Disks** → **Add Disk** → نام `data`، مسیر (Mount Path) `/var/data`، اندازه ۱GB.
3. در Environment اضافه کن:

```
DATA_DIR = /var/data
```

از این به بعد `groups.json`، `ai/config.json` و بقیه در دیسک می‌مانند.

---

## ۵) وصل کردن پیام‌رسان دلخواه (وب‌هوک)

هر پیام‌رسانی که بتواند JSON بفرستد/بگیرد وصل می‌شود:

```
WEBHOOK_SEND_URL = https://my-bridge.example.com/send
WEBHOOK_TOKEN    = یک-رمز-دلخواه
PLATFORMS        = bale,webhook
```

**ورودی** — پل تو این آدرس را صدا می‌زند:

```
POST https://<سرویس>.onrender.com/webhook/webhook
Header: X-Webhook-Token: یک-رمز-دلخواه
```

```json
{"chat_id": "-100123", "chat_type": "group", "chat_title": "گروه من",
 "user_id": 555, "user_name": "علی", "text": "سلام", "message_id": 1}
```

پاسخ فوری: `{"ok": true, "queued": 1}`

**خروجی** — ربات هر پاسخ را به آدرس تو می‌فرستد:

```json
{"method": "sendMessage", "chat_id": "-100123", "text": "سلام علی 👋",
 "parse_mode": "Markdown", "reply_to_message_id": 1}
```

پل تو فقط باید همین را به API پیام‌رسان خودت ترجمه کند و
`{"ok": true, "result": {"message_id": 99}}` برگرداند.
(متدهای دیگر — `editMessageText`، `deleteMessage`، `answerCallbackQuery`،
`banChatMember`، … — هم با همان `method` می‌آیند.)

---

## ۶) راه‌اندازی روی میزبان‌های دیگر

| میزبان | نحوه |
|---|---|
| **Railway / Fly.io** | همین ریپو، Start: `python3 main.py`، env همان‌ها. برای Fly: `fly launch` (همین `Procfile` کار می‌کند) |
| **Heroku** | `Procfile` موجود است (`web: python3 main.py`)، env را در Settings بگذار |
| **VPS / سرور خودت** | `git clone` → `pip install -r requirements.txt` → `export BALE_TOKEN=...` → `python3 main.py` (زیر `systemd` یا `tmux`) |

روی سرور خودت می‌توانی از فایل `.env` هم استفاده کنی:

```bash
cp .env.example .env    # مقادیر را پر کن
set -a; source .env; set +a
python3 main.py
```

---

## ۷) عیب‌یابی سریع

| علامت | علت / راه‌حل |
|---|---|
| `❌ هیچ توکنی تنظیم نشده` | `BALE_TOKEN` یا `TELEGRAM_TOKEN` را در Environment بگذار (بعد از تغییر، سرویس خودکار ری‌استارت می‌شود) |
| در لاگ: `❌ اتصال به بله برقرار نشد` | توکن غلط است یا ربات را در BotFather باطل کرده‌ای |
| ربات جواب نمی‌دهد ولی لاگ ساکت است | سرویس خوابیده — پینگر `/healthz` را راه بینداز (بخش ۳) |
| `/healthz` باز نمی‌شود | Health Check Path را `/healthz` بگذار و مطمئن شو `PORT` را خودت ست نکرده‌ای (Render خودش می‌دهد) |
| Build با خطای `No module named ...` می‌خورد | Start Command باید `python3 -u main.py` باشد (نه `python main.py` — رندر `python` ندارد) |
| لاگ‌ها دیر می‌آیند یا تب Logs خالی است | `-u` را در Start Command فراموش نکن |
| `🧠 هوش مصنوعی روشن است ولی کلید تنظیم نشده` | `OPENROUTER_API_KEY` را بگذار |
| داده‌ها بعد از هر دیپلوی پاک می‌شوند | پلن رایگان دیسک ندارد — بخش ۴ |
| `[bale:sendMessage] HTTP 400` با `parse entities` | باگ escape است؛ لاگ و پیام را بفرست تا درست کنم (تست‌ها این را می‌گیرند) |

---

## ۸) چک‌لیست بعد از دیپلوی

- [ ] در Logs: `✅ متصل به بله` دیده می‌شود
- [ ] `/healthz` جواب `ok: true` می‌دهد
- [ ] در پیوی ربات `/start` زدم و پنل آمد
- [ ] ربات را در گروه ادمین کردم و `/پنل` کار می‌کند
- [ ] برای AI: `/کلیدai` کار نکرد؟ → `OPENROUTER_API_KEY` را در env بگذار و سرویس را ری‌استارت کن
- [ ] اگر چند پیام‌رسان خواستم: `PLATFORMS=bale,telegram` و هر دو توکن
