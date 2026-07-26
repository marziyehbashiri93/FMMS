"""Domain entities for material requests."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from apps.material.domain.exceptions import MaterialRequestInvalidStateError


class MaterialRequestStatus(StrEnum):
    """Lifecycle states for material requests."""

    REQUESTED = "REQUESTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"  # Legacy; transport reject is removed from the flow.
    WAITING_STOCK = "WAITING_STOCK"
    STOCK_ISSUED = "STOCK_ISSUED"
    PURCHASE_REQUIRED = "PURCHASE_REQUIRED"
    PARTIALLY_ISSUED = "PARTIALLY_ISSUED"
    RECEIVED = "RECEIVED"


class MaterialItemDecision(StrEnum):
    """Transport decision for one requested material line."""

    PENDING = "PENDING"
    FROM_STOCK = "FROM_STOCK"
    PURCHASE = "PURCHASE"


class MaterialItemStatus(StrEnum):
    """Fulfillment status for one requested material line."""

    PENDING = "PENDING"
    READY = "READY"
    PURCHASE_REQUIRED = "PURCHASE_REQUIRED"


_ALLOWED_TRANSITIONS: dict[MaterialRequestStatus, frozenset[MaterialRequestStatus]] = {
    MaterialRequestStatus.REQUESTED: frozenset({MaterialRequestStatus.APPROVED}),
    MaterialRequestStatus.APPROVED: frozenset(
        {
            MaterialRequestStatus.WAITING_STOCK,
            MaterialRequestStatus.STOCK_ISSUED,
            MaterialRequestStatus.PURCHASE_REQUIRED,
            MaterialRequestStatus.PARTIALLY_ISSUED,
        }
    ),
    MaterialRequestStatus.REJECTED: frozenset(),
    MaterialRequestStatus.WAITING_STOCK: frozenset(
        {
            MaterialRequestStatus.STOCK_ISSUED,
            MaterialRequestStatus.PURCHASE_REQUIRED,
            MaterialRequestStatus.PARTIALLY_ISSUED,
        }
    ),
    MaterialRequestStatus.STOCK_ISSUED: frozenset({MaterialRequestStatus.RECEIVED}),
    MaterialRequestStatus.PURCHASE_REQUIRED: frozenset(
        {
            MaterialRequestStatus.WAITING_STOCK,
            MaterialRequestStatus.STOCK_ISSUED,
            MaterialRequestStatus.PARTIALLY_ISSUED,
        }
    ),
    MaterialRequestStatus.PARTIALLY_ISSUED: frozenset(
        {MaterialRequestStatus.STOCK_ISSUED}
    ),
    MaterialRequestStatus.RECEIVED: frozenset(),
}


@dataclass
class MaterialRequestItem:
    """One requested material line with optional per-item fulfillment state."""

    id: uuid.UUID
    material_number: str
    quantity: Decimal
    unit_of_measure: str
    from_catalog: bool = True
    decision: MaterialItemDecision = MaterialItemDecision.PENDING
    item_status: MaterialItemStatus = MaterialItemStatus.PENDING
    available_quantity_snapshot: Decimal | None = None


@dataclass
class MaterialRequest:
    """Aggregate root for material requests."""

    id: uuid.UUID
    repair_order_id: uuid.UUID
    status: MaterialRequestStatus
    created_by_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    items: list[MaterialRequestItem] = field(default_factory=list)

    def transition_to(self, target: MaterialRequestStatus) -> None:
        """Transition to the target state if allowed."""
        if target not in _ALLOWED_TRANSITIONS.get(self.status, frozenset()):
            raise MaterialRequestInvalidStateError(self.status.value, target.value)
        self.status = target

    def approve(self) -> None:
        """Approve request (internal step before stock/purchase branching)."""
        self.transition_to(MaterialRequestStatus.APPROVED)

    def receive(self) -> None:
        """Confirm physical receipt of parts at the workshop."""
        self.transition_to(MaterialRequestStatus.RECEIVED)
