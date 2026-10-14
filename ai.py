# -*- coding: utf-8 -*-
"""موتور هوش مصنوعی — OpenRouter با چرخش خودکار مدل‌های رایگان.

قابلیت‌ها:
  * لیست زنده‌ی مدل‌های رایگان را از OpenRouter می‌گیرد و رتبه‌بندی می‌کند
    (چون خط مدل‌های رایگان هر چند ماه عوض می‌شود، هیچ‌وقت هاردکد نمی‌کنیم).
  * اگر یک مدل لیمیت خورد (۴۲۹) یا خطا داد، خودکار می‌رود سراغ مدل بعدی.
  * هر مدل کول‌داون مستقل دارد؛ `X-RateLimit-Reset` و `Retry-After` هم خوانده می‌شود.
  * سقف درخواست در دقیقه/روز برای اینکه سهمیه‌ی رایگان بیهوده نسوزد.
  * اگر همه‌ی مدل‌ها خواب باشند → به‌جای پیام خطا، `None` برمی‌گرداند تا
    لایه‌ی بالاتر پاسخ‌های برنامه‌نویسی‌شده را بدهد.
"""
import json
import os
import random
import re
import socket
import threading
import time
import urllib.error
import urllib.parse
import urllib.request


# ============================================================
# مسیرها
# ============================================================
def _ai_dir():
    import config
    return os.path.join(config.DATA_DIR, "ai")


def _config_file():
    return os.path.join(_ai_dir(), "config.json")


def _models_file():
    return os.path.join(_ai_dir(), "models.json")

API_BASE = "https://openrouter.ai/api/v1"
MODELS_URL = API_BASE + "/models"
CHAT_URL = API_BASE + "/chat/completions"

MODELS_TTL = 6 * 3600          # عمر کش لیست مدل‌ها
MAX_CHAIN = 14                 # حداکثر تعداد مدل در زنجیره‌ی fallback

_lock = threading.RLock()

# ============================================================
# تنظیمات پیش‌فرض
# ============================================================
DEFAULTS = {
    "enabled": True,
    "api_key": "",              # اگر خالی باشد از OPENROUTER_API_KEY خوانده می‌شود
    "api_base": API_BASE,
    "max_tokens": 420,
    "temperature": 0.95,
    "timeout": 22,
    "rpm_limit": 18,            # سقف خودمانی در دقیقه (سقف واقعی ۲۰)
    "daily_limit": 180,         # سقف خودمانی در روز (سقف واقعی ~۵۰ برای هر مدل)
    "preferred": [],            # مدل‌هایی که کاربر می‌خواهد اول امتحان شوند
    "blocked": [],              # مدل‌های مسدود
    "use_auto_router": True,    # در آخر زنجیره openrouter/free امتحان شود
    "site_url": "https://ble.ir/",
    "site_name": "Alpha Group Manager",
}

_cfg = None
_models = None              # [{"id","name","ctx","score"}]
_models_ts = 0
_cooldowns = {}             # model -> until_ts
_fails = {}                 # model -> تعداد خطای پشت‌سرهم
_dead = set()               # مدل‌هایی که 404 گرفتن (حذف شدن)
_reqs = []                  # زمان درخواست‌ها (برای سقف دقیقه)
_day = {"key": "", "count": 0}
_stats = {
    "ok": 0, "fail": 0, "rate_limited": 0, "last_error": "",
    "last_model": "", "last_ok_ts": 0,
}
_key_invalid = [0.0]        # زمان آخرین 401


# ============================================================
# ابزار فایل
# ============================================================
def _ensure_dir():
    try:
        os.makedirs(_ai_dir(), exist_ok=True)
    except Exception:
        pass


def _read_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _write_json(path, data):
    _ensure_dir()
    try:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except Exception as e:
        print(f"[ai] write {os.path.basename(path)}: {e}")


# ============================================================
# تنظیمات
# ============================================================
def config():
    global _cfg
    with _lock:
        if _cfg is None:
            c = dict(DEFAULTS)
            c.update(_read_json(_config_file(), {}) or {})
            _cfg = c
        return _cfg


def set_config(**kw):
    with _lock:
        c = config()
        c.update({k: v for k, v in kw.items() if k in DEFAULTS})
        _write_json(_config_file(), c)
        return c


def api_key():
    """کلید API — اول فایل تنظیمات، بعد متغیر محیطی."""
    key = (config().get("api_key") or "").strip()
    if not key:
        key = (os.environ.get("OPENROUTER_API_KEY") or "").strip()
    return key


def set_api_key(key):
    return set_config(api_key=(key or "").strip())


def enabled():
    return bool(config().get("enabled"))


def set_enabled(flag):
    return set_config(enabled=bool(flag))


def ready():
    """آیا الان می‌شود روی AI حساب کرد؟"""
    if not enabled() or not api_key():
        return False
    if time.time() - _key_invalid[0] < 600:
        return False
    if _rpm_exceeded() or _daily_exceeded():
        return False
    return True


# ============================================================
# سقف نرخ خودمانی
# ============================================================
def _prune_reqs(now=None):
    now = now or time.time()
    cut = now - 60
    while _reqs and _reqs[0] < cut:
        _reqs.pop(0)


def _rpm_exceeded():
    with _lock:
        now = time.time()
        _prune_reqs(now)
        return len(_reqs) >= int(config().get("rpm_limit", 18))


def _today():
    return time.strftime("%Y-%m-%d")


def _daily_exceeded():
    with _lock:
        if _day["key"] != _today():
            _day["key"] = _today()
            _day["count"] = 0
        return _day["count"] >= int(config().get("daily_limit", 180))


def _count_request():
    with _lock:
        if _day["key"] != _today():
            _day["key"] = _today()
            _day["count"] = 0
        _reqs.append(time.time())
        _day["count"] += 1


def usage_today():
    with _lock:
        if _day["key"] != _today():
            return 0
        return _day["count"]


# ============================================================
# رتبه‌بندی مدل‌های رایگان
# ============================================================
# امتیاز پایه بر اساس خانواده‌ی مدل (هرچه بالاتر، اول امتحان می‌شود)
_FAMILY_SCORE = [
    ("nemotron-3-ultra", 100), ("nemotron-3-super", 94), ("nemotron-3-nano", 72),
    ("qwen3.6", 92), ("qwen3.5", 90), ("qwen3-next", 88), ("qwen3-coder", 84),
    ("qwen3", 82), ("qwen2.5", 70),
    ("glm-5", 90), ("glm-4", 78),
    ("gpt-oss-120b", 86), ("gpt-oss-20b", 72),
    ("llama-4-maverick", 84), ("llama-4-scout", 76),
    ("llama-3.3-70b", 82), ("llama-3.1-70b", 74),
    ("gemma-4-31b", 80), ("gemma-4", 76), ("gemma-3-27b", 74), ("gemma", 66),
    ("deepseek-v4", 88), ("deepseek-v3", 84), ("deepseek-r1", 74), ("deepseek", 76),
    ("minimax", 80), ("kimi", 80), ("moonshot", 76),
    ("mistral-large", 82), ("mistral-medium", 76), ("mistral", 68),
    ("grok", 86), ("gemini", 82), ("claude", 88), ("gpt-4", 88),
    ("laguna", 74), ("north-mini-code", 70), ("ling-3", 76), ("ling", 68),
    ("command-r", 72), ("hermes", 70), ("dolphin", 62), ("phi-", 60),
]

_WEAK_HINTS = ("1b", "2b", "2.6b", "3b", "4b", "7b", "8b", "9b", "mini", "tiny")
_FAST_OK = ("instruct", "chat", "it", "flash", "turbo")
_SLOW_HINTS = ("thinking", "reasoning", "-r1", "deepseek-r", "cot")
_NON_TEXT = ("vision-only", "image", "audio", "tts", "whisper", "embed", "lyria", "video")


def _score_model(m):
    mid = (m.get("id") or "").lower()
    name = (m.get("name") or "").lower()
    ctx = int(m.get("context_length") or 0)
    score = 50.0

    for sub, val in _FAMILY_SCORE:
        if sub in mid:
            score = max(score, float(val))
            break

    # مدل‌های ضعیف/خیلی کوچک
    for w in _WEAK_HINTS:
        if re.search(rf"(?<![a-z0-9]){re.escape(w)}(?![a-z0-9])", mid):
            score -= 16
            break

    # مدل استدلالی: جواب‌های طولانی‌تر و کندتر
    if any(s in mid for s in _SLOW_HINTS):
        score -= 8

    # مودال غیرمتنی
    if any(s in mid for s in _NON_TEXT):
        score -= 25

    # پنجره‌ی متن
    if ctx >= 1_000_000:
        score += 8
    elif ctx >= 262_000:
        score += 6
    elif ctx >= 128_000:
        score += 4
    elif ctx and ctx < 32_000:
        score -= 8

    # نشانه‌های خوب
    if any(s in mid or s in name for s in _FAST_OK):
        score += 3
    if "free" in mid:
        score += 2

    return round(score, 2)


def _is_free(m):
    mid = (m.get("id") or "")
    if mid.endswith(":free"):
        return True
    pricing = m.get("pricing") or {}
    try:
        p = float(pricing.get("prompt") or 0)
        c = float(pricing.get("completion") or 0)
        return (p == 0 and c == 0)
    except (TypeError, ValueError):
        return False


# اگر شبکه در دسترس نبود، این‌ها به‌عنوان حدس اولیه استفاده می‌شوند
# (بعد از اولین اتصال موفق، لیست زنده جایگزین می‌شود)
STATIC_FALLBACK = [
    "nvidia/nemotron-3-super-120b-a12b:free",
    "qwen/qwen3-next-80b-a3b-instruct:free",
    "openai/gpt-oss-120b:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemma-4-31b-it:free",
    "meta-llama/llama-4-maverick:free",
    "deepseek/deepseek-v3.2:free",
    "mistralai/mistral-small-3.2-24b-instruct:free",
]


def _http(url, data=None, headers=None, timeout=20):
    """درخواست HTTP با urllib (بدون وابستگی خارجی).

    خروجی: (status, headers, body_text)
    """
    req = urllib.request.Request(url, data=data, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", "replace")
        except Exception:
            pass
        return e.code, dict(e.headers or {}), body
    except (urllib.error.URLError, socket.timeout, OSError) as e:
        return 0, {}, str(e)


def refresh_models(force=False):
    """لیست مدل‌های رایگان را از OpenRouter می‌گیرد و رتبه‌بندی می‌کند."""
    global _models, _models_ts
    with _lock:
        now = time.time()
        if not force and _models is not None and (now - _models_ts) < MODELS_TTL:
            return _models
        if not force and _models is None:
            cached = _read_json(_models_file(), None)
            if cached and (now - float(cached.get("ts") or 0)) < MODELS_TTL:
                _models = cached.get("models") or []
                _models_ts = float(cached.get("ts") or 0)
                if _models:
                    return _models

    # --- واکشی زنده ---
    headers = {"Accept": "application/json"}
    key = api_key()
    if key:
        headers["Authorization"] = f"Bearer {key}"
    status, _, body = _http(MODELS_URL, headers=headers, timeout=25)

    items = []
    if status == 200:
        try:
            data = json.loads(body)
            for m in data.get("data", []):
                if not _is_free(m):
                    continue
                items.append({
                    "id": m.get("id"),
                    "name": m.get("name") or m.get("id"),
                    "ctx": int(m.get("context_length") or 0),
                })
        except Exception as e:
            print(f"[ai] parse models: {e}")

    blocked = set(config().get("blocked") or [])
    for it in items:
        it["score"] = _score_model(it)
        it["blocked"] = it["id"] in blocked
    items = [i for i in items if i["id"] and not i["blocked"]]
    items.sort(key=lambda x: (-x["score"], -(x["ctx"] or 0), x["id"]))

    with _lock:
        if items:
            _models = items
            _models_ts = time.time()
            _write_json(_models_file(), {"ts": _models_ts, "models": items})
            print(f"[ai] {len(items)} مدل رایگان پیدا شد | صدر: {items[0]['id']}")
        else:
            if _models is None:
                # حدس اولیه — ربات بدون لیست زنده هم کار کند
                _models = [{"id": mid, "name": mid, "ctx": 0,
                            "score": _score_model({"id": mid}), "blocked": False}
                           for mid in STATIC_FALLBACK
                           if mid not in blocked]
                _models.sort(key=lambda x: -x["score"])
                print("[ai] لیست زنده نیامد — از لیست پیش‌فرض استفاده می‌کنم")
            _models_ts = time.time() - MODELS_TTL + 300   # ۵ دقیقه بعد دوباره تلاش
        return _models


def model_chain():
    """ترتیب مدل‌هایی که امتحان می‌شوند."""
    models = list(refresh_models()) or []
    ids = [m["id"] for m in models if m["id"] not in _dead]
    pref = [p for p in (config().get("preferred") or []) if p]
    chain = []
    for p in pref:
        if p not in _dead:
            chain.append(p)
    for i in ids:
        if i not in chain:
            chain.append(i)
    chain = chain[:MAX_CHAIN]
    if config().get("use_auto_router") and "openrouter/free" not in _dead:
        chain.append("openrouter/free")     # مسیریاب خودکار OpenRouter
    return chain


# ============================================================
# کول‌داون
# ============================================================
def _cool(model, seconds, why=""):
    with _lock:
        until = time.time() + max(5, int(seconds))
        _cooldowns[model] = max(_cooldowns.get(model, 0), until)
    if why:
        print(f"[ai] {model} خنک شد ({why}) برای {int(seconds)}s")


def _is_cool(model):
    with _lock:
        return _cooldowns.get(model, 0) > time.time()


def cooldown_report():
    now = time.time()
    out = []
    with _lock:
        for m, until in sorted(_cooldowns.items(), key=lambda x: -x[1]):
            left = int(until - now)
            if left > 0:
                out.append((m, left))
    return out


def _parse_reset_seconds(headers, body):
    """مدت کول‌داون را از هدرها یا متن خطا استخراج می‌کند."""
    h = {str(k).lower(): v for k, v in (headers or {}).items()}
    try:
        ra = h.get("retry-after")
        if ra:
            return min(3600, max(5, int(float(ra))))
    except (TypeError, ValueError):
        pass
    try:
        reset = h.get("x-ratelimit-reset")
        if reset:
            ts = float(reset)
            if ts > 1e12:      # میلی‌ثانیه
                ts /= 1000.0
            return min(3600, max(5, int(ts - time.time())))
    except (TypeError, ValueError):
        pass
    low = (body or "").lower()
    if "per day" in low or "daily" in low or "rpd" in low:
        return 1800            # سهمیه‌ی روزانه — نیم ساعت صبر کن
    if "per minute" in low or "rpm" in low:
        return 60
    return 45


# ============================================================
# پاک‌سازی خروجی مدل
# ============================================================
_MD_PAIRS = [("**", "**"), ("__", "__"), ("`", "`")]


def md_balanced(text):
    """آیا مارک‌داون متن متوازن است؟ (تا خطای parse_mode نگیریم)"""
    t = re.sub(r"\\(.)", "\ue000", text)
    if t.count("`") % 2 != 0:
        return False
    if t.count("**") % 2 != 0:
        return False
    if t.replace("**", "").count("*") % 2 != 0:
        return False
    if t.count("__") % 2 != 0:
        return False
    if t.replace("__", "").count("_") % 2 != 0:
        return False
    return True


def safe_md(text):
    """اگر مارک‌داون متن نامتوازن بود، کاراکترهای ویژه را escape می‌کند."""
    if not text:
        return text
    if md_balanced(text):
        return text
    return re.sub(r"([_*`])", r"\\\1", text)


def _clean(text, max_len=900):
    if not text:
        return ""
    t = text.strip()
    # حذف نقل‌قول‌های اضافه
    t = re.sub(r"^(assistant|پاسخ)\s*[:：]\s*", "", t, flags=re.I)
    if len(t) > max_len:
        t = t[:max_len].rstrip() + "…"
    return t.strip()


# ============================================================
# فراخوانی اصلی
# ============================================================
def _extract(body):
    """متن پاسخ را از بدنه‌ی JSON بیرون می‌کشد."""
    try:
        data = json.loads(body)
    except Exception:
        return None, "bad-json"
    if isinstance(data, dict) and data.get("error"):
        err = data["error"]
        code = err.get("code") if isinstance(err, dict) else None
        msg = err.get("message") if isinstance(err, dict) else str(err)
        return None, f"body-error:{code}:{(msg or '')[:120]}"
    try:
        choices = data.get("choices") or []
        if not choices:
            return None, "no-choices"
        msg = choices[0].get("message") or {}
        content = (msg.get("content") or "").strip()
        if not content:
            # بعضی مدل‌ها فقط reasoning می‌دهند
            content = (msg.get("reasoning") or "").strip()
        if not content:
            return None, "empty-content"
        return content, None
    except Exception as e:
        return None, f"parse:{e}"


def chat(messages, max_tokens=None, temperature=None, purpose="", timeout=None):
    """یک درخواست چت با چرخش خودکار مدل‌ها.

    خروجی: (متن پاسخ یا None، نام مدل یا دلیل شکست)
    """
    if not ready():
        return None, _why_not_ready()

    cfg = config()
    max_tokens = int(max_tokens or cfg.get("max_tokens", 420))
    temperature = float(temperature if temperature is not None else cfg.get("temperature", 0.95))
    timeout = int(timeout or cfg.get("timeout", 22))
    key = api_key()

    chain = [m for m in model_chain() if not _is_cool(m)]
    if not chain:
        chain = model_chain()      # همه خوابن — باز هم یک تلاش
    if not chain:
        return None, "no-models"

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "HTTP-Referer": cfg.get("site_url", ""),
        "X-Title": cfg.get("site_name", "Alpha"),
    }

    last_err = "unknown"
    for model in chain:
        if _rpm_exceeded():
            last_err = "rpm-guard"
            break
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": 0.95,
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        _count_request()
        status, rheaders, rbody = _http(CHAT_URL, data=body, headers=headers, timeout=timeout)

        # ---- موفق ----
        if status == 200:
            text, err = _extract(rbody)
            if text:
                with _lock:
                    _stats["ok"] += 1
                    _stats["last_model"] = model
                    _stats["last_ok_ts"] = time.time()
                    _stats["last_error"] = ""
                    _fails[model] = 0
                hdr = {str(k).lower(): v for k, v in rheaders.items()}
                try:
                    if int(hdr.get("x-ratelimit-remaining", "1")) <= 0:
                        _cool(model, _parse_reset_seconds(rheaders, ""), "سهمیه تمام")
                except (TypeError, ValueError):
                    pass
                # ✅ اطمینان نهایی: متن AI نباید ربات را به خطای parse_mode ببرد
                return safe_md(_clean(text)), model
            # ۲۰۰ ولی خطا/خالی
            last_err = err or "empty"
            with _lock:
                _fails[model] = _fails.get(model, 0) + 1
            if "rate" in str(err).lower() or "limit" in str(err).lower():
                _cool(model, _parse_reset_seconds(rheaders, rbody), "لیمیت در بدنه")
            else:
                _cool(model, 30, last_err)
            continue

        # ---- خطای کلید ----
        if status in (401, 403):
            with _lock:
                _key_invalid[0] = time.time()
                _stats["fail"] += 1
                _stats["last_error"] = f"کلید نامعتبر ({status})"
            print(f"[ai] کلید OpenRouter رد شد ({status}) — ۱۰ دقیقه غیرفعال")
            return None, "bad-key"

        # ---- لیمیت ----
        if status == 429:
            secs = _parse_reset_seconds(rheaders, rbody)
            _cool(model, secs, "429")
            with _lock:
                _stats["rate_limited"] += 1
                _stats["last_error"] = "rate-limit"
            last_err = "rate-limit"
            continue

        if status == 402:
            _cool(model, 3600, "اعتبار/سهمیه")
            with _lock:
                _stats["last_error"] = "quota-402"
            last_err = "quota"
            continue

        # ---- مدل حذف شده ----
        if status == 404:
            with _lock:
                _dead.add(model)
            with _lock:
                _stats["last_error"] = f"مدل حذف شده: {model}"
            last_err = "gone"
            refresh_models(force=True)
            continue

        # ---- خطای موقت سرور / شبکه ----
        if status in (408, 409, 500, 502, 503, 504) or status == 0:
            with _lock:
                _fails[model] = _fails.get(model, 0) + 1
                n = _fails[model]
                _stats["last_error"] = f"{status or 'net'}: {(rbody or '')[:80]}"
            _cool(model, min(300, 20 * n), f"{status or 'net'}")
            last_err = "server"
            continue

        # ---- ۴۰۰ (پارامتر/کانتکست) ----
        with _lock:
            _stats["last_error"] = f"{status}: {(rbody or '')[:100]}"
        last_err = f"http-{status}"
        _cool(model, 60, f"http-{status}")
        continue

    with _lock:
        _stats["fail"] += 1
    return None, last_err


def _why_not_ready():
    if not enabled():
        return "off"
    if not api_key():
        return "no-key"
    if time.time() - _key_invalid[0] < 600:
        return "bad-key"
    if _rpm_exceeded():
        return "rpm-guard"
    if _daily_exceeded():
        return "daily-guard"
    return "not-ready"


def chat_async(messages, callback, fallback=None, **kw):
    """اجرای غیرهمزمان تا حلقه‌ی polling ربات بلاک نشود.

    callback(text, model)  — text هرگز None نیست؛ در صورت شکست `fallback`.
    """
    def _run():
        try:
            text, model = chat(messages, **kw)
        except Exception as e:
            print(f"[ai:async] {e}")
            text, model = None, "exception"
        if not text:
            text, model = (fallback or ""), f"fallback:{model}"
        try:
            callback(text, model)
        except Exception as e:
            print(f"[ai:callback] {e}")

    t = threading.Thread(target=_run, daemon=True, name="ai-call")
    t.start()
    return t


# ============================================================
# ابزارهای مدیریتی
# ============================================================
def test_call(prompt="یه جمله کوتاه دربارهی مدیریت گروه بگو."):
    """تست سریع برای پنل."""
    return chat([{"role": "user", "content": prompt}], max_tokens=120, temperature=0.7)


def status():
    models = list(refresh_models())
    chain = model_chain()
    return {
        "enabled": enabled(),
        "key_set": bool(api_key()),
        "models_total": len(models),
        "chain": chain[:8],
        "top": [m["id"] for m in models[:5]],
        "cooldowns": cooldown_report(),
        "usage_today": usage_today(),
        "daily_limit": config().get("daily_limit"),
        "rpm_limit": config().get("rpm_limit"),
        "stats": dict(_stats),
        "dead": sorted(_dead),
        "key_invalid": time.time() - _key_invalid[0] < 600,
    }


def reset_runtime():
    """پاک‌کردن کول‌داون‌ها و آمار (برای پنل)."""
    with _lock:
        _cooldowns.clear()
        _fails.clear()
        _key_invalid[0] = 0.0
        _stats.update({"ok": 0, "fail": 0, "rate_limited": 0, "last_error": ""})
    return True
