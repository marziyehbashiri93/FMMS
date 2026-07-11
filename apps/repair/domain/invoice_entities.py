"""Domain entities for external repair invoices."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from apps.repair.domain.exceptions import RepairOrderInvalidStateTransitionError


class ExternalRepairInvoiceStatus(StrEnum):
    """External repair invoice statuses."""

    UPLOADED = "UPLOADED"
    APPROVED = "APPROVED"
    PAID = "PAID"


@dataclass
class ExternalRepairInvoice:
    """External repair invoice aggregate."""

    id: uuid.UUID
    repair_order_id: uuid.UUID
    amount: float
    currency: str
    status: ExternalRepairInvoiceStatus
    created_by_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    vendor_id: str | None = None
    document: str | None = None

    def approve(self) -> None:
        """Approve uploaded invoice."""
        if self.status != ExternalRepairInvoiceStatus.UPLOADED:
            raise RepairOrderInvalidStateTransitionError(
                current_status=self.status.value,
                target_status=ExternalRepairInvoiceStatus.APPROVED.value,
            )
        self.status = ExternalRepairInvoiceStatus.APPROVED
