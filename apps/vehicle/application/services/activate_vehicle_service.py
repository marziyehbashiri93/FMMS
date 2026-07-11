"""Service that orchestrates re-activation of a vehicle after maintenance."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from apps.fault.domain.entities import Fault, FaultStatus
from apps.fault.domain.exceptions import FaultNotFoundError
from apps.fault.domain.interfaces.fault_repository import IFaultRepository
from apps.repair.domain.entities import RepairOrderStatus
from apps.repair.domain.interfaces.repair_repository import IRepairOrderRepository
from apps.vehicle.application.dto.vehicle_dto import (
    ActivateVehicleDTO,
    VehicleResponseDTO,
)
from apps.vehicle.domain.entities import Vehicle, VehicleStatus
from apps.vehicle.domain.interfaces.vehicle_repository import IVehicleRepository
from core.exceptions.base_exception import FMMSConflictError
from core.exceptions.translation import load_or_not_found
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger("vehicle", __name__)


def _close_faults_for_completed_repairs(
    *,
    vehicle_id: uuid.UUID,
    repair_order_repository: IRepairOrderRepository,
    fault_repository: IFaultRepository,
    request_id: str,
) -> None:
    """Close open faults linked to finished repair orders for a vehicle.

    When maintenance is finished and the vehicle returns to service, any fault
    that still has a COMPLETED or ACCEPTED_BY_DRIVER repair order but remains
    open is resolved here. Already-closed faults are skipped (idempotent).
    ASSIGNED faults are moved through IN_REPAIR before closing so the domain
    state machine is respected.

    Args:
        vehicle_id: Vehicle being re-activated.
        repair_order_repository: Source of finished repair orders.
        fault_repository: Fault aggregate persistence port.
        request_id: Correlation ID for structured logging.
    """
    finished_orders: list = []
    for status in (
        RepairOrderStatus.COMPLETED,
        RepairOrderStatus.ACCEPTED_BY_DRIVER,
    ):
        finished_orders.extend(
            repair_order_repository.list_by_vehicle(vehicle_id, status=status)
        )
    closed_fault_ids: set[uuid.UUID] = set()

    for order in finished_orders:
        if order.fault_id in closed_fault_ids:
            continue

        try:
            fault = fault_repository.get_by_id(order.fault_id)
        except FaultNotFoundError:
            logger.warning(
                "Skipping fault closure — fault not found for completed repair",
                extra={
                    "domain": "vehicle",
                    "service": "ActivateVehicleService",
                    "operation": "close_completed_repair_faults",
                    "request_id": request_id,
                    "entity_id": str(order.fault_id),
                    "repair_order_id": str(order.id),
                },
            )
            continue

        if fault.status == FaultStatus.CLOSED:
            closed_fault_ids.add(fault.id)
            continue

        _close_open_fault(fault)
        fault.updated_at = datetime.now(tz=UTC)
        fault_repository.save(fault)
        closed_fault_ids.add(fault.id)

        logger.info(
            "Fault closed after vehicle activation",
            extra={
                "domain": "vehicle",
                "service": "ActivateVehicleService",
                "operation": "close_completed_repair_faults",
                "request_id": request_id,
                "entity_id": str(fault.id),
                "repair_order_id": str(order.id),
                "vehicle_id": str(vehicle_id),
                "result": "success",
            },
        )


def _close_open_fault(fault: Fault) -> None:
    """Transition a non-closed fault to CLOSED via the domain entity.

    Args:
        fault: Fault aggregate to close.

    Raises:
        FaultAlreadyClosedError: If already CLOSED (caller should skip).
        FaultInvalidStateTransitionError: If the entity rejects the transition.
    """
    if fault.status == FaultStatus.ASSIGNED:
        fault.start_repair()
    fault.close()


class ActivateVehicleService:
    """Re-activate a vehicle when no open repair orders block the transition.

    After a successful activation, open faults linked to COMPLETED repair orders
    for the vehicle are closed so the maintenance cycle is fully resolved.

    Args:
        vehicle_repository: Concrete ``IVehicleRepository``.
        repair_order_repository: Used to enforce the cross-domain invariant that
            a vehicle with active repair orders cannot be re-activated.
        fault_repository: Used to close faults resolved by completed repairs.
    """

    def __init__(
        self,
        vehicle_repository: IVehicleRepository,
        repair_order_repository: IRepairOrderRepository,
        fault_repository: IFaultRepository,
    ) -> None:
        self._vehicle_repo = vehicle_repository
        self._repair_repo = repair_order_repository
        self._fault_repo = fault_repository

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

        _close_faults_for_completed_repairs(
            vehicle_id=dto.vehicle_id,
            repair_order_repository=self._repair_repo,
            fault_repository=self._fault_repo,
            request_id=dto.request_id,
        )

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


def _to_response_dto(vehicle: Vehicle) -> VehicleResponseDTO:
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
