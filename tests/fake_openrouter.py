# -*- coding: utf-8 -*-
"""شبیه‌ساز OpenRouter — برای تست آفلاین موتور هوش مصنوعی.

جای `ai._http` را می‌گیرد و رفتار واقعی سرور را تقلید می‌کند:
  * لیست مدل‌های رایگان
  * 429 با هدرهای X-RateLimit-* و Retry-After
  * 402 (سهمیه)، 401 (کلید بد)، 404 (مدل حذف‌شده)، 5xx
  * پاسخ موفق + گاهی خطای داخل بدنه‌ی ۲۰۰
"""
import json
import itertools
import threading
import time

FREE_MODELS = [
    {"id": "nvidia/nemotron-3-ultra-550b-a55b:free", "name": "Nemotron 3 Ultra",
     "context_length": 1000000,
     "pricing": {"prompt": "0", "completion": "0"}},
    {"id": "nvidia/nemotron-3-super-120b-a12b:free", "name": "Nemotron 3 Super",
     "context_length": 262144, "pricing": {"prompt": "0", "completion": "0"}},
    {"id": "openai/gpt-oss-120b:free", "name": "GPT OSS 120B",
     "context_length": 131072, "pricing": {"prompt": "0", "completion": "0"}},
    {"id": "meta-llama/llama-3.3-70b-instruct:free", "name": "Llama 3.3 70B",
     "context_length": 131072, "pricing": {"prompt": "0", "completion": "0"}},
    {"id": "liquid/lfm-2.5-2.6b:free", "name": "LFM tiny",
     "context_length": 65536, "pricing": {"prompt": "0", "completion": "0"}},
    # پول‌دار → نباید در لیست بیاید
    {"id": "deepseek/deepseek-v4", "name": "DeepSeek V4",
     "context_length": 1000000,
     "pricing": {"prompt": "0.0000002", "completion": "0.0000008"}},
]

DEFAULT_REPLY = "گروه مرتبه، فقط حواست به قوانین باشه. 🌱"


class FakeOpenRouter:
    """سرور جعلی OpenRouter."""

    def __init__(self):
        self.calls = []                 # (model, payload)
        self.models_calls = 0
        self.lock = threading.RLock()
        self.reply = DEFAULT_REPLY
        self.key = "sk-or-v1-test"
        # رفتار هر مدل: "ok" | 429 | 402 | 401 | 404 | 500 | "empty" | "body-error"
        self.behavior = {}
        self.default_behavior = "ok"
        self.reset_seconds = 30
        self.served = []                # مدل‌هایی که جواب دادند
        self.replies = []               # صف پاسخ‌های متفاوت (برای تست تنوع)

    # ----------------------------------------------------------
    def _models_response(self):
        return 200, {}, json.dumps({"data": FREE_MODELS})

    def _chat_response(self, payload):
        model = payload.get("model")
        with self.lock:
            self.calls.append((model, payload))
        beh = self.behavior.get(model, self.default_behavior)

        if beh == "ok":
            with self.lock:
                self.served.append(model)
                if self.replies:
                    text = self.replies.pop(0)
                else:
                    text = self.reply
            body = {"id": "cmpl-1", "model": model,
                    "choices": [{"index": 0, "message": {"role": "assistant",
                                                         "content": text},
                                 "finish_reason": "stop"}]}
            return 200, {}, json.dumps(body, ensure_ascii=False)

        if beh == "empty":
            body = {"id": "cmpl-1", "model": model,
                    "choices": [{"index": 0, "message": {"role": "assistant",
                                                         "content": ""},
                                 "finish_reason": "stop"}]}
            return 200, {}, json.dumps(body)

        if beh == "body-error":
            return 200, {}, json.dumps({"error": {"code": 429,
                                                  "message": "Rate limit exceeded"}})

        code = beh if isinstance(beh, int) else 500
        if code == 429:
            body = {"error": {"code": 429, "message": "Rate limit exceeded",
                              "metadata": {"headers": {
                                  "X-RateLimit-Limit": "50",
                                  "X-RateLimit-Remaining": "0",
                                  "X-RateLimit-Reset": str(int(time.time() + self.reset_seconds))}}}}
            headers = {"X-RateLimit-Limit": "50", "X-RateLimit-Remaining": "0",
                       "X-RateLimit-Reset": str(int((time.time() + self.reset_seconds) * 1000)),
                       "Retry-After": str(self.reset_seconds)}
            return 429, headers, json.dumps(body)
        if code == 402:
            return 402, {}, json.dumps({"error": {"code": 402, "message": "Insufficient credits"}})
        if code in (401, 403):
            return code, {}, json.dumps({"error": {"code": code, "message": "Invalid API key"}})
        if code == 404:
            return 404, {}, json.dumps({"error": {"code": 404, "message": "No endpoints found"}})
        return code, {}, json.dumps({"error": {"code": code, "message": "Server error"}})

    # ----------------------------------------------------------
    def http(self, url, data=None, headers=None, timeout=20):
        """جانشین ai._http"""
        hdrs = {str(k).lower(): v for k, v in (headers or {}).items()}
        auth = hdrs.get("authorization", "")

        if url.endswith("/models"):
            with self.lock:
                self.models_calls += 1
            if auth and auth != f"Bearer {self.key}":
                return 401, {}, json.dumps({"error": {"code": 401, "message": "Invalid key"}})
            return self._models_response()

        if url.endswith("/chat/completions"):
            if not auth:
                return 401, {}, json.dumps({"error": {"code": 401, "message": "No key"}})
            if auth != f"Bearer {self.key}":
                return 401, {}, json.dumps({"error": {"code": 401, "message": "Invalid key"}})
            try:
                payload = json.loads(data.decode("utf-8")) if data else {}
            except Exception:
                payload = {}
            return self._chat_response(payload)

        return 404, {}, json.dumps({"error": {"code": 404, "message": "unknown url"}})

    # ----------------------------------------------------------
    def install(self, ai_module):
        self._orig = ai_module._http
        ai_module._http = self.http
        return self

    def uninstall(self, ai_module):
        ai_module._http = self._orig


def same_model(a, b):
    return a == b
