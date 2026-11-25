"""Internationalization (i18n) module for Arabic and English support.

Provides translation functions and direction awareness for right-to-left
languages (Arabic). All UI text should go through this module.
"""

from __future__ import annotations

ARABIC = "ar"
ENGLISH = "en"

DEFAULT_LANGUAGE = ARABIC


def tr(key: str, lang: str = DEFAULT_LANGUAGE) -> str:
    """Translate a localization key to the specified language.

    Args:
        key: The localization key (English text by default).
        lang: Language code ('ar' for Arabic, 'en' for English).

    Returns:
        The translated string, or the original key if no translation is found.
    """
    if lang == ARABIC:
        return ARABIC_TRANSLATIONS.get(key, key)
    return key


def get_language() -> str:
    """Get the current language setting."""
    return DEFAULT_LANGUAGE


def set_language(lang: str) -> None:
    """Set the current language.

    Args:
        lang: Language code ('ar' for Arabic, 'en' for English).
    """
    global DEFAULT_LANGUAGE
    if lang in (ARABIC, ENGLISH):
        DEFAULT_LANGUAGE = lang


# ============================================================
# Arabic translations (all UI text translated to Arabic)
# Keys are the original English text, values are Arabic translations.
# ============================================================

ARABIC_TRANSLATIONS: dict[str, str] = {
    # App and Header
    "AirGesture": "AirGesture - التحكم بالإيماءات",
    "Emergency stop": "إيقاف طوارئ",
    "Settings folder": "مجلد الإعدادات",
    "Start control": "بدء التحكم",
    "Stop control": "إيقاف التحكم",
    "Pause": "إيقاف مؤقت",
    "Recalibrate": "إعادة المعايرة",
    # Sidebar Navigation & Page Titles
    "Dashboard": "لوحة التحكم",
    "Gestures": "الإيماءات",
    "Calibration": "المعايرة",
    "Mouse": "الفأرة",
    "Camera": "الكاميرا",
    "Appearance": "المظهر",
    "Help": "المساعدة",
    # Page Subtitles
    "Live control, status and everything you need at a glance.": "التحكم المباشر، الحالة وكل ما تحتاجه في لمحة سريعة.",
    "Live control, status and everything you need at a glance": "التحكم المباشر، الحالة وكل ما تحتاجه في لمحة سريعة.",
    "Bind comfortable hand poses to actions and tune how easily they trigger.": "ربط حركات اليد بالإجراءات وضبط حساسية وسرعة استجابتها.",
    "Bind comfortable hand poses to actions and tune how easily they trigger": "ربط حركات اليد بالإجراءات وضبط حساسية وسرعة استجابتها.",
    "Guided setup: camera, hand position, active area and cursor sensitivity.": "إعداد موجه: الكاميرا، وضع اليد، المنطقة النشطة وحساسية المؤشر.",
    "Guided setup: camera, hand position, active area and cursor sensitivity": "إعداد موجه: الكاميرا، وضع اليد، المنطقة النشطة وحساسية المؤشر.",
    "Choose your webcam, resolution and detection sensitivity.": "اختيار الكاميرا، الدقة وحساسية الكشف والتتبع.",
    "Choose your webcam, resolution and detection sensitivity": "اختيار الكاميرا، الدقة وحساسية الكشف والتتبع.",
    "Tune cursor movement, smoothing and safety guards. Test live with your own mouse.": "ضبط حركة المؤشر، التنعيم وحدود الأمان. اختبار مباشر لتحكم الفأرة.",
    "Tune cursor movement, smoothing and safety guards. Test live with your own mouse": "ضبط حركة المؤشر، التنعيم وحدود الأمان. اختبار مباشر لتحكم الفأرة.",
    "Choose dark/light/system theme, accent colour and UI scale.": "اختيار المظهر (داكن/فاتح)، لون التمييز ومقياس واجهة المستخدم.",
    "Choose dark/light/system theme, accent colour and UI scale": "اختيار المظهر (داكن/فاتح)، لون التمييز ومقياس واجهة المستخدم.",
    "Getting started, gesture reference, safety and troubleshooting.": "دليل البدء، مرجع حركات اليد، الأمان واستكشاف الأخطاء وإصلاحها.",
    "Getting started, gesture reference, safety and troubleshooting": "دليل البدء، مرجع حركات اليد، الأمان واستكشاف الأخطاء وإصلاحها.",

    # Recognizer Action Labels in UI
    "move": "تحريك المؤشر",
    "left_click": "نقرة يسار",
    "right_click": "نقرة يمين",
    "double_click": "نقرة مزدوجة",
    "drag": "تحديد وسحب العنصر",
    "scroll": "تمرير الشاشة",
    "pause": "إيقاف مؤقت",
    "none": "لا تفعل شيئاً",
    "moving": "جاري التحريك",
    "dragging": "جاري السحب",
    "scrolling": "جاري التمرير",
    "click": "نقرة",
    "idle": "خامل",
    "waiting": "في الانتظار",
    # Dashboard Cards & Controls
    "Mode": "الوضع",
    "auto - always active": "تلقائي - نشط دائماً",
    "active - hold palm to control": "تفاعلي - ابسط راحة اليد للتحكم",
    "Live preview": "المعاينة المباشرة",
    "Mirrored webcam with tracking overlay": "صورة الكاميرا المعكوسة مع خطوط التتبع المباشر",
    "Control status": "حالة التحكم",
    "Tracking": "التتبع",
    "Recognition": "التعرف",
    "Mouse control": "التحكم بالفأرة",
    "Current gesture": "الإيماءة الحالية",
    "Action": "الإجراء",
    "Confidence": "درجة الثقة",
    "Performance": "الأداء",
    "Gesture guide": "دليل الإيماءات",
    "No hand": "لا توجد يد",
    "No hand in view": "لا توجد يد في مجال الرؤية",
    "Waiting for hand": "في انتظار حركة اليد",
    "Camera streaming": "الكاميرا تبث بانتظام",
    "Camera starting": "جاري تشغيل الكاميرا",
    "Camera error": "خطأ في الكاميرا",
    "Control paused": "التحكم موقوف مؤقتاً",
    "Mouse control ON": "التحكم بالفأرة مفعّل",
    "Mouse control OFF": "التحكم بالفأرة معطّل",
    "Hand detected": "تم اكتشاف اليد",
    # Gesture Names & Labels
    "Open Palm": "راحة يد مفتوحة",
    "Fist": "قبضة مغلقة (تحديد وسحب)",
    "Point (index)": "إشارة بالسبابة",
    "Pinch": "قرصة (إبهام وسبابة)",
    "Two fingers": "إصبعان (سبابة ووسطى)",
    "Three fingers": "ثلاثة أصابع",
    "Four fingers": "أربعة أصابع",
    "No gesture": "بدون إيماءة",
    # Gesture Hints
    "Relaxed open hand - move your palm to move the cursor.": "يد مفتوحة ومسترخية - حرّك راحة يدك لتحريك المؤشر.",
    "Relaxed open hand - move your palm to move the cursor": "يد مفتوحة ومسترخية - حرّك راحة يدك لتحريك المؤشر.",
    "All fingers curled - pauses the cursor so you can rest.": "قبضة اليد مغلقة - لتحديد العنصر وسحبه مع المؤشر أثناء التحريك.",
    "All fingers curled - pauses the cursor so you can rest": "قبضة اليد مغلقة - لتحديد العنصر وسحبه مع المؤشر أثناء التحريك.",
    "All fingers curled - grab and drag the item with the cursor.": "قبضة اليد مغلقة - لتحديد العنصر وسحبه مع المؤشر أثناء التحريك.",
    "Index finger up, others relaxed. Pinch the thumb to it to click.": "رفع السبابة مع إرخاء باقي الأصابع. اقرص الإبهام معها للنقر.",
    "Index finger up, others relaxed. Pinch the thumb to it to click": "رفع السبابة مع إرخاء باقي الأصابع. اقرص الإبهام معها للنقر.",
    "Touch thumb and index finger tips together - a pinch click.": "ملامسة طرفي الإبهام والسبابة معاً - نقرة زر الفأرة الأيسر.",
    "Touch thumb and index finger tips together - a pinch click": "ملامسة طرفي الإبهام والسبابة معاً - نقرة زر الفأرة الأيسر.",
    "Index and middle up, like a relaxed peace sign.": "رفع السبابة والوسطى كعلامة النصر - نقرة زر الفأرة الأيمن.",
    "Index and middle up, like a relaxed peace sign": "رفع السبابة والوسطى كعلامة النصر - نقرة زر الفأرة الأيمن.",
    "Index, middle and ring up. Keep the pinky relaxed.": "رفع السبابة والوسطى والبنصر - نقرة مزدوجة.",
    "Index, middle and ring up. Keep the pinky relaxed": "رفع السبابة والوسطى والبنصر - نقرة مزدوجة.",
    "Four fingers up, thumb relaxed.": "رفع أربعة أصابع مع إرخاء الإبهام.",
    "Four fingers up, thumb relaxed": "رفع أربعة أصابع مع إرخاء الإبهام.",
    # Actions Labels
    "Move cursor": "تحريك المؤشر",
    "Left click": "نقرة يسار",
    "Right click": "نقرة يمين",
    "Double click": "نقرة مزدوجة",
    "Click and drag": "تحديد وسحب العنصر",
    "Scroll": "تمرير الشاشة",
    "Pause control": "إيقاف التحكم مؤقتاً",
    "Do nothing": "لا تفعل شيئاً",
    # Gestures Page
    "Gesture profile": "ملف تكوين الإيماءات",
    "Restore defaults": "استعادة الإعدادات الافتراضية",
    "Learning guide": "دليل التدريب",
    "Learn comfortable pose": "تدريب على الحركة المريحة",
    "Sensitivity": "الحساسية",
    "Activation delay": "تأخير التفعيل",
    "Cooldown": "فترة التهدئة",
    # Calibration Page
    "Step": "الخطوة",
    "Camera check": "فحص الكاميرا",
    "Hand position": "موضع اليد",
    "Active area (4 corners)": "المنطقة النشطة (4 زوايا)",
    "Active area — 4 corners": "المنطقة النشطة — 4 زوايا",
    "Cursor sensitivity": "حساسية المؤشر",
    "Practice & finish": "التدريب والإنهاء",
    "Back": "رجوع",
    "Skip step": "تخطي الخطوة",
    "Next": "التالي",
    "Finish": "إنهاء",
    "Waiting for frames…": "في انتظار إطارات الكاميرا…",
    "Camera is delivering frames.": "الكاميرا تبث الإطارات بنجاح.",
    "Hold your open palm steady in the centre of the camera view.": "ثبّت راحة يدك المفتوحة في منتصف شاشة الكاميرا.",
    "Move your hand to each corner, in order. Hold each for 0.7 s.": "حرّك يدك إلى كل زاوية بالترتيب وثبّتها لمدة 0.7 ثانية.",
    "Slide to try the cursor gain. Higher = farther cursor movement per hand move.": "اضبط حساسية حركة المؤشر. القيمة الأعلى تعني حركة أسرع وأوسع للمؤشر.",
    "Try each action with your hand, then tick the box.": "جرّب كل إجراء بيدك، ثم ضع علامة على المربع للتأكيد.",
    "Calibration complete": "اكتملت المعايرة بنجاح",
    # Mouse Settings Page
    "Cursor movement": "حركة المؤشر",
    "Live-mapped settings.": "إعدادات الربط المباشر لحركة الفأرة.",
    "Speed": "السرعة",
    "Smoothing": "التنعيم والهدوء",
    "Acceleration": "تسارع المؤشر",
    "Active area width": "عرض المنطقة النشطة",
    "Active area height": "ارتفاع المنطقة النشطة",
    "Deadzone": "المنطقة الخاملة",
    "Jump guard": "مانع القفزات المفاجئة",
    "Scroll speed": "سرعة التمرير",
    "Natural scroll": "التمرير الطبيعي",
    "Wheel moves content in the same direction as your hand.": "عجلة الفأرة تحرّك المحتوى في نفس اتجاه حركة يدك.",
    "Position mode": "نمط موضع المؤشر",
    "Absolute": "مطلق",
    "Relative": "نسبي",
    "Reset mouse settings": "إعادة تعيين إعدادات الفأرة",
    "Live test": "اختبار مباشر",
    "Marker shows where your palm maps on screen.": "النقطة توضح موضع راحة يدك الفعلي على الشاشة.",
    "» Test centre click": "» اختبار نقرة في منتصف الشاشة",
    "Test centre click": "اختبار نقرة في المنتصف",
    "WARNING: this really clicks the left mouse button at the centre of your screen.": "تنبيه: هذا الزر يقوم بالنقر الفعلي بزر الفأرة الأيسر في وسط شاشتك.",
    "WARNING: this really clicks the left mouse button at the centre of your screen": "تنبيه: هذا الزر يقوم بالنقر الفعلي بزر الفأرة الأيسر في وسط شاشتك.",
    "Screen size unavailable.": "أبعاد الشاشة غير متوفرة حالياً.",
    "Screen size unavailable": "أبعاد الشاشة غير متوفرة حالياً.",
    # Camera Settings Page
    "Device & resolution": "الجهاز والدقة",
    "Pick the camera and frame size.": "اختر كاميرا الويب ودقة وحجم الإطار.",
    "Refresh camera list": "تحديث قائمة الكاميرات",
    "Resolution": "دقة العرض",
    "FPS": "معدل الإطارات بالثانية",
    "Detection & handedness": "الكشف والتتبع واليد",
    "MediaPipe confidence and hand filter.": "درجة ثقة MediaPipe ونوع اليد المستخدمة.",
    "Detection confidence": "ثقة كشف اليد",
    "Tracking confidence": "ثقة تتبع النقاط",
    "Mirror preview": "عكس صورة المعاينة",
    "Flip the camera image horizontally (matches a mirror).": "عكس صورة الكاميرا أفقياً لمحاكاة المرآة الطبيعية.",
    "Handedness": "تفضيل اليد",
    "Any": "أي يد",
    "Left": "اليد اليسرى",
    "Right": "اليد اليمنى",
    "Apply & test": "تطبيق واختبار",
    "Changes take effect after Apply.": "يتم تطبيق التغييرات فور الضغط على زر التطبيق.",
    "Apply & restart camera": "تطبيق وإعادة تشغيل الكاميرا",
    "Test camera (1 s preview)": "اختبار الكاميرا (معاينة لثانية واحدة)",
    # Appearance Page
    "Theme": "المظهر",
    "Windows system resolves to dark.": "مظهر النظام يتوافق مع النمط الداكن.",
    "Dark": "داكن",
    "Light": "فاتح",
    "System": "تلقائي (النظام)",
    "Accent colour": "لون التمييز",
    "Pick your accent colour.": "اختر اللون الرئيسي المميز للواجهة.",
    "UI scale": "مقياس واجهة المستخدم",
    "Start-up & overlay": "بدء التشغيل وطبقات العرض",
    "Show tracking overlay in preview": "إظهار خطوط هيكل اليد في المعاينة",
    "Draws the skeleton and active-area rectangle on the camera preview.": "رسم هيكل الأصابع ومستطيل المنطقة النشطة فوق فيديو الكاميرا.",
    "Start with Windows control active": "تفعيل التحكم بالفأرة فور بدء التشغيل",
    "Mouse control turns on automatically when the app launches.": "بدء التحكم بالماوس تلقائياً بمجرد فتح البرنامج.",
    "Start minimized": "البدء كنافذة مصغّرة",
    "The window opens iconified on launch.": "فتح التطبيق مصغراً في شريط المهام عند الإقلاع.",
    "Reset appearance": "إعادة تعيين المظهر",
    # Help Page
    "Getting started": "دليل البدء السريع",
    "Your gestures": "إيماءاتك المفعلة",
    "Enabled gestures and their bound actions (from current settings):": "الإيماءات المفعلة والإجراءات المربوطة بها حالياً:",
    "Safety": "إرشادات الأمان والحماية",
    "Keyboard shortcuts": "اختصارات لوحة المفاتيح",
    "Troubleshooting": "حل المشكلات الشائعة",
    "Open settings folder (%APPDATA%\\AirGesture)": "فتح مجلد الإعدادات (%APPDATA%\\AirGesture)",
    # Learning Dialog
    "Teaching:": "تدريب حركة:",
    "Hold this pose in front of the camera, comfortably.": "ثبّت هذه الحركة بيدك أمام الكاميرا بوضع مريح.",
    "Start capture": "بدء التقاط الحركة",
    "Cancel": "إلغاء",
    "Confirm": "تأكيد وحفظ",
    "Retry": "إعادة المحاولة",
    # General & Buttons
    "Settings": "الإعدادات",
    "reset": "إعادة ضبط",
    "English": "English",
    "Arabic": "العربية",
}
