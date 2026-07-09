"""Unit tests for overdue PM trigger Celery task and application sweep service."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from apps.preventive_maintenance.application.dto.pm_dto import PMWorkOrderResponseDTO
from apps.preventive_maintenance.application.services.trigger_overdue_pm_work_orders_service import (
    TriggerOverduePMWorkOrdersService,
)
from apps.preventive_maintenance.domain.entities import (
    PMPlan,
    PMPlanStatus,
    PMWorkOrderStatus,
)
from apps.preventive_maintenance.domain.value_objects import (
    IntervalUnit,
    MaintenanceInterval,
    TriggerCondition,
    TriggerType,
)
from infrastructure.messaging.tasks.maintenance_tasks import (
    trigger_overdue_pm_work_orders,
)


def _make_plan(*, next_due_at: datetime | None) -> PMPlan:
    now = datetime.now(tz=UTC)
    return PMPlan(
        id=uuid.uuid4(),
        vehicle_id=uuid.uuid4(),
        name="Oil change",
        description="Periodic oil",
        interval=MaintenanceInterval(value=30, unit=IntervalUnit.DAYS),
        trigger_condition=TriggerCondition(
            trigger_type=TriggerType.TIME_BASED, threshold=30
        ),
        status=PMPlanStatus.ACTIVE,
        created_by_id=uuid.uuid4(),
        created_at=now,
        updated_at=now,
        next_due_at=next_due_at,
    )


@pytest.mark.unit
def test_trigger_overdue_pm_work_orders_task_calls_service() -> None:
    """Task resolves deps and calls the overdue PM application service."""
    service = MagicMock()
    service.execute.return_value = []
    with patch(
        "interfaces.api.v1.deps.get_trigger_overdue_pm_work_orders_service",
        return_value=service,
    ):
        result = trigger_overdue_pm_work_orders.run(correlation_id="corr-pm-1")

    service.execute.assert_called_once_with(
        request_id="corr-pm-1",
        create_sap_notification=False,
    )
    assert result["status"] == "ok"
    assert result["count"] == 0


@pytest.mark.unit
def test_overdue_service_triggers_only_due_plans() -> None:
    """Sweep service triggers plans with next_due_at in the past only."""
    overdue = _make_plan(next_due_at=datetime.now(tz=UTC) - timedelta(days=1))
    future = _make_plan(next_due_at=datetime.now(tz=UTC) + timedelta(days=7))
    undated = _make_plan(next_due_at=None)

    plan_repo = MagicMock()
    plan_repo.list_active.return_value = [overdue, future, undated]
    trigger = MagicMock()
    trigger.execute.return_value = PMWorkOrderResponseDTO(
        id=uuid.uuid4(),
        plan_id=overdue.id,
        vehicle_id=overdue.vehicle_id,
        status=PMWorkOrderStatus.TRIGGERED,
        scheduled_date=overdue.next_due_at or datetime.now(tz=UTC),
        created_at=datetime.now(tz=UTC),
        updated_at=datetime.now(tz=UTC),
    )

    results = TriggerOverduePMWorkOrdersService(plan_repo, trigger).execute(
        request_id="corr-sweep"
    )

    assert len(results) == 1
    assert trigger.execute.call_count == 1
    assert trigger.execute.call_args.args[0].plan_id == overdue.id
