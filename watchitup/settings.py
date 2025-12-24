"""
Django settings for watchitup project.
"""

import environ
import os
from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# ------------------ BASE DIRECTORY ------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# ------------------ ENV CONFIG ------------------
env = environ.Env()
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))  # Load from .env

# ------------------ SECURITY ------------------
SECRET_KEY = env('SECRET_KEY', default='insecure-secret-key')
DEBUG = env.bool("DEBUG", default=True)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["*"])

# ------------------ APPLICATIONS ------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'crispy_forms',
    'crispy_bootstrap5',
    'django_ratelimit',
    
    'users',
    'admin_panel',
    'products',
    
]

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# ------------------ MIDDLEWARE ------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'users.middleware.BlockedUserMiddleware', 
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

ROOT_URLCONF = 'watchitup.urls'
WSGI_APPLICATION = 'watchitup.wsgi.application'

# ------------------ DATABASE ------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('DB_NAME'),
        'USER': env('DB_USER'),
        'PASSWORD': env('DB_PASSWORD'),
        'HOST': env('DB_HOST'),
        'PORT': env('DB_PORT'),
    }
}

# ------------------ EMAIL CONFIG (TLS with certifi) ------------------
EMAIL_BACKEND = 'users.email_backend.CertifiTLSBackend'
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = env('EMAIL_HOST_USER')          # Gmail
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD')  # Gmail App Password
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
EMAIL_TIMEOUT = 30



# -------------------------------
# 🔒 Razorpay Configuration
# -------------------------------
RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID')
RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET')

# Add after ALLOWED_HOSTS
SECURE_CROSS_ORIGIN_OPENER_POLICY = None  # Important for Razorpay popup

# Add CSP settings for Razorpay
CSP_DEFAULT_SRC = ("'self'", "https://checkout.razorpay.com", "https://api.razorpay.com")
CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'", "https://checkout.razorpay.com")
CSP_FRAME_SRC = ("'self'", "https://api.razorpay.com")
CSP_CONNECT_SRC = ("'self'", "https://api.razorpay.com", "https://lumberjack.razorpay.com")


# IMPORTANT: Add CSRF trusted origins
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]

# ------------------ OTP SETTINGS ------------------
OTP_EXPIRY_TIME = 300  # 5 minutes in seconds

# ------------------ LOGGING ------------------
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': LOGS_DIR / 'watchitup.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'users': {  # Your app-specific logging
            'handlers': ['console', 'file'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
    },
}

# ------------------ AUTHENTICATION ------------------
AUTH_USER_MODEL = 'users.CustomUser'
AUTHENTICATION_BACKENDS = [
    'users.backends.EmailOrUsernameModelBackend',  # Custom backend
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

SITE_ID = 1
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = 'none'
ACCOUNT_LOGIN_ATTEMPTS_LIMIT = 5
ACCOUNT_LOGIN_ATTEMPTS_TIMEOUT = 86400
ACCOUNT_LOGOUT_ON_GET = True



LOGIN_REDIRECT_URL = '/products/'
LOGOUT_REDIRECT_URL = '/users/login/'
ACCOUNT_LOGOUT_REDIRECT_URL = '/users/login/'
LOGIN_URL = '/users/login/'


SESSION_COOKIE_AGE = 1800  # 30 minutes
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = False


# ------------------ GOOGLE OAUTH ------------------
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {
            'access_type': 'offline',  # Changed from 'online'
            'prompt': 'consent',       # This forces the consent screen
        },
        'APP': {
            'client_id': env('GOOGLE_CLIENT_ID'),
            'secret': env('GOOGLE_CLIENT_SECRET'),
            'key': ''
        },
        'OAUTH_PKCE_ENABLED': True,
    }
}
SOCIALACCOUNT_AUTO_SIGNUP = True  # Keep this True
SOCIALACCOUNT_QUERY_EMAIL = True
SOCIALACCOUNT_LOGIN_ON_GET = False  # Changed from True - this was causing direct redirect
SOCIALACCOUNT_ADAPTER = 'users.adapters.CustomSocialAccountAdapter'
SOCIALACCOUNT_EMAIL_VERIFICATION = 'none'

# ------------------ CACHING (Redis for ratelimit) ------------------
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}

# ------------------ PASSWORD VALIDATORS ------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ------------------ INTERNATIONALIZATION ------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# ------------------ STATIC & MEDIA ------------------
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ------------------ TEMPLATES ------------------
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'products.context_processors.cart_wishlist_counts',
            ],
        },
    },
]


# ------------------ EMAIL CHANGE OTP SETTINGS (ADD THIS) ------------------
EMAIL_CHANGE_OTP_EXPIRY_TIME = 300  # 5 minutes in seconds

# ------------------ FILE UPLOAD SETTINGS (ADD THIS) ------------------
# Maximum file size for profile pictures (2MB)
FILE_UPLOAD_MAX_MEMORY_SIZE = 2621440  # 2.5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 2621440  # 2.5MB

# Allowed image formats for profile pictures
ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif']
MAX_PROFILE_IMAGE_SIZE = 2 * 1024 * 1024  # 2MB in bytes

# ------------------ CUSTOM ADMIN PANEL REDIRECTS ------------------
ADMIN_LOGIN_URL = '/admin_panel/login/'
ADMIN_LOGIN_REDIRECT_URL = '/admin_panel/dashboard/'
ADMIN_LOGOUT_REDIRECT_URL = '/admin_panel/login/'

# ------------------ DEFAULTS ------------------
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ------------------ REPORT GENERATION SETTINGS ------------------
# For PDF reports using ReportLab
REPORTLAB_FONT_PATH = BASE_DIR / 'fonts'  # Optional: for custom fonts

# Maximum records in downloadable reports
MAX_REPORT_RECORDS_PDF = 1000
MAX_REPORT_RECORDS_EXCEL = 10000

# Report caching (optional, for better performance)
REPORT_CACHE_TIMEOUT = 300  # 5 minutes

# ------------------ DATE FORMAT SETTINGS ------------------
# For consistent date formatting in reports
REPORT_DATE_FORMAT = '%Y-%m-%d'
REPORT_DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'

APPEND_SLASHES = True

import ssl, certifi
ssl._create_default_https_context = lambda: ssl.create_default_context(cafile=certifi.where())