"""Service that orchestrates updates to mutable vehicle fields.

Only fields explicitly supplied in the DTO are updated.  Status transitions
are not performed here — they live in dedicated services or domain methods.
"""

from __future__ import annotations

from datetime import UTC, datetime

from apps.vehicle.application.dto.vehicle_dto import (
    UpdateVehicleDTO,
    VehicleResponseDTO,
)
from apps.vehicle.domain.entities import Vehicle
from apps.vehicle.domain.interfaces.vehicle_repository import IVehicleRepository
from apps.vehicle.domain.value_objects import ChassisNumber, SAPEquipmentNumber
from core.exceptions.base_exception import FMMSNotFoundError
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger("vehicle", __name__)


class UpdateVehicleService:
    """Orchestrates partial updates to an existing vehicle's mutable fields.

    Args:
        vehicle_repository: Concrete implementation of ``IVehicleRepository``.
    """

    def __init__(self, vehicle_repository: IVehicleRepository) -> None:
        self._repo = vehicle_repository

    def execute(self, dto: UpdateVehicleDTO) -> VehicleResponseDTO:
        """Apply a partial update to an existing vehicle.

        Only the fields provided (non-``None``) in the DTO are written; all
        others retain their current values.

        Args:
            dto: Input specifying which fields to update.

        Returns:
            ``VehicleResponseDTO`` reflecting the updated vehicle state.

        Raises:
            FMMSNotFoundError: If no vehicle with ``dto.vehicle_id`` exists.
        """
        logger.info(
            "Updating vehicle",
            extra={
                "domain": "vehicle",
                "service": "UpdateVehicleService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(dto.vehicle_id),
            },
        )

        vehicle = self._repo.get_by_id(dto.vehicle_id)
        if vehicle is None:
            raise FMMSNotFoundError(
                message=f"Vehicle '{dto.vehicle_id}' not found.",
                details={"vehicle_id": str(dto.vehicle_id)},
            )

        vehicle = _apply_updates(vehicle, dto)

        saved = self._repo.save(vehicle)

        logger.info(
            "Vehicle updated successfully",
            extra={
                "domain": "vehicle",
                "service": "UpdateVehicleService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(saved.id),
                "result": "success",
            },
        )

        return _to_response_dto(saved)


def _apply_updates(vehicle: Vehicle, dto: UpdateVehicleDTO) -> Vehicle:
    """Return a copy of ``vehicle`` with the DTO's non-``None`` fields applied.

    Mutates the entity in-place (``Vehicle`` is a mutable dataclass) and
    refreshes ``updated_at`` to the current UTC time.

    Args:
        vehicle: The loaded domain entity.
        dto: The partial update instruction.

    Returns:
        The same entity object after mutation.
    """
    if dto.make is not None:
        vehicle.make = dto.make
    if dto.model is not None:
        vehicle.model = dto.model
    if dto.year is not None:
        vehicle.year = dto.year
    if dto.category is not None:
        vehicle.category = dto.category
    if dto.chassis_number is not None:
        vehicle.chassis_number = ChassisNumber(dto.chassis_number)
    if dto.sap_equipment_number is not None:
        vehicle.sap_equipment_number = SAPEquipmentNumber(dto.sap_equipment_number)

    vehicle.updated_at = datetime.now(tz=UTC)
    return vehicle


def _to_response_dto(vehicle: Vehicle) -> VehicleResponseDTO:
    """Map domain entity → response DTO."""
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
