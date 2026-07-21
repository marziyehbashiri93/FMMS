"""Read-only services for retrieving driver data.

No mutations happen here. These services are query-side only.
"""

from __future__ import annotations

import uuid
from typing import Any

from apps.driver.application.dto.driver_dto import DriverResponseDTO
from apps.driver.domain.entities import Driver, DriverStatus
from apps.driver.domain.interfaces.driver_repository import IDriverRepository
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


def _to_response_dto(driver: Driver) -> DriverResponseDTO:
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
    )


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

        return _to_response_dto(driver)


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

        return [_to_response_dto(d) for d in drivers]


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
