"""ASGI config for FMMS project."""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

import django

django.setup()

from infrastructure.database.bootstrap import (  # noqa: E402
    DatabaseBootstrapError,
    ensure_database_from_django_settings,
)

try:
    ensure_database_from_django_settings()
except DatabaseBootstrapError:
    raise

from django.core.asgi import get_asgi_application  # noqa: E402

application = get_asgi_application()
