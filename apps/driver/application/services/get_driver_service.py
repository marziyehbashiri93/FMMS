"""Read-only services for retrieving driver data.

No mutations happen here. These services are query-side only.
"""

from __future__ import annotations

import uuid

from apps.driver.application.dto.driver_dto import DriverResponseDTO
from apps.driver.domain.entities import Driver, DriverStatus
from apps.driver.domain.interfaces.driver_repository import IDriverRepository
from core.exceptions.translation import load_or_not_found
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger("driver", __name__)


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
        status: DriverStatus = DriverStatus.ACTIVE,
        request_id: str = "",
    ) -> list[DriverResponseDTO]:
        """Return drivers filtered by lifecycle status.

        Defaults to returning only ACTIVE drivers.

        Args:
            status: Status filter (defaults to ``ACTIVE``).
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
                "status_filter": status.value,
            },
        )

        drivers = self._repo.list_by_status(status)

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
