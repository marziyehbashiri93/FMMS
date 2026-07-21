"""Read-only services for retrieving vehicle data.

No mutations happen here.  These services are query-side only.
"""

from __future__ import annotations

import uuid
from typing import Any

from apps.vehicle.application.dto.vehicle_dto import VehicleResponseDTO
from apps.vehicle.domain.entities import VEHICLE_STATUS_LABELS, Vehicle, VehicleStatus
from apps.vehicle.domain.interfaces.vehicle_repository import IVehicleRepository
from core.exceptions.base_exception import FMMSValidationError
from core.exceptions.translation import load_or_not_found
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger("vehicle", __name__)

_VEHICLE_ORDERING_FIELDS = frozenset(
    {
        "vehicle_number",
        "license_plate",
        "status",
        "created_at",
        "updated_at",
        "commissioning_date",
        "driver1_customer_number",
        "driver2_customer_number",
    }
)


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
        ordering: str = "",
        request_id: str = "",
    ) -> list[VehicleResponseDTO]:
        """Return vehicles optionally filtered by lifecycle status.

        When ``status`` is ``None`` all active vehicles are returned via
        ``IVehicleRepository.list_active()``.  When a specific status is
        provided, ``IVehicleRepository.list_by_status()`` is used instead.

        Args:
            status: Optional status filter.
            ordering: Optional ordering field. Prefix with ``-`` for descending.
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
                "ordering": ordering,
            },
        )

        vehicles = (
            self._repo.list_by_status(status)
            if status is not None
            else self._repo.list_active()
        )
        vehicles = _sort_vehicles(vehicles, ordering)

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


def _sort_vehicles(vehicles: list[Vehicle], ordering: str) -> list[Vehicle]:
    """Return vehicles sorted by a whitelisted response field."""
    if not ordering:
        return vehicles
    descending = ordering.startswith("-")
    field_name = ordering[1:] if descending else ordering
    if field_name not in _VEHICLE_ORDERING_FIELDS:
        raise FMMSValidationError(
            message=f"Unsupported vehicle ordering field: {field_name}.",
            error_code="INVALID_ORDERING",
            details={
                "field": field_name,
                "allowed_fields": sorted(_VEHICLE_ORDERING_FIELDS),
            },
        )
    return sorted(
        vehicles,
        key=lambda vehicle: _sortable_value(getattr(vehicle, field_name)),
        reverse=descending,
    )


def _sortable_value(value: Any) -> Any:
    """Return a primitive value suitable for stable sorting."""
    return getattr(value, "value", value) or ""
