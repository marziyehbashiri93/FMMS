"""
FMMS Development Settings.

Local development environment — debug mode, verbose logging, relaxed security.
Never use in production.
"""

from .base import *  # noqa: F401, F403
from .base import INSTALLED_APPS, LOGGING, MIDDLEWARE

# ──────────────────────────────────────────────────────────────────────────────
# Core
# ──────────────────────────────────────────────────────────────────────────────
DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0", "app"]  # noqa: S104

# ──────────────────────────────────────────────────────────────────────────────
# Security — relaxed for local development
# ──────────────────────────────────────────────────────────────────────────────
CORS_ALLOW_ALL_ORIGINS = True

# ──────────────────────────────────────────────────────────────────────────────
# Debug Toolbar
# ──────────────────────────────────────────────────────────────────────────────
INSTALLED_APPS = INSTALLED_APPS + ["debug_toolbar"]
MIDDLEWARE = ["debug_toolbar.middleware.DebugToolbarMiddleware"] + MIDDLEWARE
INTERNAL_IPS = ["127.0.0.1"]

# ──────────────────────────────────────────────────────────────────────────────
# Logging — verbose in development
# ──────────────────────────────────────────────────────────────────────────────
LOGGING["loggers"]["django"]["level"] = "INFO"  # type: ignore[index]
LOGGING["loggers"]["django.db.backends"]["level"] = "DEBUG"  # type: ignore[index]
LOGGING["root"]["level"] = "DEBUG"  # type: ignore[index]

# ──────────────────────────────────────────────────────────────────────────────
# Email — output to console in development
# ──────────────────────────────────────────────────────────────────────────────
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
