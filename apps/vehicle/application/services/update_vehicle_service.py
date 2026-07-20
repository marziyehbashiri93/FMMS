"""Service that orchestrates FMMS-owned vehicle status updates."""

from __future__ import annotations

from datetime import UTC, datetime

from apps.vehicle.application.dto.vehicle_dto import (
    UpdateVehicleDTO,
    VehicleResponseDTO,
)
from apps.vehicle.domain.entities import VEHICLE_STATUS_LABELS, Vehicle
from apps.vehicle.domain.interfaces.vehicle_repository import IVehicleRepository
from core.exceptions.translation import load_or_not_found
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger("vehicle", __name__)


class UpdateVehicleService:
    """Orchestrates status updates for an existing vehicle.

    Args:
        vehicle_repository: Concrete implementation of ``IVehicleRepository``.
    """

    def __init__(self, vehicle_repository: IVehicleRepository) -> None:
        self._repo = vehicle_repository

    def execute(self, dto: UpdateVehicleDTO) -> VehicleResponseDTO:
        """Apply an FMMS-owned status update to an existing vehicle.

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

        vehicle = load_or_not_found(
            lambda: self._repo.get_by_id(dto.vehicle_id),
            message=f"Vehicle '{dto.vehicle_id}' not found.",
            details={"vehicle_id": str(dto.vehicle_id)},
        )

        vehicle = _apply_status_update(vehicle, dto)

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


def _apply_status_update(vehicle: Vehicle, dto: UpdateVehicleDTO) -> Vehicle:
    """Apply the requested lifecycle status to ``vehicle``.

    Mutates the entity in-place (``Vehicle`` is a mutable dataclass) and
    refreshes ``updated_at`` to the current UTC time.

    Args:
        vehicle: The loaded domain entity.
        dto: The partial update instruction.

    Returns:
        The same entity object after mutation.
    """
    vehicle.transition_to(dto.status)
    vehicle.updated_at = datetime.now(tz=UTC)
    return vehicle


def _to_response_dto(vehicle: Vehicle) -> VehicleResponseDTO:
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
        driver1_customer_number=vehicle.driver1_customer_number,
        driver2_customer_number=vehicle.driver2_customer_number,
    )
