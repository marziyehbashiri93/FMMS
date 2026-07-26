"""Unit tests for PostgreSQL database bootstrap."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
from django.test import override_settings
from psycopg2 import OperationalError

from infrastructure.database.bootstrap import (
    BootstrapResult,
    DatabaseBootstrapError,
    PostgresConnectionConfig,
    build_postgres_config,
    ensure_database_exists,
    ensure_database_from_django_settings,
)


def _config(**overrides: Any) -> PostgresConnectionConfig:
    payload: dict[str, Any] = {
        "db_name": "fmms",
        "user": "fmms",
        "password": "secret",
        "host": "localhost",
        "port": 5432,
        "maintenance_db": "postgres",
    }
    payload.update(overrides)
    return PostgresConnectionConfig(**payload)


@pytest.mark.unit
class TestBuildPostgresConfig:
    """Validation for discrete PostgreSQL settings."""

    def test_builds_django_database_without_url(self) -> None:
        """Django settings dict uses discrete fields, not DATABASE_URL."""
        config = build_postgres_config(
            db_name="fmms",
            user="fmms",
            password="secret",
            host="db",
            port="5432",
        )
        django_db = config.as_django_database()
        assert django_db["ENGINE"] == "django.db.backends.postgresql"
        assert django_db["NAME"] == "fmms"
        assert django_db["USER"] == "fmms"
        assert django_db["PASSWORD"] == "secret"
        assert django_db["HOST"] == "db"
        assert django_db["PORT"] == "5432"
        assert "URL" not in django_db

    def test_missing_host_raises(self) -> None:
        """Blank host is rejected with a clear error."""
        with pytest.raises(DatabaseBootstrapError, match="POSTGRES_HOST"):
            build_postgres_config(
                db_name="fmms",
                user="fmms",
                password="x",
                host="",
                port=5432,
            )


@pytest.mark.unit
class TestEnsureDatabaseExists:
    """Bootstrap create / exists / credential failure paths."""

    def test_database_exists_skips_creation(self) -> None:
        """When the database exists, CREATE DATABASE is not attempted."""
        cursor = MagicMock()
        cursor.fetchone.return_value = (1,)
        cursor_cm = MagicMock()
        cursor_cm.__enter__.return_value = cursor
        cursor_cm.__exit__.return_value = False

        conn = MagicMock()
        conn.cursor.return_value = cursor_cm
        connect = MagicMock(return_value=conn)

        result = ensure_database_exists(_config(), connect=connect)

        assert result == BootstrapResult(
            action="exists",
            database="fmms",
            host="localhost",
            port=5432,
        )
        connect.assert_called_once()
        # Only the existence SELECT — no CREATE DATABASE
        executed_sql = " ".join(
            str(call.args[0]) for call in cursor.execute.call_args_list
        )
        assert "pg_database" in executed_sql or cursor.execute.call_count == 1
        assert cursor.execute.call_count == 1

    def test_database_missing_creates(self) -> None:
        """Missing database triggers a single CREATE DATABASE."""
        cursor = MagicMock()
        cursor.fetchone.return_value = None
        cursor_cm = MagicMock()
        cursor_cm.__enter__.return_value = cursor
        cursor_cm.__exit__.return_value = False

        conn = MagicMock()
        conn.cursor.return_value = cursor_cm
        conn.autocommit = False
        connect = MagicMock(return_value=conn)

        result = ensure_database_exists(_config(), connect=connect)

        assert result.action == "created"
        assert cursor.execute.call_count == 2
        conn.close.assert_called_once()

    def test_invalid_credentials_raise_clear_error(self) -> None:
        """OperationalError on connect becomes DatabaseBootstrapError."""

        def boom(**_kwargs: Any) -> None:
            raise OperationalError('password authentication failed for user "fmms"')

        with pytest.raises(DatabaseBootstrapError, match="Unable to connect"):
            ensure_database_exists(_config(), connect=boom)

    def test_repeated_runs_are_idempotent(self) -> None:
        """Calling bootstrap twice when DB exists never attempts creation."""
        cursor = MagicMock()
        cursor.fetchone.return_value = (1,)
        cursor_cm = MagicMock()
        cursor_cm.__enter__.return_value = cursor
        cursor_cm.__exit__.return_value = False
        conn = MagicMock()
        conn.cursor.return_value = cursor_cm
        connect = MagicMock(return_value=conn)

        first = ensure_database_exists(_config(), connect=connect)
        second = ensure_database_exists(_config(), connect=connect)

        assert first.action == "exists"
        assert second.action == "exists"
        assert connect.call_count == 2
        assert cursor.execute.call_count == 2


@pytest.mark.unit
@pytest.mark.django_db
class TestEnsureDatabaseFromDjangoSettings:
    """Settings-aware bootstrap skips SQLite test engine."""

    @override_settings(
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": ":memory:",
            }
        }
    )
    def test_sqlite_test_settings_are_skipped(self) -> None:
        """Test settings use SQLite — bootstrap must no-op."""
        connect = MagicMock()
        result = ensure_database_from_django_settings(connect=connect)
        assert result.action == "skipped"
        connect.assert_not_called()
