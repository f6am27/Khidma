# users/utils.py
import re
import phonenumbers
from phonenumbers import NumberParseException
from django.conf import settings


def _preclean(raw: str) -> str:
    """
    تنظيف أولي - إزالة المسافات وتحويل 00 إلى +
    """
    if not raw:
        return raw
    s = raw.strip()
    s = re.sub(r'[^\d+]', '', s)  # إبقاء الأرقام و + فقط
    if s.startswith("00"):
        s = "+" + s[2:]
    return s


def normalize_phone(phone_str):
    """
    تطبيع رقم الهاتف - إزالة المسافات والرموز غير الضرورية
    """
    if not phone_str:
        return phone_str
    
    return _preclean(phone_str)


def to_e164(phone_str, default_region='MR'):
    """
    تحويل رقم الهاتف لصيغة E164 الدولية
    مثال: "12345678" -> "+22212345678"
    """
    if not phone_str:
        raise ValueError("invalid_phone_format")
    
    try:
        # تطبيع الرقم أولاً
        phone_clean = _preclean(phone_str)
        region = getattr(settings, "DEFAULT_REGION", default_region)
        
        # تحليل الرقم
        phone_obj = phonenumbers.parse(
            phone_clean, 
            None if phone_clean.startswith("+") else region
        )
        
        # التحقق من صحة الرقم
        if not (phonenumbers.is_possible_number(phone_obj) and 
                phonenumbers.is_valid_number(phone_obj)):
            raise ValueError("invalid_phone_format")
        
        # تحويل لصيغة E164
        return phonenumbers.format_number(
            phone_obj, 
            phonenumbers.PhoneNumberFormat.E164
        )
    
    except NumberParseException:
        raise ValueError("invalid_phone_format")


def is_valid_phone(phone_str, region='MR'):
    """
    التحقق من صحة رقم الهاتف
    """
    try:
        to_e164(phone_str, region)
        return True
    except (ValueError, NumberParseException):
        return False