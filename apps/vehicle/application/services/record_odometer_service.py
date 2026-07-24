"""Services for recording and reading vehicle daily odometer history."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from enum import StrEnum

from django.db import transaction

from apps.vehicle.application.dto.vehicle_dto import (
    RecordVehicleOdometerDTO,
    VehicleOdometerResponseDTO,
)
from apps.vehicle.domain.interfaces.vehicle_repository import IVehicleRepository
from apps.vehicle.infrastructure.models import VehicleOdometerReadingModel
from core.exceptions.base_exception import FMMSValidationError
from core.exceptions.translation import load_or_not_found
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger("vehicle", __name__)

_MIN_DAILY_DELTA_KM = 10
_MAX_ODOMETER_KM = 2_147_483_647


class VehicleOdometerSource(StrEnum):
    """Supported sources for vehicle odometer readings."""

    DRIVER = "DRIVER"
    TECHNICIAN = "TECHNICIAN"
    ADMIN = "ADMIN"


class RecordVehicleOdometerService:
    """Create or update one daily odometer reading for a vehicle."""

    def __init__(self, vehicle_repository: IVehicleRepository) -> None:
        self._vehicle_repo = vehicle_repository

    @transaction.atomic
    def execute(self, dto: RecordVehicleOdometerDTO) -> VehicleOdometerResponseDTO:
        """Record a daily odometer value after validating monotonic growth."""
        load_or_not_found(
            lambda: self._vehicle_repo.get_by_id(dto.vehicle_id),
            message=f"Vehicle '{dto.vehicle_id}' not found.",
            details={"vehicle_id": str(dto.vehicle_id)},
        )
        current = (
            VehicleOdometerReadingModel.objects.select_for_update()
            .filter(
                vehicle_id=dto.vehicle_id,
                reading_date=dto.reading_date,
                is_deleted=False,
            )
            .first()
        )
        if current is not None:
            previous = None
        else:
            previous = (
                VehicleOdometerReadingModel.objects.filter(
                    vehicle_id=dto.vehicle_id,
                    reading_date__lt=dto.reading_date,
                    is_deleted=False,
                )
                .order_by("-reading_date")
                .first()
            )

        if previous is not None:
            minimum = previous.odometer_km + _MIN_DAILY_DELTA_KM
            if dto.odometer_km < minimum:
                raise FMMSValidationError(
                    message=(
                        "Odometer reading must be at least "
                        f"{_MIN_DAILY_DELTA_KM} km greater than the previous reading."
                    ),
                    details={
                        "vehicle_id": str(dto.vehicle_id),
                        "previous_date": str(previous.reading_date),
                        "previous_odometer_km": previous.odometer_km,
                        "minimum_odometer_km": minimum,
                        "submitted_odometer_km": dto.odometer_km,
                    },
                )

        now = datetime.now(tz=UTC)
        if current is None:
            obj, created = VehicleOdometerReadingModel.objects.update_or_create(
                vehicle_id=dto.vehicle_id,
                reading_date=dto.reading_date,
                is_deleted=False,
                defaults={
                    "odometer_km": dto.odometer_km,
                    "source": dto.source,
                    "recorded_by_id": dto.recorded_by,
                    "recorded_at": now,
                },
            )
        else:
            current.odometer_km = dto.odometer_km
            current.source = dto.source
            current.recorded_by_id = dto.recorded_by
            current.recorded_at = now
            current.save(
                update_fields=[
                    "odometer_km",
                    "source",
                    "recorded_by_id",
                    "recorded_at",
                    "updated_at",
                ]
            )
            obj = current
            created = False
        logger.info(
            "Vehicle odometer recorded",
            extra={
                "domain": "vehicle",
                "service": "RecordVehicleOdometerService",
                "operation": "execute",
                "request_id": dto.request_id,
                "vehicle_id": str(dto.vehicle_id),
                "reading_date": str(dto.reading_date),
                "record_created": created,
            },
        )
        return _to_response_dto(obj)


class ListVehicleOdometerHistoryService:
    """List odometer readings for one vehicle in newest-first order."""

    def __init__(self, vehicle_repository: IVehicleRepository) -> None:
        self._vehicle_repo = vehicle_repository

    def execute(
        self,
        vehicle_id: uuid.UUID,
        *,
        from_date: date | None = None,
        to_date: date | None = None,
        request_id: str = "",
    ) -> list[VehicleOdometerResponseDTO]:
        """Return all non-deleted odometer readings for ``vehicle_id``."""
        load_or_not_found(
            lambda: self._vehicle_repo.get_by_id(vehicle_id),
            message=f"Vehicle '{vehicle_id}' not found.",
            details={"vehicle_id": str(vehicle_id)},
        )
        qs = VehicleOdometerReadingModel.objects.filter(
            vehicle_id=vehicle_id,
            is_deleted=False,
        )
        if from_date is not None:
            qs = qs.filter(reading_date__gte=from_date)
        if to_date is not None:
            qs = qs.filter(reading_date__lte=to_date)
        qs = qs.order_by("-reading_date")
        return [_to_response_dto(obj) for obj in qs]


class GetVehicleCurrentOdometerService:
    """Return the latest odometer reading for one vehicle."""

    def __init__(self, vehicle_repository: IVehicleRepository) -> None:
        self._vehicle_repo = vehicle_repository

    def execute(
        self,
        vehicle_id: uuid.UUID,
        request_id: str = "",
    ) -> VehicleOdometerResponseDTO:
        """Return the newest non-deleted odometer reading for ``vehicle_id``."""
        del request_id
        load_or_not_found(
            lambda: self._vehicle_repo.get_by_id(vehicle_id),
            message=f"Vehicle '{vehicle_id}' not found.",
            details={"vehicle_id": str(vehicle_id)},
        )
        obj = (
            VehicleOdometerReadingModel.objects.filter(
                vehicle_id=vehicle_id,
                is_deleted=False,
            )
            .order_by("-reading_date")
            .first()
        )
        current = load_or_not_found(
            lambda: obj,
            message=f"Vehicle '{vehicle_id}' has no odometer reading.",
            details={"vehicle_id": str(vehicle_id)},
        )
        return _to_response_dto(current)


def _to_response_dto(
    obj: VehicleOdometerReadingModel,
) -> VehicleOdometerResponseDTO:
    return VehicleOdometerResponseDTO(
        id=obj.id,
        vehicle_id=obj.vehicle_id,
        reading_date=obj.reading_date,
        odometer_km=obj.odometer_km,
        source=obj.source,
        recorded_by=obj.recorded_by_id,
        recorded_at=obj.recorded_at,
        updated_at=obj.updated_at,
    )
