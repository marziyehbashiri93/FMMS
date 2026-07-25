"""Services for transport-supervisor repair approval and workshop selection."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Protocol

from apps.fault.domain.entities import FaultStatus
from apps.fault.domain.interfaces.fault_repository import IFaultRepository
from apps.repair.application.dto.repair_dto import (
    ApproveRepairOrderDTO,
    AssignWorkshopDTO,
    ExternalWorkshopReferralResponseDTO,
    RejectRepairOrderByTransportDTO,
    RepairDecisionResponseDTO,
)
from apps.repair.application.services._timeline_helper import (
    record_repair_timeline_event,
)
from apps.repair.application.services.repair_order_timeline_service import (
    RecordRepairOrderEventService,
)
from apps.repair.domain.entities import (
    ExternalWorkshopReferralRequest,
    ExternalWorkshopReferralStatus,
    RepairOrder,
    RepairOrderEventType,
    WorkshopType,
)
from apps.repair.domain.interfaces.external_referral_repository import (
    IExternalWorkshopReferralRepository,
)
from apps.repair.domain.interfaces.repair_repository import IRepairOrderRepository
from apps.vehicle.domain.entities import VehicleStatus
from apps.vehicle.domain.interfaces.vehicle_repository import IVehicleRepository
from core.exceptions.translation import load_or_not_found
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger("repair", __name__)

_APPROVE_MESSAGE = "دستور تعمیر توسط واحد ترابری تأیید شد."
_REJECT_MESSAGE = "دستور تعمیر توسط واحد ترابری رد شد."
_WORKSHOP_MESSAGE = "نوع تعمیرگاه با موفقیت انتخاب شد."
_EXTERNAL_REFERRAL_MESSAGE = "تعمیرگاه خارجی انتخاب شد؛ درخواست مجوز ارجاع ثبت شد."
_WORKSHOP_ACCEPTED_MESSAGE = "تعمیرگاه داخلی کار را پذیرفت."
_WORKSHOP_REJECTED_MESSAGE = "تعمیرگاه درخواست تعمیر را رد کرد."


class CreateVehicleHandoverPort(Protocol):
    """Port for creating a vehicle handover after external workshop assignment."""

    def execute(self, *, repair_order_id: uuid.UUID, vehicle_id: uuid.UUID) -> None:
        """Create handover when absent for repair order."""
        ...


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


class RejectRepairOrderByTransportService:
    """Reject a CREATED repair order during initial transport review."""

    def __init__(
        self,
        repair_order_repository: IRepairOrderRepository,
        fault_repository: IFaultRepository,
        vehicle_repository: IVehicleRepository,
        event_recorder: RecordRepairOrderEventService | None = None,
    ) -> None:
        self._repo = repair_order_repository
        self._fault_repo = fault_repository
        self._vehicle_repo = vehicle_repository
        self._event_recorder = event_recorder

    def execute(
        self, dto: RejectRepairOrderByTransportDTO
    ) -> RepairDecisionResponseDTO:
        """Transition CREATED repair order to REJECTED_BY_TRANSPORT."""
        order = load_or_not_found(
            lambda: self._repo.get_by_id(dto.repair_order_id),
            message=f"Repair order '{dto.repair_order_id}' not found.",
            details={"repair_order_id": str(dto.repair_order_id)},
        )
        reason = dto.reason.strip()
        order.reject_by_transport(reason)
        order.updated_at = datetime.now(tz=UTC)
        saved = self._repo.save(order)

        fault = load_or_not_found(
            lambda: self._fault_repo.get_by_id(saved.fault_id),
            message=f"Fault '{saved.fault_id}' not found.",
            details={"fault_id": str(saved.fault_id)},
        )
        if fault.status == FaultStatus.AWAITING_TRANSPORT:
            fault.transition_to(FaultStatus.OPEN)
            fault.updated_at = datetime.now(tz=UTC)
            self._fault_repo.save(fault)

        vehicle = load_or_not_found(
            lambda: self._vehicle_repo.get_by_id(saved.vehicle_id),
            message=f"Vehicle '{saved.vehicle_id}' not found.",
            details={"vehicle_id": str(saved.vehicle_id)},
        )
        if vehicle.status != VehicleStatus.ACTIVE:
            vehicle.activate()
            vehicle.updated_at = datetime.now(tz=UTC)
            self._vehicle_repo.save(vehicle)

        record_repair_timeline_event(
            self._event_recorder,
            saved.id,
            RepairOrderEventType.TRANSPORT_REJECTED,
            f"{_REJECT_MESSAGE} دلیل: {reason}",
            created_by_id=dto.rejected_by,
            request_id=dto.request_id,
        )
        return RepairDecisionResponseDTO(
            id=saved.id,
            status=saved.status,
            message=_REJECT_MESSAGE,
            workshop_type=saved.workshop_type,
            workshop_id=saved.workshop_id,
            transport_rejection_reason=saved.transport_rejection_reason,
        )


class AssignWorkshopService:
    """Assign INTERNAL/EXTERNAL workshop after transport approval.

    For ``EXTERNAL``, a permission request is created and the order waits for
    external referral approval.

    Args:
        repair_order_repository: Concrete ``IRepairOrderRepository``.
        vehicle_repository: Used to mark the vehicle waiting for driver handover.
        create_handover_service: Creates the driver handover record for EXTERNAL.
        event_recorder: Optional timeline recorder.
    """

    def __init__(
        self,
        repair_order_repository: IRepairOrderRepository,
        external_referral_repository: IExternalWorkshopReferralRepository | None = None,
        vehicle_repository: IVehicleRepository | None = None,
        create_handover_service: CreateVehicleHandoverPort | None = None,
        event_recorder: RecordRepairOrderEventService | None = None,
    ) -> None:
        self._repo = repair_order_repository
        self._external_referrals = external_referral_repository
        self._vehicle_repo = vehicle_repository
        self._create_handover_service = create_handover_service
        self._event_recorder = event_recorder

    def execute(self, dto: AssignWorkshopDTO) -> RepairDecisionResponseDTO:
        """Transition APPROVED → WORKSHOP_ASSIGNED (INTERNAL) or driver handover (EXTERNAL).

        Args:
            dto: Workshop assignment request.

        Returns:
            Compact decision response with Persian confirmation message.

        Raises:
            FMMSNotFoundError: If the repair order or vehicle does not exist.
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
        now = datetime.now(tz=UTC)
        order.assign_workshop(dto.workshop_type, dto.workshop_id)
        order.updated_at = now
        saved = self._repo.save(order)
        record_repair_timeline_event(
            self._event_recorder,
            saved.id,
            RepairOrderEventType.WORKSHOP_ASSIGNED,
            _WORKSHOP_MESSAGE,
            created_by_id=dto.assigned_by,
            request_id=dto.request_id,
        )

        message = _WORKSHOP_MESSAGE
        if saved.workshop_type == WorkshopType.EXTERNAL:
            referral = self._create_external_referral(
                order=saved,
                assigned_by=dto.assigned_by,
                request_id=dto.request_id,
                now=now,
                reason=dto.reason,
            )
            message = _EXTERNAL_REFERRAL_MESSAGE
        else:
            referral = None

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
                "status": saved.status.value,
            },
        )
        return RepairDecisionResponseDTO(
            id=saved.id,
            status=saved.status,
            message=message,
            workshop_type=saved.workshop_type,
            workshop_id=saved.workshop_id,
            external_referral_request_id=referral.id if referral else None,
        )

    def _create_external_referral(
        self,
        *,
        order: RepairOrder,
        assigned_by: uuid.UUID,
        request_id: str,
        now: datetime,
        reason: str,
    ) -> ExternalWorkshopReferralRequest:
        """Create a referral permission request for an external workshop."""
        if self._external_referrals is None:
            raise RuntimeError(
                "AssignWorkshopService requires referral repository for EXTERNAL."
            )
        existing = self._external_referrals.get_open_by_repair_order(order.id)
        if existing is not None:
            return existing

        referral = ExternalWorkshopReferralRequest(
            id=uuid.uuid4(),
            repair_order_id=order.id,
            vehicle_id=order.vehicle_id,
            fault_id=order.fault_id,
            status=ExternalWorkshopReferralStatus.REQUESTED,
            workshop_id=order.workshop_id,
            reason=reason,
            requested_by_id=assigned_by,
            requested_at=now,
            created_at=now,
            updated_at=now,
        )
        saved = self._external_referrals.save(referral)
        record_repair_timeline_event(
            self._event_recorder,
            order.id,
            RepairOrderEventType.EXTERNAL_REFERRAL_REQUESTED,
            "درخواست مجوز ارجاع به تعمیرگاه بیرونی ثبت شد.",
            created_by_id=assigned_by,
            request_id=request_id,
        )
        return saved

    def _advance_external_to_driver_handover(
        self,
        *,
        order: RepairOrder,
        assigned_by: uuid.UUID,
        request_id: str,
        now: datetime,
    ) -> RepairOrder:
        """Move EXTERNAL repair to WAITING_DRIVER_CONFIRMATION and create handover."""
        if self._vehicle_repo is None or self._create_handover_service is None:
            raise RuntimeError(
                "AssignWorkshopService requires vehicle and handover ports for EXTERNAL."
            )

        order.complete_waiting_driver_confirmation(completed_at=now)
        order.updated_at = now
        saved = self._repo.save(order)

        vehicle = load_or_not_found(
            lambda: self._vehicle_repo.get_by_id(saved.vehicle_id),
            message=f"Vehicle '{saved.vehicle_id}' not found.",
            details={"vehicle_id": str(saved.vehicle_id)},
        )
        if vehicle.status == VehicleStatus.INACTIVE:
            vehicle.mark_under_repair()
            vehicle.updated_at = now
            self._vehicle_repo.save(vehicle)
        if vehicle.status != VehicleStatus.WAITING_DRIVER_CONFIRMATION:
            vehicle.mark_waiting_driver_confirmation()
            vehicle.updated_at = now
            self._vehicle_repo.save(vehicle)

        self._create_handover_service.execute(
            repair_order_id=saved.id,
            vehicle_id=saved.vehicle_id,
        )
        record_repair_timeline_event(
            self._event_recorder,
            saved.id,
            RepairOrderEventType.WAITING_DRIVER_CONFIRMATION,
            "تعمیر خارجی به مرحله تایید تحویل راننده منتقل شد.",
            created_by_id=assigned_by,
            request_id=request_id,
        )
        return saved


def external_referral_to_dto(
    request: ExternalWorkshopReferralRequest,
) -> ExternalWorkshopReferralResponseDTO:
    """Map external referral request entity to response DTO."""
    return ExternalWorkshopReferralResponseDTO(
        id=request.id,
        repair_order_id=request.repair_order_id,
        vehicle_id=request.vehicle_id,
        fault_id=request.fault_id,
        status=request.status,
        workshop_id=request.workshop_id,
        reason=request.reason,
        requested_by_id=request.requested_by_id,
        requested_at=request.requested_at,
        approved_by_id=request.approved_by_id,
        approved_at=request.approved_at,
        rejected_by_id=request.rejected_by_id,
        rejected_at=request.rejected_at,
        rejection_reason=request.rejection_reason,
        created_at=request.created_at,
        updated_at=request.updated_at,
    )


class ListExternalWorkshopReferralRequestsService:
    """List external-workshop referral permission requests."""

    def __init__(self, repository: IExternalWorkshopReferralRepository) -> None:
        self._repo = repository

    def execute(
        self,
        status: ExternalWorkshopReferralStatus | None = None,
    ) -> list[ExternalWorkshopReferralResponseDTO]:
        """Return referral requests, optionally filtered by status."""
        return [external_referral_to_dto(item) for item in self._repo.list_all(status)]


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
