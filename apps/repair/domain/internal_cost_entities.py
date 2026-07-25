"""Domain entities for internal workshop financial registration."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum


class InternalRepairCostStatus(StrEnum):
    """Lifecycle of an internal repair cost document."""

    DRAFT = "DRAFT"
    REGISTERED = "REGISTERED"


@dataclass
class InternalRepairCost:
    """Financial registration for an INTERNAL workshop repair."""

    id: uuid.UUID
    repair_order_id: uuid.UUID
    invoice_number: str
    labor_cost: Decimal
    parts_cost: Decimal
    service_cost: Decimal
    currency: str
    status: InternalRepairCostStatus
    notes: str
    registered_by_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    @property
    def total_cost(self) -> Decimal:
        """Return sum of labor, parts, and service costs."""
        return self.labor_cost + self.parts_cost + self.service_cost

    def register(self) -> None:
        """Mark the cost document as registered."""
        self.status = InternalRepairCostStatus.REGISTERED
