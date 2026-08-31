"""Django settings for the **shortener** microservice.

Owns URL shortening, tagging, and RBAC/tier rules for URLs. Has no
``users`` table of its own — every request is authenticated by asking
the auth service to verify the access token over gRPC (see
``apps.common.jwt_auth.RemoteJWTAuthentication``), never by a local
database lookup.
"""

from pathlib import Path

from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("SECRET_KEY", default="django-insecure-dev-key")
DEBUG = config("DEBUG", default=True, cast=bool)
ALLOWED_HOSTS: list[str] = config(
    "ALLOWED_HOSTS", default="*", cast=lambda v: [h.strip() for h in v.split(",")]
)

# No django.contrib.auth/admin/sessions here — this service has no
# notion of a local Django user to log in as; identity is a JWT claim.
INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "apps.shortener",
]

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",),
    "DEFAULT_PARSER_CLASSES": (
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
    ),
    "DEFAULT_AUTHENTICATION_CLASSES": ("apps.common.jwt_auth.RemoteJWTAuthentication",),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    # DRF's default for an unauthenticated request is Django's
    # AnonymousUser, which needs django.contrib.auth installed — this
    # service deliberately doesn't have it (no local users table).
    "UNAUTHENTICATED_USER": None,
    "DEFAULT_FILTER_BACKENDS": (
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Shortener Service",
    "DESCRIPTION": "Owns URL shortening, tagging, RBAC, and tier rules for URLs.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# ─── Cross-service JWT verification (gRPC call to auth) ────────────
AUTH_GRPC_URL = config("AUTH_GRPC_URL", default="localhost:50052")

# Shared secret for internal (service-to-service) gRPC calls — the
# auth token-validation lookup this service makes, and the ownership
# lookup the analytics service makes here. Never sent to browsers/clients.
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
        "HOST": config("DB_HOST"),
        "PORT": config("DB_PORT"),
    }
}

# Backs CachedURLRepository's read-through cache.
REDIS_URL = config("REDIS_URL", default="redis://127.0.0.1:6379/0")

# Backs ClickEventPublisher — the transport to the analytics service.
KAFKA_BOOTSTRAP_SERVERS = config("KAFKA_BOOTSTRAP_SERVERS", default="localhost:9094")

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Kigali"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

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
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "apps.shortener": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
