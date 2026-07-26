"""Read-only services for retrieving driver data.

No mutations happen here. These services are query-side only.
"""

from __future__ import annotations

import uuid
from enum import StrEnum
from typing import Any, Protocol

from apps.driver.application.dto.driver_dto import (
    DriverAssignedVehicleDTO,
    DriverResponseDTO,
)
from apps.driver.application.interfaces.vehicle_assignment_reader import (
    IDriverVehicleAssignmentReader,
)
from apps.driver.domain.entities import Driver, DriverStatus
from apps.driver.domain.value_objects import CustomerNumber
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


class DriverAssignmentRole(StrEnum):
    """Supported current-vehicle assignment roles for driver list filtering."""

    DRIVER = "DRIVER"
    ASSISTANT = "ASSISTANT"


class IDriverReadRepository(Protocol):
    """Read-only driver repository capability required by query services."""

    def get_by_id(self, driver_id: uuid.UUID) -> Driver:
        """Retrieve a driver by UUID."""

    def get_by_customer_number(self, customer_number: CustomerNumber) -> Driver:
        """Retrieve a driver by SAP customer number."""

    def list_by_status(self, status: DriverStatus) -> list[Driver]:
        """Return all drivers matching a given status."""

    def list_all(self) -> list[Driver]:
        """Return all drivers."""

    def list_filtered(
        self,
        *,
        status: DriverStatus | None = None,
        ordering: str = "",
        search: str = "",
    ) -> list[Driver]:
        """Return drivers filtered and ordered by the backing store."""


class NullDriverVehicleAssignmentReader(IDriverVehicleAssignmentReader):
    """No-op assignment reader used by isolated unit tests."""

    def vehicles_by_driver_customer_numbers(
        self,
        customer_numbers: set[str],
    ) -> tuple[
        dict[str, DriverAssignedVehicleDTO],
        dict[str, DriverAssignedVehicleDTO],
    ]:
        """Return empty assignment maps."""
        del customer_numbers
        return {}, {}


def _to_response_dto(
    driver: Driver,
    *,
    current_vehicle_as_driver: DriverAssignedVehicleDTO | None = None,
    current_vehicle_as_assistant: DriverAssignedVehicleDTO | None = None,
) -> DriverResponseDTO:
    """Map domain entity to response DTO."""
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


class GetDriverService:
    """Fetch a single driver by its UUID.

    Args:
        driver_repository: Concrete driver read repository.
        assignment_reader: Read model for current vehicle assignments.
    """

    def __init__(
        self,
        driver_repository: IDriverReadRepository,
        assignment_reader: IDriverVehicleAssignmentReader | None = None,
    ) -> None:
        self._repo = driver_repository
        self._assignment_reader = assignment_reader or NullDriverVehicleAssignmentReader()

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

        customer_number = driver.customer_number.value
        as_driver, as_assistant = (
            self._assignment_reader.vehicles_by_driver_customer_numbers(
                {customer_number}
            )
        )
        return _to_response_dto(
            driver,
            current_vehicle_as_driver=as_driver.get(customer_number),
            current_vehicle_as_assistant=as_assistant.get(customer_number),
        )


class ListDriversService:
    """Fetch a filtered list of drivers.

    Args:
        driver_repository: Concrete driver read repository.
        assignment_reader: Read model for current vehicle assignments.
    """

    def __init__(
        self,
        driver_repository: IDriverReadRepository,
        assignment_reader: IDriverVehicleAssignmentReader | None = None,
    ) -> None:
        self._repo = driver_repository
        self._assignment_reader = assignment_reader or NullDriverVehicleAssignmentReader()

    def execute(
        self,
        status: DriverStatus | None = None,
        ordering: str = "",
        search: str = "",
        role: DriverAssignmentRole | None = None,
        request_id: str = "",
    ) -> list[DriverResponseDTO]:
        """Return drivers, optionally filtered by lifecycle status.

        Args:
            status: Optional status filter. When ``None``, all statuses are returned.
            ordering: Optional ordering field. Prefix with ``-`` for descending.
            search: Optional case-insensitive text filter.
            role: Optional current-vehicle assignment role filter.
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
                "search": search,
                "role": role.value if role else None,
            },
        )

        _validate_ordering(ordering)
        if hasattr(self._repo, "list_filtered"):
            drivers = self._repo.list_filtered(
                status=status,
                ordering=ordering,
                search=search,
            )
        else:
            drivers = self._repo.list_by_status(status) if status else self._repo.list_all()
            drivers = _filter_drivers_by_search(drivers, search)
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
        as_driver, as_assistant = (
            self._assignment_reader.vehicles_by_driver_customer_numbers(customer_numbers)
        )
        items = [
            _to_response_dto(
                driver,
                current_vehicle_as_driver=as_driver.get(driver.customer_number.value),
                current_vehicle_as_assistant=as_assistant.get(
                    driver.customer_number.value
                ),
            )
            for driver in drivers
        ]
        return _filter_driver_dtos_by_role(items, role)


def _validate_ordering(ordering: str) -> None:
    """Validate driver ordering against the response field allowlist."""
    if not ordering:
        return
    field_name = ordering.removeprefix("-")
    if field_name not in _DRIVER_ORDERING_FIELDS:
        raise FMMSValidationError(
            message=f"Unsupported driver ordering field: {field_name}.",
            error_code="INVALID_ORDERING",
            details={
                "field": field_name,
                "allowed_fields": sorted(_DRIVER_ORDERING_FIELDS),
            },
        )


def _sort_drivers(drivers: list[Driver], ordering: str) -> list[Driver]:
    """Return drivers sorted by a whitelisted response field."""
    if not ordering:
        return drivers
    _validate_ordering(ordering)
    descending = ordering.startswith("-")
    field_name = ordering[1:] if descending else ordering
    return sorted(
        drivers,
        key=lambda driver: _sortable_value(getattr(driver, field_name)),
        reverse=descending,
    )


def _filter_drivers_by_search(drivers: list[Driver], search: str) -> list[Driver]:
    """Return drivers matching a case-insensitive name/personnel search."""
    needle = search.strip().casefold()
    if not needle:
        return drivers
    return [
        driver
        for driver in drivers
        if needle in driver.name.casefold()
        or (
            driver.personnel_number is not None
            and needle in driver.personnel_number.casefold()
        )
    ]


def _filter_driver_dtos_by_role(
    items: list[DriverResponseDTO],
    role: DriverAssignmentRole | None,
) -> list[DriverResponseDTO]:
    """Return driver DTOs matching a current vehicle assignment role."""
    if role is None:
        return items
    if role is DriverAssignmentRole.DRIVER:
        return [item for item in items if item.current_vehicle_as_driver is not None]
    return [item for item in items if item.current_vehicle_as_assistant is not None]


def _sortable_value(value: Any) -> Any:
    """Return a primitive value suitable for stable sorting."""
    return getattr(value, "value", value) or ""
