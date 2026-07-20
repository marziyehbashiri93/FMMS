"""Read-only services for retrieving vehicle data.

No mutations happen here.  These services are query-side only.
"""

from __future__ import annotations

import uuid

from apps.vehicle.application.dto.vehicle_dto import VehicleResponseDTO
from apps.vehicle.domain.entities import VEHICLE_STATUS_LABELS, Vehicle, VehicleStatus
from apps.vehicle.domain.interfaces.vehicle_repository import IVehicleRepository
from core.exceptions.translation import load_or_not_found
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger("vehicle", __name__)


def _to_response_dto(vehicle: Vehicle) -> VehicleResponseDTO:
    """Map domain entity → response DTO."""
    return VehicleResponseDTO(
        id=vehicle.id,
        vehicle_number=vehicle.vehicle_number.value,
        license_plate=vehicle.license_plate.value,
        status=vehicle.status,
        status_label=VEHICLE_STATUS_LABELS[vehicle.status],
        created_at=vehicle.created_at,
        updated_at=vehicle.updated_at,
        commissioning_date=vehicle.commissioning_date,
        driver1_customer_number=vehicle.driver1_customer_number,
        driver2_customer_number=vehicle.driver2_customer_number,
    )


class GetVehicleService:
    """Fetch a single vehicle by its UUID.

    Args:
        vehicle_repository: Concrete ``IVehicleRepository``.
    """

    def __init__(self, vehicle_repository: IVehicleRepository) -> None:
        self._repo = vehicle_repository

    def execute(
        self, vehicle_id: uuid.UUID, request_id: str = ""
    ) -> VehicleResponseDTO:
        """Return the vehicle identified by ``vehicle_id``.

        Args:
            vehicle_id: Target vehicle UUID.
            request_id: Optional correlation ID for structured logging.

        Returns:
            ``VehicleResponseDTO`` for the requested vehicle.

        Raises:
            FMMSNotFoundError: If no vehicle with ``vehicle_id`` exists.
        """
        logger.info(
            "Fetching vehicle",
            extra={
                "domain": "vehicle",
                "service": "GetVehicleService",
                "operation": "execute",
                "request_id": request_id,
                "entity_id": str(vehicle_id),
            },
        )

        vehicle = load_or_not_found(
            lambda: self._repo.get_by_id(vehicle_id),
            message=f"Vehicle '{vehicle_id}' not found.",
            details={"vehicle_id": str(vehicle_id)},
        )

        logger.info(
            "Vehicle fetched",
            extra={
                "domain": "vehicle",
                "service": "GetVehicleService",
                "operation": "execute",
                "request_id": request_id,
                "entity_id": str(vehicle_id),
                "result": "success",
            },
        )

        return _to_response_dto(vehicle)


class ListVehiclesService:
    """Fetch a filtered list of vehicles.

    Args:
        vehicle_repository: Concrete ``IVehicleRepository``.
    """

    def __init__(self, vehicle_repository: IVehicleRepository) -> None:
        self._repo = vehicle_repository

    def execute(
        self,
        status: VehicleStatus | None = None,
        request_id: str = "",
    ) -> list[VehicleResponseDTO]:
        """Return vehicles optionally filtered by lifecycle status.

        When ``status`` is ``None`` all active vehicles are returned via
        ``IVehicleRepository.list_active()``.  When a specific status is
        provided, ``IVehicleRepository.list_by_status()`` is used instead.

        Args:
            status: Optional status filter.
            request_id: Optional correlation ID for structured logging.

        Returns:
            Ordered list of ``VehicleResponseDTO`` objects.
        """
        logger.info(
            "Listing vehicles",
            extra={
                "domain": "vehicle",
                "service": "ListVehiclesService",
                "operation": "execute",
                "request_id": request_id,
                "status_filter": status.value if status else "ACTIVE",
            },
        )

        vehicles = (
            self._repo.list_by_status(status)
            if status is not None
            else self._repo.list_active()
        )

        logger.info(
            "Vehicles listed",
            extra={
                "domain": "vehicle",
                "service": "ListVehiclesService",
                "operation": "execute",
                "request_id": request_id,
                "result": "success",
                "count": len(vehicles),
            },
        )

        return [_to_response_dto(v) for v in vehicles]
