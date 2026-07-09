"""Model shim — re-exports ORM models for Django auto-discovery."""

from apps.fault.infrastructure.models import FaultModel

__all__ = ["FaultModel"]
