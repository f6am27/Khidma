# admin_api/email_service.py
from django.core.mail import send_mail
from django.conf import settings
import random
import string
from django.core.cache import cache


def generate_otp():
    """توليد OTP من 6 أرقام"""
    return ''.join(random.choices(string.digits, k=6))


def send_password_reset_email(email, otp, language='fr'):
    """
    إرسال OTP لإعادة تعيين كلمة المرور
    """
    
    # النصوص حسب اللغة
    subjects = {
        'fr': 'Réinitialisation de mot de passe - Khidma Admin',
        'ar': 'إعادة تعيين كلمة المرور - Khidma Admin',
        'en': 'Password Reset - Khidma Admin'
    }
    
    messages = {
        'fr': f"""
Bonjour,

Vous avez demandé la réinitialisation de votre mot de passe administrateur.

Votre code de vérification est: {otp}

Ce code est valide pendant 10 minutes.

Si vous n'avez pas demandé cette réinitialisation, ignorez cet email.

Cordialement,
L'équipe Khidma
        """,
        'ar': f"""
مرحباً،

لقد طلبت إعادة تعيين كلمة مرور المسؤول الخاصة بك.

رمز التحقق الخاص بك هو: {otp}

هذا الرمز صالح لمدة 10 دقائق.

إذا لم تطلب هذه الإعادة، تجاهل هذا البريد.

مع تحياتنا،
فريق Khidma
        """,
        'en': f"""
Hello,

You have requested to reset your administrator password.

Your verification code is: {otp}

This code is valid for 10 minutes.

If you did not request this reset, please ignore this email.

Best regards,
Khidma Team
        """
    }
    
    lang = language if language in subjects else 'fr'
    
    try:
        send_mail(
            subject=subjects[lang],
            message=messages[lang],
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False


def store_otp(email, otp):
    """
    حفظ OTP في cache لمدة 10 دقائق
    """
    cache_key = f"admin_password_reset:{email}"
    cache.set(cache_key, {
        'otp': otp,
        'attempts': 0
    }, timeout=600)  # 10 دقائق


def verify_otp(email, otp):
    """
    التحقق من صحة OTP
    """
    cache_key = f"admin_password_reset:{email}"
    data = cache.get(cache_key)
    
    if not data:
        return False, "Code expiré ou invalide"
    
    # التحقق من عدد المحاولات
    if data['attempts'] >= 5:
        cache.delete(cache_key)
        return False, "Trop de tentatives. Demandez un nouveau code"
    
    # التحقق من صحة OTP
    if data['otp'] != otp:
        data['attempts'] += 1
        cache.set(cache_key, data, timeout=600)
        return False, "Code incorrect"
    
    # نجح التحقق
    return True, "Code vérifié"


def clear_otp(email):
    """
    حذف OTP بعد الاستخدام
    """
    cache_key = f"admin_password_reset:{email}"
    cache.delete(cache_key)