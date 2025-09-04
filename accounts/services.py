import time
from django.conf import settings
from django.core.cache import cache
from django.contrib.auth.models import User
from django.db import transaction
from twilio.rest import Client
from .utils import normalize_phone
from .models import Profile  # استيراد مرة واحدة يكفي

# ==============================
# إعدادات OTP وتوابع مساعدة
# ==============================

OTP_CACHE_PREFIX = "otp:"
PWD_CACHE_PREFIX = "pwd:"  # مفاتيح الكاش لاسترجاع كلمة المرور


def _otp_key(phone: str) -> str:
    return f"{OTP_CACHE_PREFIX}{phone}"


def _pwd_key(phone: str) -> str:
    return f"{PWD_CACHE_PREFIX}{phone}"


def _twilio_client() -> Client:
    acc = settings.TWILIO_ACCOUNT_SID
    tok = settings.TWILIO_AUTH_TOKEN
    if not (acc and tok):
        raise RuntimeError("otp_provider_unavailable")
    return Client(acc, tok)


def _twilio_send_verification(phone: str, lang: str = "ar"):
    """بدء إرسال رمز عبر Twilio Verify"""
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
    """التحقق من الرمز عند Twilio"""
    client = _twilio_client()
    svc = settings.TWILIO_VERIFY_SERVICE_SID
    res = client.verify.v2.services(svc).verification_checks.create(to=phone, code=code)
    return (res.status == "approved")


# ==============================
# تسجيل جديد
# ==============================

def start_registration(username: str, phone: str, password: str, lang: str = "ar", role: str = "client"):
    phone = normalize_phone(phone)

    # تحقق أولي
    if User.objects.filter(username=username).exists():
        return {"error": ("username_taken", "اسم المستخدم مستخدم مسبقاً")}
    if Profile.objects.filter(phone=phone).exists():
        return {"error": ("phone_already_registered", "الهاتف مسجل مسبقاً")}

    # تبريد/مهلة
    k = _otp_key(phone)
    existing = cache.get(k)
    now = int(time.time())
    cooldown = int(getattr(settings, "OTP_RESEND_COOLDOWN", 60))
    ttl = int(getattr(settings, "OTP_TTL_SECONDS", 300))

    if existing and (now - existing.get("last_sent", 0) < cooldown):
        wait_sec = cooldown - (now - existing.get("last_sent", 0))
        return {"error": ("resend_cooldown_active", f"أعيد المحاولة بعد {wait_sec} ثانية")}

    # إرسال عبر Twilio Verify
    try:
        _twilio_send_verification(phone, lang=lang)
    except Exception:
        return {"error": ("otp_provider_unavailable", "خدمة التحقق غير متاحة حالياً")}

    # تخزين بيانات مؤقتة
    cache.set(
        k,
        {
            "username": username,
            "password": password,
            "lang": lang,
            "role": role,
            "attempts": 0,
            "last_sent": now,
            "expires_at": now + ttl,
        },
        timeout=ttl,
    )
    return {"ok": {"resend_after_sec": cooldown, "expires_in_sec": ttl}}


def verify_otp(phone: str, code: str):
    phone = normalize_phone(phone)
    k = _otp_key(phone)
    data = cache.get(k)
    now = int(time.time())
    max_attempts = int(getattr(settings, "OTP_MAX_ATTEMPTS", 5))

    if not data:
        return {"error": ("no_pending_verification", "لا يوجد تحقق جارٍ لهذا الهاتف")}
    if now > data["expires_at"]:
        cache.delete(k)
        return {"error": ("expired_code", "انتهت صلاحية الرمز")}
    if data["attempts"] >= max_attempts:
        cache.delete(k)
        return {"error": ("attempts_exceeded", "تم تجاوز عدد المحاولات")}

    # زيادة العدّاد
    data["attempts"] += 1
    cache.set(k, data, timeout=max(1, data["expires_at"] - now))

    # تحقق الرمز عند Twilio
    try:
        ok = _twilio_check_code(phone, code)
    except Exception:
        return {"error": ("otp_provider_unavailable", "تعذّر التحقق الآن")}
    if not ok:
        return {"error": ("invalid_code", "الرمز غير صحيح")}

    # نجاح: إنشاء المستخدم وتفعيل الهاتف
    # نجاح: إنشاء المستخدم وتفعيل الهاتف
    with transaction.atomic():
        user = User.objects.create_user(username=data["username"], password=data["password"])
        role = data.get("role", "client")
        Profile.objects.create(
            user=user,
            phone=phone,
            phone_verified=True,
            role=role,
            onboarding_completed=(role == "client"),  # ✅ العميل مكتمِل، العامل غير مكتمِل
        )


    cache.delete(k)
    return {"ok": {"message": "تم التحقق وإنشاء الحساب بنجاح"}}


# ==============================
# استرجاع كلمة المرور
# ==============================

def start_password_reset(phone: str, lang: str = "ar"):
    phone = normalize_phone(phone)

    try:
        profile = Profile.objects.get(phone=phone)
        user = profile.user
    except Profile.DoesNotExist:
        return {"error": ("user_not_found", "لا يوجد مستخدم بهذا الهاتف")}

    k = _pwd_key(phone)
    now = int(time.time())
    existing = cache.get(k)
    cooldown = int(getattr(settings, "OTP_RESEND_COOLDOWN", 60))
    ttl = int(getattr(settings, "OTP_TTL_SECONDS", 300))

    if existing and (now - existing.get("last_sent", 0) < cooldown):
        wait_sec = cooldown - (now - existing.get("last_sent", 0))
        return {"error": ("resend_cooldown_active", f"أعد المحاولة بعد {wait_sec} ثانية")}

    try:
        _twilio_send_verification(phone, lang=lang)
    except Exception:
        return {"error": ("otp_provider_unavailable", "تعذر إرسال رمز الاسترجاع حالياً")}

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
    phone = normalize_phone(phone)
    k = _pwd_key(phone)
    data = cache.get(k)
    now = int(time.time())
    max_attempts = int(getattr(settings, "OTP_MAX_ATTEMPTS", 5))

    if data:
        if now > data.get("expires_at", now):
            cache.delete(k)
            return {"error": ("expired_code", "انتهت صلاحية الرمز")}
        if data.get("attempts", 0) >= max_attempts:
            cache.delete(k)
            return {"error": ("attempts_exceeded", "تم تجاوز عدد المحاولات")}
        data["attempts"] = data.get("attempts", 0) + 1
        cache.set(k, data, timeout=max(1, data["expires_at"] - now))

    try:
        ok = _twilio_check_code(phone, code)
    except Exception:
        return {"error": ("otp_provider_unavailable", "تعذّر التحقق من الرمز الآن")}
    if not ok:
        return {"error": ("invalid_code", "الرمز غير صحيح")}

    try:
        if data and "user_id" in data:
            user = User.objects.get(id=data["user_id"])
        else:
            user = Profile.objects.get(phone=phone).user
    except (User.DoesNotExist, Profile.DoesNotExist):
        if data:
            cache.delete(k)
        return {"error": ("user_not_found", "المستخدم غير موجود")}

    user.set_password(new_password)
    user.save()

    if data:
        cache.delete(k)
    return {"ok": {"status": "password_reset", "message": "تم تعيين كلمة المرور الجديدة بنجاح"}}


# ==============================
# إعادة إرسال OTP (مشترك)
# ==============================

def _resend_common(cache_key: str, phone: str, lang: str = "ar"):
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
    except Exception:
        return {"error": ("otp_provider_unavailable", "تعذّر إرسال الرمز حالياً")}

    data["last_sent"] = now
    data["expires_at"] = now + ttl
    cache.set(cache_key, data, timeout=ttl)

    return {"ok": {"status": "otp_resent", "resend_after_sec": cooldown, "expires_in_sec": ttl}}


def resend_registration(phone: str, lang: str = "ar"):
    phone = normalize_phone(phone)
    k = _otp_key(phone)
    res = _resend_common(k, phone, lang=lang)
    if "error" in res and res["error"][0] == "not_found":
        return {"error": ("no_pending_verification", "لا يوجد تحقق تسجيل جارٍ لهذا الهاتف")}
    return res


def resend_password_reset(phone: str, lang: str = "ar"):
    phone = normalize_phone(phone)
    k = _pwd_key(phone)
    res = _resend_common(k, phone, lang=lang)
    if "error" in res and res["error"][0] == "not_found":
        return {"error": ("no_pending_reset", "لا توجد عملية استرجاع جارية لهذا الهاتف")}
    return res
