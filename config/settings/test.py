"""
FMMS Test Settings.

Overrides database to SQLite for fast, dependency-free test execution.
PostgreSQL is used in development (docker-compose) and production.
"""

from pathlib import Path

from .base import *  # noqa: F401, F403
from .base import BASE_DIR  # noqa: F401

# ──────────────────────────────────────────────────────────────────────────────
# Database — SQLite for tests (no external service required)
# ──────────────────────────────────────────────────────────────────────────────
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": Path(BASE_DIR) / "test.db",
        "TEST": {
            "NAME": Path(BASE_DIR) / "test_fmms.db",
        },
    }
}

# Disable ATOMIC_REQUESTS for test compatibility with pytest-django fixtures
DATABASES["default"]["ATOMIC_REQUESTS"] = False

# ──────────────────────────────────────────────────────────────────────────────
# Speed — disable password hashing in tests
# ──────────────────────────────────────────────────────────────────────────────
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# ──────────────────────────────────────────────────────────────────────────────
# Disable caching in tests
# ──────────────────────────────────────────────────────────────────────────────
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# Suppress debug toolbar in tests
DEBUG = False
