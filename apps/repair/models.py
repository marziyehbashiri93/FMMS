"""Model shim — re-exports ORM models for Django auto-discovery."""

from apps.repair.infrastructure.models import (
    ExternalRepairInvoiceModel,
    RepairActivityModel,
    RepairOrderEventModel,
    RepairOrderModel,
    RepairPartModel,
)

__all__ = [
    "RepairOrderModel",
    "RepairActivityModel",
    "RepairPartModel",
    "RepairOrderEventModel",
    "ExternalRepairInvoiceModel",
]
