"""Read port for resolving vehicle odometer values at fault-report time."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class FaultVehicleOdometerReading:
    """Latest vehicle odometer reading used for SAP measurement updates."""

    odometer_km: int
    reading_date: date
    recorded_at: datetime


class IFaultVehicleOdometerReader(ABC):
    """Read the latest odometer value for a vehicle."""

    @abstractmethod
    def get_latest(
        self,
        vehicle_id: uuid.UUID,
    ) -> FaultVehicleOdometerReading | None:
        """Return the latest odometer reading, if one exists."""
