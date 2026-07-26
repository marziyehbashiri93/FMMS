"""
FMMS Demo Settings.

Demo API against an existing PostgreSQL database (keeps your data),
without Redis or a Celery worker:

- Postgres via POSTGRES_* env (same as development)
- LocMem cache (no Redis)
- Celery eager mode (no broker / worker)

Never use outside demos.
"""

from .base import *  # noqa: F401, F403
from .base import LOGGING

DEBUG = False
ALLOWED_HOSTS = ["*"]  # noqa: S104 — demo only

CORS_ALLOW_ALL_ORIGINS = True

# DATABASES stays as Postgres from base (POSTGRES_HOST / USER / PASSWORD / DB).

# ── Cache — in-process (no Redis) ─────────────────────────────────────────────
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "fmms-demo",
    }
}

# ── Celery — run tasks inline (no broker / worker) ────────────────────────────
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BROKER_URL = "memory://"
CELERY_RESULT_BACKEND = "cache+memory://"
CELERY_BEAT_SCHEDULE = {}

LOGGING["loggers"]["django"]["level"] = "INFO"  # type: ignore[index]
LOGGING["root"]["level"] = "INFO"  # type: ignore[index]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
