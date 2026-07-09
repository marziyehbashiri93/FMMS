"""
FMMS Base Settings.

Shared configuration for all environments.
Never import environment-specific settings from this file.
"""

from pathlib import Path

import environ

# ──────────────────────────────────────────────────────────────────────────────
# Environment
# ──────────────────────────────────────────────────────────────────────────────
env = environ.Env(
    DEBUG=(bool, False),
    LOG_LEVEL=(str, "INFO"),
    ALLOWED_HOSTS=(list, []),
    CORS_ALLOWED_ORIGINS=(list, []),
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Read .env file if present (development only — production uses real env vars)
environ.Env.read_env(BASE_DIR / ".env", overwrite=False)

# ──────────────────────────────────────────────────────────────────────────────
# Core
# ──────────────────────────────────────────────────────────────────────────────
SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

# ──────────────────────────────────────────────────────────────────────────────
# Applications
# ──────────────────────────────────────────────────────────────────────────────
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
]

FMMS_APPS = [
    "apps.authentication",
    # Domain apps registered in Milestone 3:
    # "apps.vehicle",
    # "apps.driver",
    # "apps.inspection",
    # "apps.fault",
    # "apps.repair",
    # "apps.preventive_maintenance",
    # "apps.procurement",
    # "apps.integration",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + FMMS_APPS

# ──────────────────────────────────────────────────────────────────────────────
# Authentication
# ──────────────────────────────────────────────────────────────────────────────
AUTH_USER_MODEL = "authentication.FMMSUser"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ──────────────────────────────────────────────────────────────────────────────
# Middleware — order matters
# ──────────────────────────────────────────────────────────────────────────────
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # FMMS middleware — active from Milestone 1
    "core.middleware.request_id.RequestIDMiddleware",
    "core.middleware.audit_log.AuditLogMiddleware",
]

ROOT_URLCONF = "config.urls"

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ──────────────────────────────────────────────────────────────────────────────
# Templates
# ──────────────────────────────────────────────────────────────────────────────
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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

# ──────────────────────────────────────────────────────────────────────────────
# Database
# ──────────────────────────────────────────────────────────────────────────────
DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgres://fmms:fmms@localhost:5432/fmms",
    )
}
DATABASES["default"]["ATOMIC_REQUESTS"] = True  # Wrap every request in a transaction

# ──────────────────────────────────────────────────────────────────────────────
# Cache — Redis
# ──────────────────────────────────────────────────────────────────────────────
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("REDIS_URL", default="redis://localhost:6379/0"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "IGNORE_EXCEPTIONS": True,  # Degrade gracefully if Redis is unavailable
        },
        "KEY_PREFIX": "fmms",
    }
}

# ──────────────────────────────────────────────────────────────────────────────
# Migration Modules — maps apps to infrastructure/migrations/
# Extended in Milestone 3 when domain apps are registered.
# ──────────────────────────────────────────────────────────────────────────────
MIGRATION_MODULES = {
    "authentication": "apps.authentication.infrastructure.migrations",
}

# ──────────────────────────────────────────────────────────────────────────────
# Internationalization
# ──────────────────────────────────────────────────────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ──────────────────────────────────────────────────────────────────────────────
# Static & Media Files
# ──────────────────────────────────────────────────────────────────────────────
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "mediafiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ──────────────────────────────────────────────────────────────────────────────
# Django REST Framework — baseline config (endpoints added in Milestone 7)
# ──────────────────────────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
    ],
    "EXCEPTION_HANDLER": "core.exceptions.http_exception_handler.fmms_exception_handler",
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    # Pagination configured per-view in Milestone 7
    "DEFAULT_PAGINATION_CLASS": None,
}

# ──────────────────────────────────────────────────────────────────────────────
# Celery — broker and result backend (tasks registered in Milestone 8)
# ──────────────────────────────────────────────────────────────────────────────
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/1")
CELERY_RESULT_BACKEND = env("REDIS_URL", default="redis://localhost:6379/2")
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = "UTC"
CELERY_ENABLE_UTC = True
CELERY_TASK_TRACK_STARTED = True

# ──────────────────────────────────────────────────────────────────────────────
# Logging — structured JSON, all FMMS logs use fmms.* namespace
# ──────────────────────────────────────────────────────────────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "core.logging.formatters.FMMSJSONFormatter",
        },
        "simple": {
            "format": "[{levelname}] {name}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": env("LOG_LEVEL"),
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "django.db.backends": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "fmms": {
            "handlers": ["console"],
            "level": env("LOG_LEVEL"),
            "propagate": False,
        },
    },
}

# ──────────────────────────────────────────────────────────────────────────────
# SAP Integration — credentials loaded from environment
# ──────────────────────────────────────────────────────────────────────────────
SAP_HOST = env("SAP_HOST", default="")
SAP_CLIENT = env("SAP_CLIENT", default="")
SAP_USER = env("SAP_USER", default="")
SAP_PASSWORD = env("SAP_PASSWORD", default="")
SAP_SYSTEM_ID = env("SAP_SYSTEM_ID", default="")
SAP_MAX_RETRIES = env.int("SAP_MAX_RETRIES", default=3)
SAP_RETRY_BACKOFF_FACTOR = env.float("SAP_RETRY_BACKOFF_FACTOR", default=2.0)
SAP_REQUEST_TIMEOUT = env.int("SAP_REQUEST_TIMEOUT", default=30)

# ──────────────────────────────────────────────────────────────────────────────
# FMMS Application Settings
# ──────────────────────────────────────────────────────────────────────────────
FMMS_SERVICE_NAME = "fmms"
FMMS_API_VERSION = "v1"
