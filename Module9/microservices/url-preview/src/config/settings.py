"""Django settings for the **url-preview** microservice.

Fetches title/description/favicon for a destination URL on the shortener
service's behalf, resiliently (retry + backoff, plus a Redis-backed
circuit breaker per domain). Has no ``users`` table of its own — unlike
``shortener``/``analytics``, this service has *no client-facing,
JWT-gated endpoints at all*: its only route
(``POST /api/v1/internal/preview/``) is called container-to-container by
``shortener`` and is gated purely by ``HasInternalServiceToken`` at the
view level (the shared ``X-Internal-Token`` header), the same mechanism
``shortener``/``analytics`` already use for *their* internal endpoints.

Because there is no per-request identity to authenticate here (no JWT,
no ``GatewayAuthentication``), ``REST_FRAMEWORK`` below deliberately sets
``DEFAULT_AUTHENTICATION_CLASSES = ()`` (nothing authenticates a request
at the framework level) and ``DEFAULT_PERMISSION_CLASSES =
("AllowAny",)`` — the *actual* access control is the explicit
``permission_classes = [HasInternalServiceToken]`` on
``PreviewFetchView`` itself, evaluated regardless of the framework
default. This mirrors how ``shortener``'s ``URLOwnershipView`` and
``analytics``'s ``ClickIngestView`` layer ``HasInternalServiceToken`` on
top of a *global* ``IsAuthenticated`` default that would otherwise
reject them (they have no local Django user, so DRF's default anonymous
user immediately fails ``IsAuthenticated``) — since this service has no
notion of "authenticated" at all, ``AllowAny`` is the equivalent
resting state, with the per-view permission doing the real gating.
"""

from pathlib import Path

from decouple import config
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("SECRET_KEY", default="django-insecure-dev-key")
DEBUG = config("DEBUG", default=True, cast=bool)
ALLOWED_HOSTS: list[str] = config(
    "ALLOWED_HOSTS",
    cast=lambda v: [h.strip() for h in v.split(",")],
)
if "*" in ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        "ALLOWED_HOSTS must not be the '*' wildcard — set explicit hosts in .env"
    )

# No django.contrib.auth/admin/sessions here — this service has no
# notion of a local Django user to log in as, and no users table at all.
INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "apps.preview",
]

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",),
    "DEFAULT_PARSER_CLASSES": ("rest_framework.parsers.JSONParser",),
    # Nothing authenticates a request at the framework level (no JWT, no
    # gateway header parsing) — access control lives entirely in the
    # per-view HasInternalServiceToken permission. See the module
    # docstring above for why this is the right default here.
    "DEFAULT_AUTHENTICATION_CLASSES": (),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.AllowAny",),
    # DRF's default for an unauthenticated request is Django's
    # AnonymousUser, which needs django.contrib.auth installed — this
    # service deliberately doesn't have it (no local users table).
    "UNAUTHENTICATED_USER": None,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "URL Preview Service",
    "DESCRIPTION": (
        "Fetches title/description/favicon for a destination URL, called "
        "internally by the shortener service."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# Shared secret for internal (service-to-service) REST calls, sent as
# the X-Internal-Token header by shortener. Never sent to browsers/clients.
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

# Backs the result cache and the domain circuit breaker (DomainCircuitBreaker).
REDIS_URL = config("REDIS_URL", default="redis://127.0.0.1:6379/0")

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
            "filename": LOG_DIR / "url-preview.log",
            "maxBytes": 10 * 1024 * 1024,  # 10 MB
            "backupCount": 5,
            "formatter": "json",
        },
        "profile_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOG_DIR / "profile.log",
            "maxBytes": 10 * 1024 * 1024,  # 10 MB
            "backupCount": 5,
            "formatter": "json",
        },
        "breaker_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOG_DIR / "breaker.log",
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
        "apps.preview": {"handlers": ["console", "file"], "level": "INFO", "propagate": False},
        # Circuit-breaker state transitions — split into their own file so
        # they're easy to grep when triaging degraded domain fetch health.
        "apps.preview.api.services.circuit_breaker": {
            "handlers": ["console", "breaker_file"],
            "level": "INFO",
            "propagate": False,
        },
        # @profiled/@timed results — split into their own file so profiling
        # noise doesn't drown out url-preview.log, while still reaching
        # `docker logs` via console.
        "apps.preview.api.profiling": {
            "handlers": ["console", "profile_file"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# ─── Preview-fetch tuning ────────────────────────────────────────────
PREVIEW_FETCH_TIMEOUT = config("PREVIEW_FETCH_TIMEOUT", default=5.0, cast=float)
PREVIEW_MAX_ATTEMPTS = config("PREVIEW_MAX_ATTEMPTS", default=3, cast=int)
PREVIEW_RETRY_BASE_DELAY = config("PREVIEW_RETRY_BASE_DELAY", default=0.5, cast=float)
PREVIEW_MAX_BODY_BYTES = config("PREVIEW_MAX_BODY_BYTES", default=2_000_000, cast=int)
PREVIEW_CIRCUIT_FAILURE_THRESHOLD = config("PREVIEW_CIRCUIT_FAILURE_THRESHOLD", default=5, cast=int)
PREVIEW_CIRCUIT_OPEN_SECONDS = config("PREVIEW_CIRCUIT_OPEN_SECONDS", default=60, cast=int)
PREVIEW_CACHE_TTL = config("PREVIEW_CACHE_TTL", default=600, cast=int)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
