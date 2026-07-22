"""Read-only services for retrieving vehicle data.

No mutations happen here.  These services are query-side only.
"""

from __future__ import annotations

import uuid
from typing import Any

from apps.driver.domain.exceptions import DriverNotFoundError
from apps.driver.domain.interfaces.driver_repository import IDriverRepository
from apps.driver.domain.value_objects import CustomerNumber
from apps.vehicle.application.dto.vehicle_dto import (
    VehicleAssignedDriverDTO,
    VehicleResponseDTO,
)
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
    }
)


def _to_response_dto(
    vehicle: Vehicle,
    *,
    driver1: VehicleAssignedDriverDTO | None = None,
    driver2: VehicleAssignedDriverDTO | None = None,
) -> VehicleResponseDTO:
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
        driver1=driver1,
        driver2=driver2,
    )


class GetVehicleService:
    """Fetch a single vehicle by its UUID.

    Args:
        vehicle_repository: Concrete ``IVehicleRepository``.
        driver_repository: Concrete ``IDriverRepository``.
    """

    def __init__(
        self,
        vehicle_repository: IVehicleRepository,
        driver_repository: IDriverRepository,
    ) -> None:
        self._repo = vehicle_repository
        self._driver_repo = driver_repository

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

        return _to_response_dto(
            vehicle,
            driver1=_assigned_driver(
                self._driver_repo,
                vehicle.driver1_customer_number,
            ),
            driver2=_assigned_driver(
                self._driver_repo,
                vehicle.driver2_customer_number,
            ),
        )


class ListVehiclesService:
    """Fetch a filtered list of vehicles.

    Args:
        vehicle_repository: Concrete ``IVehicleRepository``.
        driver_repository: Concrete ``IDriverRepository``.
    """

    def __init__(
        self,
        vehicle_repository: IVehicleRepository,
        driver_repository: IDriverRepository,
    ) -> None:
        self._repo = vehicle_repository
        self._driver_repo = driver_repository

    def execute(
        self,
        status: VehicleStatus | None = None,
        ordering: str = "",
        search: str = "",
        request_id: str = "",
    ) -> list[VehicleResponseDTO]:
        """Return vehicles optionally filtered by lifecycle status.

        When ``status`` is ``None`` all active vehicles are returned via
        ``IVehicleRepository.list_active()``.  When a specific status is
        provided, ``IVehicleRepository.list_by_status()`` is used instead.

        Args:
            status: Optional status filter.
            ordering: Optional ordering field. Prefix with ``-`` for descending.
            search: Optional search text for license plate or SAP vehicle number.
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
                "search": search,
            },
        )

        vehicles = (
            self._repo.list_by_status(status)
            if status is not None
            else self._repo.list_active()
        )
        vehicles = _filter_vehicles_by_search(vehicles, search)
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

        assigned_drivers = _assigned_drivers_by_customer_number(
            self._driver_repo,
            vehicles,
        )
        return [
            _to_response_dto(
                vehicle,
                driver1=_assigned_driver_from_map(
                    assigned_drivers,
                    vehicle.driver1_customer_number,
                ),
                driver2=_assigned_driver_from_map(
                    assigned_drivers,
                    vehicle.driver2_customer_number,
                ),
            )
            for vehicle in vehicles
        ]


def _filter_vehicles_by_search(vehicles: list[Vehicle], search: str) -> list[Vehicle]:
    """Return vehicles matching plate or SAP vehicle number search text."""
    needle = search.strip().casefold()
    if not needle:
        return vehicles
    return [
        vehicle
        for vehicle in vehicles
        if needle in vehicle.license_plate.value.casefold()
        or needle in vehicle.vehicle_number.value.casefold()
    ]


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


def _assigned_driver(
    driver_repository: IDriverRepository,
    customer_number: str | None,
) -> VehicleAssignedDriverDTO | None:
    """Return assigned driver details by SAP customer number, when available."""
    if not customer_number:
        return None
    try:
        driver = driver_repository.get_by_customer_number(CustomerNumber(customer_number))
    except (DriverNotFoundError, ValueError):
        return VehicleAssignedDriverDTO(
            id=None,
            customer_number=customer_number,
            name=None,
        )
    return VehicleAssignedDriverDTO(
        id=driver.id,
        customer_number=driver.customer_number.value,
        name=driver.name,
    )


def _assigned_drivers_by_customer_number(
    driver_repository: IDriverRepository,
    vehicles: list[Vehicle],
) -> dict[str, VehicleAssignedDriverDTO]:
    """Return assigned driver DTOs for all vehicle driver customer numbers."""
    customer_numbers = {
        customer_number
        for vehicle in vehicles
        for customer_number in (
            vehicle.driver1_customer_number,
            vehicle.driver2_customer_number,
        )
        if customer_number
    }
    drivers = driver_repository.list_by_customer_numbers(customer_numbers)
    return {
        driver.customer_number.value: VehicleAssignedDriverDTO(
            id=driver.id,
            customer_number=driver.customer_number.value,
            name=driver.name,
        )
        for driver in drivers
    }


def _assigned_driver_from_map(
    assigned_drivers: dict[str, VehicleAssignedDriverDTO],
    customer_number: str | None,
) -> VehicleAssignedDriverDTO | None:
    """Return assigned driver from a prepared lookup map."""
    if not customer_number:
        return None
    return assigned_drivers.get(
        customer_number,
        VehicleAssignedDriverDTO(id=None, customer_number=customer_number, name=None),
    )
