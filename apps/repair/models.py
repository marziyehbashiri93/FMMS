"""Model shim — re-exports ORM models for Django auto-discovery."""

from apps.repair.infrastructure.models import (
    ExternalRepairInvoiceModel,
    InternalRepairCostModel,
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
    "InternalRepairCostModel",
]
