"""Model shim — re-exports ORM models for Django auto-discovery."""

from apps.driver.infrastructure.models import DriverModel

__all__ = ["DriverModel"]
