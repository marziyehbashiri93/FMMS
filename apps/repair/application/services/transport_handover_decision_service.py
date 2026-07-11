"""Services for transport validation after driver handover acceptance."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from apps.fault.domain.entities import Fault, FaultStatus
from apps.fault.domain.exceptions import FaultNotFoundError
from apps.fault.domain.interfaces.fault_repository import IFaultRepository
from apps.repair.application.dto.repair_dto import (
    RepairOrderResponseDTO,
    TransportHandoverApproveDTO,
    TransportHandoverRejectDTO,
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
from apps.repair.domain.entities import (
    RepairOrder,
    RepairOrderEventType,
    RepairOrderStatus,
)
from apps.repair.domain.interfaces.repair_repository import IRepairOrderRepository
from apps.vehicle.domain.interfaces.vehicle_repository import IVehicleRepository
from core.exceptions.translation import load_or_not_found
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger("repair", __name__)

_APPROVE_MESSAGE = "تایید نهایی تحویل خودرو توسط واحد ترابری ثبت شد."
_REJECT_MESSAGE = "رد صحت تعمیر توسط واحد ترابری؛ درخواست تعمیر جدید ثبت شد."


def _close_fault_for_completed_repair(
    *,
    fault_id: uuid.UUID,
    fault_repository: IFaultRepository,
    request_id: str,
    repair_order_id: uuid.UUID,
) -> None:
    """Close an open fault after transport approves a completed repair cycle."""
    try:
        fault = fault_repository.get_by_id(fault_id)
    except FaultNotFoundError:
        logger.warning(
            "Skipping fault closure — fault not found for transport approval",
            extra={
                "domain": "repair",
                "service": "ApproveTransportHandoverService",
                "operation": "close_fault",
                "request_id": request_id,
                "entity_id": str(fault_id),
                "repair_order_id": str(repair_order_id),
            },
        )
        return

    if fault.status == FaultStatus.CLOSED:
        return

    _close_open_fault(fault)
    fault.updated_at = datetime.now(tz=UTC)
    fault_repository.save(fault)


def _close_open_fault(fault: Fault) -> None:
    """Transition a non-closed fault to CLOSED via the domain entity."""
    if fault.status == FaultStatus.ASSIGNED:
        fault.start_repair()
    fault.close()


class ApproveTransportHandoverService:
    """Approve post-driver handover and finalize the maintenance cycle."""

    def __init__(
        self,
        repair_order_repository: IRepairOrderRepository,
        fault_repository: IFaultRepository,
        event_recorder: RecordRepairOrderEventService | None = None,
    ) -> None:
        self._repair_repo = repair_order_repository
        self._fault_repo = fault_repository
        self._event_recorder = event_recorder

    def execute(self, dto: TransportHandoverApproveDTO) -> RepairOrderResponseDTO:
        """Transition ACCEPTED_BY_DRIVER to COMPLETED and close the linked fault."""
        logger.info(
            "Approving transport handover",
            extra={
                "domain": "repair",
                "service": "ApproveTransportHandoverService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(dto.repair_order_id),
                "approved_by": str(dto.approved_by),
            },
        )

        order = load_or_not_found(
            lambda: self._repair_repo.get_by_id(dto.repair_order_id),
            message=f"Repair order '{dto.repair_order_id}' not found.",
            details={"repair_order_id": str(dto.repair_order_id)},
        )
        now = datetime.now(tz=UTC)
        order.complete_after_transport_handover(
            completed_at=order.completed_at or now,
        )
        order.updated_at = now
        saved = self._repair_repo.save(order)

        _close_fault_for_completed_repair(
            fault_id=saved.fault_id,
            fault_repository=self._fault_repo,
            request_id=dto.request_id,
            repair_order_id=saved.id,
        )
        record_repair_timeline_event(
            self._event_recorder,
            saved.id,
            RepairOrderEventType.TRANSPORT_HANDOVER_APPROVED,
            _APPROVE_MESSAGE,
            created_by_id=dto.approved_by,
            request_id=dto.request_id,
        )

        logger.info(
            "Transport handover approved",
            extra={
                "domain": "repair",
                "service": "ApproveTransportHandoverService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(saved.id),
                "result": "success",
            },
        )
        return _to_response_dto(saved)


class RejectTransportHandoverService:
    """Reject post-driver handover and open a follow-up repair order."""

    def __init__(
        self,
        repair_order_repository: IRepairOrderRepository,
        vehicle_repository: IVehicleRepository,
        event_recorder: RecordRepairOrderEventService | None = None,
    ) -> None:
        self._repair_repo = repair_order_repository
        self._vehicle_repo = vehicle_repository
        self._event_recorder = event_recorder

    def execute(self, dto: TransportHandoverRejectDTO) -> RepairOrderResponseDTO:
        """Archive the accepted order and create a new CREATED repair request."""
        logger.info(
            "Rejecting transport handover",
            extra={
                "domain": "repair",
                "service": "RejectTransportHandoverService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(dto.repair_order_id),
                "rejected_by": str(dto.rejected_by),
            },
        )

        order = load_or_not_found(
            lambda: self._repair_repo.get_by_id(dto.repair_order_id),
            message=f"Repair order '{dto.repair_order_id}' not found.",
            details={"repair_order_id": str(dto.repair_order_id)},
        )
        now = datetime.now(tz=UTC)
        order.complete_after_transport_handover(
            completed_at=order.completed_at or now,
        )
        order.updated_at = now
        saved = self._repair_repo.save(order)

        follow_up = _create_follow_up_repair_order(
            order=order,
            created_by_id=dto.rejected_by,
            created_at=now,
        )
        self._repair_repo.save(follow_up)

        vehicle = load_or_not_found(
            lambda: self._vehicle_repo.get_by_id(order.vehicle_id),
            message=f"Vehicle '{order.vehicle_id}' not found.",
            details={"vehicle_id": str(order.vehicle_id)},
        )
        vehicle.mark_under_repair()
        vehicle.updated_at = now
        self._vehicle_repo.save(vehicle)

        description = _REJECT_MESSAGE
        if dto.comment:
            description = f"{_REJECT_MESSAGE} ({dto.comment})"

        record_repair_timeline_event(
            self._event_recorder,
            saved.id,
            RepairOrderEventType.TRANSPORT_HANDOVER_REJECTED,
            description,
            created_by_id=dto.rejected_by,
            request_id=dto.request_id,
        )

        logger.info(
            "Transport handover rejected; follow-up repair created",
            extra={
                "domain": "repair",
                "service": "RejectTransportHandoverService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(saved.id),
                "follow_up_repair_order_id": str(follow_up.id),
                "vehicle_id": str(order.vehicle_id),
                "result": "success",
            },
        )
        return _to_response_dto(saved)


def _create_follow_up_repair_order(
    *,
    order: RepairOrder,
    created_by_id: uuid.UUID,
    created_at: datetime,
) -> RepairOrder:
    """Build a new CREATED repair order for the same vehicle and fault."""
    return RepairOrder(
        id=uuid.uuid4(),
        vehicle_id=order.vehicle_id,
        fault_id=order.fault_id,
        status=RepairOrderStatus.CREATED,
        created_by_id=created_by_id,
        created_at=created_at,
        updated_at=created_at,
    )
