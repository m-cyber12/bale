# -*- coding: utf-8 -*-
import time
import api
from storage import (
    get, set_, update, remove, save,
    save_banned, save_muted,
    remove_banned, remove_muted,
)
import locks as lock_mod
import antispam
import notify

_admin_cache = {}
_admin_cache_last_cleanup = [0]


def _cleanup_admin_cache():
    now = time.time()
    if now - _admin_cache_last_cleanup[0] < 300:
        return
    _admin_cache_last_cleanup[0] = now

    expired = []
    for k, (val, ts) in _admin_cache.items():
        if now - ts > 300:
            expired.append(k)
    for k in expired:
        _admin_cache.pop(k, None)


def is_admin(chat_id, user_id):
    if user_id == api.bot_id():
        return True

    key = (chat_id, user_id)
    now = time.time()
    if key in _admin_cache:
        cached, ts = _admin_cache[key]
        if now - ts < 60:
            return cached

    success = False
    result = False

    try:
        r = api.get_member(chat_id, user_id)
        if r and r.get("ok"):
            success = True
            status = r.get("result", {}).get("status", "")
            result = status in ("creator", "administrator")
    except Exception as e:
        print(f"[is_admin:get_member] {e}")

    if not success:
        try:
            r = api.admins(chat_id)
            if r and r.get("ok"):
                success = True
                for a in r.get("result", []):
                    if a.get("user", {}).get("id") == user_id:
                        result = True
                        break
        except Exception as e:
            print(f"[is_admin:admins] {e}")

    if success:
        _admin_cache[key] = (result, now)
        try:
            _cleanup_admin_cache()
        except Exception:
            pass
    return result


def is_creator(chat_id, user_id):
    try:
        r = api.get_member(chat_id, user_id)
        if r and r.get("ok"):
            return r["result"].get("status") == "creator"
    except Exception as e:
        print(f"[is_creator] {e}")
    return False


# ============================================================
# تبدیل @username به user_id
# ============================================================
def resolve_username(chat_id, username):
    if not username:
        return None
    username = username.lstrip("@").strip().lower()
    if not username:
        return None

    profiles = get("user_profiles", chat_id) or {}
    for uid, info in profiles.items():
        uname = (info.get("username") or "").lower()
        if uname and uname == username:
            return {
                "id": int(uid),
                "first_name": info.get("first_name", "کاربر"),
                "last_name": info.get("last_name", ""),
                "username": uname,
            }

    global_profiles = get("user_profiles", "global") or {}
    for uid, info in global_profiles.items():
        uname = (info.get("username") or "").lower()
        if uname and uname == username:
            return {
                "id": int(uid),
                "first_name": info.get("first_name", "کاربر"),
                "last_name": info.get("last_name", ""),
                "username": uname,
            }

    try:
        import storage
        all_users = storage.get("bot_users", "list") or {}
        for uid, info in all_users.items():
            uname = (info.get("username") or "").lower()
            if uname and uname == username:
                return {
                    "id": int(uid),
                    "first_name": info.get("name", "کاربر"),
                    "username": uname,
                }
    except Exception:
        pass

    return None


def get_target(message, chat_id=None):
    if message.get("reply_to_message"):
        return message["reply_to_message"]["from"]

    for e in message.get("entities", []):
        if e.get("type") == "text_mention" and e.get("user"):
            return e["user"]

    if chat_id:
        import re
        text = message.get("text", "") or ""
        matches = re.findall(r"@([A-Za-z0-9_]{3,})", text)
        for uname in matches:
            resolved = resolve_username(chat_id, uname)
            if resolved:
                return resolved

    return None


def u_name(u):
    if not u:
        return "کاربر"
    n = u.get("first_name", "")
    if u.get("last_name"):
        n += " " + u["last_name"]
    return n or "کاربر"


def parse_dur(s, default=3600):
    try:
        if not s:
            return default
        s = s.strip().lower()
        if s.endswith("s"): return int(s[:-1])
        if s.endswith("m"): return int(s[:-1]) * 60
        if s.endswith("h"): return int(s[:-1]) * 3600
        if s.endswith("d"): return int(s[:-1]) * 86400
        return int(s) * 60
    except:
        return default


def fmt_dur(sec):
    if sec < 60: return f"{sec} ثانیه"
    if sec < 3600: return f"{sec//60} دقیقه"
    if sec < 86400: return f"{sec//3600} ساعت"
    return f"{sec//86400} روز"


# ============================================================
# پیام خطای "کاربر پیدا نشد"
# ============================================================
def _send_user_not_found(chat_id, message, action_verb="", action_hint=""):
    import re
    text_msg = message.get("text", "") or ""
    found_unames = re.findall(r"@([A-Za-z0-9_]{3,})", text_msg)

    if found_unames:
        uname = found_unames[0]
        reply_hint = action_hint or action_verb or "دستور"
        api.send(chat_id,
            f"❌ **کاربر `@{uname}` پیدا نشد!**\n\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💡 **دلیل:** بله API برای جستجوی کاربر با یوزرنیم نداره.\n"
            f"ربات فقط کاربرانی رو می‌شناسه که:\n"
            f"• قبلاً توی گروه پیام دادن\n"
            f"• یا ربات رو در پیوی استارت کردن\n\n"
            f"🎯 **راه‌های حل:**\n\n"
            f"1️⃣ از `@{uname}` بخواه یه پیام توی گروه بفرسته\n\n"
            f"2️⃣ **ریپلای** روی پیامش کن و بزن:\n"
            f"   `{reply_hint}`\n\n"
            f"3️⃣ آیدی عددیش رو بگیر و بزن:\n"
            f"   `{reply_hint} 123456789`\n\n"
            f"💡 برای دیدن لیست کاربران ثبت‌شده بزن: `کاربران`",
            parse_mode="Markdown",
            reply_to=message["message_id"])
    else:
        api.send(chat_id,
            "🙏 **راه‌های انتخاب کاربر:**\n\n"
            "1️⃣ روی پیام کاربر **ریپلای** کن\n"
            "2️⃣ یا با `@username` تگ کن\n\n"
            f"📝 مثال: `{action_hint or action_verb or 'دستور'}`",
            reply_to=message["message_id"])


# ============================================================
# اخطار
# ============================================================
def cmd_warn(chat_id, user_id, message):
    t = get_target(message, chat_id)
    if not t:
        _send_user_not_found(chat_id, message,
                             action_verb="اخطار",
                             action_hint="اخطار @ali")
        return

    tid = t["id"]
    tname = u_name(t)

    if is_admin(chat_id, tid):
        api.send(chat_id,
            "✨ این کاربر از **ادمین‌های محترم** گروه است.",
            parse_mode="Markdown",
            reply_to=message["message_id"])
        return

    w = get("warnings", chat_id) or {}
    w[str(tid)] = w.get(str(tid), 0) + 1
    set_("warnings", chat_id, w)
    count = w[str(tid)]
    sender_name = u_name(message["from"])

    if count >= 3:
        try:
            api.ban(chat_id, tid)
        except Exception as e:
            print(f"[warn:ban] {e}")
        try:
            save_banned(chat_id, tid, tname)
        except Exception as e:
            print(f"[warn:save] {e}")

        w.pop(str(tid), None)
        set_("warnings", chat_id, w)

        try:
            notify.notify_punishment(tid, chat_id, "ban",
                                     reason="دریافت ۳ اخطار",
                                     by_name=sender_name)
        except Exception as e:
            print(f"[warn:notify] {e}")

        api.send(chat_id,
            f"🚫 **{tname}** به دلیل دریافت ۳ اخطار بن شد.",
            parse_mode="Markdown")
    else:
        api.send(chat_id,
            f"⚠️ **{tname}** اخطار گرفت ({count}/3)\n\n"
            f"🙏 لطفاً قوانین گروه را رعایت کنید.",
            parse_mode="Markdown")

        try:
            notify.notify_warn(tid, chat_id, count, 3,
                              by_name=sender_name,
                              reason="اخطار گروه")
        except Exception as e:
            print(f"[warn:notify] {e}")


def cmd_unwarn(chat_id, user_id, message):
    t = get_target(message, chat_id)
    if not t:
        _send_user_not_found(chat_id, message, action_hint="حذف اخطار")
        return
    w = get("warnings", chat_id) or {}
    tid = str(t["id"])
    if w.get(tid, 0) > 0:
        w[tid] -= 1
        set_("warnings", chat_id, w)
        api.send(chat_id, f"✅ یک اخطار از {u_name(t)} کم شد. ({w[tid]}/3)")
    else:
        api.send(chat_id, f"ℹ️ {u_name(t)} اخطار فعالی ندارد.")


def cmd_warns(chat_id, user_id, message):
    t = get_target(message, chat_id)
    if not t:
        api.send(chat_id, "🙏 لطفاً ریپلای بزنید یا `@username` تگ کنید.",
                 reply_to=message["message_id"])
        return
    w = get("warnings", chat_id) or {}
    c = w.get(str(t["id"]), 0)
    api.send(chat_id, f"📋 تعداد اخطارهای {u_name(t)}: **{c}**",
             parse_mode="Markdown")


# ============================================================
# سکوت
# ============================================================
def cmd_mute(chat_id, user_id, message, args):
    t = get_target(message, chat_id)
    if not t:
        _send_user_not_found(chat_id, message,
                             action_verb="سکوت",
                             action_hint="سکوت @ali 10m")
        return

    if is_admin(chat_id, t["id"]):
        api.send(chat_id, "✨ این کاربر از ادمین‌های محترم گروه است.",
                 reply_to=message["message_id"])
        return

    dur = parse_dur(args[0] if args else "", 3600)
    dur_fa = fmt_dur(dur)

    lock_mod.mute_and_save(chat_id, t["id"], dur)
    sender_name = u_name(message["from"])

    try:
        notify.notify_punishment(t["id"], chat_id, "mute",
                                 duration=dur_fa,
                                 by_name=sender_name)
    except Exception as e:
        print(f"[mute:notify] {e}")

    api.send(chat_id,
        f"🔇 **{u_name(t)}** به مدت **{dur_fa}** سکوت شد.",
        parse_mode="Markdown")


def cmd_unmute(chat_id, user_id, message):
    t = get_target(message, chat_id)
    if not t:
        _send_user_not_found(chat_id, message, action_hint="آزاد")
        return

    try:
        lock_mod.remove_from_lock_list(chat_id, t["id"])
    except Exception:
        pass

    try:
        remove_muted(chat_id, t["id"])
    except Exception:
        pass

    api.send(chat_id, f"🔊 **{u_name(t)}** از سکوت آزاد شد.",
             parse_mode="Markdown")


# ============================================================
# بن / کیک
# ============================================================
def cmd_ban(chat_id, user_id, message):
    t = get_target(message, chat_id)
    if not t:
        _send_user_not_found(chat_id, message,
                             action_verb="بن",
                             action_hint="بن @ali")
        return

    if is_admin(chat_id, t["id"]):
        api.send(chat_id, "✨ این کاربر از ادمین‌های محترم گروه است.",
                 reply_to=message["message_id"])
        return

    lock_mod.ban_and_save(chat_id, t["id"], u_name(t))
    sender_name = u_name(message["from"])

    try:
        notify.notify_punishment(t["id"], chat_id, "ban",
                                 by_name=sender_name)
    except Exception as e:
        print(f"[ban:notify] {e}")

    api.send(chat_id, f"🚫 **{u_name(t)}** از گروه بن شد.",
             parse_mode="Markdown")


def cmd_unban(chat_id, user_id, message):
    t = get_target(message, chat_id)
    if not t:
        _send_user_not_found(chat_id, message, action_hint="آنبن")
        return

    try:
        api.unban(chat_id, t["id"])
    except Exception:
        pass

    try:
        remove_banned(chat_id, t["id"])
    except Exception:
        pass

    api.send(chat_id, f"✅ **{u_name(t)}** از بن آزاد شد.",
             parse_mode="Markdown")


def cmd_kick(chat_id, user_id, message):
    t = get_target(message, chat_id)
    if not t:
        _send_user_not_found(chat_id, message,
                             action_verb="اخراج",
                             action_hint="اخراج @ali")
        return

    if is_admin(chat_id, t["id"]):
        api.send(chat_id, "✨ این کاربر از ادمین‌های محترم گروه است.",
                 reply_to=message["message_id"])
        return

    lock_mod.kick_and_save(chat_id, t["id"], u_name(t))
    sender_name = u_name(message["from"])

    try:
        notify.notify_punishment(t["id"], chat_id, "kick",
                                 by_name=sender_name)
    except Exception as e:
        print(f"[kick:notify] {e}")

    api.send(chat_id, f"👢 **{u_name(t)}** اخراج شد.",
             parse_mode="Markdown")


# ============================================================
# ارتقا / تنزل
# ============================================================
def _make_admin(chat_id, user_id):
    """چند روش برای ادمین کردن کاربر"""
    # روش ۱: پارامترهای تکی
    try:
        d = {
            "chat_id": str(chat_id),
            "user_id": str(user_id),
            "can_change_info": "true",
            "can_delete_messages": "true",
            "can_invite_users": "true",
            "can_restrict_members": "true",
            "can_pin_messages": "true",
            "can_promote_members": "false",
            "can_manage_video_chats": "true",
        }
        r = api.request("promoteChatMember", d)
        if r and r.get("ok"):
            return True, r
    except Exception as e:
        print(f"[promote:1] {e}")

    # روش ۲
    try:
        d = {
            "chat_id": chat_id,
            "user_id": user_id,
            "can_change_info": "true",
            "can_delete_messages": "true",
            "can_invite_users": "true",
            "can_restrict_members": "true",
            "can_pin_messages": "true",
        }
        r = api.request("promoteChatMember", d)
        if r and r.get("ok"):
            return True, r
    except Exception as e:
        print(f"[promote:2] {e}")

    # روش ۳
    try:
        r = api.request("setChatMemberStatus", {
            "chat_id": chat_id,
            "user_id": user_id,
            "status": "administrator",
        })
        if r and r.get("ok"):
            return True, r
    except Exception:
        pass

    return False, None


def _demote_admin(chat_id, user_id):
    try:
        d = {
            "chat_id": str(chat_id),
            "user_id": str(user_id),
            "can_change_info": "false",
            "can_delete_messages": "false",
            "can_invite_users": "false",
            "can_restrict_members": "false",
            "can_pin_messages": "false",
            "can_promote_members": "false",
            "can_manage_video_chats": "false",
        }
        r = api.request("promoteChatMember", d)
        if r and r.get("ok"):
            return True, r
    except Exception:
        pass

    try:
        r = api.request("setChatMemberStatus", {
            "chat_id": chat_id,
            "user_id": user_id,
            "status": "member",
        })
        if r and r.get("ok"):
            return True, r
    except Exception:
        pass

    return False, None


def cmd_promote(chat_id, user_id, message, args=None):
    t = get_target(message, chat_id)
    if not t:
        _send_user_not_found(chat_id, message, action_hint="ارتقا")
        return
    tid = t["id"]
    tname = u_name(t)

    if tid == user_id:
        api.send(chat_id, "🙏 نمی‌تونی خودت رو ارتقا بدی.",
                 reply_to=message["message_id"])
        return
    if tid == api.bot_id():
        api.send(chat_id, "🙏 نمی‌تونی به ربات دست بزنی.",
                 reply_to=message["message_id"])
        return
    if is_admin(chat_id, tid):
        api.send(chat_id, f"ℹ️ {tname} از قبل ادمینه.",
                 reply_to=message["message_id"])
        return

    ok, r = _make_admin(chat_id, tid)

    if ok:
        api.send(chat_id,
            f"👑 **{tname}** به ادمین ارتقا یافت!\n\n👤 `{tid}`",
            parse_mode="Markdown")
    else:
        api.send(chat_id,
            f"❌ **نتونستم {tname} رو ارتقا بدم.**\n\n"
            f"💡 بله ممکنه این قابلیت رو پشتیبانی نکنه.",
            parse_mode="Markdown")


def cmd_demote(chat_id, user_id, message):
    t = get_target(message, chat_id)
    if not t:
        _send_user_not_found(chat_id, message, action_hint="تنزل")
        return
    tid = t["id"]
    tname = u_name(t)

    if tid == user_id:
        api.send(chat_id, "🙏 نمی‌تونی خودت رو تنزل بدی.",
                 reply_to=message["message_id"])
        return
    if tid == api.bot_id():
        api.send(chat_id, "🙏 نمی‌تونی به ربات دست بزنی.",
                 reply_to=message["message_id"])
        return
    if not is_admin(chat_id, tid):
        api.send(chat_id, f"ℹ️ {tname} ادمین نیست.",
                 reply_to=message["message_id"])
        return

    ok, r = _demote_admin(chat_id, tid)

    if ok:
        api.send(chat_id, f"⬇️ **{tname}** از ادمینی حذف شد.",
                 parse_mode="Markdown")
    else:
        api.send(chat_id,
            f"❌ **نتونستم {tname} رو تنزل بدم.**",
            parse_mode="Markdown")


# ============================================================
# تگ کردن کاربران با @username
# ============================================================
def tag_users_smart(chat_id, user_id, user_name, mode="all"):
    """
    تگ کردن با @username (چون tg:// کار نمی‌کنه در بله)
    """
    now = time.time()
    all_users = {}

    # ۱. از user_profiles
    profiles = get("user_profiles", chat_id) or {}
    print(f"[tag] user_profiles: {len(profiles)}")

    for uid_str, info in profiles.items():
        last_seen = info.get("last_seen", info.get("ts", 0))
        all_users[uid_str] = {
            "id": int(uid_str),
            "name": (info.get("first_name", "") or "کاربر")[:40],
            "username": (info.get("username") or "").strip(),
            "last_seen": last_seen,
            "source": "profile",
        }

    # ۲. از members_seen
    try:
        members_seen = get("members_seen", chat_id) or {}
        print(f"[tag] members_seen: {len(members_seen)}")

        for uid_str, info in members_seen.items():
            if uid_str in all_users:
                if info.get("ts", 0) > all_users[uid_str]["last_seen"]:
                    all_users[uid_str]["last_seen"] = info.get("ts", 0)
                if info.get("username") and not all_users[uid_str].get("username"):
                    all_users[uid_str]["username"] = info["username"]
                continue

            all_users[uid_str] = {
                "id": int(uid_str),
                "name": (info.get("first_name", "") or "کاربر")[:40],
                "username": (info.get("username") or "").strip(),
                "last_seen": info.get("ts", now),
                "source": "seen",
            }
    except Exception as e:
        print(f"[tag:seen] {e}")

    # ۳. ادمین‌ها
    try:
        r = api.admins(chat_id)
        if r and r.get("ok"):
            for a in r.get("result", []):
                u = a.get("user", {})
                uid = u.get("id")
                if not uid:
                    continue
                uid_str = str(uid)
                if uid_str in all_users:
                    continue
                all_users[uid_str] = {
                    "id": uid,
                    "name": (u.get("first_name", "") or "ادمین")[:40],
                    "username": (u.get("username") or "").strip(),
                    "last_seen": now,
                    "source": "admin",
                }
    except Exception as e:
        print(f"[tag:admins] {e}")

    # ۴. فیلتر
    if mode in ("7", "7h", "هفتساعت", "7ساعت"):
        cutoff = now - 7 * 3600
        mode_fa = "۷ ساعت اخیر"
        mode_icon = "⏰"
        users = [u for u in all_users.values() if u["last_seen"] >= cutoff]
    elif mode in ("24", "24h", "24ساعت", "یکروز"):
        cutoff = now - 24 * 3600
        mode_fa = "۲۴ ساعت اخیر"
        mode_icon = "📅"
        users = [u for u in all_users.values() if u["last_seen"] >= cutoff]
    elif mode in ("week", "هفته", "7d", "7روز", "یکهفته"):
        cutoff = now - 7 * 24 * 3600
        mode_fa = "یک هفته اخیر"
        mode_icon = "📆"
        users = [u for u in all_users.values() if u["last_seen"] >= cutoff]
    else:
        mode_fa = "همه کاربران"
        mode_icon = "👥"
        users = list(all_users.values())

    users.sort(key=lambda x: x["last_seen"], reverse=True)

    if not users:
        api.send(chat_id,
            f"{mode_icon} **{mode_fa}**\n\n"
            f"❌ **هیچ کاربری پیدا نشد!**",
            parse_mode="Markdown",
            reply_to=0)
        return

    # ۵. جدا کردن: با یوزرنیم / بدون یوزرنیم
    with_username = [u for u in users if u.get("username")]
    without_username = [u for u in users if not u.get("username")]

    total = len(users)
    total_with = len(with_username)
    total_without = len(without_username)

    # ۶. ارسال پیام سرصفحه
    header = (
        f"{mode_icon} **تگ {mode_fa}**\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👥 کل: `{total}` کاربر\n"
        f"🔔 قابل تگ: `{total_with}`\n"
    )
    if total_without > 0:
        header += f"⚠️ بدون یوزرنیم: `{total_without}`\n"
    header += f"👮 توسط: **{user_name}**\n\n"

    # ۷. تگ با @username
    if with_username:
        mentions = [f"@{u['username']}" for u in with_username]

        chunks = []
        current = []
        current_len = 0
        for m in mentions:
            m_len = len(m) + 2
            if current_len + m_len > 3500 and current:
                chunks.append(current)
                current = [m]
                current_len = m_len
            else:
                current.append(m)
                current_len += m_len
        if current:
            chunks.append(current)

        try:
            api.send(chat_id, header + " ".join(chunks[0]),
                     parse_mode="Markdown", reply_to=0)
            time.sleep(0.8)
        except Exception as e:
            print(f"[tag:first] {e}")
            api.send(chat_id, "❌ خطا در ارسال تگ", reply_to=0)
            return

        for i, chunk in enumerate(chunks[1:], 2):
            try:
                api.send(chat_id,
                         f"📄 **صفحه {i} از {len(chunks)}**\n\n" + " ".join(chunk),
                         parse_mode="Markdown", reply_to=0)
                time.sleep(0.8)
            except Exception as e:
                print(f"[tag:page:{i}] {e}")
    else:
        api.send(chat_id,
                 header + "❌ **هیچ کاربری یوزرنیم نداره!**",
                 parse_mode="Markdown", reply_to=0)

    # ۸. کاربران بدون یوزرنیم
    if without_username:
        txt = f"⚠️ **کاربران بدون یوزرنیم** ({total_without} نفر)\n"
        txt += "━━━━━━━━━━━━━━━\n"
        txt += "_این کاربران قابل تگ شدن نیستن چون یوزرنیم ندارن:_\n\n"

        for u in without_username[:30]:
            txt += f"• {u['name']}\n"

        if total_without > 30:
            txt += f"\n_و {total_without - 30} نفر دیگر..._\n"

        txt += "\n💡 _بله فقط `@username` رو پشتیبانی می‌کنه_"

        try:
            api.send(chat_id, txt, parse_mode="Markdown", reply_to=0)
        except Exception as e:
            print(f"[tag:without] {e}")


# ============================================================
# لقب
# ============================================================
def cmd_title(chat_id, user_id, message, args):
    import asl_laqab
    asl_laqab.cmd_laqab(chat_id, user_id, message, args)


# ============================================================
# پیام
# ============================================================
def cmd_del(chat_id, user_id, message):
    if message.get("reply_to_message"):
        api.delete(chat_id, message["reply_to_message"]["message_id"])
        api.delete(chat_id, message["message_id"])
    else:
        api.send(chat_id, "🙏 لطفاً ریپلای بزنید.",
                 reply_to=message["message_id"])


def cmd_pin(chat_id, user_id, message):
    if message.get("reply_to_message"):
        api.pin(chat_id, message["reply_to_message"]["message_id"])
        api.send(chat_id, "📌 سنجاق شد.")
    else:
        api.send(chat_id, "🙏 لطفاً ریپلای بزنید.",
                 reply_to=message["message_id"])


def cmd_unpin(chat_id, user_id, message):
    api.unpin(chat_id)
    api.send(chat_id, "📌 سنجاق برداشته شد.")


# ============================================================
# قفل‌ها
# ============================================================
def cmd_lock(chat_id, user_id, args):
    if not args:
        from panels import locks_panel
        t, markup = locks_panel(chat_id)
        api.send(chat_id, t, parse_mode="Markdown", markup=markup)
        return

    a = list(args)
    while a and a[0].lower() in ("قفل", "قفلها", "قفل‌ها", "قفلا"):
        a.pop(0)

    if not a:
        from panels import locks_panel
        t, markup = locks_panel(chat_id)
        api.send(chat_id, t, parse_mode="Markdown", markup=markup)
        return

    name = a[0].lower().strip()

    if name in ("all", "همه"):
        lock_mod.lock_all(chat_id)
        api.send(chat_id, "🔒 **همه قفل‌ها فعال شدند.**", parse_mode="Markdown")
        return

    key = lock_mod.resolve_name(name)
    if not key:
        api.send(chat_id, f"❌ قفل «{name}» یافت نشد.", parse_mode="Markdown")
        return

    lock_mod.lock(chat_id, key)
    fa = lock_mod.LOCKS[key]["fa"]
    api.send(chat_id, f"🔒 **قفل «{fa}» فعال شد.**", parse_mode="Markdown")


def cmd_unlock(chat_id, user_id, args):
    if not args:
        lock_mod.unlock_all(chat_id)
        api.send(chat_id, "🔓 **همه قفل‌ها باز شدند.**", parse_mode="Markdown")
        return

    name = args[0].lower().strip()
    if name in ("all", "همه"):
        lock_mod.unlock_all(chat_id)
        api.send(chat_id, "🔓 **همه قفل‌ها باز شدند.**", parse_mode="Markdown")
        return

    key = lock_mod.resolve_name(name)
    if not key:
        api.send(chat_id, f"❌ قفل «{name}» یافت نشد.", parse_mode="Markdown")
        return

    lock_mod.unlock(chat_id, key)
    fa = lock_mod.LOCKS[key]["fa"]
    api.send(chat_id, f"🔓 **قفل «{fa}» باز شد.**", parse_mode="Markdown")


def cmd_locks(chat_id, user_id, args):
    from panels import locks_panel
    t, markup = locks_panel(chat_id)
    api.send(chat_id, t, parse_mode="Markdown", markup=markup)


# ============================================================
# قفل کل گروه
# ============================================================
def cmd_lock_group(chat_id, user_id, user_name):
    lock_mod.lock_group(chat_id, user_id)
    api.send(chat_id,
        "🔒 **گروه قفل شد.**\n\n"
        f"👮 توسط: **{user_name}**",
        parse_mode="Markdown")


def cmd_unlock_group(chat_id, user_id, user_name):
    try:
        locked_before = get("locked_users", chat_id) or {}
        count = len(locked_before)
    except Exception:
        count = 0

    lock_mod.unlock_group(chat_id)

    api.send(chat_id,
        "🔓 **گروه باز شد.**\n\n"
        f"👮 توسط: **{user_name}**\n"
        f"🔓 کاربران آزادشده: **{count}** نفر",
        parse_mode="Markdown")


def cmd_free_all_locked(chat_id, user_id, user_name):
    locked = get("locked_users", chat_id) or {}
    count = len(locked)
    if count == 0:
        api.send(chat_id, "ℹ️ هیچ کاربر قفل‌شده‌ای وجود نداره.")
        return
    lock_mod.clear_lock_list(chat_id)
    api.send(chat_id, f"🔓 **{count}** کاربر آزاد شدند.",
             parse_mode="Markdown")


# ============================================================
# ضد اسپم
# ============================================================
def cmd_antispam(chat_id, user_id, args):
    cfg = get("antispam", chat_id) or {}
    if not args:
        st = "🟢 روشن" if cfg.get("enabled") else "🔴 خاموش"
        api.send(chat_id, f"🛡 **ضد اسپم:** {st}", parse_mode="Markdown")
        return

    if args[0] in ("on", "روشن"):
        cfg["enabled"] = True
        cfg["limit"] = int(args[1]) if len(args) > 1 else 5
        cfg["window"] = int(args[2]) if len(args) > 2 else 10
        action_map = {"mute": "سکوت", "kick": "اخراج", "ban": "بن"}
        act = args[3] if len(args) > 3 else "mute"
        cfg["action"] = action_map.get(act, "سکوت")
        cfg["action_key"] = act
        set_("antispam", chat_id, cfg)
        api.send(chat_id, f"✅ ضد اسپم روشن شد.", parse_mode="Markdown")
    elif args[0] in ("off", "خاموش"):
        cfg["enabled"] = False
        set_("antispam", chat_id, cfg)
        api.send(chat_id, "✅ ضد اسپم خاموش شد.")


# ============================================================
# کلمات / قوانین
# ============================================================
def cmd_addword(chat_id, user_id, args):
    if not args:
        return
    bw = get("banned_words", chat_id) or []
    for w in args:
        if w not in bw:
            bw.append(w)
    set_("banned_words", chat_id, bw)
    api.send(chat_id, f"✅ **{len(args)}** کلمه اضافه شد.")


def cmd_delword(chat_id, user_id, args):
    if not args:
        return
    bw = get("banned_words", chat_id) or []
    for w in args:
        if w in bw:
            bw.remove(w)
    set_("banned_words", chat_id, bw)
    api.send(chat_id, "✅ حذف شد.")


def cmd_setrules(chat_id, user_id, message, args):
    if not args:
        api.send(chat_id, "🙏 مثال: `قوانین تنظیم متن`", parse_mode="Markdown")
        return
    set_("rules", chat_id, {"text": " ".join(args)})
    api.send(chat_id, "✅ قوانین ثبت شد.")


def cmd_reset(chat_id, user_id, args):
    try:
        lock_mod.clear_lock_list(chat_id)
    except Exception:
        pass
    set_("warnings", chat_id, {})
    set_("muted", chat_id, {})
    set_("locked_users", chat_id, {})
    set_("lock_warnings", chat_id, {})
    set_("antispam_warns", chat_id, {})
    set_("bw_warnings", chat_id, {})
    api.send(chat_id, "🔄 اخطارها، سکوت‌ها و هشدارها ریست شد.")


def cmd_stats(chat_id, user_id, args):
    w = sum((get("warnings", chat_id) or {}).values())
    m = len(get("muted", chat_id) or {})
    lu = len(get("locked_users", chat_id) or {})
    locks_on = sum(1 for v in (get("locks", chat_id) or {}).values() if v)
    as_on = (get("antispam", chat_id) or {}).get("enabled", False)
    gl_on = lock_mod.is_group_locked(chat_id)
    c = api.members_count(chat_id)
    cnt = c["result"] if c and c.get("ok") else "?"

    api.send(chat_id,
        f"📊 **آمار گروه**\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👥 اعضا: `{cnt}`\n"
        f"🔒 قفل‌های فعال: `{locks_on}`\n"
        f"🔐 قفل کل گروه: {'✅' if gl_on else '❌'}\n"
        f"🚫 کاربران قفل‌شده: `{lu}`\n"
        f"⚠️ اخطارها: `{w}`\n"
        f"🔇 سکوت‌ها: `{m}`\n"
        f"🛡 ضد اسپم: {'🟢' if as_on else '🔴'}",
        parse_mode="Markdown")