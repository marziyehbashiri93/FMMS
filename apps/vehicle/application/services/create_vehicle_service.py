"""Service that orchestrates the creation of a new fleet vehicle.

Business rule ownership:
- PlateNumber and VIN validation → value objects (domain layer).
- Duplicate-plate enforcement → this service via repository uniqueness check
  (this is an application-level guard, not a domain rule).
- No other business rules live here.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from apps.vehicle.application.dto.vehicle_dto import (
    CreateVehicleDTO,
    VehicleResponseDTO,
)
from apps.vehicle.domain.entities import Vehicle, VehicleStatus
from apps.vehicle.domain.interfaces.vehicle_repository import IVehicleRepository
from apps.vehicle.domain.value_objects import (
    VIN,
    ChassisNumber,
    PlateNumber,
    SAPEquipmentNumber,
)
from core.exceptions.base_exception import FMMSConflictError
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger("vehicle", __name__)


class CreateVehicleService:
    """Orchestrates creation of a new vehicle.

    Dependencies are injected so the service is testable without a real database.

    Args:
        vehicle_repository: Concrete implementation of ``IVehicleRepository``.
    """

    def __init__(self, vehicle_repository: IVehicleRepository) -> None:
        self._repo = vehicle_repository

    def execute(self, dto: CreateVehicleDTO) -> VehicleResponseDTO:
        """Create and persist a new vehicle.

        Validates uniqueness of the plate number via the repository before
        delegating value-object construction (which validates format/length) to
        the domain layer.  The ``Vehicle`` entity is then saved and a read-only
        response DTO is returned.

        Args:
            dto: Input data for the vehicle to create.

        Returns:
            ``VehicleResponseDTO`` representing the persisted vehicle.

        Raises:
            FMMSConflictError: If a vehicle with the same plate number already
                exists.
            FMMSValidationError: If any value object validation fails (e.g.
                invalid VIN length).
        """
        logger.info(
            "Creating vehicle",
            extra={
                "domain": "vehicle",
                "service": "CreateVehicleService",
                "operation": "execute",
                "request_id": dto.request_id,
                "plate_number": dto.plate_number,
            },
        )

        plate_vo = PlateNumber(dto.plate_number)
        if self._repo.exists_by_plate(plate_vo):
            raise FMMSConflictError(
                message=f"Vehicle with plate number '{dto.plate_number}' already exists.",
                details={"plate_number": dto.plate_number},
            )

        now = datetime.now(tz=UTC)
        vehicle = Vehicle(
            id=uuid.uuid4(),
            plate_number=plate_vo,
            vin=VIN(dto.vin),
            make=dto.make,
            model=dto.model,
            year=dto.year,
            category=dto.category,
            status=VehicleStatus.ACTIVE,
            created_at=now,
            updated_at=now,
            chassis_number=(
                ChassisNumber(dto.chassis_number) if dto.chassis_number else None
            ),
            sap_equipment_number=(
                SAPEquipmentNumber(dto.sap_equipment_number)
                if dto.sap_equipment_number
                else None
            ),
        )

        saved = self._repo.save(vehicle)

        logger.info(
            "Vehicle created successfully",
            extra={
                "domain": "vehicle",
                "service": "CreateVehicleService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(saved.id),
                "result": "success",
            },
        )

        return _to_response_dto(saved)


def _to_response_dto(vehicle: Vehicle) -> VehicleResponseDTO:
    """Map a ``Vehicle`` domain entity to a ``VehicleResponseDTO``.

    This mapping is kept in the service module so there is a single,
    explicit translation point per operation.

    Args:
        vehicle: Source domain entity.

    Returns:
        Serialisation-safe response DTO.
    """
    return VehicleResponseDTO(
        id=vehicle.id,
        plate_number=vehicle.plate_number.value,
        vin=vehicle.vin.value,
        make=vehicle.make,
        model=vehicle.model,
        year=vehicle.year,
        category=vehicle.category,
        status=vehicle.status,
        created_at=vehicle.created_at,
        updated_at=vehicle.updated_at,
        chassis_number=vehicle.chassis_number.value if vehicle.chassis_number else None,
        sap_equipment_number=(
            vehicle.sap_equipment_number.value if vehicle.sap_equipment_number else None
        ),
    )
