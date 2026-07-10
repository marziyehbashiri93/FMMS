"""Management command: ensure the configured PostgreSQL database exists."""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from infrastructure.database.bootstrap import (
    DatabaseBootstrapError,
    ensure_database_from_django_settings,
)


class Command(BaseCommand):
    """Idempotently create the application database when missing."""

    help = (
        "Ensure the configured PostgreSQL database exists. "
        "Creates it when missing; no-ops when it already exists. "
        "Skipped for non-PostgreSQL engines (e.g. SQLite tests)."
    )

    def handle(self, *args: object, **options: object) -> None:
        """Execute database bootstrap.

        Raises:
            CommandError: When bootstrap fails.
        """
        try:
            result = ensure_database_from_django_settings()
        except DatabaseBootstrapError as exc:
            raise CommandError(exc.message) from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"Database bootstrap complete: action={result.action} "
                f"database={result.database!r} host={result.host!r} "
                f"port={result.port}"
            )
        )
