"""PostgreSQL database bootstrap utilities.

Ensures the configured application database exists before Django connects
for migrations or request handling. Creation is idempotent and never drops
or recreates an existing database.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

import psycopg2
from psycopg2 import OperationalError, sql
from psycopg2.extensions import connection as pg_connection

from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger("core", __name__)

BootstrapAction = Literal["exists", "created", "skipped"]
ConnectFactory = Callable[..., pg_connection]


class DatabaseBootstrapError(Exception):
    """Raised when database bootstrap cannot complete safely.

    Args:
        message: Human-readable failure description (never includes passwords).
    """

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


@dataclass(frozen=True)
class PostgresConnectionConfig:
    """Connection parameters for PostgreSQL bootstrap and Django settings.

    Attributes:
        db_name: Target application database name.
        user: PostgreSQL role used to connect and create the database.
        password: Role password.
        host: PostgreSQL host.
        port: PostgreSQL port.
        maintenance_db: Database used for existence checks / CREATE DATABASE.
    """

    db_name: str
    user: str
    password: str
    host: str
    port: int
    maintenance_db: str = "postgres"

    def as_django_database(self) -> dict[str, Any]:
        """Build a Django ``DATABASES['default']`` configuration dict.

        Returns:
            Django database settings without embedding credentials in a URL.
        """
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": self.db_name,
            "USER": self.user,
            "PASSWORD": self.password,
            "HOST": self.host,
            "PORT": str(self.port),
        }


@dataclass(frozen=True)
class BootstrapResult:
    """Outcome of a bootstrap attempt.

    Attributes:
        action: ``exists``, ``created``, or ``skipped`` (non-PostgreSQL).
        database: Target database name.
        host: PostgreSQL host.
        port: PostgreSQL port.
    """

    action: BootstrapAction
    database: str
    host: str
    port: int


def build_postgres_config(
    *,
    db_name: str,
    user: str,
    password: str,
    host: str,
    port: int | str,
    maintenance_db: str = "postgres",
) -> PostgresConnectionConfig:
    """Validate and build a ``PostgresConnectionConfig``.

    Args:
        db_name: Target database name.
        user: PostgreSQL user.
        password: PostgreSQL password.
        host: PostgreSQL host.
        port: PostgreSQL port.
        maintenance_db: Maintenance database for CREATE DATABASE.

    Returns:
        Validated configuration.

    Raises:
        DatabaseBootstrapError: If required fields are blank or port is invalid.
    """
    db_name = db_name.strip()
    user = user.strip()
    host = host.strip()
    maintenance_db = (maintenance_db or "postgres").strip() or "postgres"

    missing: list[str] = []
    if not db_name:
        missing.append("POSTGRES_DB")
    if not user:
        missing.append("POSTGRES_USER")
    if not host:
        missing.append("POSTGRES_HOST")
    if missing:
        raise DatabaseBootstrapError(
            "Missing required PostgreSQL configuration values: " + ", ".join(missing)
        )

    try:
        port_int = int(port)
    except (TypeError, ValueError) as exc:
        raise DatabaseBootstrapError(f"Invalid POSTGRES_PORT value: {port!r}.") from exc
    if not (1 <= port_int <= 65535):
        raise DatabaseBootstrapError(f"POSTGRES_PORT out of range: {port_int}.")

    return PostgresConnectionConfig(
        db_name=db_name,
        user=user,
        password=password,
        host=host,
        port=port_int,
        maintenance_db=maintenance_db,
    )


def _default_connect(**kwargs: Any) -> pg_connection:
    """Open a psycopg2 connection with the given keyword arguments."""
    return psycopg2.connect(**kwargs)


def _database_exists(conn: pg_connection, db_name: str) -> bool:
    """Return True if ``db_name`` is present in ``pg_database``."""
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (db_name,),
        )
        return cursor.fetchone() is not None


def _create_database(conn: pg_connection, db_name: str) -> None:
    """Create ``db_name`` using a safely quoted identifier."""
    previous = conn.autocommit
    conn.autocommit = True
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                sql.SQL("CREATE DATABASE {}").format(sql.Identifier(db_name))
            )
    finally:
        conn.autocommit = previous


def ensure_database_exists(
    config: PostgresConnectionConfig,
    *,
    connect: ConnectFactory | None = None,
) -> BootstrapResult:
    """Ensure the target PostgreSQL database exists.

    Connects to the maintenance database with the configured credentials.
    If the application database is missing, creates it. Never drops or
    recreates an existing database.

    Args:
        config: PostgreSQL connection parameters.
        connect: Optional injectable connection factory (for tests).

    Returns:
        ``BootstrapResult`` describing the action taken.

    Raises:
        DatabaseBootstrapError: On authentication failure or other operational errors.
    """
    connect_fn = connect or _default_connect
    log_extra = {
        "domain": "core",
        "service": "DatabaseBootstrap",
        "operation": "ensure_database_exists",
        "database_host": config.host,
        "database_port": config.port,
        "database_name": config.db_name,
        "maintenance_db": config.maintenance_db,
    }

    logger.info(
        "Starting PostgreSQL database bootstrap",
        extra={**log_extra, "bootstrap_action": "check"},
    )

    try:
        conn = connect_fn(
            dbname=config.maintenance_db,
            user=config.user,
            password=config.password,
            host=config.host,
            port=config.port,
            connect_timeout=10,
        )
    except OperationalError as exc:
        safe_error = str(exc).split("password")[0].strip().rstrip(":")
        logger.error(
            "PostgreSQL bootstrap connection failed",
            extra={
                **log_extra,
                "bootstrap_action": "failed",
                "error": safe_error,
            },
        )
        raise DatabaseBootstrapError(
            "Unable to connect to PostgreSQL for database bootstrap. "
            f"host={config.host!r} port={config.port} "
            f"maintenance_db={config.maintenance_db!r} user={config.user!r}. "
            "Verify POSTGRES_HOST, POSTGRES_PORT, POSTGRES_USER, and "
            "POSTGRES_PASSWORD."
        ) from exc

    try:
        if _database_exists(conn, config.db_name):
            logger.info(
                "PostgreSQL database already exists — no creation needed",
                extra={
                    **log_extra,
                    "bootstrap_action": "exists",
                    "result": "success",
                },
            )
            return BootstrapResult(
                action="exists",
                database=config.db_name,
                host=config.host,
                port=config.port,
            )

        logger.info(
            "PostgreSQL database missing — creating",
            extra={**log_extra, "bootstrap_action": "create"},
        )
        _create_database(conn, config.db_name)
        logger.info(
            "PostgreSQL database created successfully",
            extra={
                **log_extra,
                "bootstrap_action": "created",
                "result": "success",
            },
        )
        return BootstrapResult(
            action="created",
            database=config.db_name,
            host=config.host,
            port=config.port,
        )
    except DatabaseBootstrapError:
        raise
    except Exception as exc:
        logger.error(
            "PostgreSQL database bootstrap failed",
            extra={
                **log_extra,
                "bootstrap_action": "failed",
                "error": str(exc),
            },
        )
        raise DatabaseBootstrapError(
            f"Failed to ensure database {config.db_name!r} on "
            f"{config.host}:{config.port}: {exc}"
        ) from exc
    finally:
        conn.close()


def ensure_database_from_django_settings(
    *,
    connect: ConnectFactory | None = None,
) -> BootstrapResult:
    """Run bootstrap using Django ``DATABASES['default']`` when PostgreSQL.

    Non-PostgreSQL engines (e.g. SQLite in tests) are skipped.

    Args:
        connect: Optional injectable connection factory (for tests).

    Returns:
        ``BootstrapResult`` (``skipped`` for non-PostgreSQL engines).

    Raises:
        DatabaseBootstrapError: When PostgreSQL bootstrap fails.
    """
    from django.conf import settings

    db = settings.DATABASES["default"]
    engine = str(db.get("ENGINE", ""))
    if "postgresql" not in engine:
        logger.info(
            "Skipping database bootstrap for non-PostgreSQL engine",
            extra={
                "domain": "core",
                "service": "DatabaseBootstrap",
                "operation": "ensure_database_from_django_settings",
                "bootstrap_action": "skipped",
                "engine": engine,
            },
        )
        return BootstrapResult(
            action="skipped",
            database=str(db.get("NAME", "")),
            host=str(db.get("HOST", "")),
            port=int(db.get("PORT") or 0),
        )

    config = build_postgres_config(
        db_name=str(db["NAME"]),
        user=str(db["USER"]),
        password=str(db.get("PASSWORD", "")),
        host=str(db.get("HOST") or "localhost"),
        port=int(db.get("PORT") or 5432),
        maintenance_db=str(getattr(settings, "POSTGRES_MAINTENANCE_DB", "postgres")),
    )
    return ensure_database_exists(config, connect=connect)
