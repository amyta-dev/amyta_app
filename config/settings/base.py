"""
Shared Django settings for the modular ERP project.

Only project wiring belongs here.
Business rules live inside feature apps.
"""

from datetime import timedelta
from pathlib import Path
import os


# ============================================================
# BASE
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "dev-only-change-this-secret-key",
)

DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get(
        "DJANGO_ALLOWED_HOSTS",
        "127.0.0.1,localhost",
    ).split(",")
    if host.strip()
]


# ============================================================
# APPLICATIONS
# ============================================================

DJANGO_APPS = [
    # Jazzmin MUST be before django.contrib.admin
    "jazzmin",

    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]


THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "drf_spectacular",
    "corsheaders",
]


FEATURE_APPS = [
    "core.accounts.apps.AccountsConfig",
    "apps.depreciation.apps.DepreciationConfig",
    "apps.financial_reporting.apps.FinancialReportingConfig",
    "apps.tax_review.apps.TaxReviewConfig",
]


INSTALLED_APPS = (
    DJANGO_APPS
    + THIRD_PARTY_APPS
    + FEATURE_APPS
)


# ============================================================
# MIDDLEWARE
# ============================================================

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",

    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",

    "django.middleware.clickjacking.XFrameOptionsMiddleware",

    # Custom ERP middleware
    "core.middleware.password_expiry.PasswordExpiryMiddleware",
]


# ============================================================
# URL / WSGI / ASGI
# ============================================================

ROOT_URLCONF = "config.urls"

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


# ============================================================
# TEMPLATES
# ============================================================

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",

        "DIRS": [
            BASE_DIR / "templates",
        ],

        "APP_DIRS": True,

        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",

                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


# ============================================================
# DATABASE
# ============================================================

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# ============================================================
# CUSTOM USER MODEL
# ============================================================

AUTH_USER_MODEL = "accounts.User"


# ============================================================
# PASSWORD VALIDATION
# ============================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        ),
    },
]


# ============================================================
# LOGIN / LOGOUT
# ============================================================

# Semua @login_required diarahkan ke Jazzmin/Django Admin login.
LOGIN_URL = "/admin/login/"

# Setelah login berhasil.
LOGIN_REDIRECT_URL = "/admin/"

# Setelah logout.
LOGOUT_REDIRECT_URL = "/admin/login/"


# ============================================================
# DJANGO SESSION SECURITY
# ============================================================

# 60 menit.
SESSION_COOKIE_AGE = 60 * 60

# Browser ditutup -> session cookie tidak dipertahankan.
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Membuat 30 menit menjadi idle timeout.
# Selama user aktif, expiry session diperpanjang.
SESSION_SAVE_EVERY_REQUEST = True

# JavaScript tidak boleh membaca session cookie.
SESSION_COOKIE_HTTPONLY = True

# SameSite protection.
SESSION_COOKIE_SAMESITE = "Lax"

# Development menggunakan HTTP.
#
# Untuk production HTTPS:
# SESSION_COOKIE_SECURE = True
# CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = False


# ============================================================
# CSRF SECURITY
# ============================================================

CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"

# Development HTTP.
# Ubah menjadi True pada production HTTPS.
CSRF_COOKIE_SECURE = False


# ============================================================
# INTERNATIONALIZATION
# ============================================================

LANGUAGE_CODE = "id"

TIME_ZONE = "Asia/Jakarta"

USE_I18N = True
USE_TZ = True


# ============================================================
# STATIC FILES
# ============================================================

STATIC_URL = "static/"

STATIC_ROOT = BASE_DIR / "staticfiles"

STATICFILES_STORAGE = (
    "whitenoise.storage."
    "CompressedManifestStaticFilesStorage"
)


# ============================================================
# MEDIA / UPLOADS
# ============================================================

MEDIA_URL = "media/"

MEDIA_ROOT = BASE_DIR / "media"


# ============================================================
# DEFAULT PRIMARY KEY
# ============================================================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ============================================================
# DJANGO REST FRAMEWORK
# ============================================================

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": (
        "drf_spectacular.openapi.AutoSchema"
    ),

    "DEFAULT_AUTHENTICATION_CLASSES": (
        # API authentication
        "rest_framework_simplejwt.authentication."
        "JWTAuthentication",

        # Django/Jazzmin session authentication
        "rest_framework.authentication."
        "SessionAuthentication",
    ),

    # API protected by default.
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),

    "DEFAULT_PARSER_CLASSES": (
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ),
}


# ============================================================
# SIMPLE JWT
# ============================================================

SIMPLE_JWT = {
    # Access token dibuat pendek.
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=15,
    ),

    # Refresh token maksimum 8 jam.
    "REFRESH_TOKEN_LIFETIME": timedelta(
        hours=8,
    ),

    "AUTH_HEADER_TYPES": (
        "Bearer",
    ),
}


# ============================================================
# DRF SPECTACULAR
# ============================================================

SPECTACULAR_SETTINGS = {
    "TITLE": "ERP Workspace API",

    "DESCRIPTION": (
        "Modular ERP APIs for depreciation, "
        "financial reporting, and tax review workflows."
    ),

    "VERSION": "1.0.0",

    "SERVE_INCLUDE_SCHEMA": False,
}


# ============================================================
# CORS
# ============================================================

CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5173",
    ).split(",")
    if origin.strip()
]


# ============================================================
# JAZZMIN
# ============================================================

from config.jazzmin_settings import (  # noqa: E402,F401
    JAZZMIN_SETTINGS,
    JAZZMIN_UI_TWEAKS,
)