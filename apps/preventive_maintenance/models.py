"""Model shim — re-exports ORM models for Django auto-discovery."""

from apps.preventive_maintenance.infrastructure.models import (
    PMPlanModel,
    PMWorkOrderModel,
)

__all__ = ["PMPlanModel", "PMWorkOrderModel"]
