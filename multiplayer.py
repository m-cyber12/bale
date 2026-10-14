# -*- coding: utf-8 -*-
"""بازی‌های چندنفره + صف ناشناس پیشرفته - آلفا"""
import time
import threading
import random
import api
import storage

QUEUES = {}
BETWEEN_GAMES = {}
ANON_GAMES = {}

TRUTHS = [
    "آخرین دروغ بزرگت به کی بود و چی بود؟",
    "تا حالا خیانت کردی؟ چرا؟",
    "چند نفر رو توی زندگیت واقعاً عاشقشون بودی؟",
    "بدترین کار غیراخلاقی که توی عمرت کردی چیه؟",
    "اگه می‌تونستی یه نفر رو بدون عواقب بکشی، کی رو انتخاب می‌کردی؟",
    "آخرین بار کی گریه کردی و کی باعثش شد؟",
    "بدترین دروغی که به پدر و مادرت گفتی چی بود؟",
    "تا حالا از روی حسادت به کسی آسیب زدی؟",
    "آخرین بار کِی عاشق یه نفر شدی که نباید می‌شد؟",
    "گرون‌ترین کار اشتباهی که کردی چیه؟",
    "بدترین دروغی که به دوست صمیمیت گفتی چی بود؟",
    "چند نفر رو توی زندگیت واقعاً دوست داری؟",
    "اگه یه روز متوجه بشی بچه‌ی خودت نیست، چیکار می‌کنی؟",
    "آخرین بار کِی به یکی دروغ گفتی و بعدش پشیمون شدی؟",
    "بزرگ‌ترین رازی که توی قلبت داری چیه؟",
    "اگه به یک نفر اجازه داشتی حقیقت رو بگی، اون کی بود و چی بود؟",
    "تا حالا به کسی تهمت زدی؟",
    "بدترین کاری که توی رابطه‌ت کردی چیه؟",
    "آخرین بار کِی از یه تصمیم واقعاً پشیمون شدی؟",
    "چیزی که هیچ‌کس درباره‌ت نمی‌دونه چیه؟",
    "اگه فقط ۲۴ ساعت زنده بودی، اولین کاری که می‌کردی چی بود؟",
    "چند نفر رو توی زندگیت واقعاً بخشیدی که لیاقتشو نداشتن؟",
    "بدترین کارت نسبت به خودت چی بوده؟",
    "آخرین بار کِی با کسی بحث کردی و حق با اون بود؟",
    "اگه بتونی گذشته رو عوض کنی، کدوم کارتو پاک می‌کنی؟",
    "چند تا از دوستات پشت سرت حرف می‌زنن؟",
    "کدوم یکی از عادت‌هات رو واقعاً ازش متنفری؟",
    "آخرین باری که کسی رو ناامید کردی، کِی بود؟",
    "چقدر توی زندگیت دروغ گفتی که خودت باور کردی؟",
    "تا حالا شده از روی ترس به کسی خیانت کنی؟",
    "بزرگ‌ترین آرزوی قلبی‌ت چیه که به هیچ‌کس نگفتی؟",
    "تا حالا از روی تنهایی به کسی نزدیک شدی که علاقه‌ای نداشتی؟",
    "بدترین جملات آزاردهنده‌ای که به یه نفر گفتی چی بود؟",
    "آخرین بار کی از یه نفر متنفر بودی؟",
    "چند بار توی عمرت عاشق یه نفر شدی که دوستش نداری؟",
    "اگه راز یه نفر رو می‌دونستی که می‌تونه زندگی‌شو نابود کنه، می‌گفتی؟",
    "چیزی که ازش بیشتر از هر چیزی می‌ترسی چیه؟",
    "بدترین دروغی که به خودت گفتی چیه؟",
    "چند بار توی زندگیت به کسی حسادت واقعی کردی؟",
    "آخرین بار کِی از خودت شرمنده شدی؟",
    "چیزی که توی زندگیت واقعاً ازش پشیمونی چیه؟",
    "اگه بفهمی عشق قدیمیت دوباره تنها شده، چیکار می‌کنی؟",
    "بدترین کاری که توی مستی کردی چیه؟",
    "چند تا از اسرار زندگی‌ت رو با کسی تقسیم کردی؟",
    "آخرین بار کِی از کسی ناراحت شدی و بهش نگفتی؟",
    "چیزی که از خودت پنهون می‌کنی چیه؟",
    "اگه فقط یه سوال می‌تونستی از خدا بپرسی، چی می‌پرسیدی؟",
    "بدترین تصمیم عاطفی زندگیت چی بود؟",
    "چند بار توی زندگیت به کسی دروغ گفتی که خودت گریه کردی؟",
    "آخرین بار کِی یکی رو از زندگی‌ت حذف کردی و چرا؟",
    "چیزی که هیچ‌وقت به هیچ‌کس نگفتی چیه؟",
    "تا حالا شده به کسی تعرض کلامی کنی؟",
    "چند بار توی عمرت واقعاً احساس حماقت کردی؟",
    "بدترین رفتار جنسی که از کسی دیدی چیه؟",
    "اگه یه شب بتونی هر کاری بکنی، چی می‌کنی؟",
    "چیزی که توی رابطه‌ت واقعاً ازش ترسیدی چیه؟",
    "آخرین بار کِی از کسی واقعاً بدت اومد؟",
    "چند بار توی زندگیت عاشق یه نفر شدی که فقط فیزیکی بود؟",
    "بدترین کاری که توی مهمونی کردی چیه؟",
    "چیزی که ازش بیشتر از مرگ می‌ترسی چیه؟",
    "چند بار توی عمرت واقعاً عصبانی شدی و کنترل از دستت رفت؟",
    "آخرین بار کِی به کسی گفتی دوستت دارم و واقعاً دروغ بود؟",
    "چیزی که بیشتر از همه حرصت رو در میاره چیه؟",
    "بدترین دروغی که به رئیست گفتی چی بود؟",
    "چند بار توی زندگیت از روی ناچاری کاری کردی که نمی‌خواستی؟",
    "آخرین بار کِی از خودت راضی نبودی؟",
    "چیزی که توی زندگیت واقعاً حسرتش رو می‌خوری چیه؟",
    "تا حالا شده یه دوست رو برای پول یا موقعیت بفروشی؟",
    "چند بار توی عمرت به خودت قول دادی و شکستی؟",
    "بدترین کاری که با اعتماد کسی کردی چیه؟",
    "آخرین بار کِی از کسی متنفر بودی که هیچ دلیلی نداشت؟",
    "چیزی که توی خودت ازش شرمنده‌ای چیه؟",
    "چند بار توی زندگیت عاشق کسی شدی که دوست دختر/پسر داشت؟",
    "بدترین کارت توی اینترنت چیه؟",
    "اگه یه راز داشتی که می‌تونست یه نفر رو نابود کنه، چی می‌کردی؟",
    "چند بار توی عمرت تظاهر به دوستی کردی؟",
    "آخرین بار کِی یه فرصت بزرگ رو از دست دادی؟",
    "چیزی که توی زندگیت واقعاً ازش می‌ترسی چیه؟",
    "بدترین کارت توی یه رابطه جنسی چی بوده؟",
    "چند بار توی زندگیت واقعاً به کسی خیانت کردی؟",
    "آخرین بار کِی از تنهایی ترسیدی؟",
    "چیزی که توی خودت واقعاً بدت میاد چیه؟",
    "اگه یه شب بتونی با هر کسی بخوابی، کی رو انتخاب می‌کنی؟",
    "چند بار توی عمرت به خودت دروغ گفتی که خودت رو راضی کنی؟",
    "بدترین چیزهایی که به یه نفر گفتی و بعدش گریه کردی چی بود؟",
    "آخرین بار کِی به کسی گفتی ببخشید و واقعاً از ته دل نبود؟",
    "چیزی که توی زندگیت واقعاً ازش می‌ترسی چیه؟",
    "چند بار توی عمرت عاشق شدی و پشیمون؟",
    "بدترین چیزی که از کسی شنیدی و تو رو واقعاً نابود کرد چیه؟",
    "آخرین بار کِی به یکی اعتماد کردی و ضربه خوردی؟",
    "چیزی که توی زندگیت ازش راضی هستی چیه؟",
    "اگه یه شب بتونی یه کار خیلی بد بکنی و هیچ کس نفهمه، چی می‌کنی؟",
    "چند بار توی عمرت واقعاً به کسی حسادت کردی و کار بدی کردی؟",
    "بدترین دروغی که به بهترین دوستت گفتی چی بود؟",
    "آخرین بار کِی از یه رابطه بیرون اومدی و حال کردی؟",
    "چیزی که توی زندگیت واقعاً ازش راضی نیستی چیه؟",
    "چند بار توی عمرت واقعاً از خودت بدت اومد؟",
    "بدترین کاری که توی خوابگاه/مدرسه کردی چیه؟",
    "آخرین بار کِی به کسی گفتی دوستت دارم فقط که بخوابی باهاش؟",
    "چیزی که توی زندگیت واقعاً ازش خجالت می‌کشی چیه؟",
    "چند بار توی عمرت واقعاً از کسی متنفر شدی؟",
    "بدترین کارت نسبت به یه حیوون چیه؟",
    "آخرین بار کِی از یه کارت واقعاً افتخار کردی؟",
    "چیزی که توی خودت واقعاً دوست داری چیه؟",
    "اگه یه شب بتونی برگردی به گذشته، کدوم لحظه رو انتخاب می‌کنی؟",
    "چند بار توی عمرت واقعاً از خودت متنفر شدی؟",
    "بدترین کاری که توی خیابون کردی چیه؟",
    "آخرین بار کِی از کسی واقعاً تشکر کردی؟",
    "چیزی که توی زندگیت ازش راضی هستی چیه؟",
    "چند بار توی عمرت واقعاً عاشق یه نفر شدی که باید ولش می‌کردی؟",
    "بدترین دروغی که به همکارت گفتی چی بود؟",
    "آخرین بار کِی از یه تصمیم واقعاً پشیمون شدی؟",
    "چیزی که توی زندگیت ازش خوشحالی چیه؟",
    "چند بار توی عمرت واقعاً به یکی کمک کردی که لیاقتشو نداشت؟",
    "بدترین چیزی که توی خودت می‌بینی چیه؟",
    "آخرین بار کِی از کسی واقعاً ناامید شدی؟",
    "چیزی که توی خودت واقعاً ازش افتخار می‌کنی چیه؟",
    "چند بار توی عمرت واقعاً از یه کاری پشیمون شدی؟",
    "بدترین کاری که توی یه سفر کردی چیه؟",
    "آخرین بار کِی از یه دوست واقعاً ناامید شدی؟",
    "چیزی که توی زندگیت واقعاً دوستش داری چیه؟",
    "اگه فقط یه شب با کسی می‌تونستی بخوابی، کی رو انتخاب می‌کردی؟",
    "چند بار توی عمرت واقعاً عاشق شدی و ول شدی؟",
    "بدترین چیزی که به کسی گفتی و می‌دونی هنوز یادشه چیه؟",
    "آخرین بار کِی از یکی واقعاً دلخور شدی و بهش نگفتی؟",
    "چیزی که توی خودت ازش می‌ترسی چیه؟",
    "چند بار توی عمرت واقعاً از خودت خجالت کشیدی؟",
    "بدترین کارت توی یه رابطه جنسی چی بوده که به کسی نگفتی؟",
    "آخرین بار کِی از یه دروغ واقعاً لذت بردی؟",
    "چیزی که توی زندگیت واقعاً ازش پشیمونی چیه؟",
    "چند بار توی عمرت واقعاً از یه کارت احساس گناه کردی؟",
    "بدترین چیزی که توی خودت می‌بینی چیه که به کسی نگفتی؟",
    "آخرین بار کِی از یه تصمیم واقعاً افتخار کردی؟",
    "چیزی که توی زندگیت واقعاً ازش راضی هستی چیه؟",
    "اگه یه شب می‌تونستی یه کار غیرقانونی بکنی، چی می‌کردی؟",
    "چند بار توی عمرت واقعاً عاشق یه نفر بودی که حتی نمی‌شناختی؟",
    "بدترین کارت توی یه مهمونی چی بود که به کسی نگفتی؟",
    "آخرین بار کِی از یکی واقعاً تشکر کردی که لیاقتشو داشت؟",
    "چیزی که توی زندگیت واقعاً ازش خوشحالی چیه که به کسی نگفتی؟",
    "چند بار توی عمرت واقعاً عاشق کسی شدی که نمی‌بایست؟",
    "بدترین دروغی که به کسی گفتی و هنوز یادت هست چیه؟",
    "آخرین بار کِی از یه کارت واقعاً پشیمون شدی؟",
    "چیزی که توی خودت واقعاً ازش راضی هستی چیه؟",
    "اگه فقط یه سوال می‌تونستی از کسی بپرسی و مجبور بود راست بگه، چی می‌پرسیدی؟",
]

DARES = [
    "🎤 **یه ویس بفرست** و توش بگو از کی خوشت میاد!",
    "📸 **یه سلفی از حالت الان** بفرست (حتی اگه خسته‌ای)!",
    "🎥 **یه ویدیوی ۵ ثانیه‌ای** بفرست که داری می‌رقصی!",
    "📝 **اسم کسی که ازش خوشت میاد** رو توی گروه بنویس!",
    "🎤 **ویس** بفرست و توش آواز بخون!",
    "📸 **عکس از دستات** بفرست!",
    "🎥 **یه ویدیو** بفرست که داری مثل یه بچه گریه می‌کنی!",
    "💬 **پیام عاشقانه** برای نفر بالاییت بفرست!",
    "🎤 **ویس** بفرست و توش یه جوک بگو!",
    "📸 **یه عکس با حالت مسخره** بفرست!",
    "🎥 **یه ویدیوی رقص** بفرست!",
    "🎤 **ویس** بفرست و بگو ۱۰ بار «من عاشق خودمم»!",
    "📸 **عکس از پاهات** بفرست!",
    "🎥 **یه ویدیو** بفرست که داری آواز می‌خونی!",
    "💬 **پیام برای نفر قبلی** بفرست که چقدر خوشگله!",
    "🎤 **ویس** بفرست که ۳۰ ثانیه مثل یه ربات حرف بزنی!",
    "📸 **عکس از خودت با یه فیلتر مسخره** بفرست!",
    "🎥 **ویدیو** بفرست که ۵ بار بگی «آلفا»!",
    "🎤 **ویس** بفرست و ۱۰ بار بگو «دوستت دارم»!",
    "📸 **عکس از یخچالت** بفرست!",
    "💬 **پیام** بفرست که خودت رو معرفی کنی مثل یه سلبریتی!",
    "🎥 **ویدیو** بفرست که با یه لهجه غلیظ حرف بزنی!",
    "🎤 **ویس** بفرست و یه داستان کوتاه تعریف کن!",
    "📸 **عکس از کفشات** بفرست!",
    "🎥 **ویدیو** بفرست که ۱۰ ثانیه روی یه پا وایستی!",
    "🎤 **ویس** بفرست که ۲۰ ثانیه بلند بخندی!",
    "💬 **پیام** برای نفر بعدی بنویس که چقدر خنده‌داره!",
    "📸 **عکس از پنجره اتاقت** بفرست!",
    "🎥 **ویدیو** بفرست که مثل یه گربه میو کنی!",
    "🎤 **ویس** بفرست و ۵ تا اسم تصادفی بگو!",
    "💬 **پیام** با حروف بزرگ بنویس!",
    "📸 **عکس از دفترت یا کتابت** بفرست!",
    "🎥 **ویدیو** بفرست که ۵ بار بگی «باحال»!",
    "🎤 **ویس** بفرست و ۱۰ تا ایموجی رو با صدا بگو!",
    "💬 **پیام** بفرست که شامل ۵ تا ایموجی مختلف باشه!",
    "📸 **عکس از میزت** بفرست!",
    "🎥 **ویدیو** بفرست که مثل یه بچه کوچیک حرف بزنی!",
    "🎤 **ویس** بفرست و ۵ تا تعریف از نفر بالایی بکن!",
    "💬 **پیام** بفرست که با «آلفا» تموم بشه!",
    "📸 **عکس از غذات یا نوشیدنی‌ت** بفرست!",
    "🎥 **ویدیو** بفرست که ۵ ثانیه با دستات شکل قلب درست کنی!",
    "🎤 **ویس** بفرست و اسم ۱۰ تا میوه بگو!",
    "💬 **پیام** بفرست که شامل یه شعر باشه!",
    "📸 **عکس از لباست** بفرست!",
    "🎥 **ویدیو** بفرست که داری مثل یه خرگوش می‌پری!",
    "🎤 **ویس** بفرست و ۳ بار بگو «من دیوونه‌ام»!",
    "💬 **پیام** بفرست که شامل ۳ تا کلمه انگلیسی باشه!",
    "📸 **عکس از ساعتت یا موبایلت** بفرست!",
    "🎥 **ویدیو** بفرست که ۱۰ ثانیه مثل یه پیرمرد حرف بزنی!",
    "🎤 **ویس** بفرست و یه جمله رو با ۳ لهجه بگو!",
    "💬 **پیام** برای نفر بعدی بفرست که فقط ایموجی باشه!",
    "📸 **عکس از کمد لباست** بفرست!",
    "🎥 **ویدیو** بفرست که داری یه کار احمقانه می‌کنی!",
    "🎤 **ویس** بفرست و اسم ۳ تا از دوستات رو بگو!",
    "💬 **پیام** بفرست که شامل یه سوال باشه!",
    "📸 **عکس از کیف یا کوله‌ات** بفرست!",
    "🎥 **ویدیو** بفرست که داری مثل یه ربات می‌رقصی!",
    "🎤 **ویس** بفرست و از نفر بالایی تعریف کن!",
    "💬 **پیام** بفرست که با حرف «الف» شروع بشه!",
    "📸 **عکس از دست و پات با هم** بفرست!",
    "🎥 **ویدیو** بفرست که داری یه آهنگ زمزمه می‌کنی!",
    "🎤 **ویس** بفرست و ۱۰ بار بگو «به من چه»!",
    "💬 **پیام** بفرست که یه آرزو توش باشه!",
    "📸 **عکس از پشت سرت (با کمک یکی)** بفرست!",
    "🎥 **ویدیو** بفرست که ۵ ثانیه داری می‌خندی!",
    "🎤 **ویس** بفرست و از یکی بد بگو (شوخی)!",
    "💬 **پیام** بفرست که یه نصیحت توش باشه!",
    "📸 **عکس از رنگ موهای یه نفر از گروه** بفرست!",
    "🎥 **ویدیو** بفرست که ۱۰ ثانیه مثل یه شیر غرش کنی!",
    "🎤 **ویس** بفرست و ۵ تا اسم پسرونه بگو!",
    "💬 **پیام** بفرست که یه خاطره توش باشه!",
    "📸 **عکس از نوشیدنی که داری می‌خوری** بفرست!",
    "🎥 **ویدیو** بفرست که داری مثل یه گربه راه می‌ری!",
    "🎤 **ویس** بفرست و ۵ تا اسم دخترونه بگو!",
    "💬 **پیام** بفرست که یه جوک توش باشه!",
    "📸 **عکس از دسکتاپت (کامپیوتر یا موبایل)** بفرست!",
    "🎥 **ویدیو** بفرست که داری مثل یه ابرقهرمان پرواز می‌کنی!",
    "🎤 **ویس** بفرست و ۵ بار «آلفا قویه» بگو!",
    "💬 **پیام** بفرست که یه بیت شعر توش باشه!",
    "📸 **عکس از خودت با یه اکسسوری مسخره** بفرست!",
    "🎥 **ویدیو** بفرست که داری مثل یه پنگوئن راه می‌ری!",
    "🎤 **ویس** بفرست و ۵ تا اسم حیوون بگو!",
    "💬 **پیام** بفرست که یه معذرت‌خواهی توش باشه!",
    "📸 **عکس از پشت بوم خونه (اگه می‌تونی)** بفرست!",
    "🎥 **ویدیو** بفرست که ۱۰ ثانیه مثل یه بز می‌کنی!",
    "🎤 **ویس** بفرست و اسم نفر بعدی رو ۵ بار بگو!",
    "💬 **پیام** بفرست که یه تبریک توش باشه!",
    "📸 **عکس از یه چیز قرمز اطرافت** بفرست!",
    "🎥 **ویدیو** بفرست که ۵ ثانیه دست می‌زنی!",
    "🎤 **ویس** بفرست و ۳ بار بگو «من باهوشم»!",
    "💬 **پیام** بفرست که یه سوال از گروه بپرسی!",
    "📸 **عکس از یه چیز آبی اطرافت** بفرست!",
    "🎥 **ویدیو** بفرست که داری مثل یه ماهی شنا می‌کنی!",
    "🎤 **ویس** بفرست و اسم ۵ تا از اعضای گروه رو بگو!",
    "💬 **پیام** بفرست که یه آرزو برای گروه توش باشه!",
    "📸 **عکس از یه چیز سبز اطرافت** بفرست!",
    "🎥 **ویدیو** بفرست که ۱۰ ثانیه با یه زبان دیگه حرف بزنی!",
    "🎤 **ویس** بفرست و ۳ بار بگو «فدای شما»!",
    "💬 **پیام** بفرست که یه خاطره از این گروه توش باشه!",
    "📸 **عکس از یه چیز زرد اطرافت** بفرست!",
    "🎥 **ویدیو** بفرست که داری مثل یه مار می‌خزی!",
    "🎤 **ویس** بفرست و ۵ بار بگو «اینم بگذره»!",
    "💬 **پیام** بفرست که یه تعریف از خودت توش باشه!",
    "📸 **عکس از یه چیز بنفش اطرافت** بفرست!",
    "🎥 **ویدیو** بفرست که داری مثل یه زرافه راه می‌ری!",
    "🎤 **ویس** بفرست و ۵ بار بگو «چه خبر»!",
    "💬 **پیام** بفرست که یه خنده توش باشه (هاهاها)!",
    "📸 **عکس از یه چیز صورتی اطرافت** بفرست!",
    "🎥 **ویدیو** بفرست که داری مثل یه اسب شیهه می‌کشی!",
    "🎤 **ویس** بفرست و ۵ بار بگو «جدی می‌گم»!",
    "💬 **پیام** بفرست که یه تشکر توش باشه!",
    "📸 **عکس از یه چیز نارنجی اطرافت** بفرست!",
    "🎥 **ویدیو** بفرست که داری مثل یه خرس راه می‌ری!",
    "🎤 **ویس** بفرست و ۵ بار بگو «آلفا یه رباته»!",
    "💬 **پیام** بفرست که یه شوخی توش باشه!",
    "📸 **عکس از یه چیز سفید اطرافت** بفرست!",
    "🎥 **ویدیو** بفرست که داری مثل یه کانگورو می‌پری!",
    "🎤 **ویس** بفرست و ۵ بار بگو «باحال بود»!",
    "💬 **پیام** بفرست که یه خبر توش باشه!",
    "📸 **عکس از یه چیز مشکی اطرافت** بفرست!",
    "🎥 **ویدیو** بفرست که داری مثل یه لاک‌پشت راه می‌ری!",
    "🎤 **ویس** بفرست و ۵ بار بگو «عالیجناب»!",
    "💬 **پیام** بفرست که یه دلخوری توش باشه!",
    "📸 **عکس از یه چیز طوسی اطرافت** بفرست!",
    "🎥 **ویدیو** بفرست که داری مثل یه فیل راه می‌ری!",
    "🎤 **ویس** بفرست و ۵ بار بگو «خب بریم»!",
    "💬 **پیام** بفرست که یه نصیحت به خودت توش باشه!",
    "📸 **عکس از یه چیز قهوه‌ای اطرافت** بفرست!",
    "🎥 **ویدیو** بفرست که داری مثل یه عقاب پرواز می‌کنی!",
    "🎤 **ویس** بفرست و ۵ بار بگو «صبر کن»!",
    "💬 **پیام** بفرست که یه شعر عاشقانه توش باشه!",
    "📸 **عکس از یه چیز طلایی اطرافت** بفرست!",
    "🎥 **ویدیو** بفرست که داری مثل یه دلفین می‌شینی!",
    "🎤 **ویس** بفرست و ۵ بار بگو «دوستت دارم»!",
    "💬 **پیام** بفرست که یه دروغ توش باشه!",
    "📸 **عکس از یه چیز نقره‌ای اطرافت** بفرست!",
    "🎥 **ویدیو** بفرست که ۱۰ ثانیه مثل یه پسر بچه حرف بزنی!",
    "🎤 **ویس** بفرست و ۵ بار بگو «نمی‌تونم»!",
    "💬 **پیام** بفرست که یه تعریف از دوستت توش باشه!",
    "📸 **عکس از یه چیز عجیب اطرافت** بفرست!",
    "🎥 **ویدیو** بفرست که ۱۰ ثانیه مثل یه پیرزن حرف بزنی!",
]

RPS_EMOJI = {"rock": "🪨", "paper": "📄", "scissor": "✂️"}
RPS_FA = {"rock": "سنگ", "paper": "کاغذ", "scissor": "قیچی"}

WORDS = ["کتاب", "دریا", "خورشید", "ستاره", "کوه", "پرنده", "گل", "برف",
         "آتش", "باد", "ماه", "ابر", "رود", "جنگل", "سنگ", "آسمان",
         "زمین", "شهر", "خانه", "دوست", "مادر", "پدر", "برادر", "خواهر"]


def kb(rows):
    return {"inline_keyboard": [r for r in rows if r]}


def btn(text, data=None):
    return {"text": text, "callback_data": data}


def game_round_label(current, total):
    return f"{current} از {total}"


# ============================================================
# انتخاب حریف از گپ
# ============================================================
def ask_pick_target(chat_id, user_id, game_type, msg_id):
    settings = storage.get("settings", chat_id) or {}
    rounds = settings.get("todd_rounds", 3) if game_type == "todd" else None

    settings["pick_target"] = {
        "user_id": user_id,
        "game_type": game_type,
        "panel_msg": msg_id,
        "rounds": rounds,
    }
    storage.set_("settings", chat_id, settings)

    extra = ""
    if game_type == "todd" and rounds:
        extra = f"\n🎲 **تعداد راند:** `{rounds}`"

    api.send(chat_id,
        "👤 **انتخاب حریف**\n"
        "━━━━━━━━━━━━━━━\n"
        "📌 روی پیام طرف مقابل **ریپلای** کن\n"
        "بعد یه پیام بفرست (هرچی، مثلاً «بریم»)"
        f"{extra}\n\n"
        "_مثال: ریپلای روی پیام علی → بفرست «بازی»_",
        parse_mode="Markdown")


def check_pick_target(chat_id, user_id, message):
    settings = storage.get("settings", chat_id) or {}
    pick = settings.get("pick_target")
    if not pick or pick.get("user_id") != user_id:
        return False

    if not message.get("reply_to_message"):
        return False

    reply_user = message["reply_to_message"]["from"]
    if reply_user.get("id") == user_id:
        api.send(chat_id, "🙏 نمی‌تونی با خودت بازی کنی!", reply_to=message["message_id"])
        return True
    if reply_user.get("is_bot"):
        api.send(chat_id, "🙏 ربات نمی‌تونه حریف باشه!", reply_to=message["message_id"])
        return True

    target_id = reply_user["id"]
    target_name = reply_user.get("first_name", "کاربر")
    game_type = pick["game_type"]
    rounds = pick.get("rounds", 3)

    settings.pop("pick_target", None)
    settings["pending_rounds"] = rounds
    storage.set_("settings", chat_id, settings)

    start_between(chat_id, game_type, user_id, target_id, target_name)
    return True


# ============================================================
# شروع بازی دو نفره
# ============================================================
def start_between(chat_id, game_type, p1_id, p2_id, p2_name):
    if game_type == "rps":
        _start_rps(chat_id, p1_id, p2_id, p2_name)
    elif game_type == "todd":
        _start_todd(chat_id, p1_id, p2_id, p2_name)
    elif game_type == "guess":
        _start_guess(chat_id, p1_id, p2_id, p2_name)
    elif game_type == "word":
        _start_word(chat_id, p1_id, p2_id, p2_name)
    elif game_type == "scramble":
        _start_scramble(chat_id, p1_id, p2_id, p2_name)
    elif game_type == "dice":
        _start_dice(chat_id, p1_id, p2_id, p2_name)
    elif game_type == "coin":
        _start_coin(chat_id, p1_id, p2_id, p2_name)


def _start_rps(chat_id, p1_id, p2_id, p2_name):
    BETWEEN_GAMES[chat_id] = {
        "type": "rps", "p1": p1_id, "p2": p2_id,
        "state": "choosing", "choices": {}, "ts": time.time(),
    }
    rows = [
        [btn("🪨 سنگ", "rpsg:rock"), btn("📄 کاغذ", "rpsg:paper"), btn("✂️ قیچی", "rpsg:scissor")],
    ]
    api.send(chat_id,
        "╔══════════════════════════╗\n"
        "║    🪨  سـنـگ کـاغـذ قـیـچـی    ║\n"
        "╚══════════════════════════╝\n\n"
        f"👤 <a href='tg://user?id={p1_id}'>بازیکن ۱</a>  ⚔️  <a href='tg://user?id={p2_id}'>{api.esc_html(p2_name)}</a>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🎯 <b>هر دو نفر یکی رو انتخاب کنید:</b>",
        markup=kb(rows), parse_mode="HTML")


def _start_todd(chat_id, p1_id, p2_id, p2_name):
    settings = storage.get("settings", chat_id) or {}
    rounds = settings.pop("pending_rounds", None) or settings.get("todd_rounds", 3)
    storage.set_("settings", chat_id, settings)

    kind = "حقیقت" if random.random() < 0.5 else "جرئت"
    q = random.choice(TRUTHS) if kind == "حقیقت" else random.choice(DARES)

    game = {
        "type": "todd",
        "p1": p1_id,
        "p2": p2_id,
        "p2_name": p2_name,
        "kind": kind,
        "question": q,
        "round": 1,
        "max_rounds": rounds,
        "scores": {str(p1_id): 0, str(p2_id): 0},
        "votes": {},
        "vote_msg_id": None,
        "grace_until": None,
        "ts": time.time(),
        "state": "playing",
        "performer": p1_id,
    }
    BETWEEN_GAMES[chat_id] = game

    rows = [
        [btn("✅ انجام داد", "todd:vote:yes"),
         btn("❌ انجام نداد", "todd:vote:no")],
    ]

    r = api.send(chat_id,
        f"╔══════════════════════════╗\n"
        f"║    🎯  جـرئـت  یـا  حـقـیـقـت    ║\n"
        f"╚══════════════════════════╝\n\n"
        f"👤 <a href='tg://user?id={p1_id}'>بازیکن ۱</a>  ⚔️  <a href='tg://user?id={p2_id}'>{api.esc_html(p2_name)}</a>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎲 <b>راند {game_round_label(1, rounds)}</b>\n"
        f"📌 قرعه: <b>{api.esc_html(kind)}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"❓ <i>{q}</i>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 <i>اگه شامل ویس، عکس یا ویدیو هست، بفرستش</i>\n\n"
        f"👇 <b>بعد از انجام، همه اعضا رأی می‌دن:</b>",
        markup=kb(rows),
        parse_mode="HTML")

    if r and r.get("ok"):
        g = BETWEEN_GAMES.get(chat_id)
        if g:
            g["vote_msg_id"] = r["result"]["message_id"]
            BETWEEN_GAMES[chat_id] = g


def _start_guess(chat_id, p1_id, p2_id, p2_name):
    target = random.randint(1, 100)
    BETWEEN_GAMES[chat_id] = {
        "type": "guess", "p1": p1_id, "p2": p2_id,
        "answer": target, "guesses": {}, "ts": time.time(),
    }
    api.send(chat_id,
        "🎯 <b>چلنج حدس عدد</b>\n"
        "━━━━━━━━━━━━━━━\n"
        f"👤 <a href='tg://user?id={p1_id}'>بازیکن ۱</a>\n"
        f"👤 <a href='tg://user?id={p2_id}'>{api.esc_html(p2_name)}</a>\n\n"
        "هر دو یه عدد بین ۱ تا ۱۰۰ حدس بزنن!\n"
        "هر کی نزدیک‌تر بود می‌بره.\n\n"
        "👇 عدد رو توی چت بنویسید:",
        parse_mode="HTML")


def _start_word(chat_id, p1_id, p2_id, p2_name):
    w = random.choice(WORDS)
    BETWEEN_GAMES[chat_id] = {
        "type": "word", "p1": p1_id, "p2": p2_id,
        "answer": w, "ts": time.time(),
    }
    api.send(chat_id,
        "💭 <b>چلنج حدس کلمه</b>\n"
        "━━━━━━━━━━━━━━━\n"
        f"👤 <a href='tg://user?id={p1_id}'>بازیکن ۱</a>\n"
        f"👤 <a href='tg://user?id={p2_id}'>{api.esc_html(p2_name)}</a>\n\n"
        f"🔤 تعداد حروف: <code>{len(w)}</code>\n"
        f"🏁 اولین کسی که درست بگه می‌بره!\n\n"
        "👇 توی چت بنویسید:",
        parse_mode="HTML")


def _start_scramble(chat_id, p1_id, p2_id, p2_name):
    w = random.choice(WORDS)
    letters = list(w)
    random.shuffle(letters)
    scrambled = " ".join(letters)
    BETWEEN_GAMES[chat_id] = {
        "type": "scramble", "p1": p1_id, "p2": p2_id,
        "answer": w, "ts": time.time(),
    }
    api.send(chat_id,
        f"🔤 <b>چلنج حروف بهم ریخته</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👤 <a href='tg://user?id={p1_id}'>بازیکن ۱</a>\n"
        f"👤 <a href='tg://user?id={p2_id}'>{api.esc_html(p2_name)}</a>\n\n"
        f"🔤 <code>{scrambled}</code>\n\n"
        "🏁 اولین کسی که درست بگه می‌بره!",
        parse_mode="HTML")


def _start_dice(chat_id, p1_id, p2_id, p2_name):
    r1 = random.randint(1, 6)
    r2 = random.randint(1, 6)
    faces = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]
    if r1 > r2:
        winner = f"<a href='tg://user?id={p1_id}'>بازیکن ۱</a>"
    elif r2 > r1:
        winner = f"<a href='tg://user?id={p2_id}'>{p2_name}</a>"
    else:
        winner = "🤝 مساوی"

    api.send(chat_id,
        f"🎲 <b>نبرد تاس</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👤 بازیکن ۱: {faces[r1-1]} ({r1})\n"
        f"👤 {api.esc_html(p2_name)}: {faces[r2-1]} ({r2})\n\n"
        f"🏆 برنده: <b>{api.esc_html(winner)}</b>",
        parse_mode="HTML")


def _start_coin(chat_id, p1_id, p2_id, p2_name):
    c1 = random.choice(["شیر 🦁", "خط ✏️"])
    c2 = "خط ✏️" if c1.startswith("شیر") else "شیر 🦁"
    api.send(chat_id,
        f"🪙 <b>شیر یا خط</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👤 بازیکن ۱: {c1}\n"
        f"👤 {api.esc_html(p2_name)}: {c2}\n\n"
        f"🏆 نتیجه: هر دو برنده!",
        parse_mode="HTML")


# ============================================================
# ورودی کاربر در بازی دو نفره
# ============================================================
def handle_message(chat_id, user_id, text, message):
    game = BETWEEN_GAMES.get(chat_id)
    if not game:
        return False
    if user_id not in (game["p1"], game["p2"]):
        return False

    gtype = game["type"]

    if gtype == "guess":
        try:
            n = int(text.strip())
            if not (1 <= n <= 100):
                return False
        except ValueError:
            return False
        game["guesses"][user_id] = n
        target = game["answer"]
        if n == target:
            p_name = "بازیکن ۱" if user_id == game["p1"] else "بازیکن ۲"
            api.send(chat_id, f"🎉 **{p_name} درست حدس زد!**\nعدد `{target}` بود.")
            BETWEEN_GAMES.pop(chat_id, None)
            return True
        if len(game["guesses"]) == 2:
            g1 = game["guesses"][game["p1"]]
            g2 = game["guesses"][game["p2"]]
            d1, d2 = abs(g1 - target), abs(g2 - target)
            if d1 < d2:
                winner = f"<a href='tg://user?id={game['p1']}'>بازیکن ۱</a>"
            elif d2 < d1:
                winner = f"<a href='tg://user?id={game['p2']}'>بازیکن ۲</a>"
            else:
                winner = "🤝 مساوی"
            api.send(chat_id,
                f"🏆 <b>نتیجه:</b>\nعدد درست: <code>{target}</code>\n"
                f"بازیکن ۱: <code>{g1}</code> | بازیکن ۲: <code>{g2}</code>\n\nبرنده: {winner}",
                parse_mode="HTML")
            BETWEEN_GAMES.pop(chat_id, None)
            return True
        api.send(chat_id, "✅ ثبت شد. منتظر حریف...")
        return True

    if gtype in ("word", "scramble"):
        if text.strip() == game["answer"]:
            p_name = "بازیکن ۱" if user_id == game["p1"] else "بازیکن ۲"
            api.send(chat_id, f"🎉 **{p_name} برنده شد!**\nکلمه «{game['answer']}» بود.")
            BETWEEN_GAMES.pop(chat_id, None)
        return True

    return False


# ============================================================
# سنگ کاغذ قیچی دو نفره
# ============================================================
def rps_choice(chat_id, user_id, choice):
    game = BETWEEN_GAMES.get(chat_id)
    if not game or game["type"] != "rps":
        return False, "❌ بازی فعال نیست!"
    if user_id not in (game["p1"], game["p2"]):
        return False, "❌ تو بازیکن نیستی!"
    if user_id in game["choices"]:
        return False, "❗️ قبلا انتخاب کردی!"

    game["choices"][user_id] = choice

    if len(game["choices"]) == 2:
        c1 = game["choices"][game["p1"]]
        c2 = game["choices"][game["p2"]]
        if c1 == c2:
            result = "🤝 مساوی!"
        elif (c1 == "rock" and c2 == "scissor") or \
             (c1 == "paper" and c2 == "rock") or \
             (c1 == "scissor" and c2 == "paper"):
            result = f"🎉 <a href='tg://user?id={game['p1']}'>بازیکن ۱</a> برد!"
        else:
            result = f"🎉 <a href='tg://user?id={game['p2']}'>بازیکن ۲</a> برد!"
        api.send(chat_id,
            f"🪨 <b>نتیجه:</b>\n"
            f"بازیکن ۱: {RPS_EMOJI[c1]}\n"
            f"بازیکن ۲: {RPS_EMOJI[c2]}\n\n{result}",
            parse_mode="HTML")
        BETWEEN_GAMES.pop(chat_id, None)
    else:
        api.send(chat_id, "✅ ثبت شد. منتظر حریف...")
    return True, "ثبت شد"


# ============================================================
# رأی‌گیری جرئت‌حقیقت (همه کاربران گروه)
# ============================================================
def handle_todd_vote(chat_id, user_id, vote):
    game = BETWEEN_GAMES.get(chat_id)
    if not game or game.get("type") != "todd":
        return False, "❌ بازی فعال نیست"
    if game.get("state") != "playing":
        return False, "❌ الان رأی‌گیری نیست"

    # 🎯 فقط کسی که نوبتشه نمی‌تونه رأی بده
    performer = game.get("performer", game["p1"])
    if user_id == performer:
        return False, "❗️ تو نوبتت هست، نمی‌تونی رأی بدی"

    # جلوگیری از رأی تکراری
    if str(user_id) in game["votes"]:
        return False, "❗️ قبلاً رأی دادی"

    game["votes"][str(user_id)] = vote
    BETWEEN_GAMES[chat_id] = game

    yes = sum(1 for v in game["votes"].values() if v == "yes")
    no = sum(1 for v in game["votes"].values() if v == "no")

    # اگه اکثریت "انجام نداد" → فرصت ۱۰ ثانیه
    if no > yes and no >= 1 and (yes + no) >= 2:
        _ask_grace(chat_id, game)
        return True, "⏳ فرصت ۱۰ ثانیه"

    return True, f"🗳 ثبت شد ({yes} ✅ / {no} ❌)"


def _ask_grace(chat_id, game):
    if game.get("grace_until"):
        return
    game["grace_until"] = time.time() + 10
    game["state"] = "grace"
    BETWEEN_GAMES[chat_id] = game

    performer = game.get("performer", game["p1"])
    performer_name = "بازیکن ۱" if performer == game["p1"] else game["p2_name"]

    rows = [
        [btn("✅ الان می‌فرستم", "todd:grace_ok"),
         btn("❌ نمی‌تونم", "todd:grace_no")],
    ]

    api.send(chat_id,
        f"╔══════════════════════════╗\n"
        f"║    ⏳  فـرصـت ۱۰ ثـانـیـه     ║\n"
        f"╚══════════════════════════╝\n\n"
        f"🙏 **اکثریت رأی دادن که انجام نشده!**\n\n"
        f"🎯 **{api.esc_md(performer_name)}** جان، وقت داری **۱۰ ثانیه** انجامش بدی\n"
        f"وگرنه **۱۵ امتیاز** ازت کم میشه 💔\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👇 **انتخاب کن:**",
        markup=kb(rows),
        parse_mode="Markdown")

    def _timeout():
        time.sleep(10)
        g = BETWEEN_GAMES.get(chat_id)
        if not g or g.get("state") != "grace":
            return
        _finish_todd_round(chat_id, refused=True)

    threading.Thread(target=_timeout, daemon=True).start()


def handle_todd_grace(chat_id, user_id, action):
    game = BETWEEN_GAMES.get(chat_id)
    if not game or game.get("state") != "grace":
        return False, "❌ الان فرصت نیست"

    performer = game.get("performer")
    if user_id != performer:
        return False, "❗️ این فرصت برای تو نیست"

    if action == "ok":
        return True, "✅ منتظریم..."
    else:
        _finish_todd_round(chat_id, refused=True, refuser_id=user_id)
        return True, "❌ رد شد"


def _finish_todd_round(chat_id, refused=False, refuser_id=None):
    game = BETWEEN_GAMES.get(chat_id)
    if not game:
        return

    panel_msg_id = game.get("vote_msg_id")
    round_num = game.get("round", 1)
    max_rounds = game.get("max_rounds", 3)
    scores = game.get("scores", {})
    p1 = game["p1"]
    p2 = game["p2"]
    p2_name = game["p2_name"]

    performer = game.get("performer", p1)
    performer_name = "بازیکن ۱" if performer == p1 else p2_name

    if refused:
        scores[str(performer)] = scores.get(str(performer), 0) - 15
        result = (
            f"❌ **{api.esc_md(performer_name)}** انجام نداد!\n"
            f"💔 **۱۵ امتیاز** کم شد"
        )
    else:
        scores[str(performer)] = scores.get(str(performer), 0) + 15
        result = (
            f"🎉 **{api.esc_md(performer_name)}** انجام داد!\n"
            f"⭐ **۱۵ امتیاز** گرفت"
        )

    game["scores"] = scores
    game["state"] = "round_end"
    BETWEEN_GAMES[chat_id] = game

    score_p1 = scores.get(str(p1), 0)
    score_p2 = scores.get(str(p2), 0)

    result_text = (
        f"╔══════════════════════════╗\n"
        f"║    📊  نـتـیـجـه رانـد       ║\n"
        f"╚══════════════════════════╝\n\n"
        f"🎲 **راند {round_num} از {max_rounds}**\n\n"
        f"{result}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🏆 **جدول امتیازات:**\n"
        f"👤 بازیکن ۱ → **{api.esc_md(score_p1)}**\n"
        f"👤 {api.esc_md(p2_name)} → **{api.esc_md(score_p2)}**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
    )

    if round_num >= max_rounds:
        if score_p1 > score_p2:
            winner = "🏆 **بازیکن ۱ برنده شد!**"
        elif score_p2 > score_p1:
            winner = f"🏆 **{api.esc_md(p2_name)} برنده شد!**"
        else:
            winner = "🤝 **مساوی!**"

        result_text += f"\n\n{winner}\n\n💐 _با تشکر از بازی شما_"
        BETWEEN_GAMES.pop(chat_id, None)

        if panel_msg_id:
            try:
                api.edit_message(chat_id, panel_msg_id, result_text, parse_mode="Markdown")
                return
            except:
                pass
        api.send(chat_id, result_text, parse_mode="Markdown")
        return

    next_kind = "حقیقت" if random.random() < 0.5 else "جرئت"
    next_q = random.choice(TRUTHS) if next_kind == "حقیقت" else random.choice(DARES)

    game = BETWEEN_GAMES.get(chat_id)
    if not game:
        return

    next_performer = p2 if performer == p1 else p1

    game["round"] = round_num + 1
    game["kind"] = next_kind
    game["question"] = next_q
    game["votes"] = {}
    game["grace_until"] = None
    game["state"] = "playing"
    game["performer"] = next_performer
    BETWEEN_GAMES[chat_id] = game

    next_performer_name = "بازیکن ۱" if next_performer == p1 else p2_name

    rows = [
        [btn("✅ انجام داد", "todd:vote:yes"),
         btn("❌ انجام نداد", "todd:vote:no")],
    ]

    next_text = result_text + (
        f"\n\n━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎲 **راند {game['round']} از {max_rounds}**\n"
        f"📌 قرعه: **{api.esc_md(next_kind)}**\n"
        f"👤 روی: **{api.esc_md(next_performer_name)}**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"❓ _{next_q}_\n\n"
        f"👇 **بعد از انجام، همه اعضا رأی می‌دن:**"
    )

    if panel_msg_id:
        try:
            api.edit_message(chat_id, panel_msg_id, next_text, markup=kb(rows), parse_mode="Markdown")
            return
        except Exception as e:
            print(f"[todd:next:edit] {e}")

    r = api.send(chat_id, next_text, markup=kb(rows), parse_mode="Markdown")
    if r and r.get("ok"):
        game = BETWEEN_GAMES.get(chat_id)
        if game:
            game["vote_msg_id"] = r["result"]["message_id"]
            BETWEEN_GAMES[chat_id] = game


# ============================================================
# صف ناشناس
# ============================================================
def add_to_queue(game_type, user_id, user_name, chat_id):
    if game_type not in QUEUES:
        QUEUES[game_type] = []
    for u in QUEUES[game_type]:
        if u["id"] == user_id:
            return "already"
    QUEUES[game_type].append({
        "id": user_id,
        "name": user_name,
        "chat_id": chat_id,
        "ts": time.time(),
    })
    if len(QUEUES[game_type]) >= 2:
        a = QUEUES[game_type].pop(0)
        b = QUEUES[game_type].pop(0)
        threading.Thread(target=_anon_match, args=(game_type, a, b), daemon=True).start()
        return "matched"
    return "queued"


def remove_from_queue(game_type, user_id):
    if game_type in QUEUES:
        QUEUES[game_type] = [u for u in QUEUES[game_type] if u["id"] != user_id]


def _anon_match(game_type, a, b):
    time.sleep(1)
    pair_id = f"{a['id']}_{b['id']}_{int(time.time())}"
    game = {
        "type": game_type,
        "players": [a["id"], b["id"]],
        "names": {str(a["id"]): a["name"], str(b["id"]): b["name"]},
        "moves": {},
        "started": time.time(),
    }

    if game_type == "todd":
        rounds = 3
        kind = "حقیقت" if random.random() < 0.5 else "جرئت"
        q = random.choice(TRUTHS) if kind == "حقیقت" else random.choice(DARES)

        game["round"] = 1
        game["max_rounds"] = rounds
        game["kind"] = kind
        game["question"] = q
        game["scores"] = {str(a["id"]): 0, str(b["id"]): 0}
        game["performer"] = a["id"]
        game["votes"] = {}
        game["state"] = "playing"
        ANON_GAMES[pair_id] = game

        for u, opp in [(a, b), (b, a)]:
            try:
                rows = [
                    [btn("✅ انجام داد", f"anon_todd:vote:{pair_id}:yes"),
                     btn("❌ انجام نداد", f"anon_todd:vote:{pair_id}:no")],
                ]
                api.send(u["id"],
                    f"🎉 **حریف پیدا شد!**\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"👤 حریف: **{api.esc_md(opp['name'])}**\n\n"
                    f"╔══════════════════════════╗\n"
                    f"║    🎯  جـرئـت  یـا  حـقـیـقـت    ║\n"
                    f"╚══════════════════════════╝\n\n"
                    f"🎲 **راند {game_round_label(1, rounds)}**\n"
                    f"📌 قرعه: **{api.esc_md(kind)}**\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"❓ _{q}_\n\n"
                    f"💡 _اگه شامل ویس، عکس یا ویدیو هست، بفرستش_\n\n"
                    f"👇 **بعد از انجام، رأی بده:**",
                    markup=kb(rows),
                    parse_mode="Markdown")
            except Exception as e:
                print(f"[anon_todd] {e}")
        return

    if game_type == "rps":
        for u, opp in [(a, b), (b, a)]:
            try:
                api.send(u["id"],
                    f"🎮 **حریف پیدا شد!**\n"
                    f"👤 حریف: **{api.esc_md(opp['name'])}**\n\n"
                    f"یکی رو انتخاب کن:",
                    markup=kb([
                        [btn("🪨 سنگ", f"anon:rps:{pair_id}:rock"),
                         btn("📄 کاغذ", f"anon:rps:{pair_id}:paper")],
                        [btn("✂️ قیچی", f"anon:rps:{pair_id}:scissor")],
                    ]),
                    parse_mode="Markdown")
            except Exception as e:
                print(f"[anon_rps] {e}")
        ANON_GAMES[pair_id] = game
        return

    if game_type == "guess":
        target = random.randint(1, 100)
        game["answer"] = target
        for u, opp in [(a, b), (b, a)]:
            try:
                api.send(u["id"],
                    f"🎯 **چلنج حدس عدد**\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"👤 حریف: **{api.esc_md(opp['name'])}**\n\n"
                    f"یه عدد بین ۱ تا ۱۰۰ حدس بزن.\n"
                    f"هر کی نزدیک‌تر بود می‌بره!\n\n"
                    f"👇 عدد رو بفرست:",
                    parse_mode="Markdown")
            except Exception as e:
                print(f"[anon_guess] {e}")
        ANON_GAMES[pair_id] = game
        return

    if game_type == "word":
        w = random.choice(WORDS)
        game["answer"] = w
        for u, opp in [(a, b), (b, a)]:
            try:
                api.send(u["id"],
                    f"💭 **چلنج حدس کلمه**\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"👤 حریف: **{api.esc_md(opp['name'])}**\n"
                    f"🔤 تعداد حروف: `{len(w)}`\n\n"
                    f"🏁 اولین کسی که درست بگه می‌بره!\n\n"
                    f"👇 کلمه رو بفرست:",
                    parse_mode="Markdown")
            except Exception as e:
                print(f"[anon_word] {e}")
        ANON_GAMES[pair_id] = game
        return

    if game_type == "scramble":
        w = random.choice(WORDS)
        letters = list(w)
        random.shuffle(letters)
        scrambled = " ".join(letters)
        game["answer"] = w
        for u, opp in [(a, b), (b, a)]:
            try:
                api.send(u["id"],
                    f"🔤 **چلنج حروف بهم ریخته**\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"👤 حریف: **{api.esc_md(opp['name'])}**\n"
                    f"🔤 `{scrambled}`\n\n"
                    f"🏁 اولین کسی که درست بگه می‌بره!",
                    parse_mode="Markdown")
            except Exception as e:
                print(f"[anon_scramble] {e}")
        ANON_GAMES[pair_id] = game
        return

    if game_type == "dice":
        for u, opp in [(a, b), (b, a)]:
            try:
                api.send(u["id"],
                    f"🎲 **نبرد تاس**\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"👤 حریف: **{api.esc_md(opp['name'])}**\n\n"
                    f"🎲 تاس بریز:",
                    markup=kb([[btn("🎲 بریز!", f"anon:dice:{pair_id}:roll")]]),
                    parse_mode="Markdown")
            except Exception as e:
                print(f"[anon_dice] {e}")
        ANON_GAMES[pair_id] = game
        return

    if game_type == "coin":
        for u, opp in [(a, b), (b, a)]:
            try:
                api.send(u["id"],
                    f"🪙 **شیر یا خط**\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"👤 حریف: **{api.esc_md(opp['name'])}**\n\n"
                    f"انتخاب کن:",
                    markup=kb([
                        [btn("🦁 شیر", f"anon:coin:{pair_id}:lion"),
                         btn("✏️ خط", f"anon:coin:{pair_id}:line")],
                    ]),
                    parse_mode="Markdown")
            except Exception as e:
                print(f"[anon_coin] {e}")
        ANON_GAMES[pair_id] = game
        return


# ============================================================
# پردازش حرکت ناشناس
# ============================================================
def handle_anon_move(user_id, pair_id, key, value):
    game = ANON_GAMES.get(pair_id)
    if not game:
        return False, "❌ بازی منقضی شده"

    if user_id not in game["players"]:
        return False, "❌ تو بازیکن نیستی!"

    if str(user_id) in game["moves"]:
        return False, "❗️ قبلا انتخاب کردی!"

    if game["type"] == "dice":
        value = random.randint(1, 6)

    game["moves"][str(user_id)] = value

    if len(game["moves"]) < 2:
        return True, "✅ ثبت شد، منتظر حریف..."

    return True, _resolve_anon(game, pair_id)


def _resolve_anon(game, pair_id):
    gtype = game["type"]
    p1, p2 = game["players"]
    m1 = game["moves"][str(p1)]
    m2 = game["moves"][str(p2)]
    n1 = game["names"][str(p1)]
    n2 = game["names"][str(p2)]

    result_text = ""
    winner_id = None

    if gtype == "rps":
        if m1 == m2:
            result_text = f"🪨 {n1}: {RPS_EMOJI[m1]}\n📄 {n2}: {RPS_EMOJI[m2]}\n\n🤝 مساوی!"
        elif (m1 == "rock" and m2 == "scissor") or \
             (m1 == "paper" and m2 == "rock") or \
             (m1 == "scissor" and m2 == "paper"):
            winner_id = p1
            result_text = f"🪨 {n1}: {RPS_EMOJI[m1]}\n📄 {n2}: {RPS_EMOJI[m2]}\n\n🎉 **{api.esc_md(n1)}** برنده شد!"
        else:
            winner_id = p2
            result_text = f"🪨 {n1}: {RPS_EMOJI[m1]}\n📄 {n2}: {RPS_EMOJI[m2]}\n\n🎉 **{api.esc_md(n2)}** برنده شد!"

    elif gtype == "guess":
        target = game["answer"]
        d1, d2 = abs(m1 - target), abs(m2 - target)
        result_text = f"🎯 عدد درست: `{target}`\n{n1}: `{m1}` | {n2}: `{m2}`\n\n"
        if d1 < d2:
            winner_id = p1
            result_text += f"🎉 **{api.esc_md(n1)}** نزدیک‌تر بود!"
        elif d2 < d1:
            winner_id = p2
            result_text += f"🎉 **{api.esc_md(n2)}** نزدیک‌تر بود!"
        else:
            result_text += "🤝 مساوی!"

    elif gtype in ("word", "scramble"):
        first_str = list(game["moves"].keys())[0]
        winner_id = int(first_str)
        wname = game["names"][first_str]
        result_text = f"🎉 **{api.esc_md(wname)}** زودتر جواب داد!\n✅ کلمه: `{game['answer']}`"

    elif gtype == "dice":
        faces = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]
        result_text = f"🎲 {n1}: {faces[m1-1]} ({m1})\n🎲 {n2}: {faces[m2-1]} ({m2})\n\n"
        if m1 > m2:
            winner_id = p1
            result_text += f"🎉 **{api.esc_md(n1)}** برنده شد!"
        elif m2 > m1:
            winner_id = p2
            result_text += f"🎉 **{api.esc_md(n2)}** برنده شد!"
        else:
            result_text += "🤝 مساوی!"

    elif gtype == "coin":
        bot_side = random.choice(["lion", "line"])
        result_text = f"🪙 ربات انتخاب کرد: {'🦁 شیر' if bot_side == 'lion' else '✏️ خط'}\n\n"
        winners = []
        if m1 == bot_side:
            winners.append(n1)
        if m2 == bot_side:
            winners.append(n2)
        if len(winners) == 2:
            result_text += "🎉 هر دو برنده!"
        elif len(winners) == 1:
            result_text += f"🎉 **{api.esc_md(winners[0])}** برنده!"
        else:
            result_text += "😐 هیچ‌کس برنده نشد!"

    for uid in game["players"]:
        try:
            api.send(uid, result_text, parse_mode="Markdown")
        except Exception as e:
            print(f"[anon_result] {e}")

    ANON_GAMES.pop(pair_id, None)
    return result_text


# ============================================================
# رأی‌گیری ناشناس todd
# ============================================================
def handle_anon_todd_vote(user_id, pair_id, vote):
    game = ANON_GAMES.get(pair_id)
    if not game or game.get("type") != "todd":
        return False, "❌ بازی فعال نیست"
    if game.get("state") != "playing":
        return False, "❌ الان رأی‌گیری نیست"

    if user_id not in game["players"]:
        return False, "❌ تو بازیکن نیستی!"

    # فقط نفر نوبت‌دار نمی‌تونه رأی بده
    performer = game.get("performer")
    if user_id == performer:
        return False, "❗️ تو نوبتت هست، نمی‌تونی رأی بدی"

    votes = game.get("votes", {})
    if str(user_id) in votes:
        return False, "❗️ قبلاً رأی دادی"

    votes[str(user_id)] = vote
    game["votes"] = votes
    ANON_GAMES[pair_id] = game

    yes = sum(1 for v in votes.values() if v == "yes")
    no = sum(1 for v in votes.values() if v == "no")

    if len(votes) >= 2:
        if no > yes:
            performer = game["performer"]
            game["state"] = "grace"
            game["grace_until"] = time.time() + 10
            ANON_GAMES[pair_id] = game

            try:
                api.send(performer,
                    "╔══════════════════════════╗\n"
                    "║    ⏳  فـرصـت ۱۰ ثـانـیـه     ║\n"
                    "╚══════════════════════════╝\n\n"
                    "🙏 **حریف گفت انجام ندادی!**\n\n"
                    "🎯 **۱۰ ثانیه** وقت داری انجامش بدی\n"
                    "وگرنه **۱۵ امتیاز** ازت کم میشه 💔",
                    parse_mode="Markdown")

                def _timeout():
                    time.sleep(10)
                    g = ANON_GAMES.get(pair_id)
                    if not g or g.get("state") != "grace":
                        return
                    _finish_anon_todd(pair_id, refused=True)

                threading.Thread(target=_timeout, daemon=True).start()
            except Exception as e:
                print(f"[anon_todd:grace] {e}")

            return True, "⏳"
        else:
            _finish_anon_todd(pair_id, refused=False)
            return True, "✅"

    return True, "🗳"


def _finish_anon_todd(pair_id, refused=False):
    game = ANON_GAMES.get(pair_id)
    if not game:
        return

    round_num = game.get("round", 1)
    max_rounds = game.get("max_rounds", 3)
    scores = game.get("scores", {})
    p1, p2 = game["players"]
    n1 = game["names"][str(p1)]
    n2 = game["names"][str(p2)]
    performer = game.get("performer", p1)
    performer_name = n1 if performer == p1 else n2

    if refused:
        scores[str(performer)] = scores.get(str(performer), 0) - 15
        result = f"❌ **{api.esc_md(performer_name)}** انجام نداد! 💔 ۱۵ امتیاز کم شد"
    else:
        scores[str(performer)] = scores.get(str(performer), 0) + 15
        result = f"🎉 **{api.esc_md(performer_name)}** انجام داد! ⭐ ۱۵ امتیاز گرفت"

    game["scores"] = scores
    s1 = scores.get(str(p1), 0)
    s2 = scores.get(str(p2), 0)

    result_text = (
        f"╔══════════════════════════╗\n"
        f"║    📊  نـتـیـجـه رانـد       ║\n"
        f"╚══════════════════════════╝\n\n"
        f"🎲 **راند {round_num} از {max_rounds}**\n\n"
        f"{result}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🏆 **جدول امتیازات:**\n"
        f"👤 {n1} → **{api.esc_md(s1)}**\n"
        f"👤 {n2} → **{api.esc_md(s2)}**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
    )

    next_performer = None

    if round_num >= max_rounds:
        if s1 > s2:
            winner = f"🏆 **{n1} برنده شد!**"
        elif s2 > s1:
            winner = f"🏆 **{n2} برنده شد!**"
        else:
            winner = "🤝 **مساوی!**"
        result_text += f"\n\n{winner}"
        ANON_GAMES.pop(pair_id, None)
    else:
        next_kind = "حقیقت" if random.random() < 0.5 else "جرئت"
        next_q = random.choice(TRUTHS) if next_kind == "حقیقت" else random.choice(DARES)
        next_performer = p2 if performer == p1 else p1
        next_performer_name = n1 if next_performer == p1 else n2

        game["round"] = round_num + 1
        game["kind"] = next_kind
        game["question"] = next_q
        game["votes"] = {}
        game["state"] = "playing"
        game["performer"] = next_performer
        ANON_GAMES[pair_id] = game

        result_text += (
            f"\n\n━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎲 **راند {game['round']} از {max_rounds}**\n"
            f"📌 قرعه: **{api.esc_md(next_kind)}**\n"
            f"👤 روی: **{api.esc_md(next_performer_name)}**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"❓ _{next_q}_\n\n"
            f"💡 _اگه شامل ویس، عکس یا ویدیو هست، بفرستش_"
        )

    rows = [
        [btn("✅ انجام داد", f"anon_todd:vote:{pair_id}:yes"),
         btn("❌ انجام نداد", f"anon_todd:vote:{pair_id}:no")],
    ]

    for uid in [p1, p2]:
        try:
            if next_performer is not None and uid == next_performer:
                api.send(uid, result_text, markup=kb(rows), parse_mode="Markdown")
            else:
                api.send(uid, result_text, parse_mode="Markdown")
        except Exception as e:
            print(f"[anon_todd:finish] {e}")


# ============================================================
# سازگاری
# ============================================================
def handle_anon_rps(user_id, choice):
    return True, "ثبت شد"


def handle_anon_callback(cb_user_id, data):
    parts = data.split(":")
    if len(parts) < 4:
        return False, "❓"

    _, gtype, pair_id, value = parts[0], parts[1], parts[2], parts[3]

    if gtype == "rps":
        if value not in ("rock", "paper", "scissor"):
            return False, "❓"
    elif gtype == "coin":
        if value not in ("lion", "line"):
            return False, "❓"
    elif gtype == "dice":
        value = "roll"

    return handle_anon_move(cb_user_id, pair_id, gtype, value)