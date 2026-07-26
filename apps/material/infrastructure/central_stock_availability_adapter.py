"""Inventory availability backed by synced central warehouse stock (KH08)."""

from __future__ import annotations

from apps.material.domain.entities import MaterialRequestItem
from apps.material.domain.interfaces.central_stock_repository import (
    ICentralStockRepository,
)
from apps.material.domain.interfaces.inventory_availability_port import (
    IInventoryAvailabilityPort,
)


class CentralStockAvailabilityAdapter(IInventoryAvailabilityPort):
    """Check material request availability against local KH08 stock snapshot."""

    def __init__(self, stock_repository: ICentralStockRepository) -> None:
        self._repo = stock_repository

    def is_available(self, item: MaterialRequestItem) -> bool:
        """Return whether unrestricted KH08 stock covers the requested quantity."""
        available = self._repo.get_available_quantity(item.material_number)
        return available >= item.quantity
