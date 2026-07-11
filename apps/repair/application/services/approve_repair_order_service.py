"""Services for transport-supervisor repair approval and workshop selection."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from apps.repair.application.dto.repair_dto import (
    ApproveRepairOrderDTO,
    AssignWorkshopDTO,
    RepairDecisionResponseDTO,
)
from apps.repair.application.services._timeline_helper import (
    record_repair_timeline_event,
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

_APPROVE_MESSAGE = "دستور تعمیر توسط واحد ترابری تأیید شد."
_WORKSHOP_MESSAGE = "نوع تعمیرگاه با موفقیت انتخاب شد."
_WORKSHOP_ACCEPTED_MESSAGE = "تعمیرگاه داخلی کار را پذیرفت."
_WORKSHOP_REJECTED_MESSAGE = "تعمیرگاه درخواست تعمیر را رد کرد."


class ApproveRepairOrderService:
    """Approve a CREATED repair order (transport supervisor decision).

    Args:
        repair_order_repository: Concrete ``IRepairOrderRepository``.
    """

    def __init__(
        self,
        repair_order_repository: IRepairOrderRepository,
        event_recorder: RecordRepairOrderEventService | None = None,
    ) -> None:
        self._repo = repair_order_repository
        self._event_recorder = event_recorder

    def execute(self, dto: ApproveRepairOrderDTO) -> RepairDecisionResponseDTO:
        """Transition a repair order from CREATED to APPROVED.

        Args:
            dto: Approval request.

        Returns:
            Compact decision response with Persian confirmation message.

        Raises:
            FMMSNotFoundError: If the repair order does not exist.
            RepairOrderInvalidStateTransitionError: If not in CREATED status.
        """
        logger.info(
            "Approving repair order",
            extra={
                "domain": "repair",
                "service": "ApproveRepairOrderService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(dto.repair_order_id),
                "approved_by": str(dto.approved_by),
            },
        )

        order = load_or_not_found(
            lambda: self._repo.get_by_id(dto.repair_order_id),
            message=f"Repair order '{dto.repair_order_id}' not found.",
            details={"repair_order_id": str(dto.repair_order_id)},
        )
        order.approve()
        order.updated_at = datetime.now(tz=UTC)
        saved = self._repo.save(order)
        record_repair_timeline_event(
            self._event_recorder,
            saved.id,
            RepairOrderEventType.TRANSPORT_APPROVED,
            _APPROVE_MESSAGE,
            created_by_id=dto.approved_by,
            request_id=dto.request_id,
        )

        logger.info(
            "Repair order approved",
            extra={
                "domain": "repair",
                "service": "ApproveRepairOrderService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(saved.id),
                "result": "success",
            },
        )
        return RepairDecisionResponseDTO(
            id=saved.id,
            status=saved.status,
            message=_APPROVE_MESSAGE,
            workshop_type=saved.workshop_type,
            workshop_id=saved.workshop_id,
        )


class AssignWorkshopService:
    """Assign INTERNAL/EXTERNAL workshop after transport approval.

    Args:
        repair_order_repository: Concrete ``IRepairOrderRepository``.
    """

    def __init__(
        self,
        repair_order_repository: IRepairOrderRepository,
        event_recorder: RecordRepairOrderEventService | None = None,
    ) -> None:
        self._repo = repair_order_repository
        self._event_recorder = event_recorder

    def execute(self, dto: AssignWorkshopDTO) -> RepairDecisionResponseDTO:
        """Transition APPROVED → WORKSHOP_ASSIGNED and store workshop type.

        Args:
            dto: Workshop assignment request.

        Returns:
            Compact decision response with Persian confirmation message.

        Raises:
            FMMSNotFoundError: If the repair order does not exist.
            RepairOrderInvalidStateTransitionError: If not in APPROVED status.
        """
        logger.info(
            "Assigning workshop to repair order",
            extra={
                "domain": "repair",
                "service": "AssignWorkshopService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(dto.repair_order_id),
                "workshop_type": dto.workshop_type.value,
                "assigned_by": str(dto.assigned_by),
            },
        )

        order = load_or_not_found(
            lambda: self._repo.get_by_id(dto.repair_order_id),
            message=f"Repair order '{dto.repair_order_id}' not found.",
            details={"repair_order_id": str(dto.repair_order_id)},
        )
        order.assign_workshop(dto.workshop_type, dto.workshop_id)
        order.updated_at = datetime.now(tz=UTC)
        saved = self._repo.save(order)
        record_repair_timeline_event(
            self._event_recorder,
            saved.id,
            RepairOrderEventType.WORKSHOP_ASSIGNED,
            _WORKSHOP_MESSAGE,
            created_by_id=dto.assigned_by,
            request_id=dto.request_id,
        )

        logger.info(
            "Workshop assigned to repair order",
            extra={
                "domain": "repair",
                "service": "AssignWorkshopService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(saved.id),
                "result": "success",
                "workshop_type": (
                    saved.workshop_type.value if saved.workshop_type else None
                ),
            },
        )
        return RepairDecisionResponseDTO(
            id=saved.id,
            status=saved.status,
            message=_WORKSHOP_MESSAGE,
            workshop_type=saved.workshop_type,
            workshop_id=saved.workshop_id,
        )


class AcceptRepairOrderService:
    """Accept an internally assigned workshop before technical start."""

    def __init__(
        self,
        repair_order_repository: IRepairOrderRepository,
        event_recorder: RecordRepairOrderEventService | None = None,
    ) -> None:
        self._repo = repair_order_repository
        self._event_recorder = event_recorder

    def execute(
        self,
        repair_order_id: uuid.UUID,
        request_id: str,
        accepted_by: uuid.UUID,
    ) -> RepairDecisionResponseDTO:
        """Transition WORKSHOP_ASSIGNED(INTERNAL) to WAITING_WORKSHOP_CONFIRMATION."""
        order = load_or_not_found(
            lambda: self._repo.get_by_id(repair_order_id),
            message=f"Repair order '{repair_order_id}' not found.",
            details={"repair_order_id": str(repair_order_id)},
        )
        order.accept_internal_workshop()
        order.updated_at = datetime.now(tz=UTC)
        saved = self._repo.save(order)
        record_repair_timeline_event(
            self._event_recorder,
            saved.id,
            RepairOrderEventType.TECHNICIAN_ACCEPTED,
            _WORKSHOP_ACCEPTED_MESSAGE,
            created_by_id=accepted_by,
            request_id=request_id,
        )
        return RepairDecisionResponseDTO(
            id=saved.id,
            status=saved.status,
            message=_WORKSHOP_ACCEPTED_MESSAGE,
            workshop_type=saved.workshop_type,
            workshop_id=saved.workshop_id,
        )


class RejectRepairOrderService:
    """Reject repair order at workshop step and cancel workflow."""

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
        request_id: str,
        rejected_by: uuid.UUID,
    ) -> RepairDecisionResponseDTO:
        """Transition WORKSHOP_ASSIGNED to CANCELLED."""
        order = load_or_not_found(
            lambda: self._repo.get_by_id(repair_order_id),
            message=f"Repair order '{repair_order_id}' not found.",
            details={"repair_order_id": str(repair_order_id)},
        )
        order.cancel()
        order.updated_at = datetime.now(tz=UTC)
        saved = self._repo.save(order)
        vehicle = load_or_not_found(
            lambda: self._vehicle_repo.get_by_id(order.vehicle_id),
            message=f"Vehicle '{order.vehicle_id}' not found.",
            details={"vehicle_id": str(order.vehicle_id)},
        )
        if vehicle.status != VehicleStatus.ACTIVE:
            vehicle.activate()
            vehicle.updated_at = datetime.now(tz=UTC)
            self._vehicle_repo.save(vehicle)
        record_repair_timeline_event(
            self._event_recorder,
            saved.id,
            RepairOrderEventType.REPAIR_REJECTED,
            _WORKSHOP_REJECTED_MESSAGE,
            created_by_id=rejected_by,
            request_id=request_id,
        )
        return RepairDecisionResponseDTO(
            id=saved.id,
            status=saved.status,
            message=_WORKSHOP_REJECTED_MESSAGE,
            workshop_type=saved.workshop_type,
            workshop_id=saved.workshop_id,
        )
