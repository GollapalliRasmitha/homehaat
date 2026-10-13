"""
HomeHaat Django settings.

Every secret and machine-specific value comes from the root .env file
(see .env.example). Nothing secret is written in this file.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/
load_dotenv(BASE_DIR.parent / ".env")  # homehaat/.env


def env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes")


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "")
DEBUG = env_bool("DJANGO_DEBUG", False)
if not SECRET_KEY:
    if not DEBUG:
        raise RuntimeError("DJANGO_SECRET_KEY must be set when DEBUG is false.")
    SECRET_KEY = "dev-only-insecure-key"

ALLOWED_HOSTS = [h.strip() for h in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "django_filters",
    # HomeHaat apps
    "core",
    "accounts",
    "catalog",
    "cart",
    "orders",
    "payments",
    "reviews",
    "custom_requests",
    "ai",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
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
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "homehaat"),
        "USER": os.getenv("POSTGRES_USER", "homehaat"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", "homehaat"),
        "HOST": os.getenv("POSTGRES_HOST", "127.0.0.1"),
        "PORT": os.getenv("POSTGRES_PORT", "5433"),
    }
}

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

if "test" in sys.argv:
    # Tests create many users; a fast (weak) hasher keeps the suite quick. Never used outside tests.
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

LANGUAGE_CODE = "en-in"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
# Uploaded photos. MEDIA_ROOT can be overridden so a throwaway test copy never touches real uploads.
MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT", BASE_DIR / "media"))

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# --- Sessions, cookies, CSRF ---
# The browser talks to Next.js on :3000, which proxies /api/* here, so the
# session cookie is first-party. HttpOnly keeps it away from JavaScript.
# Own cookie names: browsers share cookies across ports on "localhost", so Oppora's
# default "sessionid"/"csrftoken" cookies would otherwise collide with ours.
SESSION_COOKIE_NAME = "homehaat_session"
CSRF_COOKIE_NAME = "homehaat_csrftoken"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
CSRF_TRUSTED_ORIGINS = [FRONTEND_ORIGIN]

# --- Security headers (more in Stage 7) ---
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# --- Django REST Framework ---
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_THROTTLE_RATES": {
        "auth": "10/min",
        "checkout": "10/min",
        "custom_requests": "10/hour",
        "ai_listing": "10/hour",  # per seller; keeps everyone inside Gemini's free daily limit
    },
}

# --- Razorpay (test mode only) ---
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
if RAZORPAY_KEY_ID and not RAZORPAY_KEY_ID.startswith("rzp_test_"):
    raise RuntimeError("HomeHaat only runs Razorpay in test mode. Use a key that starts with rzp_test_.")

# --- Orders ---
# Checkout holds the stock for this long. Unpaid after that -> order fails, stock goes back.
ORDER_HOLD_MINUTES = 15

# --- AI listing helper (Stage 6) ---
AI_ENABLED = env_bool("AI_ENABLED", False)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")  # HomeHaat's own key, never Oppora's
# Tried in order. Google retires model names (gemini-2.5-flash is closed to new keys) and busy models
# answer 503, so we use Google's "-latest" aliases, which it keeps pointing at a current model.
# Flash-Lite first: a short description of a photo is an easy task, and it answers in ~2 s; full Flash is
# the backup. GEMINI_MODEL in .env can put a specific model first.
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "").strip() or "gemini-flash-lite-latest"
GEMINI_MODELS = list(
    dict.fromkeys(  # no duplicates, order kept
        [GEMINI_MODEL]
        + [m.strip() for m in os.getenv("GEMINI_FALLBACK_MODELS", "").split(",") if m.strip()]
        + ["gemini-flash-lite-latest", "gemini-flash-latest"]
    )
)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {"homehaat": {"handlers": ["console"], "level": "INFO"}},
}
