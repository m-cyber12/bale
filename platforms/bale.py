# -*- coding: utf-8 -*-
"""پیام‌رسان بله (پیش‌فرض) — Bot API مشابه تلگرام.

توکن: `BALE_TOKEN` (یا `BOT_TOKEN` برای ستاپ‌های قدیمی، یا فایل
`data/bale_token.txt`).
"""
from .base import Platform


class BalePlatform(Platform):
    key = "bale"
    title = "بله"
    token_envs = ("BALE_TOKEN", "BOT_TOKEN", "TOKEN")
    base_url = "https://tapi.bale.ai/bot{token}/"
    body_format = "form"
    supported_parse_modes = ("Markdown", "HTML")

    # بله بعضی متدها را ندارد → 501 می‌دهد و api.py کش می‌کند
    def _log_http(self, method, code, desc):
        silent = (
            "getChatMember", "getChatAdministrators", "banChatMember",
            "restrictChatMember", "deleteMessage", "editMessageText",
            "answerCallbackQuery", "editMessageReplyMarkup",
            "pinChatMessage", "unpinChatMessage", "setChatPermissions",
            "getChatMembersCount",
        )
        if method not in silent:
            print(f"[bale:{method}] HTTP {code} {desc or ''}")
