"""Application services for the external workshop workflow."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from django.db import transaction

from apps.fault.domain.entities import FaultStatus
from apps.fault.domain.exceptions import FaultNotFoundError
from apps.fault.domain.interfaces.fault_repository import IFaultRepository
from apps.repair.application.dto.repair_dto import (
    AssignExternalWorkshopDTO,
    CancelExternalWorkshopAssignmentDTO,
    CloseExternalRepairDTO,
    ConfirmExternalWorkshopDeliveryDTO,
    ConfirmExternalWorkshopPickupDTO,
    ExternalRepairReviewResponseDTO,
    ExternalWorkshopAssignmentResponseDTO,
    ExternalWorkshopDeliveryResponseDTO,
    ExternalWorkshopPickupResponseDTO,
    ReviewExternalRepairDTO,
)
from apps.repair.application.services._timeline_helper import (
    record_repair_timeline_event,
)
from apps.repair.application.services.repair_order_timeline_service import (
    RecordRepairOrderEventService,
)
from apps.repair.domain.entities import (
    RepairOrder,
    RepairOrderEventType,
    RepairOrderStatus,
    RepairPart,
)
from apps.repair.domain.external_workshop_entities import (
    ExternalRepairReview,
    ExternalRepairReviewStatus,
    ExternalWorkshopAssignment,
    ExternalWorkshopAssignmentCancellationReason,
    ExternalWorkshopAssignmentStatus,
    ExternalWorkshopDelivery,
    ExternalWorkshopPickup,
)
from apps.repair.domain.interfaces.external_workshop_repository import (
    IExternalWorkshopRepository,
)
from apps.repair.domain.interfaces.repair_repository import IRepairOrderRepository
from apps.repair.domain.value_objects import PartQuantity
from apps.vehicle.application.services.record_component_history_service import (
    RecordComponentHistoryFromRepairService,
)
from apps.vehicle.domain.entities import VehicleStatus
from apps.vehicle.domain.interfaces.vehicle_repository import IVehicleRepository
from core.exceptions.base_exception import FMMSConflictError, FMMSValidationError
from core.exceptions.translation import load_or_not_found


def _delivery_to_dto(
    delivery: ExternalWorkshopDelivery | None,
) -> ExternalWorkshopDeliveryResponseDTO | None:
    if delivery is None:
        return None
    return ExternalWorkshopDeliveryResponseDTO(
        id=delivery.id,
        assignment_id=delivery.assignment_id,
        repair_order_id=delivery.repair_order_id,
        vehicle_id=delivery.vehicle_id,
        delivery_datetime=delivery.delivery_datetime,
        workshop_name=delivery.workshop_name,
        workshop_address=delivery.workshop_address,
        workshop_phone=delivery.workshop_phone,
        vehicle_odometer=delivery.vehicle_odometer,
        notes=delivery.notes,
        delivered_by_id=delivery.delivered_by_id,
        created_at=delivery.created_at,
        updated_at=delivery.updated_at,
    )


def _pickup_to_dto(
    pickup: ExternalWorkshopPickup | None,
) -> ExternalWorkshopPickupResponseDTO | None:
    if pickup is None:
        return None
    return ExternalWorkshopPickupResponseDTO(
        id=pickup.id,
        assignment_id=pickup.assignment_id,
        repair_order_id=pickup.repair_order_id,
        vehicle_id=pickup.vehicle_id,
        pickup_datetime=pickup.pickup_datetime,
        vehicle_odometer=pickup.vehicle_odometer,
        notes=pickup.notes,
        picked_up_by_id=pickup.picked_up_by_id,
        created_at=pickup.created_at,
        updated_at=pickup.updated_at,
    )


def _review_to_dto(
    review: ExternalRepairReview | None,
) -> ExternalRepairReviewResponseDTO | None:
    if review is None:
        return None
    return ExternalRepairReviewResponseDTO(
        id=review.id,
        assignment_id=review.assignment_id,
        repair_order_id=review.repair_order_id,
        invoice_attachment=review.invoice_attachment,
        repair_services=review.repair_services,
        replaced_parts=review.replaced_parts,
        repair_cost=review.repair_cost,
        additional_notes=review.additional_notes,
        sap_purchase_order_number=review.sap_purchase_order_number,
        sap_invoice_document_number=review.sap_invoice_document_number,
        status=review.status,
        reviewed_by_id=review.reviewed_by_id,
        created_at=review.created_at,
        updated_at=review.updated_at,
    )


def _assignment_to_dto(
    repo: IExternalWorkshopRepository,
    assignment: ExternalWorkshopAssignment,
) -> ExternalWorkshopAssignmentResponseDTO:
    return ExternalWorkshopAssignmentResponseDTO(
        id=assignment.id,
        repair_order_id=assignment.repair_order_id,
        vehicle_id=assignment.vehicle_id,
        fault_id=assignment.fault_id,
        workshop_id=assignment.workshop_id,
        workshop_name=assignment.workshop_name,
        workshop_address=assignment.workshop_address,
        assignment_date=assignment.assignment_date,
        repair_reason=assignment.repair_reason,
        description=assignment.description,
        status=assignment.status,
        assigned_by_id=assignment.assigned_by_id,
        cancellation_reason=assignment.cancellation_reason,
        cancellation_note=assignment.cancellation_note,
        cancelled_by_id=assignment.cancelled_by_id,
        cancelled_at=assignment.cancelled_at,
        created_at=assignment.created_at,
        updated_at=assignment.updated_at,
        delivery=_delivery_to_dto(repo.get_delivery_by_assignment(assignment.id)),
        pickup=_pickup_to_dto(repo.get_pickup_by_assignment(assignment.id)),
        review=_review_to_dto(repo.get_review_by_assignment(assignment.id)),
    )


class AssignExternalWorkshopService:
    """Assign or replace an external workshop before driver delivery."""

    def __init__(
        self,
        external_workshop_repository: IExternalWorkshopRepository,
        repair_order_repository: IRepairOrderRepository,
        event_recorder: RecordRepairOrderEventService | None = None,
    ) -> None:
        self._repo = external_workshop_repository
        self._repair_repo = repair_order_repository
        self._event_recorder = event_recorder

    @transaction.atomic
    def execute(self, dto: AssignExternalWorkshopDTO) -> ExternalWorkshopAssignmentResponseDTO:
        order = load_or_not_found(
            lambda: self._repair_repo.get_by_id(dto.repair_order_id),
            message=f"Repair order '{dto.repair_order_id}' not found.",
            details={"repair_order_id": str(dto.repair_order_id)},
        )
        now = datetime.now(tz=UTC)
        existing = self._repo.get_active_assignment_by_repair_order(order.id)
        if existing is not None:
            if self._repo.get_delivery_by_assignment(existing.id) is not None:
                raise FMMSConflictError(
                    message="External workshop assignment cannot be changed after delivery.",
                    error_code="EXTERNAL_ASSIGNMENT_READ_ONLY_AFTER_DELIVERY",
                    details={"assignment_id": str(existing.id)},
                )
            if _same_assignment(existing, dto):
                return _assignment_to_dto(self._repo, existing)
            existing.cancel(
                reason=ExternalWorkshopAssignmentCancellationReason.WORKSHOP_CHANGED,
                cancelled_by_id=dto.assigned_by,
                cancelled_at=now,
                note="تغییر تعمیرگاه قبل از تحویل خودرو.",
            )
            self._repo.save_assignment(existing)
            record_repair_timeline_event(
                self._event_recorder,
                order.id,
                RepairOrderEventType.EXTERNAL_WORKSHOP_ASSIGNMENT_CANCELLED,
                "ارجاع به تعمیرگاه بیرونی لغو شد. دلیل: تغییر تعمیرگاه.",
                created_by_id=dto.assigned_by,
                request_id=dto.request_id,
            )

        order.assign_external_workshop(dto.workshop_id)
        order.updated_at = now
        self._repair_repo.save(order)
        assignment = ExternalWorkshopAssignment(
            id=uuid.uuid4(),
            repair_order_id=order.id,
            vehicle_id=order.vehicle_id,
            fault_id=order.fault_id,
            workshop_id=dto.workshop_id,
            workshop_name=dto.workshop_name.strip(),
            workshop_address=dto.workshop_address.strip(),
            assignment_date=dto.assignment_date,
            repair_reason=dto.repair_reason.strip(),
            description=dto.description.strip(),
            status=ExternalWorkshopAssignmentStatus.ACTIVE,
            assigned_by_id=dto.assigned_by,
            created_at=now,
            updated_at=now,
        )
        saved = self._repo.save_assignment(assignment)
        record_repair_timeline_event(
            self._event_recorder,
            order.id,
            RepairOrderEventType.EXTERNAL_WORKSHOP_ASSIGNED,
            "ارجاع به تعمیرگاه بیرونی ثبت شد.",
            created_by_id=dto.assigned_by,
            request_id=dto.request_id,
        )
        return _assignment_to_dto(self._repo, saved)


class ConfirmExternalWorkshopDeliveryService:
    """Confirm driver delivery and start the external repair immediately."""

    def __init__(
        self,
        external_workshop_repository: IExternalWorkshopRepository,
        repair_order_repository: IRepairOrderRepository,
        vehicle_repository: IVehicleRepository,
        event_recorder: RecordRepairOrderEventService | None = None,
    ) -> None:
        self._repo = external_workshop_repository
        self._repair_repo = repair_order_repository
        self._vehicle_repo = vehicle_repository
        self._event_recorder = event_recorder

    @transaction.atomic
    def execute(
        self, dto: ConfirmExternalWorkshopDeliveryDTO
    ) -> ExternalWorkshopAssignmentResponseDTO:
        assignment = self._repo.get_assignment_by_id(dto.assignment_id)
        assignment.ensure_active()
        if self._repo.get_delivery_by_assignment(assignment.id) is not None:
            raise FMMSConflictError(
                message="External workshop delivery was already confirmed.",
                error_code="EXTERNAL_DELIVERY_ALREADY_CONFIRMED",
                details={"assignment_id": str(assignment.id)},
            )
        order = _load_order(self._repair_repo, assignment.repair_order_id)
        if order.status != RepairOrderStatus.WAITING_EXTERNAL_DELIVERY:
            raise FMMSConflictError(
                message="External delivery can only be confirmed while waiting for delivery.",
                error_code="EXTERNAL_DELIVERY_INVALID_REPAIR_STATE",
                details={"repair_order_id": str(order.id), "status": order.status.value},
            )
        now = datetime.now(tz=UTC)
        delivery = ExternalWorkshopDelivery(
            id=uuid.uuid4(),
            assignment_id=assignment.id,
            repair_order_id=order.id,
            vehicle_id=assignment.vehicle_id,
            delivery_datetime=dto.delivery_datetime,
            workshop_name=dto.workshop_name.strip(),
            workshop_address=dto.workshop_address.strip(),
            workshop_phone=dto.workshop_phone.strip(),
            vehicle_odometer=dto.vehicle_odometer,
            notes=dto.notes.strip(),
            delivered_by_id=dto.delivered_by,
            created_at=now,
            updated_at=now,
        )
        self._repo.save_delivery(delivery)
        order.confirm_external_delivery()
        order.updated_at = now
        self._repair_repo.save(order)
        vehicle = _load_vehicle(self._vehicle_repo, assignment.vehicle_id)
        if vehicle.status != VehicleStatus.UNDER_EXTERNAL_REPAIR:
            vehicle.mark_under_external_repair()
            vehicle.updated_at = now
            self._vehicle_repo.save(vehicle)
        record_repair_timeline_event(
            self._event_recorder,
            order.id,
            RepairOrderEventType.EXTERNAL_VEHICLE_DELIVERED,
            "خودرو به تعمیرگاه بیرونی تحویل شد.",
            created_by_id=dto.delivered_by,
            request_id=dto.request_id,
        )
        record_repair_timeline_event(
            self._event_recorder,
            order.id,
            RepairOrderEventType.EXTERNAL_REPAIR_IN_PROGRESS,
            "تعمیر بیرونی در حال انجام است.",
            created_by_id=dto.delivered_by,
            request_id=dto.request_id,
        )
        return _assignment_to_dto(self._repo, assignment)


class ConfirmExternalWorkshopPickupService:
    """Confirm pickup and immediately return vehicle availability."""

    def __init__(
        self,
        external_workshop_repository: IExternalWorkshopRepository,
        repair_order_repository: IRepairOrderRepository,
        vehicle_repository: IVehicleRepository,
        event_recorder: RecordRepairOrderEventService | None = None,
    ) -> None:
        self._repo = external_workshop_repository
        self._repair_repo = repair_order_repository
        self._vehicle_repo = vehicle_repository
        self._event_recorder = event_recorder

    @transaction.atomic
    def execute(
        self, dto: ConfirmExternalWorkshopPickupDTO
    ) -> ExternalWorkshopAssignmentResponseDTO:
        assignment = self._repo.get_assignment_by_id(dto.assignment_id)
        assignment.ensure_active()
        if self._repo.get_delivery_by_assignment(assignment.id) is None:
            raise FMMSConflictError(
                message="External workshop pickup cannot be confirmed before delivery.",
                error_code="EXTERNAL_PICKUP_REQUIRES_DELIVERY",
                details={"assignment_id": str(assignment.id)},
            )
        if self._repo.get_pickup_by_assignment(assignment.id) is not None:
            raise FMMSConflictError(
                message="External workshop pickup was already confirmed.",
                error_code="EXTERNAL_PICKUP_ALREADY_CONFIRMED",
                details={"assignment_id": str(assignment.id)},
            )
        order = _load_order(self._repair_repo, assignment.repair_order_id)
        if order.status != RepairOrderStatus.EXTERNAL_REPAIR_IN_PROGRESS:
            raise FMMSConflictError(
                message="External pickup requires repair in progress.",
                error_code="EXTERNAL_PICKUP_INVALID_REPAIR_STATE",
                details={"repair_order_id": str(order.id), "status": order.status.value},
            )
        now = datetime.now(tz=UTC)
        pickup = ExternalWorkshopPickup(
            id=uuid.uuid4(),
            assignment_id=assignment.id,
            repair_order_id=order.id,
            vehicle_id=assignment.vehicle_id,
            pickup_datetime=dto.pickup_datetime,
            vehicle_odometer=dto.vehicle_odometer,
            notes=dto.notes.strip(),
            picked_up_by_id=dto.picked_up_by,
            created_at=now,
            updated_at=now,
        )
        self._repo.save_pickup(pickup)
        order.confirm_external_pickup()
        order.updated_at = now
        self._repair_repo.save(order)
        vehicle = _load_vehicle(self._vehicle_repo, assignment.vehicle_id)
        if vehicle.status != VehicleStatus.ACTIVE:
            vehicle.activate()
            vehicle.updated_at = now
            self._vehicle_repo.save(vehicle)
        record_repair_timeline_event(
            self._event_recorder,
            order.id,
            RepairOrderEventType.EXTERNAL_VEHICLE_PICKED_UP,
            "خودرو از تعمیرگاه بیرونی دریافت شد.",
            created_by_id=dto.picked_up_by,
            request_id=dto.request_id,
        )
        return _assignment_to_dto(self._repo, assignment)


class ReviewExternalRepairService:
    """Save Transportation's external repair review as a draft."""

    def __init__(
        self,
        external_workshop_repository: IExternalWorkshopRepository,
        repair_order_repository: IRepairOrderRepository,
        event_recorder: RecordRepairOrderEventService | None = None,
    ) -> None:
        self._repo = external_workshop_repository
        self._repair_repo = repair_order_repository
        self._event_recorder = event_recorder

    @transaction.atomic
    def execute(self, dto: ReviewExternalRepairDTO) -> ExternalWorkshopAssignmentResponseDTO:
        assignment = self._repo.get_assignment_by_id(dto.assignment_id)
        assignment.ensure_active()
        if self._repo.get_pickup_by_assignment(assignment.id) is None:
            raise FMMSConflictError(
                message="External repair review cannot be saved before pickup.",
                error_code="EXTERNAL_REVIEW_REQUIRES_PICKUP",
                details={"assignment_id": str(assignment.id)},
            )
        order = _load_order(self._repair_repo, assignment.repair_order_id)
        if order.status != RepairOrderStatus.WAITING_EXTERNAL_ADMIN_REVIEW:
            raise FMMSConflictError(
                message="External repair review is only allowed after pickup.",
                error_code="EXTERNAL_REVIEW_INVALID_REPAIR_STATE",
                details={"repair_order_id": str(order.id), "status": order.status.value},
            )
        now = datetime.now(tz=UTC)
        existing = self._repo.get_review_by_assignment(assignment.id)
        review = ExternalRepairReview(
            id=existing.id if existing else uuid.uuid4(),
            assignment_id=assignment.id,
            repair_order_id=order.id,
            invoice_attachment=(dto.invoice_attachment or "").strip() or None,
            repair_services=dto.repair_services,
            replaced_parts=dto.replaced_parts,
            repair_cost=dto.repair_cost,
            additional_notes=dto.additional_notes.strip(),
            sap_purchase_order_number=(
                existing.sap_purchase_order_number if existing else None
            ),
            sap_invoice_document_number=(
                existing.sap_invoice_document_number if existing else None
            ),
            status=ExternalRepairReviewStatus.DRAFT,
            reviewed_by_id=dto.reviewed_by,
            created_at=existing.created_at if existing else now,
            updated_at=now,
        )
        self._repo.save_review(review)
        record_repair_timeline_event(
            self._event_recorder,
            order.id,
            RepairOrderEventType.EXTERNAL_ADMIN_REVIEW_SAVED,
            "اطلاعات فاکتور تعمیرگاه بیرونی ذخیره شد.",
            created_by_id=dto.reviewed_by,
            request_id=dto.request_id,
        )
        return _assignment_to_dto(self._repo, assignment)


class CloseExternalRepairService:
    """Close external repair after mandatory administrative review is complete."""

    def __init__(
        self,
        external_workshop_repository: IExternalWorkshopRepository,
        repair_order_repository: IRepairOrderRepository,
        fault_repository: IFaultRepository,
        component_history_service: RecordComponentHistoryFromRepairService | None = None,
        event_recorder: RecordRepairOrderEventService | None = None,
    ) -> None:
        self._repo = external_workshop_repository
        self._repair_repo = repair_order_repository
        self._fault_repo = fault_repository
        self._component_history = component_history_service
        self._event_recorder = event_recorder

    @transaction.atomic
    def execute(self, dto: CloseExternalRepairDTO) -> ExternalWorkshopAssignmentResponseDTO:
        assignment = self._repo.get_assignment_by_id(dto.assignment_id)
        assignment.ensure_active()
        review = self._repo.get_review_by_assignment(assignment.id)
        _assert_review_complete(review, assignment.id)
        assert review is not None
        order = _load_order(self._repair_repo, assignment.repair_order_id)
        if order.status != RepairOrderStatus.WAITING_EXTERNAL_ADMIN_REVIEW:
            raise FMMSConflictError(
                message="External repair can only be closed from admin review state.",
                error_code="EXTERNAL_CLOSE_INVALID_REPAIR_STATE",
                details={"repair_order_id": str(order.id), "status": order.status.value},
            )
        now = datetime.now(tz=UTC)
        _merge_review_parts_into_order(order, review)
        order.close_external_repair(completed_at=now)
        order.updated_at = now
        saved_order = self._repair_repo.save(order)
        review.mark_completed()
        review.updated_at = now
        self._repo.save_review(review)
        assignment.complete(now)
        self._repo.save_assignment(assignment)
        if self._component_history is not None:
            self._component_history.execute(
                order=saved_order,
                recorded_by=dto.closed_by,
                request_id=dto.request_id,
            )
        _close_fault(saved_order.fault_id, self._fault_repo)
        record_repair_timeline_event(
            self._event_recorder,
            order.id,
            RepairOrderEventType.EXTERNAL_REPAIR_CLOSED,
            "فرایند تعمیر بیرونی تکمیل شد.",
            created_by_id=dto.closed_by,
            request_id=dto.request_id,
        )
        return _assignment_to_dto(self._repo, assignment)


class CancelExternalWorkshopAssignmentService:
    """Cancel an external assignment with a business reason."""

    def __init__(
        self,
        external_workshop_repository: IExternalWorkshopRepository,
        repair_order_repository: IRepairOrderRepository,
        event_recorder: RecordRepairOrderEventService | None = None,
    ) -> None:
        self._repo = external_workshop_repository
        self._repair_repo = repair_order_repository
        self._event_recorder = event_recorder

    @transaction.atomic
    def execute(
        self, dto: CancelExternalWorkshopAssignmentDTO
    ) -> ExternalWorkshopAssignmentResponseDTO:
        assignment = self._repo.get_assignment_by_id(dto.assignment_id)
        assignment.ensure_active()
        if self._repo.get_delivery_by_assignment(assignment.id) is not None:
            raise FMMSConflictError(
                message="External assignment cannot be cancelled after delivery.",
                error_code="EXTERNAL_ASSIGNMENT_CANCEL_AFTER_DELIVERY",
                details={"assignment_id": str(assignment.id)},
            )
        now = datetime.now(tz=UTC)
        assignment.cancel(
            reason=dto.reason,
            note=dto.note,
            cancelled_by_id=dto.cancelled_by,
            cancelled_at=now,
        )
        self._repo.save_assignment(assignment)
        order = _load_order(self._repair_repo, assignment.repair_order_id)
        order.cancel()
        order.updated_at = now
        self._repair_repo.save(order)
        record_repair_timeline_event(
            self._event_recorder,
            order.id,
            RepairOrderEventType.EXTERNAL_WORKSHOP_ASSIGNMENT_CANCELLED,
            f"ارجاع به تعمیرگاه بیرونی لغو شد. دلیل: {dto.reason.value}.",
            created_by_id=dto.cancelled_by,
            request_id=dto.request_id,
        )
        return _assignment_to_dto(self._repo, assignment)


class GetExternalWorkshopAssignmentService:
    """Read one external workshop assignment with delivery/pickup/review."""

    def __init__(self, external_workshop_repository: IExternalWorkshopRepository) -> None:
        self._repo = external_workshop_repository

    def execute(self, assignment_id: uuid.UUID) -> ExternalWorkshopAssignmentResponseDTO:
        return _assignment_to_dto(self._repo, self._repo.get_assignment_by_id(assignment_id))


class ListExternalWorkshopAssignmentsService:
    """List external workshop assignments for driver/transport queues."""

    def __init__(self, external_workshop_repository: IExternalWorkshopRepository) -> None:
        self._repo = external_workshop_repository

    def execute(
        self, status: ExternalWorkshopAssignmentStatus | None = None
    ) -> list[ExternalWorkshopAssignmentResponseDTO]:
        return [
            _assignment_to_dto(self._repo, assignment)
            for assignment in self._repo.list_assignments(status)
        ]


def _same_assignment(
    assignment: ExternalWorkshopAssignment, dto: AssignExternalWorkshopDTO
) -> bool:
    return (
        assignment.workshop_id == dto.workshop_id
        and assignment.workshop_name == dto.workshop_name.strip()
        and assignment.workshop_address == dto.workshop_address.strip()
        and assignment.repair_reason == dto.repair_reason.strip()
        and assignment.description == dto.description.strip()
    )


def _load_order(repo: IRepairOrderRepository, order_id: uuid.UUID) -> RepairOrder:
    return load_or_not_found(
        lambda: repo.get_by_id(order_id),
        message=f"Repair order '{order_id}' not found.",
        details={"repair_order_id": str(order_id)},
    )


def _load_vehicle(repo: IVehicleRepository, vehicle_id: uuid.UUID):
    return load_or_not_found(
        lambda: repo.get_by_id(vehicle_id),
        message=f"Vehicle '{vehicle_id}' not found.",
        details={"vehicle_id": str(vehicle_id)},
    )


def _assert_review_complete(
    review: ExternalRepairReview | None, assignment_id: uuid.UUID
) -> None:
    missing: list[str] = []
    if review is None:
        missing = [
            "repair_services",
            "repair_cost",
        ]
    else:
        if not review.repair_services:
            missing.append("repair_services")
        if review.repair_cost is None or Decimal(str(review.repair_cost)) <= 0:
            missing.append("repair_cost")
    if missing:
        raise FMMSValidationError(
            message="External repair review is incomplete.",
            error_code="EXTERNAL_REVIEW_REQUIRED_FIELDS_MISSING",
            details={"assignment_id": str(assignment_id), "missing": missing},
        )


def _merge_review_parts_into_order(order: RepairOrder, review: ExternalRepairReview) -> None:
    existing_materials = {part.part_quantity.material_number for part in order.parts}
    for item in review.replaced_parts:
        material_number = str(item.get("material_number") or item.get("name") or "").strip()
        if not material_number or material_number in existing_materials:
            continue
        quantity_raw = item.get("quantity") or 1
        try:
            quantity = int(quantity_raw)
        except (TypeError, ValueError):
            quantity = 1
        order.parts.append(
            RepairPart(
                id=uuid.uuid4(),
                part_quantity=PartQuantity(
                    material_number=material_number,
                    quantity=max(quantity, 1),
                    unit_of_measure=str(item.get("unit_of_measure") or "-"),
                ),
                goods_issue_id=None,
                posted_at=datetime.now(tz=UTC),
            )
        )
        existing_materials.add(material_number)


def _close_fault(fault_id: uuid.UUID, fault_repository: IFaultRepository) -> None:
    try:
        fault = fault_repository.get_by_id(fault_id)
    except FaultNotFoundError:
        return
    if fault.status == FaultStatus.CLOSED:
        return
    if fault.status in {FaultStatus.ASSIGNED, FaultStatus.AWAITING_TRANSPORT}:
        fault.start_repair()
    fault.close()
    fault.updated_at = datetime.now(tz=UTC)
    fault_repository.save(fault)
