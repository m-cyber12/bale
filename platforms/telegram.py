# -*- coding: utf-8 -*-
"""پیام‌رسان تلگرام.

توکن: `TELEGRAM_TOKEN` (یا فایل `data/telegram_token.txt`).
فعال‌سازی: `PLATFORMS=bale,telegram`  یا  `PLATFORM=telegram`.
"""
from .base import Platform


class TelegramPlatform(Platform):
    key = "telegram"
    title = "تلگرام"
    token_envs = ("TELEGRAM_TOKEN", "TG_TOKEN", "TELEGRAM_BOT_TOKEN")
    base_url = "https://api.telegram.org/bot{token}/"
    body_format = "form"
    supported_parse_modes = ("Markdown", "MarkdownV2", "HTML")

    #: اسم متدهای متفاوت تلگرام نسبت به بله
    METHOD_ALIASES = {
        "getChatMembersCount": "getChatMemberCount",
    }

    def method_name(self, method):
        return self.METHOD_ALIASES.get(method, method)

    def _log_http(self, method, code, desc):
        silent = (
            "getChatMember", "getChatAdministrators", "banChatMember",
            "restrictChatMember", "deleteMessage", "editMessageText",
            "answerCallbackQuery", "editMessageReplyMarkup",
            "pinChatMessage", "unpinChatMessage", "setChatPermissions",
            "getChatMemberCount",
        )
        if method not in silent:
            print(f"[telegram:{method}] HTTP {code} {desc or ''}")
