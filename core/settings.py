from pathlib import Path
import os
from dotenv import load_dotenv

# المسار الأساسي للمشروع
BASE_DIR = Path(__file__).resolve().parent.parent

# تحميل متغيرات البيئة من .env
load_dotenv(BASE_DIR / ".env")

# مفاتيح وأساسيات
SECRET_KEY = os.getenv("SECRET_KEY", "CHANGE_ME_IN_ENV")
DEBUG = os.getenv("DEBUG", "True") == "True"


DEFAULT_REGION = os.getenv('DEFAULT_REGION', 'MR')
DEFAULT_COUNTRY_DIAL_CODE = os.getenv('DEFAULT_COUNTRY_DIAL_CODE', '+222')

# تفكيك ALLOWED_HOSTS من قائمة مفصولة بفواصل
_allowed = os.getenv("ALLOWED_HOSTS", "")
ALLOWED_HOSTS = [h.strip() for h in _allowed.split(",") if h.strip()]

# التطبيقات
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'rest_framework',
    'corsheaders',

    'accounts',
]

# الوسطاء (ضع corsheaders مبكرًا)
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# قاعدة البيانات (SQLite مبدئيًا)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# التحقق من كلمات المرور
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# اللغة والمنطقة الزمنية من env مع قيم افتراضية
LANGUAGE_CODE = os.getenv('DEFAULT_LANG', 'en-us')
TIME_ZONE = os.getenv('TIME_ZONE', 'UTC')
USE_I18N = True
USE_TZ = True

# الملفات الثابتة
STATIC_URL = 'static/'

# نوع المفتاح الافتراضي
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# DRF + JWT
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
}

# CORS للتطوير
CORS_ALLOW_ALL_ORIGINS = True

# كاش بسيط (OTP)
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "otp-cache",
    }
}

# ——— سياسات OTP ———
OTP_TTL_SECONDS = int(os.getenv('OTP_TTL_SECONDS', '300'))
OTP_RESEND_COOLDOWN = int(os.getenv('OTP_RESEND_COOLDOWN', '60'))
OTP_MAX_ATTEMPTS = int(os.getenv('OTP_MAX_ATTEMPTS', '5'))

# ——— مزوّد OTP الحالي: Twilio Verify ———
OTP_PROVIDER = os.getenv('OTP_PROVIDER', 'twilio_verify')
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', '')
TWILIO_VERIFY_SERVICE_SID = os.getenv('TWILIO_VERIFY_SERVICE_SID', '')

# (اختياري) مفاتيح Chinguisoft للإرجاع لاحقًا — غير مستخدمة الآن
CHINGUISOFT_BASE_URL = os.getenv('CHINGUISOFT_BASE_URL', '')
CHINGUISOFT_VALIDATION_KEY = os.getenv('CHINGUISOFT_VALIDATION_KEY', '')
CHINGUISOFT_VALIDATION_TOKEN = os.getenv('CHINGUISOFT_VALIDATION_TOKEN', '')
