"""Service that orchestrates the registration of a new driver.

Business rule ownership:
- LicenseNumber format validation → ``LicenseNumber`` value object (domain).
- Duplicate-license enforcement → this service via repository uniqueness check
  (application-level guard, not a domain rule).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from apps.driver.application.dto.driver_dto import DriverResponseDTO, RegisterDriverDTO
from apps.driver.domain.entities import Driver, DriverStatus
from apps.driver.domain.interfaces.driver_repository import IDriverRepository
from apps.driver.domain.value_objects import DriverContact, LicenseNumber
from core.exceptions.base_exception import FMMSConflictError
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger("driver", __name__)


def _to_response_dto(driver: Driver) -> DriverResponseDTO:
    """Map a ``Driver`` domain entity to a ``DriverResponseDTO``."""
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


class RegisterDriverService:
    """Orchestrates registration of a new driver.

    Args:
        driver_repository: Concrete implementation of ``IDriverRepository``.
    """

    def __init__(self, driver_repository: IDriverRepository) -> None:
        self._repo = driver_repository

    def execute(self, dto: RegisterDriverDTO) -> DriverResponseDTO:
        """Register and persist a new driver.

        Validates license number uniqueness before delegating value-object
        construction (which validates format) to the domain layer.

        Args:
            dto: Input data for the driver to register.

        Returns:
            ``DriverResponseDTO`` representing the persisted driver.

        Raises:
            FMMSConflictError: If a driver with the same license number already
                exists.
            ValueError: If ``LicenseNumber`` or ``DriverContact`` validation
                fails.
        """
        logger.info(
            "Registering driver",
            extra={
                "domain": "driver",
                "service": "RegisterDriverService",
                "operation": "execute",
                "request_id": dto.request_id,
                "license_number": dto.license_number,
            },
        )

        license_vo = LicenseNumber(dto.license_number)
        if self._repo.exists_by_license(license_vo):
            raise FMMSConflictError(
                message=f"Driver with license '{dto.license_number}' already exists.",
                details={"license_number": dto.license_number},
            )

        now = datetime.now(tz=UTC)
        driver = Driver(
            id=uuid.uuid4(),
            full_name=dto.full_name,
            license_number=license_vo,
            license_class=dto.license_class,
            contact=DriverContact(phone=dto.phone, email=dto.email),
            status=DriverStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )

        saved = self._repo.save(driver)

        logger.info(
            "Driver registered successfully",
            extra={
                "domain": "driver",
                "service": "RegisterDriverService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(saved.id),
                "result": "success",
            },
        )

        return _to_response_dto(saved)
