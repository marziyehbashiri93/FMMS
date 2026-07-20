"""Application DTOs for handover APIs."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from apps.handover.domain.entities import VehicleHandoverStatus


@dataclass(frozen=True)
class ConfirmVehicleHandoverDTO:
    """Confirm handover input DTO.

    For EXTERNAL repairs, accepting handover requires invoice fields so the
    driver uploads the workshop invoice at confirmation time.
    """

    handover_id: uuid.UUID
    accepted: bool
    comment: str | None
    request_id: str
    confirmed_by: uuid.UUID
    invoice_amount: Decimal | None = field(default=None)
    invoice_currency: str | None = field(default=None)
    invoice_vendor_id: str | None = field(default=None)
    invoice_document: str | None = field(default=None)


@dataclass(frozen=True)
class VehicleHandoverResponseDTO:
    """Handover output DTO."""

    id: uuid.UUID
    repair_order_id: uuid.UUID
    vehicle_id: uuid.UUID
    status: VehicleHandoverStatus
    created_at: datetime
    updated_at: datetime
    comment: str | None
    driver_id: uuid.UUID | None = None
    confirmed_at: datetime | None = None
