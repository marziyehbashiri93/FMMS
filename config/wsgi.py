"""WSGI config for FMMS project."""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

# Ensure Django settings are loaded before bootstrap (reads DATABASES).
import django

django.setup()

from infrastructure.database.bootstrap import (  # noqa: E402
    DatabaseBootstrapError,
    ensure_database_from_django_settings,
)

try:
    ensure_database_from_django_settings()
except DatabaseBootstrapError:
    # Re-raise so process managers surface a clear startup failure.
    raise

from django.core.wsgi import get_wsgi_application  # noqa: E402

application = get_wsgi_application()
