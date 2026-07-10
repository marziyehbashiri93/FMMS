"""Repository port for repair-order timeline events."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from apps.repair.domain.entities import RepairOrderEvent


class IRepairOrderEventRepository(ABC):
    """Persist and query repair-order lifecycle events."""

    @abstractmethod
    def append(self, event: RepairOrderEvent) -> RepairOrderEvent:
        """Persist a new timeline event."""

    @abstractmethod
    def list_by_repair_order(
        self, repair_order_id: uuid.UUID
    ) -> list[RepairOrderEvent]:
        """Return events for a repair order ordered by ``created_at`` ascending."""
