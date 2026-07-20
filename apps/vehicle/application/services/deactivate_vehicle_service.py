"""Service that orchestrates vehicle deactivation.

The distribution supervisor decides when a vehicle is no longer usable.
Deactivation transitions the vehicle to INACTIVE via the domain entity.

The domain entity's ``deactivate()`` method enforces the state-machine rule
(the vehicle must not already be INACTIVE).
"""

from __future__ import annotations

from datetime import UTC, datetime

from apps.vehicle.application.dto.vehicle_dto import (
    DeactivateVehicleDTO,
    VehicleResponseDTO,
)
from apps.vehicle.domain.entities import VEHICLE_STATUS_LABELS
from apps.vehicle.domain.interfaces.vehicle_repository import IVehicleRepository
from core.exceptions.translation import load_or_not_found
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger("vehicle", __name__)


class DeactivateVehicleService:
    """Orchestrates deactivation of a vehicle.

    Domain-level state-machine validation (e.g. a vehicle already INACTIVE
    cannot be deactivated again) is delegated to ``Vehicle.deactivate()``.

    Args:
        vehicle_repository: Concrete ``IVehicleRepository``.
    """

    def __init__(
        self,
        vehicle_repository: IVehicleRepository,
    ) -> None:
        self._vehicle_repo = vehicle_repository

    def execute(self, dto: DeactivateVehicleDTO) -> VehicleResponseDTO:
        """Deactivate a vehicle after validating domain constraints.

        Args:
            dto: Deactivation request.

        Returns:
            ``VehicleResponseDTO`` with ``status == INACTIVE``.

        Raises:
            FMMSNotFoundError: If no vehicle with ``dto.vehicle_id`` exists.
            VehicleInvalidStateTransitionError: If the vehicle is already
                INACTIVE (raised by the domain entity).
        """
        logger.info(
            "Deactivating vehicle",
            extra={
                "domain": "vehicle",
                "service": "DeactivateVehicleService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(dto.vehicle_id),
            },
        )

        vehicle = load_or_not_found(
            lambda: self._vehicle_repo.get_by_id(dto.vehicle_id),
            message=f"Vehicle '{dto.vehicle_id}' not found.",
            details={"vehicle_id": str(dto.vehicle_id)},
        )

        vehicle.deactivate()
        vehicle.updated_at = datetime.now(tz=UTC)

        saved = self._vehicle_repo.save(vehicle)

        logger.info(
            "Vehicle deactivated successfully",
            extra={
                "domain": "vehicle",
                "service": "DeactivateVehicleService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(saved.id),
                "result": "success",
            },
        )

        return VehicleResponseDTO(
            id=saved.id,
            vehicle_number=saved.vehicle_number.value,
            license_plate=saved.license_plate.value,
            status=saved.status,
            status_label=VEHICLE_STATUS_LABELS[saved.status],
            created_at=saved.created_at,
            updated_at=saved.updated_at,
            commissioning_date=saved.commissioning_date,
            driver1_customer_number=saved.driver1_customer_number,
            driver2_customer_number=saved.driver2_customer_number,
        )
