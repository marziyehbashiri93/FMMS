"""Application DTOs for handover APIs."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from apps.handover.domain.entities import VehicleHandoverStatus


@dataclass(frozen=True)
class ConfirmVehicleHandoverDTO:
    """Confirm handover input DTO."""

    handover_id: uuid.UUID
    accepted: bool
    comment: str | None
    request_id: str
    confirmed_by: uuid.UUID


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
