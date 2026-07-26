"""Repository port for vehicle component history."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from apps.vehicle.domain.component_history_entities import VehicleComponentHistory


class IVehicleComponentHistoryRepository(ABC):
    """Persist and query installed component history rows."""

    @abstractmethod
    def save(self, entry: VehicleComponentHistory) -> VehicleComponentHistory:
        """Create or update one history row."""

    @abstractmethod
    def list_by_vehicle(self, vehicle_id: uuid.UUID) -> list[VehicleComponentHistory]:
        """Return history for a vehicle, newest first."""

    @abstractmethod
    def list_by_repair_order(
        self, repair_order_id: uuid.UUID
    ) -> list[VehicleComponentHistory]:
        """Return history rows created from one repair order."""
