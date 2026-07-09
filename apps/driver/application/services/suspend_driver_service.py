"""Service that orchestrates driver suspension.

The domain entity's ``suspend()`` method enforces the state-machine rule.
This service is responsible only for loading, delegating, persisting, and logging.
"""

from __future__ import annotations

from datetime import UTC, datetime

from apps.driver.application.dto.driver_dto import DriverResponseDTO, SuspendDriverDTO
from apps.driver.domain.entities import Driver
from apps.driver.domain.interfaces.driver_repository import IDriverRepository
from core.exceptions.translation import load_or_not_found
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger("driver", __name__)


def _to_response_dto(driver: Driver) -> DriverResponseDTO:
    """Map domain entity → response DTO."""
    return DriverResponseDTO(
        id=driver.id,
        full_name=driver.full_name,
        license_number=driver.license_number.value,
        license_class=driver.license_class,
        status=driver.status,
        phone=driver.contact.phone,
        email=driver.contact.email,
        created_at=driver.created_at,
        updated_at=driver.updated_at,
        assigned_vehicle_id=driver.assigned_vehicle_id,
    )


class SuspendDriverService:
    """Orchestrates suspension of a driver.

    Args:
        driver_repository: Concrete ``IDriverRepository``.
    """

    def __init__(self, driver_repository: IDriverRepository) -> None:
        self._repo = driver_repository

    def execute(self, dto: SuspendDriverDTO) -> DriverResponseDTO:
        """Suspend the driver identified by ``dto.driver_id``.

        Delegates state-machine validation to ``Driver.suspend()``.

        Args:
            dto: Suspension request.

        Returns:
            ``DriverResponseDTO`` with ``status == SUSPENDED``.

        Raises:
            FMMSNotFoundError: If no driver with ``dto.driver_id`` exists.
            DriverInvalidStateTransitionError: If the current status does not
                permit suspension (raised by the domain entity).
        """
        logger.info(
            "Suspending driver",
            extra={
                "domain": "driver",
                "service": "SuspendDriverService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(dto.driver_id),
            },
        )

        driver = load_or_not_found(
            lambda: self._repo.get_by_id(dto.driver_id),
            message=f"Driver '{dto.driver_id}' not found.",
            details={"driver_id": str(dto.driver_id)},
        )

        driver.suspend()
        driver.updated_at = datetime.now(tz=UTC)

        saved = self._repo.save(driver)

        logger.info(
            "Driver suspended successfully",
            extra={
                "domain": "driver",
                "service": "SuspendDriverService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(saved.id),
                "result": "success",
            },
        )

        return _to_response_dto(saved)
