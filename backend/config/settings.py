"""
HomeHaat Django settings.

Every secret and machine-specific value comes from environment variables: locally the root .env file (see
.env.example), in production the Render dashboard (docs/deploy.md). Nothing secret is written in this file.
An empty variable counts as "not set", so the local defaults below still apply.
"""

import os
import sys
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv

from config.database import database_from_url

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/
load_dotenv(BASE_DIR.parent / ".env")  # homehaat/.env


def env(name: str, default: str = "") -> str:
    value = os.getenv(name, "").strip()
    return value or default


def env_bool(name: str, default: bool = False) -> bool:
    return env(name, str(default)).lower() in ("1", "true", "yes")


def env_list(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in env(name, default).split(",") if item.strip()]


TESTING = "test" in sys.argv

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env_bool("DJANGO_DEBUG", False)  # off unless switched on: production never shows error pages with code
if not SECRET_KEY:
    if not DEBUG:
        raise RuntimeError("DJANGO_SECRET_KEY must be set when DEBUG is false.")
    SECRET_KEY = "dev-only-insecure-key"

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
if env("RENDER_EXTERNAL_HOSTNAME"):  # Render sets this itself (e.g. homehaat-api.onrender.com)
    ALLOWED_HOSTS.append(env("RENDER_EXTERNAL_HOSTNAME"))
# The site people visit (Next.js). Locally :3000, in production the Vercel address. No slash at the end.
FRONTEND_ORIGIN = env("FRONTEND_ORIGIN", "http://localhost:3000").rstrip("/")
# Vercel forwards /api/* to Render. Whichever host name Django then sees (Render's or the site's), it's allowed.
_frontend_host = urlsplit(FRONTEND_ORIGIN).hostname
if _frontend_host and _frontend_host not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(_frontend_host)

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
    "guardrail",  # sends security events to GuardRail (monitoring); switched off unless configured
]

MIDDLEWARE = [
    "guardrail.middleware.GuardRailMiddleware",  # first, so it sees every final status (reports only, never changes)
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # Django admin's CSS/JS in production (no separate server)
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.LazyJobsMiddleware",  # releases expired stock holds when pages load (core/jobs.py)
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

if env("DATABASE_URL"):
    # Production: Neon. One URL with everything; encrypted connection (sslmode=require) enforced.
    DATABASES = {"default": database_from_url(env("DATABASE_URL"))}
else:
    # Local: Postgres in Docker (docker-compose.yml), exactly as before.
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("POSTGRES_DB", "homehaat"),
            "USER": env("POSTGRES_USER", "homehaat"),
            "PASSWORD": env("POSTGRES_PASSWORD", "homehaat"),
            "HOST": env("POSTGRES_HOST", "127.0.0.1"),
            "PORT": env("POSTGRES_PORT", "5433"),
        }
    }

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

if TESTING:
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
MEDIA_ROOT = Path(env("MEDIA_ROOT") or BASE_DIR / "media")

# Photos: on Cloudinary when CLOUDINARY_URL is set (production; core/storage.py keeps custom request photos private),
# otherwise in MEDIA_ROOT. Tests always use local files, so they never reach the internet.
CLOUDINARY_URL = env("CLOUDINARY_URL")
if CLOUDINARY_URL and not CLOUDINARY_URL.startswith("cloudinary://"):
    raise RuntimeError("CLOUDINARY_URL must start with cloudinary:// (copy it from the Cloudinary dashboard).")
USE_CLOUDINARY = bool(CLOUDINARY_URL) and not TESTING
STORAGES = {
    "default": {
        "BACKEND": "core.storage.CloudinaryStorage" if USE_CLOUDINARY else "django.core.files.storage.FileSystemStorage"
    },
    # Production: compressed files with a fingerprint in the name, so browsers can cache them for a long time.
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
        if not DEBUG and not TESTING
        else "django.contrib.staticfiles.storage.StaticFilesStorage"
    },
}

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
# Changes must come from our own site. Extra ones (e.g. a custom domain) can be added, comma-separated.
CSRF_TRUSTED_ORIGINS = [FRONTEND_ORIGIN] + [o.rstrip("/") for o in env_list("CSRF_TRUSTED_ORIGINS")]
# No CORS settings on purpose: the browser never calls Django from another site. It calls /api/* on the Next.js
# site, which forwards to Django (next.config.ts), so every request is same-origin for the browser.

# --- Security headers ---
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
if not DEBUG:
    # Render ends HTTPS in front of Django and says so in this header.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = not TESTING  # http:// -> https://
    SECURE_REDIRECT_EXEMPT = [r"^api/health/$"]  # Render's own health check calls plain http inside its network
    # Browsers remember "HTTPS only" for this site for 30 days. No subdomains/preload: onrender.com isn't ours.
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_HSTS_PRELOAD = False
    # Both are off on purpose (above), so the deploy check needn't warn about them.
    SILENCED_SYSTEM_CHECKS = ["security.W005", "security.W021"]

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

# --- Proxy ---
# Shared with the Next.js app (frontend/proxy.ts): proves a forwarded visitor IP really came from our proxy, so the
# sign-in rate limit counts each visitor separately. Empty = trust no forwarded IP (fine locally).
PROXY_SECRET = env("PROXY_SECRET")

# --- Scheduled jobs (core/jobs.py) ---
# The GitHub Actions schedule sends this in a header to POST /api/jobs/run/. Empty = the endpoint is switched off.
JOBS_SECRET = env("JOBS_SECRET")
# Also release expired stock holds when pages load (at most once a minute). Off in tests, which call it directly.
LAZY_JOBS = not TESTING

# --- GuardRail (security monitoring, guardrail/client.py) ---
# Events are sent in the background with a 2 s timeout; failures wait in an outbox and never affect visitors.
# Off unless all three are set. GUARDRAIL_SECRET = the same value as INGEST_SECRET_HOMEHAAT in GuardRail.
GUARDRAIL_ENABLED = env_bool("GUARDRAIL_ENABLED", False) and not TESTING  # tests switch it on themselves
GUARDRAIL_URL = env("GUARDRAIL_URL")
GUARDRAIL_SECRET = env("GUARDRAIL_SECRET")
GUARDRAIL_SYNC = False  # tests only: send inline instead of in the background thread

# --- Razorpay (test mode only) ---
RAZORPAY_KEY_ID = env("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = env("RAZORPAY_KEY_SECRET")
RAZORPAY_WEBHOOK_SECRET = env("RAZORPAY_WEBHOOK_SECRET")
if RAZORPAY_KEY_ID and not RAZORPAY_KEY_ID.startswith("rzp_test_"):
    raise RuntimeError("HomeHaat only runs Razorpay in test mode. Use a key that starts with rzp_test_.")

# --- Orders ---
# Checkout holds the stock for this long. Unpaid after that -> order fails, stock goes back.
ORDER_HOLD_MINUTES = 15

# --- AI listing helper (Stage 6) ---
AI_ENABLED = env_bool("AI_ENABLED", False)
GEMINI_API_KEY = env("GEMINI_API_KEY")  # HomeHaat's own key, never Oppora's
# Tried in order. Google retires model names (gemini-2.5-flash is closed to new keys) and busy models
# answer 503, so we use Google's "-latest" aliases, which it keeps pointing at a current model.
# Flash-Lite first: a short description of a photo is an easy task, and it answers in ~2 s; full Flash is
# the backup. GEMINI_MODEL in .env can put a specific model first.
GEMINI_MODEL = env("GEMINI_MODEL", "gemini-flash-lite-latest")
GEMINI_MODELS = list(
    dict.fromkeys(  # no duplicates, order kept
        [GEMINI_MODEL] + env_list("GEMINI_FALLBACK_MODELS") + ["gemini-flash-lite-latest", "gemini-flash-latest"]
    )
)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {
        "homehaat": {"handlers": ["console"], "level": "INFO"},
        # Server errors go to the console too, so they show in Render's Logs tab (Django hides them when DEBUG is off).
        "django": {"handlers": ["console"], "level": "WARNING"},
    },
}
