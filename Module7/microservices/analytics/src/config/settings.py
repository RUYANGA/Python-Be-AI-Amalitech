"""Django settings for the **analytics** microservice.

Owns click data and the "detailed analytics" endpoint. Has no ``users``
or ``urls`` table of its own: identity comes from an access token
verified by the auth service over REST (see
``apps.common.jwt_auth.RemoteJWTAuthentication``), and ownership of a
short code is confirmed by calling the shortener service's internal
REST API (see ``apps.analytics.api.services.url_ownership_client``).
Click events themselves arrive over REST too, at
``POST /api/v1/internal/clicks/`` (see
``apps.analytics.api.views.ClickIngestView``).
"""

from pathlib import Path

from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("SECRET_KEY", default="django-insecure-dev-key")
DEBUG = config("DEBUG", default=True, cast=bool)
ALLOWED_HOSTS: list[str] = config(
    "ALLOWED_HOSTS", default="*", cast=lambda v: [h.strip() for h in v.split(",")]
)

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "apps.analytics",
]

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",),
    "DEFAULT_PARSER_CLASSES": ("rest_framework.parsers.JSONParser",),
    "DEFAULT_AUTHENTICATION_CLASSES": ("apps.common.jwt_auth.RemoteJWTAuthentication",),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    # DRF's default for an unauthenticated request is Django's
    # AnonymousUser, which needs django.contrib.auth installed — this
    # service deliberately doesn't have it (no local users table).
    "UNAUTHENTICATED_USER": None,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Analytics Service",
    "DESCRIPTION": "Owns click data and the premium-only detailed-analytics endpoint.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# ─── Cross-service JWT verification (REST call to auth) ────────────
AUTH_SERVICE_URL = config("AUTH_SERVICE_URL", default="http://localhost:8001")

# ─── Shortener service (for the ownership lookup, over REST) ───────
SHORTENER_SERVICE_URL = config("SHORTENER_SERVICE_URL", default="http://localhost:8002")
INTERNAL_SERVICE_TOKEN = config("INTERNAL_SERVICE_TOKEN", default="")

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": ["django.template.context_processors.request"]},
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": config("DB_ENGINE", default="django.db.backends.postgresql"),
        "NAME": config("DB_NAME"),
        "USER": config("DB_USER"),
        "PASSWORD": config("DB_PASSWORD"),
        "HOST": config("DB_HOST", default="localhost"),
        "PORT": config("DB_PORT", default="5432"),
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Kigali"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

# Writes alongside the console output docker-compose logs already
# captures — a persistent file survives past a container's own log
# buffer/rotation and is handy when debugging outside Docker.
LOG_DIR = BASE_DIR.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name} {message}",
            "style": "{",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "simple": {"format": "{levelname} {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOG_DIR / "analytics.log",
            "maxBytes": 10 * 1024 * 1024,  # 10 MB
            "backupCount": 5,
            "formatter": "verbose",
        },
    },
    "root": {"handlers": ["console", "file"], "level": "INFO"},
    "loggers": {
        "django": {"handlers": ["console", "file"], "level": "INFO", "propagate": False},
        "apps.analytics": {"handlers": ["console", "file"], "level": "INFO", "propagate": False},
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
