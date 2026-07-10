"""Service that orchestrates re-activation of a vehicle after maintenance."""

from __future__ import annotations

from datetime import UTC, datetime

from apps.repair.domain.interfaces.repair_repository import IRepairOrderRepository
from apps.vehicle.application.dto.vehicle_dto import (
    ActivateVehicleDTO,
    VehicleResponseDTO,
)
from apps.vehicle.domain.entities import VehicleStatus
from apps.vehicle.domain.interfaces.vehicle_repository import IVehicleRepository
from core.exceptions.base_exception import FMMSConflictError
from core.exceptions.translation import load_or_not_found
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger("vehicle", __name__)


class ActivateVehicleService:
    """Re-activate a vehicle when no open repair orders block the transition.

    Args:
        vehicle_repository: Concrete ``IVehicleRepository``.
        repair_order_repository: Used to enforce the cross-domain invariant that
            a vehicle with active repair orders cannot be re-activated.
    """

    def __init__(
        self,
        vehicle_repository: IVehicleRepository,
        repair_order_repository: IRepairOrderRepository,
    ) -> None:
        self._vehicle_repo = vehicle_repository
        self._repair_repo = repair_order_repository

    def execute(self, dto: ActivateVehicleDTO) -> VehicleResponseDTO:
        """Activate a vehicle that is eligible to return to service.

        Args:
            dto: Activation request.

        Returns:
            ``VehicleResponseDTO`` with ``status == ACTIVE``.

        Raises:
            FMMSNotFoundError: If the vehicle does not exist.
            FMMSConflictError: If active repair orders exist for the vehicle.
            VehicleInvalidStateTransitionError: If the domain state machine
                rejects the transition to ACTIVE.
        """
        logger.info(
            "Activating vehicle",
            extra={
                "domain": "vehicle",
                "service": "ActivateVehicleService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(dto.vehicle_id),
                "user_id": str(dto.requested_by),
            },
        )

        vehicle = load_or_not_found(
            lambda: self._vehicle_repo.get_by_id(dto.vehicle_id),
            message=f"Vehicle '{dto.vehicle_id}' not found.",
            details={"vehicle_id": str(dto.vehicle_id)},
        )

        if vehicle.status == VehicleStatus.ACTIVE:
            return _to_response_dto(vehicle)

        active_orders = self._repair_repo.list_active_by_vehicle(dto.vehicle_id)
        if active_orders:
            raise FMMSConflictError(
                message="Vehicle cannot be activated while repair orders are still open.",
                error_code="VEHICLE_HAS_ACTIVE_REPAIR_ORDERS",
                details={
                    "vehicle_id": str(dto.vehicle_id),
                    "active_repair_order_ids": [str(o.id) for o in active_orders],
                },
            )

        vehicle.activate()
        vehicle.updated_at = datetime.now(tz=UTC)
        saved = self._vehicle_repo.save(vehicle)

        logger.info(
            "Vehicle activated successfully",
            extra={
                "domain": "vehicle",
                "service": "ActivateVehicleService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(saved.id),
                "result": "success",
            },
        )

        return _to_response_dto(saved)


def _to_response_dto(vehicle) -> VehicleResponseDTO:
    """Map a vehicle entity to a response DTO."""
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
