# -*- coding: utf-8 -*-
"""گیف ساز - آلفا (کیفیت بالا + سایز متن)"""
import os
import time
import threading
import urllib.request
import api
import storage
from storage import get, set_
from config import DATA_DIR, TOKEN

try:
    from PIL import Image, ImageDraw, ImageFont, ImageSequence
    PIL_OK = True
except ImportError:
    PIL_OK = False
    print("[gifmaker] ⚠️ Pillow نصب نیست!")


TMP_DIR = os.path.join(DATA_DIR, "gif_tmp")
os.makedirs(TMP_DIR, exist_ok=True)

FONT_OPTIONS = {
    "vazir_bold":   {"fa": "وزیر ضخیم",  "files": ["Vazirmatn-Bold.ttf", "Vazir-Bold.ttf"]},
    "vazir":        {"fa": "وزیر معمولی", "files": ["Vazirmatn-Regular.ttf", "Vazir.ttf"]},
    "iran_sans":    {"fa": "ایران‌سنس",  "files": ["IRANSansWeb_Bold.ttf", "IranSans-Bold.ttf"]},
    "noto_naskh":   {"fa": "نسخ",        "files": ["/system/fonts/NotoNaskhArabic-Bold.ttf"]},
    "droid_naskh":  {"fa": "دروید نسخ",  "files": ["/system/fonts/DroidNaskh-Bold.ttf"]},
    "dejavu":       {"fa": "پیش‌فرض",     "files": ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]},
}

COLOR_OPTIONS = {
    "white":    {"fa": "سفید",   "rgb": (255, 255, 255)},
    "black":    {"fa": "مشکی",   "rgb": (0, 0, 0)},
    "red":      {"fa": "قرمز",   "rgb": (239, 68, 68)},
    "yellow":   {"fa": "زرد",    "rgb": (250, 204, 21)},
    "green":    {"fa": "سبز",    "rgb": (34, 197, 94)},
    "blue":     {"fa": "آبی",    "rgb": (59, 130, 246)},
    "purple":   {"fa": "بنفش",   "rgb": (168, 85, 247)},
    "orange":   {"fa": "نارنجی", "rgb": (251, 146, 60)},
}

SIZE_OPTIONS = {
    "small":  {"fa": "کوچک (600)",   "px": 300},
    "medium": {"fa": "متوسط (900)",  "px": 450},
    "large":  {"fa": "بزرگ (1200)",  "px": 600},
    "hd":     {"fa": "اچ‌دی (1600)", "px": 800},
}


# ============================================================
# ری‌شِیپر داخلی فارسی
# ============================================================
_FORMS = {
    'ا': ('ﺍ','ﺍ','ﺎ','ﺎ'), 'آ': ('ﺁ','ﺁ','ﺂ','ﺂ'),
    'أ': ('ﺃ','ﺃ','ﺄ','ﺄ'), 'إ': ('ﺇ','ﺇ','ﺈ','ﺈ'),
    'ب': ('ﺏ','ﺑ','ﺒ','ﺐ'), 'پ': ('ﭖ','ﭘ','ﭙ','ﭗ'),
    'ت': ('ﺕ','ﺗ','ﺘ','ﺖ'), 'ث': ('ﺙ','ﺛ','ﺜ','ﺚ'),
    'ج': ('ﺝ','ﺟ','ﺠ','ﺞ'), 'چ': ('ﭺ','ﭼ','ﭽ','ﭻ'),
    'ح': ('ﺡ','ﺣ','ﺤ','ﺢ'), 'خ': ('ﺥ','ﺧ','ﺨ','ﺦ'),
    'د': ('ﺩ','ﺩ','ﺪ','ﺪ'), 'ذ': ('ﺫ','ﺫ','ﺬ','ﺬ'),
    'ر': ('ﺭ','ﺭ','ﺮ','ﺮ'), 'ز': ('ﺯ','ﺯ','ﺰ','ﺰ'),
    'ژ': ('ﮊ','ﮊ','ﮋ','ﮋ'), 'س': ('ﺱ','ﺳ','ﺴ','ﺲ'),
    'ش': ('ﺵ','ﺷ','ﺸ','ﺶ'), 'ص': ('ﺹ','ﺻ','ﺼ','ﺺ'),
    'ض': ('ﺽ','ﺿ','ﻀ','ﺾ'), 'ط': ('ﻁ','ﻃ','ﻄ','ﻂ'),
    'ظ': ('ﻅ','ﻇ','ﻈ','ﻆ'), 'ع': ('ﻉ','ﻋ','ﻌ','ﻊ'),
    'غ': ('ﻍ','ﻏ','ﻐ','ﻎ'), 'ف': ('ﻑ','ﻓ','ﻔ','ﻒ'),
    'ق': ('ﻕ','ﻗ','ﻘ','ﻖ'), 'ک': ('ک','ﮐ','ﮑ','ﮏ'),
    'ك': ('ﻙ','ﻛ','ﻜ','ﻚ'), 'گ': ('ﮒ','ﮔ','ﮕ','ﮓ'),
    'ل': ('ﻝ','ﻟ','ﻠ','ﻞ'), 'م': ('ﻡ','ﻣ','ﻤ','ﻢ'),
    'ن': ('ﻥ','ﻧ','ﻨ','ﻦ'), 'و': ('ﻭ','ﻭ','ﻮ','ﻮ'),
    'ه': ('ﻩ','ﻫ','ﻬ','ﻪ'), 'ة': ('ﺓ','ﺓ','ﺔ','ﺔ'),
    'ی': ('ﯼ','ﯾ','ﯿ','ﯽ'), 'ي': ('ﻱ','ﻳ','ﻴ','ﻲ'),
    'ئ': ('ﺉ','ﺋ','ﺌ','ﺊ'),
}

_CONNECTORS = set("بپتثجچحخسشصضطظعغفقکگلمنهیئةئي")
_LATIN = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")


def _reshape(text):
    if not text:
        return text
    chars = list(text)
    out = []
    for i, ch in enumerate(chars):
        if ch not in _FORMS:
            out.append(ch)
            continue
        prev = chars[i-1] if i > 0 else ''
        nxt = chars[i+1] if i + 1 < len(chars) else ''
        prev_connects = prev in _CONNECTORS
        i_connects = ch in _CONNECTORS and nxt in _FORMS
        if not prev_connects and not i_connects:
            form = _FORMS[ch][0]
        elif not prev_connects and i_connects:
            form = _FORMS[ch][1]
        elif prev_connects and i_connects:
            form = _FORMS[ch][2]
        else:
            form = _FORMS[ch][3]
        out.append(form)
    return ''.join(out)


def _to_visual(text):
    if not text:
        return text
    reshaped = _reshape(text)
    chars = list(reshaped)
    i = 0
    runs = []
    while i < len(chars):
        if chars[i] in _LATIN or chars[i] in " .:,;!?-+*/()[]{}":
            j = i
            while j < len(chars) and (chars[j] in _LATIN or chars[j] in " .:,;!?-+*/()[]{}"):
                j += 1
            runs.append((i, j, True))
            i = j
        else:
            j = i
            while j < len(chars) and not (chars[j] in _LATIN or chars[j] in " .:,;!?-+*/()[]{}"):
                j += 1
            runs.append((i, j, False))
            i = j
    result = []
    for start, end, is_latin in reversed(runs):
        segment = chars[start:end]
        if is_latin:
            result.extend(segment)
        else:
            result.extend(reversed(segment))
    return ''.join(result)


def _get_font(size, font_key="vazir_bold"):
    opt = FONT_OPTIONS.get(font_key, FONT_OPTIONS["vazir_bold"])
    for fp in opt["files"]:
        try:
            return ImageFont.truetype(fp, size)
        except Exception:
            continue
    for opt2 in FONT_OPTIONS.values():
        for fp in opt2["files"]:
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue
    try:
        return ImageFont.load_default()
    except Exception:
        return None


def kb(rows):
    return {"inline_keyboard": [r for r in rows if r]}


def btn(text, data=None):
    return {"text": text, "callback_data": data}


# ============================================================
# دانلود
# ============================================================
def _download_file(file_id, out_path):
    r = api.getFile(file_id)
    if not r or not r.get("ok"):
        print(f"[gifmaker:getFile] {r}")
        return False
    file_path = r["result"].get("file_path", "")
    if not file_path:
        return False
    urls = [
        f"https://tapi.bale.ai/file/bot{TOKEN}/{file_path}",
        f"https://tapi.bale.ai/bot{TOKEN}/{file_path}",
        f"https://tapi.bale.ai/file/{TOKEN}/{file_path}",
    ]
    for url in urls:
        try:
            urllib.request.urlretrieve(url, out_path)
            if os.path.exists(out_path) and os.path.getsize(out_path) > 100:
                return True
        except Exception as e:
            print(f"[gifmaker:dl] {url} → {e}")
            continue
    return False


def _extract_media(reply_msg):
    if not reply_msg:
        return None, None
    if reply_msg.get("photo"):
        return "photo", reply_msg["photo"][-1]["file_id"]
    if reply_msg.get("animation"):
        anim = reply_msg["animation"]
        mime = anim.get("mime_type", "")
        if "mp4" in mime or ("video" in mime and "gif" not in mime):
            return None, None
        return "animation", anim["file_id"]
    if reply_msg.get("document"):
        doc = reply_msg["document"]
        mime = doc.get("mime_type", "")
        file_name = (doc.get("file_name", "") or "").lower()
        if "gif" in mime or file_name.endswith(".gif"):
            return "animation", doc["file_id"]
    return None, None


# ============================================================
# ساخت GIF
# ============================================================
def _create_gif_from_image(img_path, out_path, text, position,
                            font_key="vazir_bold", color_key="white",
                            max_side=480, text_scale="medium"):
    try:
        img = Image.open(img_path).convert("RGB")
    except Exception as e:
        print(f"[gifmaker:open_img] {e}")
        return False

    render_side = max_side * 2

    w, h = img.size
    if w > h:
        new_w = render_side
        new_h = int(h * (render_side / w))
    else:
        new_h = render_side
        new_w = int(w * (render_side / h))

    img = img.resize((new_w, new_h), Image.LANCZOS)

    try:
        from PIL import ImageFilter
        img = img.filter(ImageFilter.UnsharpMask(radius=1, percent=80, threshold=3))
    except Exception:
        pass

    if text:
        img = _add_text(img, text, position, font_key, color_key, text_scale)

    if new_w > new_h:
        final_w = max_side
        final_h = int(new_h * (max_side / new_w))
    else:
        final_h = max_side
        final_w = int(new_w * (max_side / new_h))

    img = img.resize((final_w, final_h), Image.LANCZOS)

    try:
        img.save(out_path, format="GIF", save_all=True, duration=100, loop=0,
                 optimize=False, quality=95)
        return True
    except Exception as e:
        print(f"[gifmaker:save_img] {e}")
        return False


def _create_gif_from_gif(gif_path, out_path, text, position,
                          font_key="vazir_bold", color_key="white",
                          max_side=480, text_scale="medium"):
    try:
        gif = Image.open(gif_path)
        gif.seek(0)
    except Exception as e:
        print(f"[gifmaker:open_gif] {e}")
        return False

    render_side = max_side * 2
    frames = []

    try:
        for frame in ImageSequence.Iterator(gif):
            fr = frame.convert("RGB")
            w, h = fr.size
            if w > h:
                new_w = render_side
                new_h = int(h * (render_side / w))
            else:
                new_h = render_side
                new_w = int(w * (render_side / h))
            fr = fr.resize((new_w, new_h), Image.LANCZOS)
            if text:
                fr = _add_text(fr, text, position, font_key, color_key, text_scale)
            frames.append(fr)
            if len(frames) >= 80:
                break
    except Exception as e:
        print(f"[gifmaker:gif_frames] {e}")

    if not frames:
        return False

    duration = 80
    try:
        duration = gif.info.get("duration", 80)
        if duration < 40: duration = 40
        if duration > 200: duration = 200
    except: pass

    final_frames = []
    for fr in frames:
        w, h = fr.size
        if w > h:
            fw = max_side
            fh = int(h * (max_side / w))
        else:
            fh = max_side
            fw = int(w * (max_side / h))
        final_frames.append(fr.resize((fw, fh), Image.LANCZOS))

    try:
        final_frames[0].save(out_path, save_all=True, append_images=final_frames[1:],
                             duration=duration, loop=0, optimize=False, quality=95)
        return True
    except Exception as e:
        print(f"[gifmaker:save_gif] {e}")
        return False


def _add_text(img, text, position, font_key="vazir_bold", color_key="white", text_scale="medium"):
    img = img.copy()
    draw = ImageDraw.Draw(img)
    w, h = img.size

    shaped = _to_visual(text)

    # ✅ پایه سایز بزرگ‌تر بر اساس کوچک‌ترین ضلع
    base_size = max(32, int(min(w, h) * 0.12))

    # ✅ اختلاف واضح بین سایزها
    scale_map = {
        "small": 0.55,
        "medium": 1.0,
        "large": 1.6,
        "xlarge": 2.2,
    }
    scale = scale_map.get(text_scale, 1.0)
    font_size = int(base_size * scale)

    font = _get_font(font_size, font_key)
    if font is None:
        return img

    try:
        bbox = draw.textbbox((0, 0), shaped, font=font)
    except AttributeError:
        bbox = (0, 0, *draw.textsize(shaped, font=font))
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    # ✅ فقط اگه متن **واقعاً** بزرگ‌تر از عکس شد، کوچیکش کن
    max_allowed = int(w * 1.4)
    if tw > max_allowed:
        ratio = max_allowed / tw
        new_size = max(16, int(font_size * ratio))
        font = _get_font(new_size, font_key)
        try:
            bbox = draw.textbbox((0, 0), shaped, font=font)
        except AttributeError:
            bbox = (0, 0, *draw.textsize(shaped, font=font))
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]

    pad = int(h * 0.03)
    positions = {
        "tl": (pad, pad),
        "tc": ((w - tw) // 2, pad),
        "tr": (w - tw - pad, pad),
        "ml": (pad, (h - th) // 2),
        "mc": ((w - tw) // 2, (h - th) // 2),
        "mr": (w - tw - pad, (h - th) // 2),
        "bl": (pad, h - th - pad * 2),
        "bc": ((w - tw) // 2, h - th - pad * 2),
        "br": (w - tw - pad, h - th - pad * 2),
    }
    x, y = positions.get(position, positions["bc"])

    color_info = COLOR_OPTIONS.get(color_key, COLOR_OPTIONS["white"])
    text_rgb = color_info["rgb"]

    is_light = sum(text_rgb) > 380
    shadow_color = (0, 0, 0) if is_light else (255, 255, 255)

    shadow_offsets = [(-2,-2),(0,-2),(2,-2),(-2,0),(2,0),(-2,2),(0,2),(2,2)]
    for dx, dy in shadow_offsets:
        draw.text((x + dx, y + dy), shaped, font=font, fill=shadow_color)

    draw.text((x, y), shaped, font=font, fill=text_rgb)
    return img


# ============================================================
# آپلود
# ============================================================
def _upload_gif(chat_id, gif_path, caption=None, reply_to=None):
    data = {"chat_id": str(chat_id)}
    if caption:
        data["caption"] = caption
    if reply_to:
        data["reply_to_message_id"] = str(reply_to)
    r = api.upload_file("sendAnimation", {"animation": gif_path}, data)
    if r and r.get("ok"):
        return True
    data2 = {"chat_id": str(chat_id)}
    if caption:
        data2["caption"] = caption
    if reply_to:
        data2["reply_to_message_id"] = str(reply_to)
    r = api.upload_file("sendDocument", {"document": gif_path}, data2)
    return bool(r and r.get("ok"))


# ============================================================
# فلو
# ============================================================
def start_flow(chat_id, user_id, reply_msg, msg_id):
    if not PIL_OK:
        api.send(chat_id, "❌ متأسفانه کتابخانه Pillow نصب نیست.", reply_to=msg_id)
        return

    media_type, file_id = _extract_media(reply_msg)
    if not media_type:
        api.send(chat_id,
            "🙏 **توجه:**\n\n"
            "برای ساخت گیف، روی یه **عکس** یا **گیف** ریپلای کنید و بعد دستور `گیف` را بفرستید.",
            reply_to=msg_id)
        return

    flow = {
        "user_id": user_id,
        "stage": "choose_text",
        "media_type": media_type,
        "file_id": file_id,
        "text": "",
        "position": "bc",
        "size": "medium",
        "text_scale": "medium",
        "font": "vazir_bold",
        "color": "white",
        "ts": time.time(),
    }
    set_("gif_flows", chat_id, flow)

    rows = [
        [btn("✅ بله، متن اضافه کن", "gif:yes")],
        [btn("❌ نه، بدون متن", "gif:no")],
        [btn("🛑 لغو", "gif:cancel")],
    ]
    api.send(chat_id,
        "╔══════════════════════════╗\n"
        "║    🎬  گیـف سـاز آلـفـا    ║\n"
        "║        کیفیت بالا ✨        ║\n"
        "╚══════════════════════════╝\n\n"
        f"📎 **مدیا:** {'عکس 🖼' if media_type=='photo' else 'گیف 🎞'}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "❓ آیا می‌خواهید روی گیف **متن** اضافه شود؟\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "👇 انتخاب کنید:",
        markup=kb(rows),
        parse_mode="Markdown")


def handle_text(chat_id, user_id, raw_text, msg_id):
    flow = get("gif_flows", chat_id) or {}
    if not flow:
        return False
    if flow.get("user_id") != user_id:
        return False
    if flow.get("stage") != "wait_text":
        return False

    text = raw_text.strip()
    if not text:
        api.send(chat_id, "🙏 لطفاً یه متن بنویسید.", reply_to=msg_id)
        return True

    if len(text) > 100:
        text = text[:100]

    flow["text"] = text
    flow["stage"] = "choose_size"
    set_("gif_flows", chat_id, flow)

    _show_size_panel(chat_id, flow)
    return True


def _show_size_panel(chat_id, flow):
    rows = [
        [btn("📱 کوچک", "gif:size:small"), btn("📷 متوسط", "gif:size:medium")],
        [btn("🖥 بزرگ", "gif:size:large"), btn("🎬 اچ‌دی", "gif:size:hd")],
        [btn("🛑 لغو", "gif:cancel")],
    ]
    api.send(chat_id,
        "╔══════════════════════════╗\n"
        "║     📐  سـایـز عـکـس        ║\n"
        "╚══════════════════════════╝\n\n"
        f"📝 **متن شما:** _{flow.get('text','')}_\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📏 **سایز تصویر را انتخاب کنید:**\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📱 کوچک — سبک و سریع\n"
        "📷 متوسط — متعادل ✨\n"
        "🖥 بزرگ — کیفیت بالا\n"
        "🎬 اچ‌دی — بهترین کیفیت\n\n"
        "👇",
        markup=kb(rows),
        parse_mode="Markdown")


def _show_textsize_panel(chat_id, flow):
    rows = [
        [btn("🔹 کوچک", "gif:textsize:small"),
         btn("🔸 متوسط", "gif:textsize:medium")],
        [btn("🔶 بزرگ", "gif:textsize:large"),
         btn("💥 خیلی بزرگ", "gif:textsize:xlarge")],
        [btn("🛑 لغو", "gif:cancel")],
    ]
    api.send(chat_id,
        "╔══════════════════════════╗\n"
        "║     ✍️  سـایـز مـتـن         ║\n"
        "╚══════════════════════════╝\n\n"
        f"📝 **متن شما:** _{flow.get('text','')}_\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📏 **اندازه متن روی گیف:**\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🔹 کوچک — ظریف و شیک\n"
        "🔸 متوسط — متعادل ✨\n"
        "🔶 بزرگ — واضح\n"
        "💥 خیلی بزرگ — پررنگ\n\n"
        "👇",
        markup=kb(rows),
        parse_mode="Markdown")


def _show_position_panel(chat_id, flow):
    text = flow.get("text", "")
    rows = [
        [btn("↖ بالا چپ", "gif:pos:tl"), btn("⬆️ بالا", "gif:pos:tc"), btn("↗ بالا راست", "gif:pos:tr")],
        [btn("⬅️ چپ", "gif:pos:ml"), btn("⏺ مرکز", "gif:pos:mc"), btn("➡️ راست", "gif:pos:mr")],
        [btn("↙ پایین چپ", "gif:pos:bl"), btn("⬇️ پایین", "gif:pos:bc"), btn("↘ پایین راست", "gif:pos:br")],
        [btn("🛑 لغو", "gif:cancel")],
    ]
    size_info = SIZE_OPTIONS.get(flow.get("size", "medium"), SIZE_OPTIONS["medium"])
    ts_fa = {"small": "کوچک", "medium": "متوسط", "large": "بزرگ", "xlarge": "خیلی بزرگ"}.get(flow.get("text_scale", "medium"), "متوسط")
    api.send(chat_id,
        "╔══════════════════════════╗\n"
        "║    📍  محل قـرار گـیـری    ║\n"
        "╚══════════════════════════╝\n\n"
        f"📝 **متن:** _{text}_\n"
        f"📐 **سایز عکس:** {size_info['fa']}\n"
        f"✍️ **سایز متن:** {ts_fa}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🎯 **متن کجای گیف قرار بگیرد؟**\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "👇 یکی از موقعیت‌ها را انتخاب کنید:",
        markup=kb(rows),
        parse_mode="Markdown")


def _show_font_panel(chat_id, flow):
    rows = []
    keys = list(FONT_OPTIONS.keys())
    for i in range(0, len(keys), 2):
        row = []
        for k in keys[i:i+2]:
            row.append(btn(FONT_OPTIONS[k]["fa"], f"gif:font:{k}"))
        rows.append(row)
    rows.append([btn("🛑 لغو", "gif:cancel")])

    size_info = SIZE_OPTIONS.get(flow.get("size", "medium"), SIZE_OPTIONS["medium"])
    api.send(chat_id,
        "╔══════════════════════════╗\n"
        "║    ✍️  انـتـخـاب فـونـت    ║\n"
        "╚══════════════════════════╝\n\n"
        f"📝 **متن:** _{flow.get('text','')}_\n"
        f"📐 **سایز:** {size_info['fa']}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🎨 **فونت مورد نظر را انتخاب کنید:**\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "👇",
        markup=kb(rows),
        parse_mode="Markdown")


def _show_color_panel(chat_id, flow):
    rows = [
        [btn("⚪️ سفید", "gif:color:white"), btn("⚫️ مشکی", "gif:color:black")],
        [btn("🔴 قرمز", "gif:color:red"), btn("🟡 زرد", "gif:color:yellow")],
        [btn("🟢 سبز", "gif:color:green"), btn("🔵 آبی", "gif:color:blue")],
        [btn("🟣 بنفش", "gif:color:purple"), btn("🟠 نارنجی", "gif:color:orange")],
        [btn("🛑 لغو", "gif:cancel")],
    ]
    size_info = SIZE_OPTIONS.get(flow.get("size", "medium"), SIZE_OPTIONS["medium"])
    font_info = FONT_OPTIONS.get(flow.get("font", "vazir_bold"), {}).get("fa", "وزیر ضخیم")
    ts_fa = {"small": "کوچک", "medium": "متوسط", "large": "بزرگ", "xlarge": "خیلی بزرگ"}.get(flow.get("text_scale", "medium"), "متوسط")
    api.send(chat_id,
        "╔══════════════════════════╗\n"
        "║     🎨  انـتـخـاب رنـگ     ║\n"
        "╚══════════════════════════╝\n\n"
        f"📝 **متن:** _{flow.get('text','')}_\n"
        f"📐 **سایز عکس:** {size_info['fa']}\n"
        f"✍️ **سایز متن:** {ts_fa}\n"
        f"🔤 **فونت:** {font_info}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🎨 **رنگ متن را انتخاب کنید:**\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "👇",
        markup=kb(rows),
        parse_mode="Markdown")


def handle_callback(cb, cb_id, data, chat_id, msg_id, user):
    user_id = user["id"]
    flow = get("gif_flows", chat_id) or {}

    if data == "gif:start":
        api.answer_callback(cb_id, "🎬 روی عکس یا گیف ریپلای کنید و بزنید گیف", alert=True)
        return

    if data == "gif:cancel":
        set_("gif_flows", chat_id, {})
        try: api.delete(chat_id, msg_id)
        except: pass
        api.answer_callback(cb_id, "🛑 لغو شد")
        return

    if not flow:
        api.answer_callback(cb_id, "❌ منقضی شده. دوباره شروع کنید.", alert=True)
        return

    if flow.get("user_id") != user_id:
        api.answer_callback(cb_id, "⛔️ این پنل مخصوص شما نیست.", alert=True)
        return

    if data == "gif:yes":
        flow["stage"] = "wait_text"
        set_("gif_flows", chat_id, flow)
        try: api.delete(chat_id, msg_id)
        except: pass
        api.answer_callback(cb_id, "✅ متن را بفرستید")
        api.send(chat_id,
            "╔══════════════════════════╗\n"
            "║      📝  مـتـن شـمـا       ║\n"
            "╚══════════════════════════╝\n\n"
            "🙏 لطفاً متن مورد نظر را ارسال کنید.\n\n"
            "💡 _حداکثر ۱۰۰ کاراکتر_",
            parse_mode="Markdown")
        return

    if data == "gif:no":
        api.answer_callback(cb_id, "🎬 در حال ساخت...")
        try: api.delete(chat_id, msg_id)
        except: pass
        _build_and_send(chat_id, user_id, "", "bc", "medium", "vazir_bold", "white", "medium")
        return

    if data.startswith("gif:size:"):
        size = data.split(":")[2]
        flow["size"] = size
        flow["stage"] = "choose_textsize"
        set_("gif_flows", chat_id, flow)
        try: api.delete(chat_id, msg_id)
        except: pass
        api.answer_callback(cb_id, f"📐 {SIZE_OPTIONS.get(size,{}).get('fa','')}")
        _show_textsize_panel(chat_id, flow)
        return

    if data.startswith("gif:textsize:"):
        ts = data.split(":")[2]
        flow["text_scale"] = ts
        flow["stage"] = "choose_position"
        set_("gif_flows", chat_id, flow)
        try: api.delete(chat_id, msg_id)
        except: pass
        fa_map = {"small": "کوچک", "medium": "متوسط", "large": "بزرگ", "xlarge": "خیلی بزرگ"}
        api.answer_callback(cb_id, f"✍️ {fa_map.get(ts,'')}")
        _show_position_panel(chat_id, flow)
        return

    if data.startswith("gif:pos:"):
        pos = data.split(":")[2]
        flow["position"] = pos
        flow["stage"] = "choose_font"
        set_("gif_flows", chat_id, flow)
        try: api.delete(chat_id, msg_id)
        except: pass
        api.answer_callback(cb_id, "📍 موقعیت ثبت شد")
        _show_font_panel(chat_id, flow)
        return

    if data.startswith("gif:font:"):
        font = data.split(":")[2]
        flow["font"] = font
        flow["stage"] = "choose_color"
        set_("gif_flows", chat_id, flow)
        try: api.delete(chat_id, msg_id)
        except: pass
        api.answer_callback(cb_id, f"✍️ {FONT_OPTIONS.get(font,{}).get('fa','')}")
        _show_color_panel(chat_id, flow)
        return

    if data.startswith("gif:color:"):
        color = data.split(":")[2]
        flow["color"] = color
        text = flow.get("text", "")
        pos = flow.get("position", "bc")
        size = flow.get("size", "medium")
        font = flow.get("font", "vazir_bold")
        text_scale = flow.get("text_scale", "medium")
        api.answer_callback(cb_id, f"🎨 {COLOR_OPTIONS.get(color,{}).get('fa','')}")
        try: api.delete(chat_id, msg_id)
        except: pass
        _build_and_send(chat_id, user_id, text, pos, size, font, color, text_scale)
        return

    api.answer_callback(cb_id, "❓")


def _build_and_send(chat_id, user_id, text, position, size="medium",
                    font_key="vazir_bold", color_key="white", text_scale="medium"):
    flow = get("gif_flows", chat_id) or {}
    if not flow:
        return

    media_type = flow.get("media_type")
    file_id = flow.get("file_id")
    ts = int(time.time() * 1000)

    max_side = SIZE_OPTIONS.get(size, SIZE_OPTIONS["medium"])["px"]

    ext = ".jpg" if media_type == "photo" else ".gif"
    src_path = os.path.join(TMP_DIR, f"src_{chat_id}_{ts}{ext}")
    out_path = os.path.join(TMP_DIR, f"out_{chat_id}_{ts}.gif")

    api.send(chat_id,
        "╔══════════════════════════╗\n"
        "║    🎬  در حـال پـردازش    ║\n"
        "╚══════════════════════════╝\n\n"
        "⏳ _چند لحظه صبر کنید..._",
        parse_mode="Markdown")

    def _work():
        try:
            if not _download_file(file_id, src_path):
                api.send(chat_id, "❌ دانلود فایل با مشکل مواجه شد.")
                return

            if media_type == "photo":
                ok = _create_gif_from_image(src_path, out_path, text, position,
                                             font_key, color_key, max_side, text_scale)
            else:
                ok = _create_gif_from_gif(src_path, out_path, text, position,
                                           font_key, color_key, max_side, text_scale)

            if not ok:
                api.send(chat_id, "❌ پردازش با مشکل مواجه شد.")
                return

            caption = None
            if text:
                caption = (
                    "╔══════════════════════════╗\n"
                    "║    🎬  گـیـف شـمـا آمـاده شـد    ║\n"
                    "╚══════════════════════════╝\n\n"
                    f"📝 **متن:** _{text}_\n\n"
                    "✨ با کیفیت بالا ساخته شد"
                )

            sent = _upload_gif(chat_id, out_path, caption=caption)
            if not sent:
                api.send(chat_id, "❌ ارسال گیف با مشکل مواجه شد.")

            set_("gif_flows", chat_id, {})
        except Exception as e:
            print(f"[gifmaker:work] {e}")
            import traceback
            traceback.print_exc()
            api.send(chat_id, f"❌ خطای نامنتظره: `{e}`", parse_mode="Markdown")
        finally:
            for p in (src_path, out_path):
                try:
                    if os.path.exists(p):
                        os.remove(p)
                except: pass

    threading.Thread(target=_work, daemon=True).start()