# -*- coding: utf-8 -*-
"""اجرای آفلاین ربات با API شبیه‌سازی‌شده.

روش کار:
  1) config.DATA_DIR به یک پوشه موقت هدایت می‌شود (دیتای واقعی دست نمی‌خورد)
  2) api.request / api.get_updates با شبیه‌ساز جایگزین می‌شود
  3) دستورات به‌عنوان ادمین و کاربر عادی فرستاده می‌شود
  4) همه‌ی callback_data هایی که ربات تولید می‌کند، به‌صورت خودکار «فشرده» می‌شوند
  5) هر استثنا / خطای parse_mode / خطای send گزارش می‌شود

اجرا:  python3 tests/run_smoke.py  [-v]
"""
import contextlib
import io
import json
import os
import sys
import tempfile
import threading
import time
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

VERBOSE = "-v" in sys.argv

# ---------------------------------------------------------------
# دیتای موقت
# ---------------------------------------------------------------
TMP = tempfile.mkdtemp(prefix="bale_smoke_")
import config  # noqa: E402
config.DATA_DIR = TMP

import fake_bale  # noqa: E402
import api  # noqa: E402

try:
    import gifmaker  # noqa: E402
except Exception as e:  # pragma: no cover
    gifmaker = None
    print(f"[warn] gifmaker import failed: {e}")

FAKE = fake_bale.install(api, gifmaker)

# ---------------------------------------------------------------
# ضبط استثناهای نخ‌های پس‌زمینه (تایمر بازی‌ها و ...)
# ---------------------------------------------------------------
THREAD_ERRORS = []
_orig_excepthook = threading.excepthook


def _thread_hook(args):
    if issubclass(args.exc_type, SystemExit):
        return
    THREAD_ERRORS.append("".join(
        traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback)))


threading.excepthook = _thread_hook

with contextlib.redirect_stdout(io.StringIO()):
    import main  # noqa: E402

# ---------------------------------------------------------------
# شناسه‌ها
# ---------------------------------------------------------------
GROUP = -1001234567890
GROUP2 = -1009876543210
ADMIN_ID = 111
ADMIN = fake_bale.make_user(ADMIN_ID, "مدیر کل", "admin_user")
USER_ID = 222
USER = fake_bale.make_user(USER_ID, "کاربر عادی", "normal_user")
USER2_ID = 333
USER2 = fake_bale.make_user(USER2_ID, "کاربر دوم", "user2")

FAKE.statuses[(GROUP, ADMIN_ID)] = "creator"
FAKE.statuses[(GROUP2, ADMIN_ID)] = "creator"
FAKE.chats[GROUP] = {"id": GROUP, "type": "supergroup", "title": "گروه تست"}
FAKE.chats[GROUP2] = {"id": GROUP2, "type": "supergroup", "title": "گروه دوم"}

# ---------------------------------------------------------------
# زیرساخت گزارش
# ---------------------------------------------------------------
FAILURES = []


class Failure:
    def __init__(self, kind, where, detail, tb=""):
        self.kind = kind
        self.where = where
        self.detail = detail
        self.tb = tb

    def __str__(self):
        head = f"[{self.kind}] {self.where}: {self.detail}"
        if self.tb and (VERBOSE or self.kind in ("EXC", "STATE")):
            head += "\n" + self.tb.rstrip()
        return head


def record(kind, where, detail, tb=""):
    FAILURES.append(Failure(kind, where, detail, tb))


_handle_depth = [0]


def call_handle(update, label):
    """main.handle را با ضبط استثنا اجرا می‌کند."""
    buf = io.StringIO()
    before_sent = len(FAKE.sent)
    before_pe = len(FAKE.parse_errors)
    before_fb = len(FAKE.fallbacks)
    before_se = len(FAKE.stray_escapes)
    before_mm = len(FAKE.mode_mismatch)
    t0 = time.time()
    try:
        with contextlib.redirect_stdout(buf):
            main.handle(update)
    except Exception:
        record("EXC", label, "استثنای مدیریت‌نشده", traceback.format_exc())
    finally:
        dt = time.time() - t0
        if dt > 5:
            record("SLOW", label, f"پردازش {dt:.1f} ثانیه طول کشید")

    out = buf.getvalue()
    # خطاهای send که خودِ api لاگ می‌کند
    for line in out.splitlines():
        if "SEND FAIL" in line:
            record("SEND", label, line.strip()[:300])
        elif "[api:" in line and "Network" not in line:
            record("API", label, line.strip()[:300])

    # پیام‌هایی که parse_mode رد شد ولی با فالبک «بدون parse_mode» نجات یافتند
    new_fb = FAKE.fallbacks[before_fb:]
    for t in new_fb:
        record("FALLBACK", label,
               f"پیام با از دست دادن فرمت نجات یافت (escape از قلم افتاده): {t[:130]!r}")

    # متن escape‌شده‌ای که WITHOUT parse_mode فرستاده شد → بک‌اسلش برای کاربر دیده می‌شود
    new_se = FAKE.stray_escapes[before_se:]
    for t in new_se:
        record("STRAY", label,
               f"متن escape‌شده بدون parse_mode فرستاده شد: {t[:130]!r}")

    # escape از نوع اشتباه (Markdown در HTML یا برعکس)
    for kind, t in FAKE.mode_mismatch[before_mm:]:
        record("MISMATCH", label, f"{kind}: {t[:2000]!r}")
    return out


def send_cmd(chat_id, user, text, label=None, **kw):
    label = label or f"cmd:{text}"
    return call_handle(fake_bale.make_update_message(chat_id, user, text, **kw), label)


def press(chat_id, user, data, label=None, msg_id=555):
    label = label or f"cb:{data}"
    return call_handle(fake_bale.make_callback(chat_id, user, data, message_id=msg_id), label)


# ---------------------------------------------------------------
# سناریوها
# ---------------------------------------------------------------
def scenario_private():
    pm = fake_bale.make_update_message(ADMIN_ID, ADMIN, "/start", chat_type="private")
    call_handle(pm, "pm:/start")
    for t in ["/start", "شروع", "/help", "/راهنما", "/پنل", "پنل",
              "/id", "/آیدی", "امتیاز من", "/امتیازمن", "/پروفایل", "/زمان"]:
        send_cmd(ADMIN_ID, ADMIN, t, f"pm:{t}", chat_type="private")


BASIC_GROUP_CMDS = [
    "/start", "شروع", "/help", "/راهنما", "راهنما", "/پنل", "پنل",
    "/id", "/آیدی", "آیدی", "/امتیازمن", "امتیاز من", "حساب من",
    "/کاربران", "کاربران", "/تگ", "تگ", "/سرگرمی", "سرگرمی",
    "/قفل‌ها", "قفل ها", "/ضداسپم", "ضد اسپم", "/ضدفحش", "ضد فحش",
    "/خوش‌آمد", "خوش آمد", "/قوانین", "قوانین", "/یادداشت‌ها", "یادداشت‌ها",
    "/آمار", "آمار", "/لیست‌کلمات", "لیست کلمات", "/لیست‌سیاه", "لیست سیاه",
    "/اخطارها", "/سکوت", "/بن", "/آنبن", "/آزاد",
    "/قفل", "/بازکردن", "/قفل همه", "/بازکردن همه", "/قفل گروه", "/بازکردن گروه",
    "/حالت آهسته", "حالت آهسته", "/حالت شب", "حالت شب", "/حالت خواب", "حالت خواب",
    "/سفیدلیست", "سفید لیست", "/دستورات سفارشی", "/گزارش", "/گزارش هفتگی",
    "/برترین امروز", "برترین امروز", "/دعوت‌ها", "/لیدر دعوت",
    "/رتبه", "/رتبه ماهانه", "/لیدربرد", "/قرعه‌کشی", "/آزمون",
    "/ارتقا", "/تنزل", "/مدیریت", "/همگانی", "/پاکسازی",
    "/شیرخط", "/جوک", "/تاس", "/سنگ کاغذ قیچی", "/دوز", "/مافیا",
    "/جرئت حقیقت", "/گزارش باگ", "/بازی", "/پایان بازی", "/توقف",
    "/عضویت", "/برداشتن سنجاق", "/پین", "/یادداشت",
    "/اصل", "/لقب", "/حذف لقب", "/لیست لقب‌ها", "/لیدر آزمون",
    "/ذخیره", "/بگیر", "/اطلاعات", "/ریست", "/حذف اخطار", "/اخطار",
    "/کلمه ممنوعه", "/حذف کلمه", "/قوانین تنظیم", "/روزانه", "/هفتگی", "/ماهانه",
]


def scenario_group_admin():
    for t in BASIC_GROUP_CMDS:
        send_cmd(GROUP, ADMIN, t, f"g-admin:{t}")


def scenario_group_user():
    for t in ["/start", "/help", "/راهنما", "/پنل", "پنل", "/id", "/آیدی",
              "/امتیازمن", "/کاربران", "/تگ", "/قفل", "/بن", "/سکوت",
              "/همگانی", "/قفل همه", "/ضد اسپم", "/قوانین", "/آمار",
              "/رتبه", "/دعوت‌ها", "/سرگرمی", "/شیرخط", "/تاس", "/جوک",
              "/دوز", "/مافیا", "/جرئت حقیقت", "/آزمون", "/قرعه‌کشی",
              "/گزارش باگ", "/اصل", "/لقب", "/گزارش"]:
        send_cmd(GROUP, USER, t, f"g-user:{t}")


def scenario_flows():
    """جریان‌های مرحله‌ای: تنظیم قوانین، اضافه‌کردن کلمه، یادداشت، خوش‌آمد و ..."""
    # قوانین
    send_cmd(GROUP, ADMIN, "/قوانین تنظیم", "flow:rules")
    send_cmd(GROUP, ADMIN, "قانون اول: احترام بگذارید", "flow:rules-set")
    send_cmd(GROUP, ADMIN, "/قوانین", "flow:rules-show")
    # کلمه ممنوعه
    send_cmd(GROUP, ADMIN, "/کلمه ممنوعه", "flow:badword-add")
    send_cmd(GROUP, ADMIN, "کلمه‌بد", "flow:badword-value")
    send_cmd(GROUP, ADMIN, "/لیست کلمات", "flow:badword-list")
    send_cmd(GROUP, ADMIN, "کلمه‌بد", "flow:badword-msg")   # پیام حاوی کلمه بد
    send_cmd(GROUP, USER, "کلمه‌بد", "flow:badword-user")
    # یادداشت
    send_cmd(GROUP, ADMIN, "/یادداشت", "flow:note-add")
    send_cmd(GROUP, ADMIN, "قانون‌ها", "flow:note-value")
    send_cmd(GROUP, ADMIN, "/یادداشت‌ها", "flow:note-list")
    # آهسته
    for a in ["آهسته 5", "آهسته 10m", "آهسته 1h", "آهسته خاموش"]:
        send_cmd(GROUP, ADMIN, a, f"flow:slow:{a}")
    # شب و خواب
    for a in ["حالت شب روشن", "حالت شب خاموش",
              "حالت خواب روشن", "حالت خواب خاموش"]:
        send_cmd(GROUP, ADMIN, a, f"flow:mode:{a}")
    # ضد اسپم
    for a in ["ضد اسپم روشن", "ضد اسپم خاموش"]:
        send_cmd(GROUP, ADMIN, a, f"flow:as:{a}")
        send_cmd(GROUP, USER, a, f"flow:as-user:{a}")
    # سفیدلیست
    send_cmd(GROUP, ADMIN, "سفید لیست 222", "flow:wl-add")
    send_cmd(GROUP, ADMIN, "/سفیدلیست", "flow:wl-list")
    # دستور سفارشی
    send_cmd(GROUP, ADMIN, "/دستورات سفارشی", "flow:cc-add")
    send_cmd(GROUP, ADMIN, "خوب", "flow:cc-key")
    send_cmd(GROUP, ADMIN, "مرسی!", "flow:cc-val")
    send_cmd(GROUP, USER, "خوب", "flow:cc-run")
    # اخطار/سکوت/بن
    reply_target = fake_bale.make_message(GROUP, USER, "پیام کاربر",
                                          message_id=7777)
    send_cmd(GROUP, ADMIN, "/اخطار", "flow:warn",
             reply_to=reply_target)
    send_cmd(GROUP, ADMIN, "/سکوت", "flow:mute", reply_to=reply_target)
    send_cmd(GROUP, ADMIN, "/آزاد", "flow:unmute", reply_to=reply_target)
    send_cmd(GROUP, ADMIN, "/بن", "flow:ban", reply_to=reply_target)
    send_cmd(GROUP, ADMIN, "/آنبن", "flow:unban", reply_to=reply_target)
    send_cmd(GROUP, ADMIN, "222", "flow:ban-by-id")
    # ارتقا/تنزل
    send_cmd(GROUP, ADMIN, "/ارتقا", "flow:promote", reply_to=reply_target)
    send_cmd(GROUP, ADMIN, "/تنزل", "flow:demote", reply_to=reply_target)
    send_cmd(GROUP, ADMIN, "/ارتقا", "flow:promote2", reply_to=reply_target)
    # عضویت اجباری
    for a in ["عضویت @testchannel", "/عضویت", "عضویت خاموش"]:
        send_cmd(ADMIN_ID, ADMIN, a, f"flow:fj:{a}", chat_type="private")
    # همگانی
    bc_msg = fake_bale.make_message(ADMIN_ID, ADMIN, "پیام تست همگانی", message_id=8888)
    send_cmd(ADMIN_ID, ADMIN, "همگانی", "flow:broadcast", reply_to=bc_msg,
             chat_type="private")
    # بازی‌ها
    for a in ["دوز", "مافیا", "جرئت حقیقت", "تاس", "شیرخط", "جوک",
              "سنگ کاغذ قیچی", "بازی حدس", "بازی کلمه", "بازی حروف"]:
        send_cmd(GROUP, ADMIN, a, f"flow:game:{a}")
        send_cmd(GROUP, USER, a, f"flow:game-user:{a}")
    # اسپم برای تریگر antispam
    send_cmd(GROUP, ADMIN, "ضد اسپم روشن", "flow:as-on2")
    for i in range(25):
        send_cmd(GROUP, USER2, f"پیام پشت‌سرهم {i}", f"flow:spam:{i}")
    # آمار/پاکسازی/گزارش
    for a in ["آمار", "/پاکسازی", "گزارش هفتگی روشن", "گزارش هفتگی خاموش",
              "گزارش هفتگی", "برترین امروز", "رتبه", "رتبه ماهانه"]:
        send_cmd(GROUP, ADMIN, a, f"flow:misc:{a}")


def scenario_join_leave():
    for u in (USER, USER2, ADMIN):
        call_handle(fake_bale.make_chat_member_update(GROUP, u, "left", "member"),
                    f"join:{u['id']}")
        call_handle(fake_bale.make_chat_member_update(GROUP, u, "member", "left"),
                    f"leave:{u['id']}")
    # پیام خوش‌آمد باید ارسال شود
    wel = [m for m in FAKE.sent if "خوش" in (m.get("text") or "")]
    if not wel:
        record("WARN", "join", "پیام خوش‌آمدگویی ارسال نشد (ممکن است تنظیم نشده باشد)")


EVIL_IDENTITIES = [
    (401, "علی_رضا", "ali_reza"),
    (402, "*ستاره*", "star_user"),
    (403, "`کد`", "code_boy"),
    (404, "[لینک](x)", "link_girl"),
    (405, "_italic_", "under_score"),
    (406, "a*b*c", "abc_user"),
    (407, "<b>html</b>", "html_user"),
    (408, "tغییر", "user__double__"),
]


def scenario_evil_identities():
    """نام/یوزرنیم کاربران شامل کاراکترهای ویژه مارک‌داون.

    این کاراکترها در بله/تلگرام مجازند و اگر escape نشوند،
    کل پیام با خطای 400 رد می‌شود.
    """
    import storage
    from storage import add_game_win
    for uid, name, uname in EVIL_IDENTITIES:
        u = fake_bale.make_user(uid, name, uname)
        FAKE.statuses[(GROUP, uid)] = "member"
        for i in range(3):
            send_cmd(GROUP, u, f"سلام {i}", f"evil:msg:{uid}:{i}")
        add_game_win(GROUP, "doss", uid, name)     # برای لیدربرد بازی‌ها
    # پنل‌هایی که نام کاربران را فهرست می‌کنند
    for t in ["/کاربران", "کاربران", "/لیست سیاه", "/اخطارها", "/سکوت",
              "/آمار", "برترین امروز", "/رتبه", "/رتبه ماهانه",
              "/لیدربرد دوز", "/لیدربرد", "/لیدر آزمون", "/لیدر دعوت",
              "/دعوت‌ها", "/گزارش هفتگی", "/یادداشت‌ها", "/سفیدلیست"]:
        send_cmd(GROUP, ADMIN, t, f"evil:cmd:{t}")
    # نمایش نتیجه بازی‌ها با نام آلوده
    send_cmd(GROUP, ADMIN, "/دوز", "evil:doss")


EVIL_TEXT = "سلام_دنیا *ستاره* `کد` [لینک](x)"


def scenario_evil_content():
    """محتوای ذخیره‌شده با کاراکترهای مارک‌داون (قوانین/یادداشت/خوش‌آمد/عنوان گروه)."""
    import storage
    # ۱) عنوان گروه با کاراکتر ویژه
    FAKE.chats[GROUP]["title"] = "گروه_تست *آلفا*"
    # ۲) قوانین
    storage.set_("rules", GROUP, EVIL_TEXT)
    send_cmd(GROUP, ADMIN, "/قوانین", "evilc:rules")
    # ۳) خوش‌آمد
    storage.set_("welcome", GROUP, {"enabled": True, "text": EVIL_TEXT})
    call_handle(fake_bale.make_chat_member_update(
        GROUP, fake_bale.make_user(901, "علی_رضا", "ali_reza"), "left", "member"),
        "evilc:welcome")
    # ۴) یادداشت
    storage.update("notes", GROUP, "قانون_ما", EVIL_TEXT)
    send_cmd(GROUP, ADMIN, "/یادداشت‌ها", "evilc:notes")
    send_cmd(GROUP, ADMIN, "قانون_ما", "evilc:note-view")
    # ۵) دستور سفارشی
    storage.update("custom_commands", GROUP, "خوب_باش", EVIL_TEXT)
    send_cmd(GROUP, USER, "خوب_باش", "evilc:ccmd")
    send_cmd(GROUP, ADMIN, "/دستورات سفارشی", "evilc:ccmd-list")
    # ۶) کلمات ممنوعه با کاراکتر ویژه
    send_cmd(GROUP, ADMIN, "/کلمه ممنوعه", "evilc:bw")
    send_cmd(GROUP, ADMIN, "کلمه_بد", "evilc:bw-value")
    send_cmd(GROUP, USER, "این کلمه_بد است", "evilc:bw-hit")
    send_cmd(GROUP, ADMIN, "/لیست کلمات", "evilc:bw-list")
    # ۷) وضعیت کاربر‌ها با عنوان آلوده (لقب)
    send_cmd(GROUP, ADMIN, "لقب علی_رضا", "evilc:laqab")
    send_cmd(GROUP, ADMIN, "/لیست لقب‌ها", "evilc:laqab-list")
    # ۸) آمار و پنل‌ها با عنوان آلوده
    for t in ["آمار", "/آمار", "/پنل", "قفل ها", "برترین امروز", "/گزارش هفتگی"]:
        send_cmd(GROUP, ADMIN, t, f"evilc:panel:{t}")


def scenario_ai():
    """دستورات و پنل هوش مصنوعی — بدون کلید API (باید همه‌چیز با پاسخ آماده کار کند)."""
    import ai
    import panels

    # مالک ربات = ادمین تست تا مسیرهای مالکانه هم اجرا شوند
    panels.OWNER_ID = ADMIN_ID
    ai.set_api_key("")          # حالت بدون کلید
    # دستور دستیار
    for q in ["هوش مصنوعی", "/ai", "هوش مصنوعی وضعیت گروه چطوره؟",
              "هوش مصنوعی اخطارها", "هوش مصنوعی قوانین چیه؟",
              "هوش مصنوعی چند نفر عضو داریم؟", "هوش مصنوعی چیکار می‌تونی بکنی؟"]:
        send_cmd(GROUP, ADMIN, q, f"ai:cmd:{q}")
        send_cmd(GROUP, USER, q, f"ai:cmd-user:{q}")
    # دستور کلید (فقط مالک ربات)
    for k in ["کلید ai", "کلید ai sk-or-v1-fake", "/کلیدai",
              "/کلیدai sk-or-v1-" + "x" * 24]:
        send_cmd(GROUP, ADMIN, k, f"ai:key:{k}")
    # کاربر عادی نباید بتواند کلید بگذارد
    send_cmd(GROUP, USER, "/کلیدai sk-or-v1-hack", "ai:key:hacker")
    ai.set_api_key("")
    # ریپلای روی پیام کاربر → پرونده
    reply = fake_bale.make_message(GROUP, USER, "پیام کاربر", message_id=9001)
    send_cmd(GROUP, ADMIN, "هوش مصنوعی", "ai:cmd-reply", reply_to=reply)
    # پنل‌های AI
    for d in ["ai:group", "ai:how", "ai:users:0", "ai:main", "ai:detail",
              "ai:g:announce", "ai:g:assistant", "ai:g:welcome",
              "ai:test", "ai:refresh", "ai:toggle", "ai:toggle"]:
        press(GROUP, ADMIN, d, f"ai:cb:{d}")
    press(ADMIN_ID, ADMIN, "ai:main", "ai:cb:owner-main", msg_id=999)
    # کاربر عادی نباید دسترسی داشته باشد
    press(GROUP, USER, "ai:group", "ai:cb:denied")
    press(GROUP, USER, "ai:toggle", "ai:cb:denied2")
    # پرونده‌ی یک کاربر
    press(GROUP, ADMIN, f"ai:u:{USER_ID}", "ai:cb:user-dossier")
    press(GROUP, ADMIN, f"ai:relax:{USER_ID}", "ai:cb:relax")
    press(GROUP, ADMIN, f"ai:harder:{USER_ID}", "ai:cb:harder")
    press(GROUP, ADMIN, f"ai:ureset:{USER_ID}", "ai:cb:ureset")
    # وضعیت TTL: مقداردهی پرونده با تخلفات زیاد
    import ai_persona
    for i in range(5):
        ai_persona.note_violation(GROUP, USER_ID, "spam")
    press(GROUP, ADMIN, "ai:users:0", "ai:cb:users-after-violations")
    press(GROUP, ADMIN, f"ai:u:{USER_ID}", "ai:cb:dossier-after")


def scenario_malformed():
    """آپدیت‌های خراب نباید ربات را بیندازند."""
    bad_updates = [
        {},
        {"update_id": 1},
        {"update_id": 2, "message": {}},
        {"update_id": 3, "message": {"chat": {"id": GROUP, "type": "supergroup"}}},
        {"update_id": 4, "message": {"chat": {"id": GROUP, "type": "supergroup"},
                                     "from": {"id": 1}, "text": None}},
        {"update_id": 5, "callback_query": {}},
        {"update_id": 6, "callback_query": {"id": "x", "from": {"id": 1},
                                            "message": {"chat": {"id": GROUP}}}},
        {"update_id": 7, "callback_query": {"id": "x", "from": {"id": 1},
                                            "message": {"chat": {"id": GROUP},
                                                        "message_id": 5},
                                            "data": ""}},
        {"update_id": 8, "callback_query": {"id": "x", "from": {"id": 1},
                                            "message": {"chat": {"id": GROUP},
                                                        "message_id": 5},
                                            "data": "user:profile:"}},
        {"update_id": 9, "callback_query": {"id": "x", "from": {"id": 1},
                                            "message": {"chat": {"id": GROUP},
                                                        "message_id": 5},
                                            "data": ":::"}},
        {"update_id": 10, "channel_post": {"chat": {"id": GROUP, "type": "channel"},
                                           "text": "test"}},
        {"update_id": 11, "edited_message": {"chat": {"id": GROUP, "type": "supergroup"},
                                             "from": {"id": ADMIN_ID},
                                             "text": "ویرایش"}},
        {"update_id": 12, "message": {"chat": {"id": GROUP, "type": "supergroup"},
                                      "from": {"id": ADMIN_ID, "first_name": "x"},
                                      "text": "/دوز", "message_id": 1}},
    ]
    for i, u in enumerate(bad_updates):
        call_handle(u, f"malformed:{i}")


def scenario_fuzz(n=600, seed=1234):
    """آپدیت‌های تصادفی/ناقص — هیچ‌کدام نباید استثنای مدیریت‌نشده بدهند."""
    import random as rnd
    r = rnd.Random(seed)
    chat_variants = [
        {"id": GROUP, "type": "supergroup", "title": "گروه"},
        {"id": GROUP},                       # بدون type
        {},                                   # خالی
        {"id": ADMIN_ID, "type": "private"},
    ]
    user_variants = [
        {"id": ADMIN_ID, "first_name": "مدیر"},
        {"id": USER_ID, "first_name": "علی_رضا", "username": "ali_reza"},
        {"id": None},
        {},
    ]
    texts = ["سلام", "/start", "/دوز", "/تگ", "پنل", "", None, "/مافیا",
             "/ناشناخته", "/قفل", "/بن", "@user", "a" * 100, "/آمار"]

    for i in range(n):
        kind = r.random()
        if kind < 0.75:
            msg = {}
            if r.random() < 0.9:
                msg["chat"] = r.choice(chat_variants)
            if r.random() < 0.9:
                msg["from"] = r.choice(user_variants)
            if r.random() < 0.9:
                msg["text"] = r.choice(texts)
            if r.random() < 0.5:
                msg["message_id"] = r.randint(1, 10 ** 6)
            elif r.random() < 0.3:
                msg["message_id"] = None
            if r.random() < 0.2:
                msg["reply_to_message"] = {"message_id": r.randint(1, 100)}
            upd = {"update_id": i, "message": msg}
            if r.random() < 0.05:
                del upd["message"]
                upd["channel_post"] = msg
        else:
            cbq = {}
            if r.random() < 0.9:
                cbq["id"] = f"cb{i}"
            if r.random() < 0.9:
                cbq["from"] = r.choice(user_variants)
            if r.random() < 0.9:
                cbq["message"] = {"chat": r.choice(chat_variants),
                                  "message_id": r.randint(1, 10 ** 5)}
            cbq["data"] = r.choice([
                "", "noop", "panel:main", "user:main", "doss:play:1:2",
                "game:x", "mode:1", "lb:1", "rank:1", "tag:all", "asl:x",
                "todd:vote:yes", "todd:setrounds:3", "anon_cancel:1",
                "mp:join", "mafia:join", "gif:x", "quiz:ans:0:1",
                ":::", "user:", "panel:", "/nope",
            ])
            upd = {"update_id": i, "callback_query": cbq}
        if r.random() < 0.03:
            upd = {"update_id": i}          # آپدیت کاملاً خالی
        call_handle(upd, f"fuzz:{i}:{kind:.2f}")


def scenario_weird_text():
    """متن‌های عجیب: ایموجی، لینک، منشن، طول زیاد، نیم‌فاصله، کاراکتر کنترلی."""
    texts = [
        "سلام 👋🌹🎉",
        "http://example.com",
        "https://t.me/joinchat/abcdef",
        "@username سلام",
        "a" * 500,
        "کاربر‌با‌نیم‌فاصله",
        "текст русский",
        "עברית",
        "\u200c\u200d\ufeff",
        "```code```",
        "*bold* _italic_ `code` [link](http://a.com)",
        "<b>tag</b>",
        "👨‍👩‍👧‍👦 خانواده",
        "\x00\x01\x02",
        "سلام" * 300,
        "  ",
        ".",
        "/",
        "//",
        "///",
        "/ناشناخته123",
        "🟥🟧🟨🟩🟦🟪",
    ]
    for i, t in enumerate(texts):
        send_cmd(GROUP, USER, t, f"weird:{i}")
        send_cmd(GROUP, ADMIN, t, f"weird-admin:{i}")


def scenario_callback_walk():
    """همه‌ی دکمه‌های تولیدشده را فشار می‌دهد (با سقف و بدون تکرار)."""
    pressed = set()
    round_no = 0
    identities = [ADMIN, USER, USER]
    while FAKE.callback_queue and round_no < 4000:
        data, chat_id, msg_id = FAKE.callback_queue.pop(0)
        key = (data, chat_id)
        if key in pressed:
            continue
        pressed.add(key)
        round_no += 1
        who = identities[round_no % len(identities)]
        ct = "private" if chat_id == ADMIN_ID else "supergroup"
        call_handle(fake_bale.make_callback(chat_id, who, data, message_id=msg_id or 555,
                                            msg_text="پیام دکمه", chat_type=ct),
                    f"walk:{data}")
    print(f"  {round_no} دکمه فشرده شد")


# ---------------------------------------------------------------
def main_run():
    print("=" * 70)
    print("اجرای تست آفلاین ربات آلفا")
    print(f"دیتای موقت: {TMP}")
    print("=" * 70)

    steps = [
        ("پیوی", scenario_private),
        ("دستورات گروه (ادمین)", scenario_group_admin),
        ("دستورات گروه (کاربر عادی)", scenario_group_user),
        ("جریان‌های تنظیمات", scenario_flows),
        ("ورود/خروج اعضا", scenario_join_leave),
        ("نام‌های تهاجمی (مارک‌داون)", scenario_evil_identities),
        ("محتوای تهاجمی", scenario_evil_content),
        ("آپدیت‌های خراب", scenario_malformed),
        ("متن‌های عجیب", scenario_weird_text),
        ("فاز فازی (خراب‌کارانه)", scenario_fuzz),
        ("هوش مصنوعی", scenario_ai),
    ]
    for name, fn in steps:
        n_before = len(FAILURES)
        t0 = time.time()
        try:
            fn()
        except Exception:
            record("EXC", f"scenario:{name}", "استثنای خود سناریو", traceback.format_exc())
        bad = len(FAILURES) - n_before
        flag = "❌" if bad else "✅"
        print(f"{flag} {name}  ({time.time() - t0:.1f}s، {bad} مشکل)")

    print("—" * 70)
    print("پیمایش خودکار دکمه‌ها ...")
    t0 = time.time()
    n_before = len(FAILURES)
    try:
        scenario_callback_walk()
    except Exception:
        record("EXC", "scenario:walk", "استثنای خود سناریو", traceback.format_exc())
    bad = len(FAILURES) - n_before
    print(f"{'❌' if bad else '✅'} پیمایش دکمه‌ها ({time.time() - t0:.1f}s، {bad} مشکل)")

    # استثناهای نخ‌های پس‌زمینه
    for tb in THREAD_ERRORS:
        record("THREAD", "background", "استثنا در نخ پس‌زمینه", tb)

    # ---------------------------------------------------------------
    print("=" * 70)
    kinds = {}
    for f in FAILURES:
        kinds.setdefault(f.kind, []).append(f)

    if not FAILURES:
        print("🎉 هیچ خطایی پیدا نشد")
    else:
        print(f"جمع کل مشکلات: {len(FAILURES)}")
        for k, items in sorted(kinds.items(), key=lambda x: -len(x[1])):
            print(f"  {k}: {len(items)}")
        print("=" * 70)
        # گروه‌بندی تکراری‌ها
        seen = {}
        for f in FAILURES:
            sig = (f.kind, f.detail[:160])
            seen.setdefault(sig, []).append(f)
        for (kind, detail), items in seen.items():
            print(f"\n[{kind}] ×{len(items)}  (مثال: {items[0].where})")
            print(f"   {detail}")
            if VERBOSE and items[0].tb:
                print(items[0].tb)

    # ذخیره گزارش کامل
    report = os.path.join(ROOT, "tests", "last_run.json")
    with open(report, "w", encoding="utf-8") as fh:
        json.dump(
            {
                "failures": [
                    {"kind": f.kind, "where": f.where, "detail": f.detail, "tb": f.tb}
                    for f in FAILURES
                ],
                "sent": len(FAKE.sent),
                "edited": len(FAKE.edited),
                "calls": len(FAKE.calls),
            },
            fh, ensure_ascii=False, indent=2)
    print(f"\nگزارش کامل: {report}")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main_run())
