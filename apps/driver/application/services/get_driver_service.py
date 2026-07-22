"""Read-only services for retrieving driver data.

No mutations happen here. These services are query-side only.
"""

from __future__ import annotations

import uuid
from typing import Any

from django.db.models import Q

from apps.driver.application.dto.driver_dto import (
    DriverAssignedVehicleDTO,
    DriverResponseDTO,
)
from apps.driver.domain.entities import Driver, DriverStatus
from apps.driver.domain.interfaces.driver_repository import IDriverRepository
from apps.vehicle.infrastructure.models import VehicleModel
from core.exceptions.base_exception import FMMSValidationError
from core.exceptions.translation import load_or_not_found
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger("driver", __name__)

_DRIVER_ORDERING_FIELDS = frozenset(
    {
        "customer_number",
        "name",
        "mobile",
        "personnel_number",
        "gender",
        "nilofar_code",
        "status",
        "created_at",
        "updated_at",
    }
)


def _to_response_dto(
    driver: Driver,
    *,
    current_vehicle_as_driver: DriverAssignedVehicleDTO | None = None,
    current_vehicle_as_assistant: DriverAssignedVehicleDTO | None = None,
) -> DriverResponseDTO:
    """Map domain entity → response DTO."""
    return DriverResponseDTO(
        id=driver.id,
        customer_number=driver.customer_number.value,
        name=driver.name,
        status=driver.status,
        created_at=driver.created_at,
        updated_at=driver.updated_at,
        mobile=driver.mobile,
        personnel_number=driver.personnel_number,
        gender=driver.gender,
        nilofar_code=driver.nilofar_code,
        current_vehicle_as_driver=current_vehicle_as_driver,
        current_vehicle_as_assistant=current_vehicle_as_assistant,
    )


def _assigned_vehicle_dto(vehicle: VehicleModel) -> DriverAssignedVehicleDTO:
    """Map a vehicle ORM row to the assigned-vehicle response DTO."""
    return DriverAssignedVehicleDTO(
        id=vehicle.id,
        vehicle_number=vehicle.vehicle_number,
        license_plate=vehicle.license_plate,
    )


def _vehicles_by_driver_customer_numbers(
    customer_numbers: set[str],
) -> tuple[
    dict[str, DriverAssignedVehicleDTO],
    dict[str, DriverAssignedVehicleDTO],
]:
    """Batch-load current vehicles keyed by driver customer number.

    Builds two maps from a single query:

    - ``as_driver``: customer number → vehicle where the driver is ``driver1``
    - ``as_assistant``: customer number → vehicle where the driver is ``driver2``

    When a customer number appears on multiple vehicles for the same role, the
    most recently updated vehicle wins.

    Args:
        customer_numbers: SAP customer numbers to resolve.

    Returns:
        Tuple of ``(as_driver, as_assistant)`` maps.
    """
    if not customer_numbers:
        return {}, {}

    vehicles = (
        VehicleModel.objects.filter(is_deleted=False)
        .filter(
            Q(driver1_customer_number__in=customer_numbers)
            | Q(driver2_customer_number__in=customer_numbers)
        )
        .order_by("-updated_at")
    )

    as_driver: dict[str, DriverAssignedVehicleDTO] = {}
    as_assistant: dict[str, DriverAssignedVehicleDTO] = {}
    for vehicle in vehicles:
        dto = _assigned_vehicle_dto(vehicle)
        driver1 = vehicle.driver1_customer_number
        driver2 = vehicle.driver2_customer_number
        if driver1 and driver1 in customer_numbers and driver1 not in as_driver:
            as_driver[driver1] = dto
        if driver2 and driver2 in customer_numbers and driver2 not in as_assistant:
            as_assistant[driver2] = dto
    return as_driver, as_assistant


class GetDriverService:
    """Fetch a single driver by its UUID.

    Args:
        driver_repository: Concrete ``IDriverRepository``.
    """

    def __init__(self, driver_repository: IDriverRepository) -> None:
        self._repo = driver_repository

    def execute(self, driver_id: uuid.UUID, request_id: str = "") -> DriverResponseDTO:
        """Return the driver identified by ``driver_id``.

        Args:
            driver_id: Target driver UUID.
            request_id: Optional correlation ID for structured logging.

        Returns:
            ``DriverResponseDTO`` for the requested driver.

        Raises:
            FMMSNotFoundError: If no driver with ``driver_id`` exists.
        """
        logger.info(
            "Fetching driver",
            extra={
                "domain": "driver",
                "service": "GetDriverService",
                "operation": "execute",
                "request_id": request_id,
                "entity_id": str(driver_id),
            },
        )

        driver = load_or_not_found(
            lambda: self._repo.get_by_id(driver_id),
            message=f"Driver '{driver_id}' not found.",
            details={"driver_id": str(driver_id)},
        )

        logger.info(
            "Driver fetched",
            extra={
                "domain": "driver",
                "service": "GetDriverService",
                "operation": "execute",
                "request_id": request_id,
                "entity_id": str(driver_id),
                "result": "success",
            },
        )

        as_driver, as_assistant = _vehicles_by_driver_customer_numbers(
            {driver.customer_number.value}
        )
        customer_number = driver.customer_number.value
        return _to_response_dto(
            driver,
            current_vehicle_as_driver=as_driver.get(customer_number),
            current_vehicle_as_assistant=as_assistant.get(customer_number),
        )


class ListDriversService:
    """Fetch a filtered list of drivers.

    Args:
        driver_repository: Concrete ``IDriverRepository``.
    """

    def __init__(self, driver_repository: IDriverRepository) -> None:
        self._repo = driver_repository

    def execute(
        self,
        status: DriverStatus | None = None,
        ordering: str = "",
        request_id: str = "",
    ) -> list[DriverResponseDTO]:
        """Return drivers, optionally filtered by lifecycle status.

        Args:
            status: Optional status filter. When ``None``, all statuses are returned.
            ordering: Optional ordering field. Prefix with ``-`` for descending.
            request_id: Optional correlation ID for structured logging.

        Returns:
            Ordered list of ``DriverResponseDTO`` objects.
        """
        logger.info(
            "Listing drivers",
            extra={
                "domain": "driver",
                "service": "ListDriversService",
                "operation": "execute",
                "request_id": request_id,
                "status_filter": status.value if status else None,
                "ordering": ordering,
            },
        )

        drivers = self._repo.list_by_status(status) if status else self._repo.list_all()
        drivers = _sort_drivers(drivers, ordering)

        logger.info(
            "Drivers listed",
            extra={
                "domain": "driver",
                "service": "ListDriversService",
                "operation": "execute",
                "request_id": request_id,
                "result": "success",
                "count": len(drivers),
            },
        )

        customer_numbers = {driver.customer_number.value for driver in drivers}
        as_driver, as_assistant = _vehicles_by_driver_customer_numbers(customer_numbers)
        return [
            _to_response_dto(
                driver,
                current_vehicle_as_driver=as_driver.get(driver.customer_number.value),
                current_vehicle_as_assistant=as_assistant.get(
                    driver.customer_number.value
                ),
            )
            for driver in drivers
        ]


def _sort_drivers(drivers: list[Driver], ordering: str) -> list[Driver]:
    """Return drivers sorted by a whitelisted response field."""
    if not ordering:
        return drivers
    descending = ordering.startswith("-")
    field_name = ordering[1:] if descending else ordering
    if field_name not in _DRIVER_ORDERING_FIELDS:
        raise FMMSValidationError(
            message=f"Unsupported driver ordering field: {field_name}.",
            error_code="INVALID_ORDERING",
            details={
                "field": field_name,
                "allowed_fields": sorted(_DRIVER_ORDERING_FIELDS),
            },
        )
    return sorted(
        drivers,
        key=lambda driver: _sortable_value(getattr(driver, field_name)),
        reverse=descending,
    )


def _sortable_value(value: Any) -> Any:
    """Return a primitive value suitable for stable sorting."""
    return getattr(value, "value", value) or ""
