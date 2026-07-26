"""Domain entities for the external workshop repair workflow."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from core.exceptions.base_exception import FMMSConflictError


class ExternalWorkshopAssignmentStatus(StrEnum):
    """Lifecycle states for an external workshop assignment."""

    ACTIVE = "ACTIVE"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"


class ExternalWorkshopAssignmentCancellationReason(StrEnum):
    """Business reasons for cancelling an external workshop assignment."""

    WORKSHOP_CHANGED = "WORKSHOP_CHANGED"
    REPAIR_ORDER_CANCELLED = "REPAIR_ORDER_CANCELLED"
    DUPLICATE_ASSIGNMENT = "DUPLICATE_ASSIGNMENT"
    ADMINISTRATIVE_DECISION = "ADMINISTRATIVE_DECISION"
    OTHER = "OTHER"


class ExternalRepairReviewStatus(StrEnum):
    """Transportation administrative review states."""

    DRAFT = "DRAFT"
    COMPLETED = "COMPLETED"


@dataclass
class ExternalWorkshopAssignment:
    """Assignment of an external workshop by Transportation."""

    id: uuid.UUID
    repair_order_id: uuid.UUID
    vehicle_id: uuid.UUID
    fault_id: uuid.UUID
    workshop_name: str
    workshop_address: str
    assignment_date: datetime
    repair_reason: str
    description: str
    status: ExternalWorkshopAssignmentStatus
    assigned_by_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    workshop_id: str | None = field(default=None)
    cancellation_reason: ExternalWorkshopAssignmentCancellationReason | None = None
    cancellation_note: str | None = None
    cancelled_by_id: uuid.UUID | None = None
    cancelled_at: datetime | None = None

    def ensure_active(self) -> None:
        """Require an active assignment for workflow actions."""
        if self.status != ExternalWorkshopAssignmentStatus.ACTIVE:
            raise FMMSConflictError(
                message="External workshop assignment is not active.",
                error_code="EXTERNAL_ASSIGNMENT_NOT_ACTIVE",
                details={"assignment_id": str(self.id), "status": self.status.value},
            )

    def cancel(
        self,
        *,
        reason: ExternalWorkshopAssignmentCancellationReason,
        cancelled_by_id: uuid.UUID,
        cancelled_at: datetime,
        note: str | None = None,
    ) -> None:
        """Cancel the active assignment with an auditable business reason."""
        self.ensure_active()
        self.status = ExternalWorkshopAssignmentStatus.CANCELLED
        self.cancellation_reason = reason
        self.cancellation_note = note
        self.cancelled_by_id = cancelled_by_id
        self.cancelled_at = cancelled_at
        self.updated_at = cancelled_at

    def complete(self, completed_at: datetime) -> None:
        """Mark assignment complete when external repair workflow closes."""
        self.ensure_active()
        self.status = ExternalWorkshopAssignmentStatus.COMPLETED
        self.updated_at = completed_at


@dataclass(frozen=True)
class ExternalWorkshopDelivery:
    """Driver confirmation that the vehicle was delivered to the workshop."""

    id: uuid.UUID
    assignment_id: uuid.UUID
    repair_order_id: uuid.UUID
    vehicle_id: uuid.UUID
    delivery_datetime: datetime
    workshop_name: str
    workshop_address: str
    workshop_phone: str
    vehicle_odometer: int
    notes: str
    delivered_by_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class ExternalWorkshopPickup:
    """Driver confirmation that the repaired vehicle was picked up."""

    id: uuid.UUID
    assignment_id: uuid.UUID
    repair_order_id: uuid.UUID
    vehicle_id: uuid.UUID
    pickup_datetime: datetime
    vehicle_odometer: int
    notes: str
    picked_up_by_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


@dataclass
class ExternalRepairReview:
    """Transportation administrative review for an external repair."""

    id: uuid.UUID
    assignment_id: uuid.UUID
    repair_order_id: uuid.UUID
    invoice_attachment: str | None
    repair_services: list[dict[str, object]]
    replaced_parts: list[dict[str, object]]
    repair_cost: Decimal | None
    additional_notes: str
    sap_purchase_order_number: str | None
    sap_invoice_document_number: str | None
    status: ExternalRepairReviewStatus
    reviewed_by_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    def mark_completed(self) -> None:
        """Mark the review completed after mandatory fields are present."""
        self.status = ExternalRepairReviewStatus.COMPLETED
