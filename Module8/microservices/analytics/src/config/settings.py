"""Django settings for the **analytics** microservice.

Owns click data and the "detailed analytics" endpoint. Has no ``users``
or ``urls`` table of its own, and never verifies a JWT itself — the
nginx API gateway (``/gateway`` at the repo root) does that once, up
front, via an ``auth_request`` call to the auth service, and forwards
the verified claims as trusted headers (see
``apps.analytics.api.authentication.GatewayAuthentication``). Ownership
of a short code is confirmed by calling the shortener service's internal
REST API (see ``apps.analytics.api.services.url_ownership_client``).
Click events themselves arrive over REST too, at
``POST /api/v1/internal/clicks/`` (see
``apps.analytics.api.views.ClickIngestView``). This service is only
ever reached through the gateway.
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
    "DEFAULT_AUTHENTICATION_CLASSES": ("apps.analytics.api.authentication.GatewayAuthentication",),
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

# ─── Shortener service (for the ownership lookup, over REST) ───────
# Called directly over the internal Docker network, not through the
# gateway — the gateway's job is centralizing client-facing auth
# (see /gateway), which has nothing to do with this internal,
# X-Internal-Token-authenticated call.
SHORTENER_SERVICE_URL = config("SHORTENER_SERVICE_URL", default="http://shortener:8000")
INTERNAL_SERVICE_TOKEN = config("INTERNAL_SERVICE_TOKEN", default="")

# Backs CachedClickAnalyticsRepository's read-through cache over the
# analytics-by-code endpoint's aggregate queries.
REDIS_URL = config("REDIS_URL", default="redis://127.0.0.1:6379/0")

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
        "json": {"()": "config.json_logging.JSONFormatter"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "json"},
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOG_DIR / "analytics.log",
            "maxBytes": 10 * 1024 * 1024,  # 10 MB
            "backupCount": 5,
            "formatter": "json",
        },
    },
    "root": {"handlers": ["console", "file"], "level": "INFO"},
    "loggers": {
        "django": {"handlers": ["console", "file"], "level": "INFO", "propagate": False},
        # Django logs a 500 here at ERROR — kept explicit so it's never
        # silently dropped regardless of the "django" logger's level above.
        "django.request": {"handlers": ["console", "file"], "level": "ERROR", "propagate": False},
        # DisallowedHost, SuspiciousOperation, CSRF failures, etc.
        "django.security": {
            "handlers": ["console", "file"],
            "level": "WARNING",
            "propagate": False,
        },
        "apps.analytics": {"handlers": ["console", "file"], "level": "INFO", "propagate": False},
        "celery": {"handlers": ["console", "file"], "level": "INFO", "propagate": False},
    },
}

# ─── Celery (write-behind click ingestion: see apps.analytics.tasks) ──
# A *different Redis DB* than REDIS_URL/the cache — not just a
# different key namespace. Celery's redis transport consumes an entire
# queue with a plain BRPOP on a fixed key ("celery" by default), with no
# per-app prefix, so if this shared Redis' cache DB were reused as the
# broker DB for more than one service, each service's worker would also
# BRPOP the *other* service's tasks off the same list — a message
# consumed by the wrong worker is simply dropped, not requeued. Own DB
# index per service's broker avoids that entirely (shortener uses /1).
CELERY_BROKER_URL = config("CELERY_BROKER_URL", default="redis://127.0.0.1:6379/2")
CELERY_RESULT_BACKEND = None
CELERY_TASK_ALWAYS_EAGER = config("CELERY_TASK_ALWAYS_EAGER", default=False, cast=bool)
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
