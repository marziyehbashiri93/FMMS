"""Concrete Django ORM implementations of IPMPlanRepository and IPMWorkOrderRepository."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from apps.preventive_maintenance.domain.entities import (
    PMPlan,
    PMPlanStatus,
    PMWorkOrder,
    PMWorkOrderStatus,
)
from apps.preventive_maintenance.domain.exceptions import (
    PMPlanNotFoundError,
    PMWorkOrderNotFoundError,
)
from apps.preventive_maintenance.domain.interfaces.pm_repository import (
    IPMPlanRepository,
    IPMWorkOrderRepository,
)
from apps.preventive_maintenance.domain.value_objects import (
    IntervalUnit,
    MaintenanceInterval,
    TriggerCondition,
    TriggerType,
)
from apps.preventive_maintenance.infrastructure.models import (
    PMPlanModel,
    PMWorkOrderModel,
)
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger(domain="preventive_maintenance", module=__name__)


def _plan_to_domain(orm: PMPlanModel) -> PMPlan:
    """Map PMPlanModel to PMPlan domain aggregate."""
    return PMPlan(
        id=uuid.UUID(str(orm.id)),
        vehicle_id=orm.vehicle_id,
        name=orm.name,
        description=orm.description,
        interval=MaintenanceInterval(
            value=orm.interval_value,
            unit=IntervalUnit(orm.interval_unit),
        ),
        trigger_condition=TriggerCondition(
            trigger_type=TriggerType(orm.trigger_type),
            threshold=orm.trigger_threshold,
        ),
        status=PMPlanStatus(orm.status),
        created_by_id=orm.initiator_id,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
        last_triggered_at=orm.last_triggered_at,
        next_due_at=orm.next_due_at,
    )


def _wo_to_domain(orm: PMWorkOrderModel) -> PMWorkOrder:
    """Map PMWorkOrderModel to PMWorkOrder domain aggregate."""
    return PMWorkOrder(
        id=uuid.UUID(str(orm.id)),
        plan_id=orm.plan_id,
        vehicle_id=orm.vehicle_id,
        status=PMWorkOrderStatus(orm.status),
        scheduled_date=orm.scheduled_date,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
        triggered_at=orm.triggered_at,
        completed_at=orm.completed_at,
        notes=orm.notes or None,
        sap_order_number=orm.sap_order_number or None,
    )


class DjangoPMPlanRepository(IPMPlanRepository):
    """Concrete repository for PMPlan aggregates backed by Django ORM."""

    def get_by_id(self, plan_id: uuid.UUID) -> PMPlan:
        """Retrieve a PM plan by UUID."""
        try:
            orm = PMPlanModel.objects.get(id=plan_id, is_deleted=False)
        except PMPlanModel.DoesNotExist:
            raise PMPlanNotFoundError(plan_id) from None
        return _plan_to_domain(orm)

    def list_by_vehicle(
        self,
        vehicle_id: uuid.UUID,
        status: PMPlanStatus | None = None,
    ) -> list[PMPlan]:
        """Return PM plans for a vehicle, optionally filtered by status."""
        qs = PMPlanModel.objects.filter(vehicle_id=vehicle_id, is_deleted=False)
        if status is not None:
            qs = qs.filter(status=status.value)
        return [_plan_to_domain(orm) for orm in qs]

    def list_active(self) -> list[PMPlan]:
        """Return all ACTIVE PM plans."""
        qs = PMPlanModel.objects.filter(
            status=PMPlanStatus.ACTIVE.value, is_deleted=False
        )
        return [_plan_to_domain(orm) for orm in qs]

    def save(self, plan: PMPlan) -> PMPlan:
        """Persist a new or updated PM plan."""
        obj, created = PMPlanModel.objects.update_or_create(
            id=plan.id,
            defaults={
                "vehicle_id": plan.vehicle_id,
                "name": plan.name,
                "description": plan.description,
                "status": plan.status.value,
                "interval_value": plan.interval.value,
                "interval_unit": plan.interval.unit.value,
                "trigger_type": plan.trigger_condition.trigger_type.value,
                "trigger_threshold": plan.trigger_condition.threshold,
                "initiator_id": plan.created_by_id,
                "last_triggered_at": plan.last_triggered_at,
                "next_due_at": plan.next_due_at,
                "updated_at": datetime.now(tz=UTC),
            },
        )
        if created:
            obj.created_at = plan.created_at
            obj.save(update_fields=["created_at"])
        logger.debug("plan saved", extra={"plan_id": str(plan.id), "is_new": created})
        return plan

    def delete(self, plan_id: uuid.UUID) -> None:
        """Soft-delete a PM plan record."""
        updated = PMPlanModel.objects.filter(id=plan_id, is_deleted=False).update(
            is_deleted=True,
            deleted_at=datetime.now(tz=UTC),
        )
        if updated == 0:
            raise PMPlanNotFoundError(plan_id)


class DjangoPMWorkOrderRepository(IPMWorkOrderRepository):
    """Concrete repository for PMWorkOrder aggregates backed by Django ORM."""

    def get_by_id(self, work_order_id: uuid.UUID) -> PMWorkOrder:
        """Retrieve a PM work order by UUID."""
        try:
            orm = PMWorkOrderModel.objects.get(id=work_order_id, is_deleted=False)
        except PMWorkOrderModel.DoesNotExist:
            raise PMWorkOrderNotFoundError(work_order_id) from None
        return _wo_to_domain(orm)

    def list_by_plan(
        self,
        plan_id: uuid.UUID,
        status: PMWorkOrderStatus | None = None,
    ) -> list[PMWorkOrder]:
        """Return work orders for a plan, optionally filtered by status."""
        qs = PMWorkOrderModel.objects.filter(plan_id=plan_id, is_deleted=False)
        if status is not None:
            qs = qs.filter(status=status.value)
        return [_wo_to_domain(orm) for orm in qs]

    def list_overdue(self) -> list[PMWorkOrder]:
        """Return all OVERDUE work orders."""
        qs = PMWorkOrderModel.objects.filter(
            status=PMWorkOrderStatus.OVERDUE.value, is_deleted=False
        )
        return [_wo_to_domain(orm) for orm in qs]

    def save(self, work_order: PMWorkOrder) -> PMWorkOrder:
        """Persist a new or updated PM work order."""
        obj, created = PMWorkOrderModel.objects.update_or_create(
            id=work_order.id,
            defaults={
                "plan_id": work_order.plan_id,
                "vehicle_id": work_order.vehicle_id,
                "status": work_order.status.value,
                "scheduled_date": work_order.scheduled_date,
                "triggered_at": work_order.triggered_at,
                "completed_at": work_order.completed_at,
                "notes": work_order.notes or "",
                "sap_order_number": work_order.sap_order_number or "",
                "updated_at": datetime.now(tz=UTC),
            },
        )
        if created:
            obj.created_at = work_order.created_at
            obj.save(update_fields=["created_at"])
        logger.debug(
            "work_order saved", extra={"wo_id": str(work_order.id), "is_new": created}
        )
        return work_order
