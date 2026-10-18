"""Django settings. Django owns the schema, migrations and the admin; FastAPI (api/) serves the public API."""
import os
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-insecure-key" if DEBUG else "")
if not SECRET_KEY:
    raise RuntimeError("DJANGO_SECRET_KEY must be set when DJANGO_DEBUG=0")

ALLOWED_HOSTS = [h for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",") if h]
CSRF_TRUSTED_ORIGINS = [o for o in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if o]
CORS_ORIGINS = [o for o in os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",") if o]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "listings",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

# On Vercel (serverless) don't keep connections open between invocations; use Neon's pooled URL.
ON_VERCEL = bool(os.environ.get("VERCEL"))
DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}", conn_max_age=0 if ON_VERCEL else 60
    )
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LANGUAGE_CODE = "en"
TIME_ZONE = "Asia/Manila"
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Public API shows a listing only at or above this trust tier (see listings.models.TrustTier).
PUBLIC_MIN_TIER = int(os.environ.get("PUBLIC_MIN_TIER", "1"))

# Meta tag an owner adds to their website's home page to prove they control it.
VERIFICATION_META_NAME = "ahtara-site-verification"

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
