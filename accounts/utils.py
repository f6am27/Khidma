import re
import phonenumbers
from django.conf import settings

_DIGITS = re.compile(r"[^\d+]")

def _preclean(raw: str) -> str:
    """
    تنظيف أولي:
    - إزالة المسافات والرموز.
    - تحويل بادئة 00 إلى +.
    """
    if not raw:
        return raw
    s = raw.strip()
    s = _DIGITS.sub(lambda m: "" if m.group(0) != "+" else "+", s)  # نبقي على +
    if s.startswith("00"):
        s = "+" + s[2:]
    return s

def to_e164(raw: str) -> str:
    """
    يحوّل أي إدخال (محلي 8 أرقام، 00222..., 222..., +222...) إلى صيغة E.164.
    يرفع ValueError('invalid_phone_format') إن كان غير صالح.
    """
    if not raw:
        raise ValueError("invalid_phone_format")

    s = _preclean(raw)
    region = getattr(settings, "DEFAULT_REGION", "MR")

    try:
        # إن كان يبدأ بـ + نحلل مباشرة؛ وإلا نحلل باعتبار المنطقة الافتراضية (MR)
        num = phonenumbers.parse(s, None if s.startswith("+") else region)
    except phonenumbers.NumberParseException:
        raise ValueError("invalid_phone_format")

    # نتحقق من الصلاحية وفق بيانات البلد
    if not (phonenumbers.is_possible_number(num) and phonenumbers.is_valid_number(num)):
        raise ValueError("invalid_phone_format")

    return phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.E164)

def normalize_phone(phone: str) -> str:
    """
    دالة واجهة موحّدة نستخدمها في كل مكان.
    مثال:
      '32921288'         -> '+22232921288'
      '0022232921288'    -> '+22232921288'
      '+222 329 21 288'  -> '+22232921288'
    """
    return to_e164(phone)
