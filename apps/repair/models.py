"""Model shim — re-exports ORM models for Django auto-discovery."""

from apps.repair.infrastructure.models import (
    RepairActivityModel,
    RepairOrderModel,
    RepairPartModel,
)

__all__ = ["RepairOrderModel", "RepairActivityModel", "RepairPartModel"]
