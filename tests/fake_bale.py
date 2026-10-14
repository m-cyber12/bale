# -*- coding: utf-8 -*-
"""شبیه‌ساز آفلاین Bot API بله — برای تست بدون شبکه.

قابلیت‌ها:
  * شبیه‌سازی کامل متدهای پرکاربرد
  * ضبط همه‌ی درخواست‌ها (calls)
  * اعتبارسنجی parse_mode (Markdown/HTML) مثل سرور واقعی
    → متن نامتوازن (ستاره/بک‌تیک/تگ باز) را 400 برمی‌گرداند
  * جمع‌آوری callback_data برای پیمایش خودکار پنل‌ها
"""
import html
import itertools
import json
import re
import threading
import time


class FakeBaleAPI:
    def __init__(self):
        self.calls = []
        self.sent = []          # پیام‌های ارسالی موفق
        self.edited = []        # ویرایش‌های موفق
        self.deleted = []
        self.callback_answers = []
        self.callback_queue = []  # (data, chat_id, msg_id)
        self._seen_cb = set()
        self.mid = itertools.count(1000)
        self.lock = threading.RLock()

        self.bot = {
            "id": 999,
            "is_bot": True,
            "first_name": "AlphaBot",
            "username": "alpha_test_bot",
        }
        self.chats = {}
        self.statuses = {}      # (chat_id, user_id) -> status
        self.default_status = "member"
        self.bot_group_status = "administrator"
        self.markup_validate = True
        self.parse_errors = []
        self.fallbacks = []
        self.stray_escapes = []
        self._pending_parse_texts = set()
        self._fallback_texts = set()
        self.mode_mismatch = []
        self.strict = False     # اگر True: خطای parse_mode را استثنا می‌کند

    # ----------------------------------------------------------
    #                  اعتبارسنجی parse_mode
    # ----------------------------------------------------------
    @staticmethod
    def _strip_code(text):
        """حذف بخش‌های داخل کد (backtick) برای شمارش ستاره‌ها."""
        out = []
        in_code = False
        i = 0
        while i < len(text):
            ch = text[i]
            if ch == "`":
                in_code = not in_code
                i += 1
                continue
            if not in_code:
                out.append(ch)
            i += 1
        return "".join(out), not in_code

    def _check_markdown(self, text):
        """خطاهای parse_mode=Markdown را برمی‌گرداند (شبیه Bot API)."""
        if not isinstance(text, str):
            return None
        # پارسر واقعی: \X یعنی کاراکتر X لیترال است و معنی مارک‌داون ندارد
        # پس با یک کاراکتر بی‌اثر جایگزین می‌شود (نه اینکه خودش برگردد)
        text = re.sub(r"\\(.)", "\ue000", text)
        no_code, code_balanced = self._strip_code(text)
        if not code_balanced:
            return "Can't parse entities: can't find end of Code entity at byte offset"
        # استار ها: اول جفت‌های ** (بولد) بعد تک‌ها (ایتالیک)
        if no_code.count("**") % 2 != 0:
            return "Can't parse entities: can't find end of Bold entity"
        if no_code.replace("**", "").count("*") % 2 != 0:
            return "Can't parse entities: can't find end of Italic entity"
        # زیرخط‌ها: اول جفت‌های __ بعد تک‌ها
        if no_code.count("__") % 2 != 0:
            return "Can't parse entities: can't find end of Bold entity"
        if no_code.replace("__", "").count("_") % 2 != 0:
            return "Can't parse entities: can't find end of Italic entity"
        # لینک مارک‌داون
        for m in re.finditer(r"\[[^\[\]]*\]", no_code):
            nxt = no_code[m.end():m.end() + 1]
            if nxt not in ("(",):
                return "Can't parse entities: Bad link at byte offset"
        depth = 0
        for ch in no_code:
            if ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth < 0:
                    return "Can't parse entities: can't find start of TextLink entity"
        if depth != 0:
            return "Can't parse entities: can't find end of TextLink entity"
        return None

    def _check_html(self, text):
        if not isinstance(text, str):
            return None
        txt = re.sub(r"<a\s+href=\"[^\"]*\">", "<a>", text, flags=re.I)
        stack = []
        for m in re.finditer(r"</?([a-zA-Z]+)[^>]*>", txt):
            tag = m.group(1).lower()
            if tag not in ("b", "strong", "i", "em", "u", "s", "code", "pre", "a", "tg-spoiler"):
                continue
            if m.group(0).startswith("</"):
                if not stack or stack[-1] != tag:
                    return f"Can't parse entities: Unmatched end tag {tag}"
                stack.pop()
            else:
                stack.append(tag)
        if stack:
            return f"Can't parse entities: can't find end of {stack[-1]} entity"
        # تگ‌های < یا > تنها
        if re.search(r"<[^>]*$", text):
            return "Can't parse entities: unsupported start tag"
        return None

    def _validate(self, data):
        pm = (data or {}).get("parse_mode")
        if not pm:
            return None
        text = (data or {}).get("text") or (data or {}).get("caption") or ""
        if pm.lower() == "markdown":
            return self._check_markdown(text)
        if pm.lower() == "html":
            return self._check_html(text)
        return None

    # ----------------------------------------------------------
    @staticmethod
    def _as_id(v):
        try:
            return int(v)
        except (TypeError, ValueError):
            return v

    def _chat(self, chat_id):
        cid = self._as_id(chat_id)
        if cid not in self.chats:
            is_group = isinstance(cid, int) and cid < 0
            self.chats[cid] = {
                "id": cid,
                "type": "supergroup" if is_group else "private",
                "title": f"گروه تست {cid}" if is_group else "پیوی تست",
                "first_name": "کاربر",
            }
        return self.chats[cid]

    def _message(self, chat_id, data, result):
        return {
            "message_id": result.get("_mid"),
            "date": int(time.time()),
            "chat": self._chat(chat_id),
            "text": data.get("text", ""),
        }

    # ----------------------------------------------------------
    #                       request
    # ----------------------------------------------------------
    def request(self, method, data=None, timeout=30, **kwargs):
        data = dict(data or {})
        with self.lock:
            self.calls.append((method, data))

        # امضاهای متدها
        if method == "getMe":
            return {"ok": True, "result": self.bot}

        if method in ("sendMessage", "sendPhoto", "sendAnimation", "sendDocument",
                      "sendVideo", "sendVoice", "sendSticker", "sendAudio"):
            return self._handle_send(method, data)

        if method == "editMessageText":
            err = self._validate(data) if self.markup_validate else None
            if err:
                self._note_parse_error("editMessageText", data, err)
                return {"ok": False, "error_code": 400, "description": err}
            self._check_fallback(data)
            self._check_stray_escape(data)
            self._check_mode_mismatch(data)
            with self.lock:
                self.edited.append(data)
            return {"ok": True, "result": {"message_id": data.get("message_id"),
                                           "chat": self._chat(data.get("chat_id")),
                                           "text": data.get("text", "")}}

        if method == "editMessageReplyMarkup":
            with self.lock:
                self.edited.append(data)
            return {"ok": True, "result": {"message_id": data.get("message_id")}}

        if method == "deleteMessage":
            with self.lock:
                self.deleted.append(data)
            return {"ok": True, "result": True}

        if method == "answerCallbackQuery":
            with self.lock:
                self.callback_answers.append(data)
            return {"ok": True, "result": True}

        if method == "getChatMember":
            cid = self._as_id(data.get("chat_id"))
            uid = self._as_id(data.get("user_id"))
            if uid == self.bot["id"]:
                st = self.bot_group_status
            else:
                st = self.statuses.get((cid, uid), self.default_status)
            if st is None:
                return {"ok": False, "error_code": 400, "description": "user not found"}
            return {"ok": True, "result": {
                "status": st,
                "user": {"id": uid, "is_bot": False, "first_name": f"کاربر{uid}"},
            }}

        if method == "getChatAdministrators":
            cid = self._as_id(data.get("chat_id"))
            admins = []
            for (c, u), st in self.statuses.items():
                if c == cid and st in ("creator", "administrator"):
                    admins.append({"status": st,
                                   "user": {"id": u, "is_bot": False, "first_name": f"کاربر{u}"}})
            return {"ok": True, "result": admins}

        if method == "getChat":
            return {"ok": True, "result": self._chat(data.get("chat_id"))}

        if method in ("getChatMembersCount", "getChatMemberCount"):
            return {"ok": True, "result": 12}

        if method == "getFile":
            return {"ok": True, "result": {"file_id": data.get("file_id"),
                                           "file_path": "files/fake.png"}}

        if method in ("banChatMember", "unbanChatMember", "restrictChatMember",
                      "promoteChatMember", "demoteChatMember", "setChatPermissions",
                      "pinChatMessage", "unpinChatMessage", "unpinAllChatMessages",
                      "forwardMessage", "copyMessage", "leaveChat", "exportChatInviteLink",
                      "setChatTitle", "setChatDescription", "deleteWebhook"):
            return {"ok": True, "result": True}

        # متد ناشناخته → مثل سرور واقعی 501
        return {"ok": False, "error_code": 501, "description": f"Not Implemented: {method}"}

    def _handle_send(self, method, data):
        err = self._validate(data) if self.markup_validate else None
        if err:
            self._note_parse_error(method, data, err)
            return {"ok": False, "error_code": 400, "description": err}
        self._check_fallback(data)
        self._check_stray_escape(data)
        self._check_mode_mismatch(data)
        mid = next(self.mid)
        data = dict(data)
        data["_mid"] = mid
        with self.lock:
            self.sent.append(data)
            self._collect_callbacks(data)
        return {"ok": True, "result": {
            "message_id": mid,
            "date": int(time.time()),
            "chat": self._chat(data.get("chat_id")),
            "text": data.get("text", ""),
        }}

    def _collect_callbacks(self, data):
        rm = data.get("reply_markup")
        if not rm:
            return
        try:
            kb = json.loads(rm) if isinstance(rm, str) else rm
        except Exception:
            return
        rows = (kb or {}).get("inline_keyboard") or []
        for row in rows:
            for b in row:
                cd = b.get("callback_data")
                if cd and cd not in self._seen_cb:
                    self._seen_cb.add(cd)
                    self.callback_queue.append((cd, data.get("chat_id"), data.get("_mid")))

    def _note_parse_error(self, method, data, err):
        with self.lock:
            self.parse_errors = getattr(self, "parse_errors", [])
            # اگر همین متن بدون parse_mode دوباره بیاید → فالبک بوده
            self._pending_parse_texts.add((data.get("text") or ""))
            self.parse_errors.append({
                "method": method,
                "parse_mode": data.get("parse_mode"),
                "error": err,
                "text": (data.get("text") or "")[:400],
            })

    def _check_fallback(self, data):
        """تشخیص فالبک api.py: متنِ رد‌شده دوباره بدون parse_mode فرستاده شد."""
        if data.get("parse_mode"):
            return
        txt = data.get("text") or ""
        if txt in self._pending_parse_texts:
            self._pending_parse_texts.discard(txt)
            self.fallbacks.append(txt[:300])
            self._fallback_texts.add(txt)

    def _check_mode_mismatch(self, data):
        """escape مارک‌داون در پیام HTML (یا برعکس) → رشته‌ها خام دیده می‌شوند."""
        pm = ((data or {}).get("parse_mode") or "").lower()
        txt = data.get("text") or data.get("caption") or ""
        if not txt:
            return
        if pm == "html" and re.search(r"\\[_*`\[\]]", txt):
            self.mode_mismatch.append(("Markdown-escape در پیام HTML", txt[:2000]))

    def _check_stray_escape(self, data):
        """متن escape‌شده ولی بدون parse_mode → کاربر بک‌اسلش می‌بیند."""
        if data.get("parse_mode"):
            return
        txt = data.get("text") or ""
        if txt in self._fallback_texts:
            return
        if re.search(r"\\[_*`\[\]]", txt):
            self.stray_escapes.append(txt[:300])

    # ----------------------------------------------------------
    def get_updates(self, offset=None, timeout=30, **kwargs):
        return {"ok": True, "result": []}   # polling در تست استفاده نمی‌شود

    def upload_file(self, method, files_dict, data_dict=None, timeout=120):
        return self.request(method, data_dict or {})

    def send_raw(self, chat_id, text, markup=None, parse_mode=None, reply_to=None):
        """ارسال پیام بدون اعتبارسنجی (برای ساخت پیش‌نیاز تست)."""
        d = {"chat_id": chat_id, "text": text}
        if markup:
            d["reply_markup"] = json.dumps(markup, ensure_ascii=False)
        if parse_mode:
            d["parse_mode"] = parse_mode
        return self._handle_send("sendMessage", d)


# ==============================================================
#                        install / helpers
# ==============================================================
def install(api_module, gifmaker_module=None):
    """api واقعی را با شبیه‌ساز جایگزین می‌کند."""
    fake = FakeBaleAPI()
    api_module.request = fake.request
    api_module.get_updates = fake.get_updates
    api_module.upload_file = fake.upload_file
    if gifmaker_module is not None:
        gifmaker_module.urllib.request.urlretrieve = lambda url, path: (None, None)
        gifmaker_module.urllib.request.urlopen = lambda *a, **k: (_ for _ in ()).throw(
            OSError("offline"))
    return fake


def make_user(uid, name="کاربر", username=None, is_bot=False):
    u = {"id": uid, "is_bot": is_bot, "first_name": name}
    if username:
        u["username"] = username
    return u


def make_message(chat_id, user, text, message_id=None, chat_type="supergroup",
                 reply_to=None, entities=None):
    msg = {
        "message_id": message_id if message_id is not None else int(time.time() * 1000) % 10 ** 7,
        "date": int(time.time()),
        "chat": {"id": chat_id, "type": chat_type,
                 "title": "گروه تست" if chat_type != "private" else None},
        "from": user,
        "text": text,
    }
    if chat_type == "private":
        msg["chat"] = {"id": chat_id, "type": "private",
                       "first_name": user.get("first_name", "کاربر")}
    if reply_to:
        msg["reply_to_message"] = reply_to
    if entities:
        msg["entities"] = entities
    return msg


def make_update_message(chat_id, user, text, **kw):
    return {"update_id": int(time.time() * 1000) % 10 ** 9,
            "message": make_message(chat_id, user, text, **kw)}


def make_callback(chat_id, user, data, message_id=555, msg_text="", chat_type="supergroup",
                  reply_to=None):
    msg = {
        "message_id": message_id,
        "date": int(time.time()),
        "chat": {"id": chat_id, "type": chat_type,
                 "title": "گروه تست" if chat_type != "private" else None},
        "text": msg_text,
    }
    if chat_type == "private":
        msg["chat"] = {"id": chat_id, "type": "private", "first_name": user.get("first_name")}
    if reply_to:
        msg["reply_to_message"] = reply_to
    return {
        "update_id": int(time.time() * 1000) % 10 ** 9,
        "callback_query": {
            "id": f"cb{int(time.time() * 10 ** 6) % 10 ** 9}",
            "from": user,
            "message": msg,
            "chat_instance": "1",
            "data": data,
        },
    }


def make_chat_member_update(chat_id, user, old="left", new="member"):
    return {
        "update_id": int(time.time() * 1000) % 10 ** 9,
        "chat_member": {
            "chat": {"id": chat_id, "type": "supergroup", "title": "گروه تست"},
            "from": user,
            "date": int(time.time()),
            "old_chat_member": {"status": old, "user": user},
            "new_chat_member": {"status": new, "user": user},
        },
    }
