"""Model shim for Django app auto-discovery."""

from apps.material.infrastructure.models import (
    CentralStockModel,
    MaterialRequestItemModel,
    MaterialRequestModel,
)

__all__ = [
    "CentralStockModel",
    "MaterialRequestModel",
    "MaterialRequestItemModel",
]
