"""Vehicle odometer read models used by other application services."""

from __future__ import annotations

import uuid

from apps.fault.application.interfaces.vehicle_odometer_reader import (
    FaultVehicleOdometerReading,
    IFaultVehicleOdometerReader,
)
from apps.vehicle.infrastructure.models import VehicleOdometerReadingModel


class DjangoFaultVehicleOdometerReader(IFaultVehicleOdometerReader):
    """Resolve latest non-deleted vehicle odometer reading for fault SAP sync."""

    def get_latest(
        self,
        vehicle_id: uuid.UUID,
    ) -> FaultVehicleOdometerReading | None:
        """Return the latest odometer reading for ``vehicle_id``."""
        row = (
            VehicleOdometerReadingModel.objects.filter(
                vehicle_id=vehicle_id,
                is_deleted=False,
            )
            .order_by("-reading_date", "-recorded_at")
            .first()
        )
        if row is None:
            return None
        return FaultVehicleOdometerReading(
            odometer_km=row.odometer_km,
            reading_date=row.reading_date,
            recorded_at=row.recorded_at,
        )
