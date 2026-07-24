"""Service for changing FMMS-controlled vehicle status."""

from __future__ import annotations

import uuid
from contextlib import nullcontext
from datetime import UTC, datetime

from django.db import transaction

from apps.fault.domain.entities import Fault, FaultStatus
from apps.fault.domain.exceptions import FaultNotFoundError
from apps.fault.domain.interfaces.fault_repository import IFaultRepository
from apps.repair.domain.entities import RepairOrderStatus
from apps.repair.domain.interfaces.repair_repository import IRepairOrderRepository
from apps.vehicle.application.dto.vehicle_dto import (
    ChangeVehicleStatusDTO,
    VehicleResponseDTO,
)
from apps.vehicle.application.mappers import vehicle_to_response_dto
from apps.vehicle.domain.entities import VehicleStatus
from apps.vehicle.domain.interfaces.vehicle_repository import IVehicleRepository
from core.exceptions.base_exception import FMMSConflictError, FMMSValidationError
from core.exceptions.translation import load_or_not_found
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger("vehicle", __name__)


_MANUAL_STATUS_CHANGE_ALLOWED_STATUSES = frozenset(
    {
        VehicleStatus.ACTIVE,
        VehicleStatus.INACTIVE,
        VehicleStatus.UNDER_REPAIR,
        VehicleStatus.SUSPENDED,
        VehicleStatus.OUT_OF_SERVICE,
    }
)


def _close_faults_for_completed_repairs(
    *,
    vehicle_id: uuid.UUID,
    repair_order_repository: IRepairOrderRepository,
    fault_repository: IFaultRepository,
    request_id: str,
) -> None:
    """Close open faults linked to completed repair orders for a vehicle."""
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
                "Skipping fault closure; fault not found for completed repair",
                extra={
                    "domain": "vehicle",
                    "service": "ChangeVehicleStatusService",
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


def _close_open_fault(fault: Fault) -> None:
    """Close a non-closed fault through valid fault state transitions."""
    if fault.status == FaultStatus.ASSIGNED:
        fault.start_repair()
    fault.close()


class ChangeVehicleStatusService:
    """Change vehicle status while enforcing cross-domain availability rules."""

    def __init__(
        self,
        vehicle_repository: IVehicleRepository,
        repair_order_repository: IRepairOrderRepository,
        fault_repository: IFaultRepository,
    ) -> None:
        self._vehicle_repo = vehicle_repository
        self._repair_repo = repair_order_repository
        self._fault_repo = fault_repository

    def execute(self, dto: ChangeVehicleStatusDTO) -> VehicleResponseDTO:
        """Apply a status change requested from FMMS operations.

        Args:
            dto: Target vehicle and status.

        Returns:
            Updated vehicle response DTO.

        Raises:
            FMMSNotFoundError: If the vehicle does not exist.
            FMMSValidationError: If the target status is SAP-owned.
            FMMSConflictError: If ACTIVE is requested while open flows exist.
            VehicleInvalidStateTransitionError: If the domain transition is invalid.
        """
        logger.info(
            "Changing vehicle status",
            extra={
                "domain": "vehicle",
                "service": "ChangeVehicleStatusService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(dto.vehicle_id),
                "target_status": dto.status.value,
                "user_id": str(dto.requested_by),
            },
        )

        if dto.status not in _MANUAL_STATUS_CHANGE_ALLOWED_STATUSES:
            raise FMMSValidationError(
                message="This vehicle status is controlled by a dedicated workflow.",
                error_code="VEHICLE_STATUS_WORKFLOW_CONTROLLED",
                details={
                    "vehicle_id": str(dto.vehicle_id),
                    "status": dto.status.value,
                },
            )

        atomic = (
            transaction.atomic()
            if getattr(self._vehicle_repo, "uses_transactions", False)
            else nullcontext()
        )
        with atomic:
            vehicle = load_or_not_found(
                lambda: self._vehicle_repo.get_by_id(dto.vehicle_id),
                message=f"Vehicle '{dto.vehicle_id}' not found.",
                details={"vehicle_id": str(dto.vehicle_id)},
            )

            if dto.status == VehicleStatus.ACTIVE:
                self._prepare_for_active_status(dto.vehicle_id, dto.request_id)

            if vehicle.status == dto.status:
                return vehicle_to_response_dto(vehicle)

            vehicle.transition_to(dto.status)
            vehicle.updated_at = datetime.now(tz=UTC)
            saved = self._vehicle_repo.save(vehicle)

        logger.info(
            "Vehicle status changed successfully",
            extra={
                "domain": "vehicle",
                "service": "ChangeVehicleStatusService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(saved.id),
                "target_status": saved.status.value,
                "result": "success",
            },
        )

        return vehicle_to_response_dto(saved)

    def _prepare_for_active_status(
        self, vehicle_id: uuid.UUID, request_id: str
    ) -> None:
        """Resolve completed repair faults and reject remaining open workflows."""
        active_orders = self._repair_repo.list_active_by_vehicle(vehicle_id)
        if active_orders:
            raise FMMSConflictError(
                message="Vehicle cannot be active while repair orders are still open.",
                error_code="VEHICLE_HAS_ACTIVE_REPAIR_ORDERS",
                details={
                    "vehicle_id": str(vehicle_id),
                    "active_repair_order_ids": [
                        str(order.id) for order in active_orders
                    ],
                },
            )

        _close_faults_for_completed_repairs(
            vehicle_id=vehicle_id,
            repair_order_repository=self._repair_repo,
            fault_repository=self._fault_repo,
            request_id=request_id,
        )

        if self._fault_repo.has_open_fault_for_vehicle(vehicle_id):
            raise FMMSConflictError(
                message="Vehicle cannot be active while it has open faults.",
                error_code="VEHICLE_HAS_OPEN_FAULTS",
                details={"vehicle_id": str(vehicle_id)},
            )
