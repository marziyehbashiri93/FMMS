"""Domain entities for vehicle handover."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from apps.handover.domain.exceptions import VehicleHandoverInvalidStateError


class VehicleHandoverStatus(StrEnum):
    """Vehicle handover statuses."""

    WAITING_DRIVER_CONFIRMATION = "WAITING_DRIVER_CONFIRMATION"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


@dataclass
class VehicleHandover:
    """Handover aggregate root."""

    id: uuid.UUID
    repair_order_id: uuid.UUID
    vehicle_id: uuid.UUID
    status: VehicleHandoverStatus
    created_at: datetime
    updated_at: datetime
    driver_id: uuid.UUID | None = None
    comment: str | None = None
    confirmed_at: datetime | None = None

    def confirm(
        self,
        accepted: bool,
        comment: str | None = None,
        *,
        confirmed_at: datetime | None = None,
        driver_id: uuid.UUID | None = None,
    ) -> None:
        """Apply handover confirmation."""
        if self.status != VehicleHandoverStatus.WAITING_DRIVER_CONFIRMATION:
            target = (
                VehicleHandoverStatus.ACCEPTED
                if accepted
                else VehicleHandoverStatus.REJECTED
            )
            raise VehicleHandoverInvalidStateError(self.status.value, target.value)
        self.status = (
            VehicleHandoverStatus.ACCEPTED
            if accepted
            else VehicleHandoverStatus.REJECTED
        )
        self.comment = comment
        self.confirmed_at = confirmed_at
        if driver_id is not None:
            self.driver_id = driver_id
