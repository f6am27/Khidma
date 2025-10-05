# users/services.py
import time
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from twilio.rest import Client
from .models import User
from .utils import normalize_phone, to_e164


# ==============================
# إعدادات OTP وتوابع مساعدة
# ==============================

OTP_CACHE_PREFIX = "otp:"
PWD_CACHE_PREFIX = "pwd:"


def _otp_key(phone: str) -> str:
    """مفتاح cache للتسجيل"""
    return f"{OTP_CACHE_PREFIX}{phone}"


def _pwd_key(phone: str) -> str:
    """مفتاح cache لاستعادة كلمة المرور"""
    return f"{PWD_CACHE_PREFIX}{phone}"


def _twilio_client() -> Client:
    """إنشاء عميل Twilio"""
    acc = settings.TWILIO_ACCOUNT_SID
    tok = settings.TWILIO_AUTH_TOKEN
    if not (acc and tok):
        raise RuntimeError("otp_provider_unavailable")
    return Client(acc, tok)


def _twilio_send_verification(phone: str, lang: str = "ar"):
    """إرسال رمز التحقق عبر Twilio Verify"""
    client = _twilio_client()
    svc = settings.TWILIO_VERIFY_SERVICE_SID
    if not svc:
        raise RuntimeError("otp_provider_unavailable")

    client.verify.v2.services(svc).verifications.create(
        to=phone,
        channel="sms",
        locale=lang if lang else None
    )


def _twilio_check_code(phone: str, code: str) -> bool:
    """التحقق من صحة الرمز عند Twilio"""
    client = _twilio_client()
    svc = settings.TWILIO_VERIFY_SERVICE_SID
    res = client.verify.v2.services(svc).verification_checks.create(
        to=phone, 
        code=code
    )
    return (res.status == "approved")


# ==============================
# تسجيل مستخدم جديد
# ==============================

# في users/services.py - حدث start_registration

def start_registration(username: str, phone: str, password: str, lang: str = "ar", role: str = "client", ip_address: str = None):
    """بدء عملية التسجيل - إرسال OTP مع Rate Limiting محسن"""
    phone = normalize_phone(phone)

    # فحص Rate Limiting العالمي أولاً
    rate_check = _check_global_rate_limit(phone, ip_address)
    if "error" in rate_check:
        return rate_check

    # باقي الفحوصات الموجودة...
    if User.objects.filter(first_name=username).exists():
        return {"error": ("username_taken", "اسم المستخدم مستخدم مسبقاً")}
    
    if User.objects.filter(phone=phone).exists():
        return {"error": ("phone_already_registered", "الهاتف مسجل مسبقاً")}

    # فحص مهلة إعادة الإرسال (الكود الموجود)
    k = _otp_key(phone)
    existing = cache.get(k)
    now = int(time.time())
    cooldown = int(getattr(settings, "OTP_RESEND_COOLDOWN", 60))
    ttl = int(getattr(settings, "OTP_TTL_SECONDS", 300))

    if existing and (now - existing.get("last_sent", 0) < cooldown):
        wait_sec = cooldown - (now - existing.get("last_sent", 0))
        return {"error": ("resend_cooldown_active", f"أعيد المحاولة بعد {wait_sec} ثانية")}

    # إرسال OTP عبر Twilio
    try:
        _twilio_send_verification(phone, lang=lang)
        
        # تسجيل المحاولة في الـ rate limiter
        _record_otp_attempt(phone, ip_address)
        
    except Exception:
        return {"error": ("otp_provider_unavailable", "خدمة التحقق غير متاحة حالياً")}

    # باقي الكود كما هو...
    cache.set(k, {
        "username": username,
        "password": password,
        "lang": lang,
        "role": role,
        "attempts": 0,
        "last_sent": now,
        "expires_at": now + ttl,
    }, timeout=ttl)
    
    return {"ok": {"resend_after_sec": cooldown, "expires_in_sec": ttl}}

def verify_otp(phone: str, code: str):
    """التحقق من رمز OTP وإنشاء المستخدم"""
    phone = normalize_phone(phone)
    k = _otp_key(phone)
    data = cache.get(k)
    now = int(time.time())
    max_attempts = int(getattr(settings, "OTP_MAX_ATTEMPTS", 5))

    # التحقق من وجود عملية تحقق جارية
    if not data:
        return {"error": ("no_pending_verification", "لا يوجد تحقق جارٍ لهذا الهاتف")}
    
    if now > data["expires_at"]:
        cache.delete(k)
        return {"error": ("expired_code", "انتهت صلاحية الرمز")}
    
    if data["attempts"] >= max_attempts:
        cache.delete(k)
        return {"error": ("attempts_exceeded", "تم تجاوز عدد المحاولات")}

    # زيادة عداد المحاولات
    data["attempts"] += 1
    cache.set(k, data, timeout=max(1, data["expires_at"] - now))

    # التحقق من الرمز عند Twilio
    try:
        ok = _twilio_check_code(phone, code)
    except Exception:
        return {"error": ("otp_provider_unavailable", "تعذّر التحقق الآن")}
    
    if not ok:
        return {"error": ("invalid_code", "الرمز غير صحيح")}

    # نجاح التحقق - إنشاء المستخدم
    with transaction.atomic():
        role = data.get("role", "client")
        username = data.get("username", "")
        
        # إنشاء User جديد باستخدام المدير المخصص
        user = User.objects.create_user(
            identifier=phone,  # phone للعميل/العامل
            password=data["password"],
            role=role,
            first_name=username,  # استخدام username كـ first_name
            is_verified=True
        )
        
        # تحديد حالة onboarding
        if role == "worker":
            # العامل يحتاج onboarding
            user.onboarding_completed = False
        else:
            # العميل مكتمل مباشرة
            user.onboarding_completed = True
        
        user.save()

    cache.delete(k)
    return {"ok": {"message": "تم التحقق وإنشاء الحساب بنجاح"}}


# ==============================
# استعادة كلمة المرور
# ==============================

def start_password_reset(phone: str, lang: str = "ar", ip_address: str = None):
    """بدء عملية استعادة كلمة المرور مع Rate Limiting محسن"""
    phone = normalize_phone(phone)

    # فحص Rate Limiting العالمي أولاً
    rate_check = _check_global_rate_limit(phone, ip_address)
    if "error" in rate_check:
        return rate_check

    # التحقق من وجود المستخدم
    try:
        user = User.objects.get(phone=phone)
    except User.DoesNotExist:
        return {"error": ("user_not_found", "لا يوجد مستخدم بهذا الهاتف")}

    # فحص مهلة إعادة الإرسال (Session-based)
    k = _pwd_key(phone)
    now = int(time.time())
    existing = cache.get(k)
    cooldown = int(getattr(settings, "OTP_RESEND_COOLDOWN", 60))
    ttl = int(getattr(settings, "OTP_TTL_SECONDS", 300))

    if existing and (now - existing.get("last_sent", 0) < cooldown):
        wait_sec = cooldown - (now - existing.get("last_sent", 0))
        return {"error": ("resend_cooldown_active", f"أعد المحاولة بعد {wait_sec} ثانية")}

    # إرسال OTP
    try:
        _twilio_send_verification(phone, lang=lang)
        
        # تسجيل المحاولة في الـ rate limiter العالمي
        _record_otp_attempt(phone, ip_address)
        
    except Exception:
        return {"error": ("otp_provider_unavailable", "تعذر إرسال رمز الاسترجاع حالياً")}

    # تخزين بيانات العملية
    cache.set(
        k,
        {
            "attempts": 0,
            "last_sent": now,
            "expires_at": now + ttl,
            "lang": lang,
            "user_id": user.id,
        },
        timeout=ttl,
    )

    return {"ok": {"status": "otp_sent", "resend_after_sec": cooldown, "expires_in_sec": ttl}}

def confirm_password_reset(phone: str, code: str, new_password: str):
    """تأكيد استعادة كلمة المرور"""
    phone = normalize_phone(phone)
    k = _pwd_key(phone)
    data = cache.get(k)
    now = int(time.time())
    max_attempts = int(getattr(settings, "OTP_MAX_ATTEMPTS", 5))

    # التحقق من صحة العملية
    if not data:
        return {"error": ("no_pending_reset", "لا توجد عملية استعادة جارية")}
    
    if now > data.get("expires_at", now):
        cache.delete(k)
        return {"error": ("expired_code", "انتهت صلاحية الرمز")}
    
    if data.get("attempts", 0) >= max_attempts:
        cache.delete(k)
        return {"error": ("attempts_exceeded", "تم تجاوز عدد المحاولات")}

    # زيادة عداد المحاولات
    data["attempts"] = data.get("attempts", 0) + 1
    cache.set(k, data, timeout=max(1, data["expires_at"] - now))

    # التحقق من الرمز
    try:
        ok = _twilio_check_code(phone, code)
    except Exception:
        return {"error": ("otp_provider_unavailable", "تعذّر التحقق من الرمز الآن")}
    
    if not ok:
        return {"error": ("invalid_code", "الرمز غير صحيح")}

    # تحديث كلمة المرور
    try:
        if data and "user_id" in data:
            user = User.objects.get(id=data["user_id"])
        else:
            user = User.objects.get(phone=phone)
    except User.DoesNotExist:
        cache.delete(k)
        return {"error": ("user_not_found", "المستخدم غير موجود")}

    user.set_password(new_password)
    user.save()

    cache.delete(k)
    return {"ok": {"status": "password_reset", "message": "تم تعيين كلمة المرور الجديدة بنجاح"}}


# ==============================
# إعادة إرسال OTP
# ==============================

def _resend_common(cache_key: str, phone: str, lang: str = "ar", ip_address: str = None):
    """وظيفة مشتركة لإعادة إرسال OTP"""
    data = cache.get(cache_key)
    if not data:
        return {"error": ("not_found", "لا توجد عملية جارية لهذا الهاتف")}

    now = int(time.time())
    cooldown = int(getattr(settings, "OTP_RESEND_COOLDOWN", 60))
    ttl = int(getattr(settings, "OTP_TTL_SECONDS", 300))

    if now - data.get("last_sent", 0) < cooldown:
        wait_sec = cooldown - (now - data["last_sent"])
        return {"error": ("resend_cooldown_active", f"أعيد المحاولة بعد {wait_sec} ثانية")}

    try:
        _twilio_send_verification(phone, lang=lang)
        
        # تسجيل المحاولة في الـ rate limiter العالمي
        if ip_address:
            _record_otp_attempt(phone, ip_address)
            
    except Exception:
        return {"error": ("otp_provider_unavailable", "تعذّر إرسال الرمز حالياً")}

    data["last_sent"] = now
    data["expires_at"] = now + ttl
    cache.set(cache_key, data, timeout=ttl)

    return {"ok": {"status": "otp_resent", "resend_after_sec": cooldown, "expires_in_sec": ttl}}
def resend_registration(phone: str, lang: str = "ar", ip_address: str = None):
    """إعادة إرسال رمز التسجيل مع Rate Limiting"""
    phone = normalize_phone(phone)
    
    # فحص Rate Limiting العالمي أولاً
    if ip_address:
        rate_check = _check_global_rate_limit(phone, ip_address)
        if "error" in rate_check:
            return rate_check
    
    k = _otp_key(phone)
    res = _resend_common(k, phone, lang=lang, ip_address=ip_address)
    
    if "error" in res and res["error"][0] == "not_found":
        return {"error": ("no_pending_verification", "لا يوجد تحقق تسجيل جارٍ لهذا الهاتف")}
    
    return res

def resend_password_reset(phone: str, lang: str = "ar", ip_address: str = None):
    """إعادة إرسال رمز استعادة كلمة المرور مع Rate Limiting"""
    phone = normalize_phone(phone)
    
    # فحص Rate Limiting العالمي أولاً
    if ip_address:
        rate_check = _check_global_rate_limit(phone, ip_address)
        if "error" in rate_check:
            return rate_check
    
    k = _pwd_key(phone)
    res = _resend_common(k, phone, lang=lang, ip_address=ip_address)
    
    if "error" in res and res["error"][0] == "not_found":
        return {"error": ("no_pending_reset", "لا توجد عملية استرجاع جارية لهذا الهاتف")}
    
    return res

# في users/services.py - أضف هذه الوظائف

def _get_global_rate_limit_key(phone, request_type='otp'):
    """مفتاح cache للـ rate limiting العالمي"""
    return f"global_rate_limit:{request_type}:{phone}"

def _get_ip_rate_limit_key(ip_address, request_type='otp'):
    """مفتاح cache لـ rate limiting حسب IP"""
    return f"ip_rate_limit:{request_type}:{ip_address}"

def _check_global_rate_limit(phone, ip_address=None):
    """فحص Rate Limiting العالمي"""
    from django.conf import settings
    from django.core.cache import cache
    import time
    
    rate_config = getattr(settings, 'GLOBAL_OTP_RATE_LIMIT', {})
    max_phone_attempts = rate_config.get('MAX_ATTEMPTS_PER_PHONE_PER_HOUR', 10)
    max_ip_attempts = rate_config.get('MAX_ATTEMPTS_PER_IP_PER_HOUR', 20)
    
    now = int(time.time())
    hour_window = 3600  # ساعة واحدة
    
    # فحص rate limit للهاتف
    phone_key = _get_global_rate_limit_key(phone)
    phone_attempts = cache.get(phone_key, [])
    
    # تنظيف المحاولات القديمة (أكثر من ساعة)
    phone_attempts = [attempt for attempt in phone_attempts if now - attempt < hour_window]
    
    if len(phone_attempts) >= max_phone_attempts:
        return {"error": ("rate_limit_phone", f"تم تجاوز حد الإرسال لهذا الرقم. حاول بعد ساعة")}
    
    # فحص rate limit للـ IP إذا متوفر
    if ip_address:
        ip_key = _get_ip_rate_limit_key(ip_address)
        ip_attempts = cache.get(ip_key, [])
        ip_attempts = [attempt for attempt in ip_attempts if now - attempt < hour_window]
        
        if len(ip_attempts) >= max_ip_attempts:
            return {"error": ("rate_limit_ip", f"تم تجاوز حد الإرسال من هذا العنوان. حاول بعد ساعة")}
    
    return {"ok": True}

def _record_otp_attempt(phone, ip_address=None):
    """تسجيل محاولة إرسال OTP"""
    from django.core.cache import cache
    import time
    
    now = int(time.time())
    
    # تسجيل محاولة للهاتف
    phone_key = _get_global_rate_limit_key(phone)
    phone_attempts = cache.get(phone_key, [])
    phone_attempts.append(now)
    cache.set(phone_key, phone_attempts, timeout=3600)  # ساعة واحدة
    
    # تسجيل محاولة للـ IP
    if ip_address:
        ip_key = _get_ip_rate_limit_key(ip_address)
        ip_attempts = cache.get(ip_key, [])
        ip_attempts.append(now)
        cache.set(ip_key, ip_attempts, timeout=3600)