"""Repository interfaces for handover records."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from apps.handover.domain.entities import VehicleHandover


class IVehicleHandoverRepository(ABC):
    """Vehicle handover repository port."""

    @abstractmethod
    def get_by_id(self, handover_id: uuid.UUID) -> VehicleHandover:
        """Get one handover by id."""

    @abstractmethod
    def get_by_repair_order(self, repair_order_id: uuid.UUID) -> VehicleHandover | None:
        """Get handover by repair order."""

    @abstractmethod
    def list_all(self) -> list[VehicleHandover]:
        """List handovers."""

    @abstractmethod
    def save(self, handover: VehicleHandover) -> VehicleHandover:
        """Persist handover aggregate."""
