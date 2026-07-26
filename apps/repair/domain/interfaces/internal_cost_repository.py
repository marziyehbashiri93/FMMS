"""Repository port for internal repair cost documents."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from apps.repair.domain.internal_cost_entities import InternalRepairCost


class IInternalRepairCostRepository(ABC):
    """Persist internal workshop cost registrations."""

    @abstractmethod
    def save(self, cost: InternalRepairCost) -> InternalRepairCost:
        """Create or update a cost document."""

    @abstractmethod
    def get_by_repair_order(self, repair_order_id: uuid.UUID) -> InternalRepairCost | None:
        """Return the cost document for a repair order, if any."""
