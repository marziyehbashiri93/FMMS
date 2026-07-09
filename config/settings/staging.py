"""
FMMS Staging Settings.

Mirrors production configuration with test credentials.
Used for QA and pre-production validation.
"""

from .base import *  # noqa: F401, F403
from .base import env

# ──────────────────────────────────────────────────────────────────────────────
# Core
# ──────────────────────────────────────────────────────────────────────────────
DEBUG = False
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")

# ──────────────────────────────────────────────────────────────────────────────
# Security — production-like but not fully hardened
# ──────────────────────────────────────────────────────────────────────────────
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=False)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])

# ──────────────────────────────────────────────────────────────────────────────
# Sentry — error tracking for staging
# ──────────────────────────────────────────────────────────────────────────────
SENTRY_DSN = env("SENTRY_DSN", default="")
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        environment="staging",
        traces_sample_rate=0.1,
        send_default_pii=False,
    )

# ──────────────────────────────────────────────────────────────────────────────
# Email
# ──────────────────────────────────────────────────────────────────────────────
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
