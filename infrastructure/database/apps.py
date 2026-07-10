"""Django app config for infrastructure database utilities."""

from __future__ import annotations

from django.apps import AppConfig


class DatabaseConfig(AppConfig):
    """Registers management commands for database bootstrap."""

    name = "infrastructure.database"
    label = "fmms_database"
    verbose_name = "FMMS Database Infrastructure"

    def ready(self) -> None:
        """No-op ready hook — bootstrap is explicit via command / WSGI."""
