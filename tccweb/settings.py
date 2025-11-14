""" Django settings for tccweb project."""
import base64
import os
from pathlib import Path

from django.urls import reverse_lazy

BASE_DIR = Path(__file__).resolve().parent.parent

# Security -------------------------------------------------------------------
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-please-change-me",
)
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"

_default_allowed_hosts = "localhost 127.0.0.1 [::1]"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", _default_allowed_hosts).split()

_csrf_origins = os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "")
if _csrf_origins:
    CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in _csrf_origins.split(",") if origin.strip()]
else:
    CSRF_TRUSTED_ORIGINS: list[str] = []

FILE_ENCRYPTION_KEY = os.environ.get("FILE_ENCRYPTION_KEY")
if not FILE_ENCRYPTION_KEY:
    FILE_ENCRYPTION_KEY = base64.urlsafe_b64encode(os.urandom(32)).decode()

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GOOGLE_CLIENT_KEY = os.environ.get("GOOGLE_CLIENT_KEY", "")
GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "")
SITE_DOMAIN = os.environ.get("SITE_DOMAIN", "example.com")
SITE_NAME = os.environ.get("SITE_NAME", SITE_DOMAIN)

# Application definition -----------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "django.contrib.sites",
    "django_otp",
    "django_otp.plugins.otp_static",
    "django_otp.plugins.otp_totp",
    'channels',
    "widget_tweaks",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "tccweb.core",
    "tccweb.accounts",
    "tccweb.admin_portal",
    "tccweb.user_portal",
    "tccweb.counselor_portal",
]
SITE_ID = 1  

SOCIALACCOUNT_ADAPTER = "tccweb.core.adapters.CampusSocialAccountAdapter"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "tccweb.core.middleware.AutoLogoutMiddleware",
    "django_otp.middleware.OTPMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "tccweb.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "tccweb" / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.static",
                "tccweb.core.context_processors.google_keys",
                "tccweb.core.context_processors.enable_2fa_banner",
                "tccweb.core.context_processors.auto_logout_settings",
                "tccweb.user_portal.context_processors.unread_messages",
            ],
            "builtins": [
                "tccweb.core.templatetags.text_extras",
                "tccweb.core.templatetags.ui_extras",
            ],
        },
    }
]

WSGI_APPLICATION = "tccweb.wsgi.application"
ASGI_APPLICATION = "tccweb.asgi.application"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}

# Database -------------------------------------------------------------------

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# Password validation --------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization -------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Colombo"
USE_I18N = True
USE_TZ = True

# Static & media -------------------------------------------------------------
STATIC_URL = "/statics/"
STATICFILES_DIRS = [BASE_DIR / "tccweb" / "statics"]
STATIC_ROOT = BASE_DIR / "staticfiles"
if not DEBUG:
    STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
    
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
PROTECTED_MEDIA_ROOT = BASE_DIR / "protected_media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Authentication -------------------------------------------------------------
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

# Session management ---------------------------------------------------------
AUTO_LOGOUT_TIMEOUT = 60 * 5  # 5 minutes
SESSION_COOKIE_AGE = AUTO_LOGOUT_TIMEOUT
SESSION_SAVE_EVERY_REQUEST = True

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

# Two-factor authentication ---------------------------------------------------
OTP_TOTP_ISSUER = SITE_NAME

# django-allauth -------------------------------------------------------------
ACCOUNT_LOGIN_METHODS = {"username", "email"}
ACCOUNT_SIGNUP_FIELDS = ["username", "email"]
ACCOUNT_EMAIL_VERIFICATION = "optional"
ACCOUNT_LOGOUT_ON_GET = True

ACCOUNT_DEFAULT_HTTP_PROTOCOL = os.environ.get("ACCOUNT_DEFAULT_HTTP_PROTOCOL", "http")

# Email ----------------------------------------------------------------------
EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "true").lower() == "true"
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER or "no-reply@safecampus.app")

# Google integrations ---------------------------------------------------------
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APP": {
            "client_id": GOOGLE_CLIENT_ID,
            "secret": GOOGLE_CLIENT_SECRET,
            "key": GOOGLE_CLIENT_KEY,
        },
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "offline"},
        "OAUTH_PKCE_ENABLED": True,
    }
}