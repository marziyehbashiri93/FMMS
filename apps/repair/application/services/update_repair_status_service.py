"""Services for repair order status transitions.

Three focused services — one per terminal transition:
    StartRepairService         ASSIGNED  → IN_PROGRESS
    CompleteRepairOrderService IN_PROGRESS → COMPLETED
    CancelRepairOrderService   any mutable → CANCELLED

All state-machine logic lives in ``RepairOrder.transition_to()`` /
domain entity methods. These services only load, delegate, persist, and log.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Protocol

from apps.material.domain.entities import MaterialRequestStatus
from apps.material.domain.interfaces.material_request_repository import (
    IMaterialRequestRepository,
)
from apps.repair.application.dto.repair_dto import (
    CloseRepairOrderDTO,
    CompleteRepairOrderDTO,
    RepairOrderResponseDTO,
)
from apps.repair.application.services._timeline_helper import (
    record_repair_timeline_event,
)
from apps.repair.application.services.create_repair_order_service import (
    _to_response_dto,
)
from apps.repair.application.services.repair_order_timeline_service import (
    RecordRepairOrderEventService,
)
from apps.repair.domain.entities import RepairOrderEventType
from apps.repair.domain.interfaces.repair_repository import IRepairOrderRepository
from apps.vehicle.domain.entities import VehicleStatus
from apps.vehicle.domain.interfaces.vehicle_repository import IVehicleRepository
from core.exceptions.translation import load_or_not_found
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger("repair", __name__)


class CreateVehicleHandoverPort(Protocol):
    """Port for creating a vehicle handover after technical completion."""

    def execute(self, *, repair_order_id: uuid.UUID, vehicle_id: uuid.UUID) -> None:
        """Create handover when absent for repair order."""
        ...


class StartRepairService:
    """Transition a repair order to IN_PROGRESS.

    Args:
        repair_order_repository: Concrete ``IRepairOrderRepository``.
        event_recorder: Optional timeline recorder.
    """

    def __init__(
        self,
        repair_order_repository: IRepairOrderRepository,
        vehicle_repository: IVehicleRepository,
        event_recorder: RecordRepairOrderEventService | None = None,
    ) -> None:
        self._repo = repair_order_repository
        self._vehicle_repo = vehicle_repository
        self._event_recorder = event_recorder

    def execute(
        self,
        repair_order_id: uuid.UUID,
        request_id: str = "",
        started_by: uuid.UUID | None = None,
    ) -> RepairOrderResponseDTO:
        """Start work on an ASSIGNED or WORKSHOP_ASSIGNED repair order.

        Args:
            repair_order_id: UUID of the order to start.
            request_id: Optional correlation ID for tracing.

        Returns:
            ``RepairOrderResponseDTO`` with ``status == IN_PROGRESS``.

        Raises:
            FMMSNotFoundError: If no order with ``repair_order_id`` exists.
            RepairOrderInvalidStateTransitionError: If not ASSIGNED (entity).
        """
        logger.info(
            "Starting repair work",
            extra={
                "domain": "repair",
                "service": "StartRepairService",
                "operation": "execute",
                "request_id": request_id,
                "entity_id": str(repair_order_id),
            },
        )

        order = load_or_not_found(
            lambda: self._repo.get_by_id(repair_order_id),
            message=f"Repair order '{repair_order_id}' not found.",
            details={"repair_order_id": str(repair_order_id)},
        )

        order.start_work()
        order.updated_at = datetime.now(tz=UTC)
        saved = self._repo.save(order)
        vehicle = load_or_not_found(
            lambda: self._vehicle_repo.get_by_id(saved.vehicle_id),
            message=f"Vehicle '{saved.vehicle_id}' not found.",
            details={"vehicle_id": str(saved.vehicle_id)},
        )
        if vehicle.status != VehicleStatus.UNDER_REPAIR:
            vehicle.mark_under_repair()
            vehicle.updated_at = datetime.now(tz=UTC)
            self._vehicle_repo.save(vehicle)
        record_repair_timeline_event(
            self._event_recorder,
            saved.id,
            RepairOrderEventType.REPAIR_STARTED,
            "تعمیر شروع شد.",
            created_by_id=started_by,
            request_id=request_id,
        )

        logger.info(
            "Repair work started",
            extra={
                "domain": "repair",
                "service": "StartRepairService",
                "operation": "execute",
                "request_id": request_id,
                "entity_id": str(saved.id),
                "result": "success",
            },
        )

        return _to_response_dto(saved)


class CompleteRepairOrderService:
    """Transition a repair order from IN_PROGRESS to COMPLETED.

    Args:
        repair_order_repository: Concrete ``IRepairOrderRepository``.
        event_recorder: Optional timeline recorder.
    """

    def __init__(
        self,
        repair_order_repository: IRepairOrderRepository,
        vehicle_repository: IVehicleRepository,
        material_request_repository: IMaterialRequestRepository,
        create_vehicle_handover_service: CreateVehicleHandoverPort,
        event_recorder: RecordRepairOrderEventService | None = None,
    ) -> None:
        self._repo = repair_order_repository
        self._vehicle_repo = vehicle_repository
        self._material_request_repo = material_request_repository
        self._create_handover_service = create_vehicle_handover_service
        self._event_recorder = event_recorder

    def execute(self, dto: CompleteRepairOrderDTO) -> RepairOrderResponseDTO:
        """Complete an IN_PROGRESS repair order.

        Args:
            dto: Completion request with ``completed_at`` timestamp.

        Returns:
            ``RepairOrderResponseDTO`` with ``status == COMPLETED``.

        Raises:
            FMMSNotFoundError: If order not found.
            RepairOrderInvalidStateTransitionError: If not IN_PROGRESS (entity).
        """
        logger.info(
            "Completing repair order",
            extra={
                "domain": "repair",
                "service": "CompleteRepairOrderService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(dto.repair_order_id),
            },
        )

        order = load_or_not_found(
            lambda: self._repo.get_by_id(dto.repair_order_id),
            message=f"Repair order '{dto.repair_order_id}' not found.",
            details={"repair_order_id": str(dto.repair_order_id)},
        )

        from core.exceptions.base_exception import (  # noqa: PLC0415
            FMMSConflictError,
        )

        material_requests = self._material_request_repo.list_by_repair_order(
            dto.repair_order_id
        )
        pending_material = [
            request
            for request in material_requests
            if request.status
            not in {
                MaterialRequestStatus.REJECTED,
                MaterialRequestStatus.RECEIVED,
            }
        ]
        if pending_material:
            raise FMMSConflictError(
                message=(
                    "Cannot complete repair until all material requests are "
                    "physically received or rejected."
                ),
                error_code="PENDING_MATERIAL_REQUESTS",
                details={
                    "repair_order_id": str(dto.repair_order_id),
                    "pending_material_request_ids": [
                        str(item.id) for item in pending_material
                    ],
                },
            )

        has_received_parts = any(
            request.status == MaterialRequestStatus.RECEIVED
            for request in material_requests
        )
        if has_received_parts and not order.parts and not dto.no_parts_consumed:
            raise FMMSConflictError(
                message=(
                    "Record consumed spare parts before completing repair, "
                    "or explicitly confirm no parts were consumed."
                ),
                error_code="CONSUMED_PARTS_REQUIRED",
                details={"repair_order_id": str(dto.repair_order_id)},
            )

        order.complete_waiting_driver_confirmation(completed_at=dto.completed_at)
        order.updated_at = datetime.now(tz=UTC)
        saved = self._repo.save(order)
        vehicle = load_or_not_found(
            lambda: self._vehicle_repo.get_by_id(saved.vehicle_id),
            message=f"Vehicle '{saved.vehicle_id}' not found.",
            details={"vehicle_id": str(saved.vehicle_id)},
        )
        if vehicle.status == VehicleStatus.INACTIVE:
            vehicle.mark_under_repair()
            vehicle.updated_at = datetime.now(tz=UTC)
            self._vehicle_repo.save(vehicle)
        if vehicle.status != VehicleStatus.WAITING_DRIVER_CONFIRMATION:
            vehicle.mark_waiting_driver_confirmation()
            vehicle.updated_at = datetime.now(tz=UTC)
            self._vehicle_repo.save(vehicle)
        self._create_handover_service.execute(
            repair_order_id=saved.id,
            vehicle_id=saved.vehicle_id,
        )
        record_repair_timeline_event(
            self._event_recorder,
            saved.id,
            RepairOrderEventType.REPAIR_COMPLETED,
            "تعمیر فنی تکمیل شد.",
            created_by_id=dto.completed_by,
            request_id=dto.request_id,
        )
        record_repair_timeline_event(
            self._event_recorder,
            saved.id,
            RepairOrderEventType.WAITING_DRIVER_CONFIRMATION,
            "تعمیر انجام شد و در انتظار تایید راننده است.",
            created_by_id=dto.completed_by,
            request_id=dto.request_id,
        )

        logger.info(
            "Repair order completed",
            extra={
                "domain": "repair",
                "service": "CompleteRepairOrderService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(saved.id),
                "result": "success",
            },
        )

        return _to_response_dto(saved)


class CancelRepairOrderService:
    """Cancel a repair order from any mutable status.

    Args:
        repair_order_repository: Concrete ``IRepairOrderRepository``.
    """

    def __init__(self, repair_order_repository: IRepairOrderRepository) -> None:
        self._repo = repair_order_repository

    def execute(self, dto: CloseRepairOrderDTO) -> RepairOrderResponseDTO:
        """Cancel the repair order.

        Args:
            dto: Cancellation request.

        Returns:
            ``RepairOrderResponseDTO`` with ``status == CANCELLED``.

        Raises:
            FMMSNotFoundError: If order not found.
            RepairOrderInvalidStateTransitionError: If already COMPLETED or
                CANCELLED (raised by entity).
        """
        logger.info(
            "Cancelling repair order",
            extra={
                "domain": "repair",
                "service": "CancelRepairOrderService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(dto.repair_order_id),
            },
        )

        order = load_or_not_found(
            lambda: self._repo.get_by_id(dto.repair_order_id),
            message=f"Repair order '{dto.repair_order_id}' not found.",
            details={"repair_order_id": str(dto.repair_order_id)},
        )

        order.cancel()
        order.updated_at = datetime.now(tz=UTC)
        saved = self._repo.save(order)

        logger.info(
            "Repair order cancelled",
            extra={
                "domain": "repair",
                "service": "CancelRepairOrderService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(saved.id),
                "result": "success",
            },
        )

        return _to_response_dto(saved)
