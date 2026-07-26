"""ORM repository for external workshop workflow records."""

from __future__ import annotations

import uuid

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
from apps.repair.infrastructure.models import (
    ExternalRepairReviewModel,
    ExternalWorkshopAssignmentModel,
    ExternalWorkshopDeliveryModel,
    ExternalWorkshopPickupModel,
)
from core.exceptions.base_exception import FMMSNotFoundError


def _assignment_to_domain(
    orm: ExternalWorkshopAssignmentModel,
) -> ExternalWorkshopAssignment:
    return ExternalWorkshopAssignment(
        id=uuid.UUID(str(orm.id)),
        repair_order_id=orm.repair_order_id,
        vehicle_id=orm.vehicle_id,
        fault_id=orm.fault_id,
        workshop_id=orm.workshop_id or None,
        workshop_name=orm.workshop_name,
        workshop_address=orm.workshop_address,
        assignment_date=orm.assignment_date,
        repair_reason=orm.repair_reason,
        description=orm.description,
        status=ExternalWorkshopAssignmentStatus(orm.status),
        assigned_by_id=orm.assigned_by_id,
        cancellation_reason=(
            ExternalWorkshopAssignmentCancellationReason(orm.cancellation_reason)
            if orm.cancellation_reason
            else None
        ),
        cancellation_note=orm.cancellation_note or None,
        cancelled_by_id=orm.cancelled_by_id,
        cancelled_at=orm.cancelled_at,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


def _delivery_to_domain(
    orm: ExternalWorkshopDeliveryModel,
) -> ExternalWorkshopDelivery:
    return ExternalWorkshopDelivery(
        id=uuid.UUID(str(orm.id)),
        assignment_id=uuid.UUID(str(orm.assignment_id)),
        repair_order_id=orm.repair_order_id,
        vehicle_id=orm.vehicle_id,
        delivery_datetime=orm.delivery_datetime,
        workshop_name=orm.workshop_name,
        workshop_address=orm.workshop_address,
        workshop_phone=orm.workshop_phone,
        vehicle_odometer=orm.vehicle_odometer,
        notes=orm.notes,
        delivered_by_id=orm.delivered_by_id,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


def _pickup_to_domain(orm: ExternalWorkshopPickupModel) -> ExternalWorkshopPickup:
    return ExternalWorkshopPickup(
        id=uuid.UUID(str(orm.id)),
        assignment_id=uuid.UUID(str(orm.assignment_id)),
        repair_order_id=orm.repair_order_id,
        vehicle_id=orm.vehicle_id,
        pickup_datetime=orm.pickup_datetime,
        vehicle_odometer=orm.vehicle_odometer,
        notes=orm.notes,
        picked_up_by_id=orm.picked_up_by_id,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


def _review_to_domain(orm: ExternalRepairReviewModel) -> ExternalRepairReview:
    return ExternalRepairReview(
        id=uuid.UUID(str(orm.id)),
        assignment_id=uuid.UUID(str(orm.assignment_id)),
        repair_order_id=orm.repair_order_id,
        invoice_attachment=orm.invoice_attachment or None,
        repair_services=list(orm.repair_services or []),
        replaced_parts=list(orm.replaced_parts or []),
        repair_cost=orm.repair_cost,
        additional_notes=orm.additional_notes,
        sap_purchase_order_number=orm.sap_purchase_order_number or None,
        sap_invoice_document_number=orm.sap_invoice_document_number or None,
        status=ExternalRepairReviewStatus(orm.status),
        reviewed_by_id=orm.reviewed_by_id,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


class DjangoExternalWorkshopRepository(IExternalWorkshopRepository):
    """Django-backed repository for external workshop workflow."""

    def get_assignment_by_id(
        self, assignment_id: uuid.UUID
    ) -> ExternalWorkshopAssignment:
        try:
            orm = ExternalWorkshopAssignmentModel.objects.get(
                id=assignment_id, is_deleted=False
            )
        except ExternalWorkshopAssignmentModel.DoesNotExist:
            raise FMMSNotFoundError(
                message=f"External workshop assignment '{assignment_id}' not found.",
                error_code="EXTERNAL_ASSIGNMENT_NOT_FOUND",
                details={"assignment_id": str(assignment_id)},
            ) from None
        return _assignment_to_domain(orm)

    def get_active_assignment_by_repair_order(
        self, repair_order_id: uuid.UUID
    ) -> ExternalWorkshopAssignment | None:
        orm = (
            ExternalWorkshopAssignmentModel.objects.filter(
                repair_order_id=repair_order_id,
                status=ExternalWorkshopAssignmentStatus.ACTIVE.value,
                is_deleted=False,
            )
            .order_by("-created_at")
            .first()
        )
        return _assignment_to_domain(orm) if orm else None

    def list_assignments(
        self, status: ExternalWorkshopAssignmentStatus | None = None
    ) -> list[ExternalWorkshopAssignment]:
        qs = ExternalWorkshopAssignmentModel.objects.filter(is_deleted=False).order_by(
            "-created_at"
        )
        if status is not None:
            qs = qs.filter(status=status.value)
        return [_assignment_to_domain(row) for row in qs]

    def save_assignment(
        self, assignment: ExternalWorkshopAssignment
    ) -> ExternalWorkshopAssignment:
        obj, created = ExternalWorkshopAssignmentModel.objects.update_or_create(
            id=assignment.id,
            defaults={
                "repair_order_id": assignment.repair_order_id,
                "vehicle_id": assignment.vehicle_id,
                "fault_id": assignment.fault_id,
                "workshop_id": assignment.workshop_id or "",
                "workshop_name": assignment.workshop_name,
                "workshop_address": assignment.workshop_address,
                "assignment_date": assignment.assignment_date,
                "repair_reason": assignment.repair_reason,
                "description": assignment.description,
                "status": assignment.status.value,
                "assigned_by_id": assignment.assigned_by_id,
                "cancellation_reason": (
                    assignment.cancellation_reason.value
                    if assignment.cancellation_reason
                    else ""
                ),
                "cancellation_note": assignment.cancellation_note or "",
                "cancelled_by_id": assignment.cancelled_by_id,
                "cancelled_at": assignment.cancelled_at,
            },
        )
        if created:
            obj.created_at = assignment.created_at
            obj.save(update_fields=["created_at"])
        return assignment

    def get_delivery_by_assignment(
        self, assignment_id: uuid.UUID
    ) -> ExternalWorkshopDelivery | None:
        orm = ExternalWorkshopDeliveryModel.objects.filter(
            assignment_id=assignment_id, is_deleted=False
        ).first()
        return _delivery_to_domain(orm) if orm else None

    def save_delivery(
        self, delivery: ExternalWorkshopDelivery
    ) -> ExternalWorkshopDelivery:
        obj, created = ExternalWorkshopDeliveryModel.objects.update_or_create(
            id=delivery.id,
            defaults={
                "assignment_id": delivery.assignment_id,
                "repair_order_id": delivery.repair_order_id,
                "vehicle_id": delivery.vehicle_id,
                "delivery_datetime": delivery.delivery_datetime,
                "workshop_name": delivery.workshop_name,
                "workshop_address": delivery.workshop_address,
                "workshop_phone": delivery.workshop_phone,
                "vehicle_odometer": delivery.vehicle_odometer,
                "notes": delivery.notes,
                "delivered_by_id": delivery.delivered_by_id,
            },
        )
        if created:
            obj.created_at = delivery.created_at
            obj.save(update_fields=["created_at"])
        return delivery

    def get_pickup_by_assignment(
        self, assignment_id: uuid.UUID
    ) -> ExternalWorkshopPickup | None:
        orm = ExternalWorkshopPickupModel.objects.filter(
            assignment_id=assignment_id, is_deleted=False
        ).first()
        return _pickup_to_domain(orm) if orm else None

    def save_pickup(self, pickup: ExternalWorkshopPickup) -> ExternalWorkshopPickup:
        obj, created = ExternalWorkshopPickupModel.objects.update_or_create(
            id=pickup.id,
            defaults={
                "assignment_id": pickup.assignment_id,
                "repair_order_id": pickup.repair_order_id,
                "vehicle_id": pickup.vehicle_id,
                "pickup_datetime": pickup.pickup_datetime,
                "vehicle_odometer": pickup.vehicle_odometer,
                "notes": pickup.notes,
                "picked_up_by_id": pickup.picked_up_by_id,
            },
        )
        if created:
            obj.created_at = pickup.created_at
            obj.save(update_fields=["created_at"])
        return pickup

    def get_review_by_assignment(
        self, assignment_id: uuid.UUID
    ) -> ExternalRepairReview | None:
        orm = ExternalRepairReviewModel.objects.filter(
            assignment_id=assignment_id, is_deleted=False
        ).first()
        return _review_to_domain(orm) if orm else None

    def save_review(self, review: ExternalRepairReview) -> ExternalRepairReview:
        obj, created = ExternalRepairReviewModel.objects.update_or_create(
            id=review.id,
            defaults={
                "assignment_id": review.assignment_id,
                "repair_order_id": review.repair_order_id,
                "invoice_attachment": review.invoice_attachment or "",
                "repair_services": review.repair_services,
                "replaced_parts": review.replaced_parts,
                "repair_cost": review.repair_cost,
                "additional_notes": review.additional_notes,
                "sap_purchase_order_number": review.sap_purchase_order_number or "",
                "sap_invoice_document_number": review.sap_invoice_document_number or "",
                "status": review.status.value,
                "reviewed_by_id": review.reviewed_by_id,
            },
        )
        if created:
            obj.created_at = review.created_at
            obj.save(update_fields=["created_at"])
        return review
