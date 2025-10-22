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

    'users', 
    'services',
    'workers',
    'tasks',
    'clients',
    'payments',
    'chat',
    'notifications',
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
    'users.middleware.ReactivateMiddleware',  

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

# Custom User Model
AUTH_USER_MODEL = 'users.User'

# ===============================================
# إضافات لرفع الصور والملفات
# ===============================================

# إعدادات الملفات والصور
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# إعدادات رفع الملفات
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
FILE_UPLOAD_PERMISSIONS = 0o644

# إعدادات أمان الملفات
ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/jpg']
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB

# للـ Development - عرض الملفات المرفوعة
if DEBUG:
    os.makedirs(MEDIA_ROOT, exist_ok=True)

# ===============================================
# Firebase Configuration - إضافة جديدة
# ===============================================

# معرف المشروع و Sender ID من .env
FIREBASE_PROJECT_ID = os.getenv('FIREBASE_PROJECT_ID', '')
FIREBASE_SENDER_ID = os.getenv('FIREBASE_SENDER_ID', '')

# مسار ملف Service Account (من .env أو افتراضي)
FIREBASE_CREDENTIALS_PATH = Path(os.getenv('FIREBASE_CREDENTIALS_PATH', r'C:\secure\firebase\serviceAccountKey.json'))

# إعدادات الإشعارات من .env
FIREBASE_NOTIFICATIONS = {
    'DEFAULT_SOUND': os.getenv('FIREBASE_DEFAULT_SOUND', 'default'),
    'DEFAULT_PRIORITY': os.getenv('FIREBASE_DEFAULT_PRIORITY', 'high'),
    'MAX_RETRIES': int(os.getenv('FIREBASE_MAX_RETRIES', '3')),
    'TIMEOUT': int(os.getenv('FIREBASE_TIMEOUT', '30')),
    'BADGE_ENABLED': True,
}

# التحقق من وجود الملفات المطلوبة (تحذير فقط في التطوير)
if DEBUG and not FIREBASE_CREDENTIALS_PATH.exists():
    print(f"تحذير: ملف Firebase غير موجود في: {FIREBASE_CREDENTIALS_PATH}")
    print("الإشعارات المتقدمة ستكون معطلة حتى إضافة الملف")

# في الإنتاج، تأكد من وجود المتغيرات الضرورية
if not DEBUG:
    if not FIREBASE_PROJECT_ID or not FIREBASE_SENDER_ID:
        print("تحذير: متغيرات Firebase غير مكتملة في الإنتاج")
    
    if not FIREBASE_CREDENTIALS_PATH.exists():
        print(f"خطأ: ملف Firebase مفقود في الإنتاج: {FIREBASE_CREDENTIALS_PATH}")

# ===============================================
# Logging Configuration - محدث
# ===============================================

# إنشاء مجلد logs إذا لم يكن موجود
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': LOGS_DIR / 'django.log',
            'formatter': 'verbose',
        },
        'firebase_file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': LOGS_DIR / 'firebase_notifications.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG' if DEBUG else 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'] if DEBUG else ['file'],
            'level': 'INFO',
            'propagate': False,
        },
        'firebase_notifications': {
            'handlers': ['firebase_file', 'console'] if DEBUG else ['firebase_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# ===============================================
# Celery Configuration (اختياري للمعالجة غير المتزامنة)
# ===============================================

# إعدادات Celery للمعالجة المتقدمة (اختياري)
USE_CELERY = os.getenv('USE_CELERY', 'False').lower() == 'true'

if USE_CELERY:
    CELERY_BROKER_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    CELERY_RESULT_BACKEND = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    CELERY_ACCEPT_CONTENT = ['json']
    CELERY_TASK_SERIALIZER = 'json'
    CELERY_RESULT_SERIALIZER = 'json'
    CELERY_TIMEZONE = TIME_ZONE

GLOBAL_OTP_RATE_LIMIT = {
    'MAX_ATTEMPTS_PER_PHONE_PER_HOUR': 10,  # 10 محاولات كحد أقصى في الساعة
    'MAX_ATTEMPTS_PER_IP_PER_HOUR': 20,     # 20 محاولة من نفس الـ IP
    'BLOCK_DURATION_MINUTES': 60,           # مدة المنع بالدقائق
}

