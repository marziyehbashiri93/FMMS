"""Service that orchestrates driver-to-vehicle assignment.

Cross-domain invariants enforced here (Application Service layer):
1. Driver must be ACTIVE and currently unassigned.
2. Vehicle must be ACTIVE (available for assignment).
3. Only one driver may be assigned to a vehicle at a time.

None of these invariants belong inside the Driver or Vehicle domain entity
because they require knowledge of both domains simultaneously.
"""

from __future__ import annotations

from datetime import UTC, datetime

from apps.driver.application.dto.driver_dto import (
    AssignDriverToVehicleDTO,
    DriverResponseDTO,
)
from apps.driver.domain.entities import Driver
from apps.driver.domain.interfaces.driver_repository import IDriverRepository
from apps.vehicle.domain.entities import VehicleStatus
from apps.vehicle.domain.interfaces.vehicle_repository import IVehicleRepository
from core.exceptions.base_exception import FMMSConflictError, FMMSNotFoundError
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger("driver", __name__)


def _to_response_dto(driver: Driver) -> DriverResponseDTO:
    """Map domain entity → response DTO."""
    from apps.driver.application.dto.driver_dto import (  # noqa: PLC0415
        DriverResponseDTO,
    )

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


class AssignDriverToVehicleService:
    """Orchestrates assignment of a driver to a vehicle.

    Args:
        driver_repository: Concrete ``IDriverRepository``.
        vehicle_repository: Concrete ``IVehicleRepository`` — used to verify
            vehicle availability across the domain boundary.
    """

    def __init__(
        self,
        driver_repository: IDriverRepository,
        vehicle_repository: IVehicleRepository,
    ) -> None:
        self._driver_repo = driver_repository
        self._vehicle_repo = vehicle_repository

    def execute(self, dto: AssignDriverToVehicleDTO) -> DriverResponseDTO:
        """Assign a driver to a vehicle after enforcing cross-domain invariants.

        Args:
            dto: Assignment request.

        Returns:
            ``DriverResponseDTO`` with ``assigned_vehicle_id`` populated.

        Raises:
            FMMSNotFoundError: If driver or vehicle does not exist.
            FMMSConflictError: If driver is not ACTIVE/available, vehicle is
                not ACTIVE, or vehicle already has an assigned driver.
        """
        logger.info(
            "Assigning driver to vehicle",
            extra={
                "domain": "driver",
                "service": "AssignDriverToVehicleService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(dto.driver_id),
                "vehicle_id": str(dto.vehicle_id),
            },
        )

        driver = self._driver_repo.get_by_id(dto.driver_id)
        if driver is None:
            raise FMMSNotFoundError(
                message=f"Driver '{dto.driver_id}' not found.",
                details={"driver_id": str(dto.driver_id)},
            )

        vehicle = self._vehicle_repo.get_by_id(dto.vehicle_id)
        if vehicle is None:
            raise FMMSNotFoundError(
                message=f"Vehicle '{dto.vehicle_id}' not found.",
                details={"vehicle_id": str(dto.vehicle_id)},
            )

        if not driver.is_available:
            raise FMMSConflictError(
                message=(
                    f"Driver '{dto.driver_id}' is not available for assignment "
                    f"(status={driver.status}, assigned={driver.assigned_vehicle_id})."
                ),
                details={
                    "driver_id": str(dto.driver_id),
                    "driver_status": driver.status,
                    "already_assigned_to": str(driver.assigned_vehicle_id),
                },
            )

        if vehicle.status != VehicleStatus.ACTIVE:
            raise FMMSConflictError(
                message=f"Vehicle '{dto.vehicle_id}' is not ACTIVE (status={vehicle.status}).",
                details={
                    "vehicle_id": str(dto.vehicle_id),
                    "vehicle_status": vehicle.status,
                },
            )

        existing_driver = self._driver_repo.get_by_vehicle(dto.vehicle_id)
        if existing_driver is not None:
            raise FMMSConflictError(
                message=(
                    f"Vehicle '{dto.vehicle_id}' already has driver "
                    f"'{existing_driver.id}' assigned."
                ),
                details={
                    "vehicle_id": str(dto.vehicle_id),
                    "existing_driver_id": str(existing_driver.id),
                },
            )

        driver.assign_vehicle(dto.vehicle_id)
        driver.updated_at = datetime.now(tz=UTC)

        saved = self._driver_repo.save(driver)

        logger.info(
            "Driver assigned to vehicle successfully",
            extra={
                "domain": "driver",
                "service": "AssignDriverToVehicleService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(saved.id),
                "result": "success",
            },
        )

        return _to_response_dto(saved)
