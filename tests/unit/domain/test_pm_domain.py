"""Unit tests for the Preventive Maintenance domain layer."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from apps.preventive_maintenance.domain.entities import (
    PMPlan,
    PMPlanStatus,
    PMWorkOrder,
    PMWorkOrderStatus,
)
from apps.preventive_maintenance.domain.exceptions import (
    PMInvalidStateTransitionError,
    PMPlanNotFoundError,
    PMWorkOrderNotFoundError,
)
from apps.preventive_maintenance.domain.value_objects import (
    IntervalUnit,
    MaintenanceInterval,
    OdometerThreshold,
    TriggerCondition,
    TriggerType,
)


def _make_plan(**kwargs: object) -> PMPlan:
    defaults: dict[str, object] = {
        "id": uuid.uuid4(),
        "vehicle_id": uuid.uuid4(),
        "name": "Engine Oil Service",
        "description": "Change engine oil and filter every 10,000 km.",
        "interval": MaintenanceInterval(value=10000, unit=IntervalUnit.KM),
        "trigger_condition": TriggerCondition(
            trigger_type=TriggerType.MILEAGE_BASED, threshold=10000
        ),
        "status": PMPlanStatus.ACTIVE,
        "created_by_id": uuid.uuid4(),
        "created_at": datetime.now(tz=UTC),
        "updated_at": datetime.now(tz=UTC),
    }
    defaults.update(kwargs)
    return PMPlan(**defaults)  # type: ignore[arg-type]


def _make_work_order(**kwargs: object) -> PMWorkOrder:
    defaults: dict[str, object] = {
        "id": uuid.uuid4(),
        "plan_id": uuid.uuid4(),
        "vehicle_id": uuid.uuid4(),
        "status": PMWorkOrderStatus.SCHEDULED,
        "scheduled_date": datetime.now(tz=UTC),
        "created_at": datetime.now(tz=UTC),
        "updated_at": datetime.now(tz=UTC),
    }
    defaults.update(kwargs)
    return PMWorkOrder(**defaults)  # type: ignore[arg-type]


class TestMaintenanceInterval:
    def test_valid(self) -> None:
        mi = MaintenanceInterval(value=10000, unit=IntervalUnit.KM)
        assert mi.value == 10000

    def test_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            MaintenanceInterval(value=0, unit=IntervalUnit.DAYS)

    def test_str(self) -> None:
        assert str(MaintenanceInterval(5000, IntervalUnit.KM)) == "Every 5000 KM"


class TestOdometerThreshold:
    def test_valid(self) -> None:
        ot = OdometerThreshold(km=50000)
        assert ot.km == 50000

    def test_negative_raises(self) -> None:
        with pytest.raises(ValueError, match="non-negative"):
            OdometerThreshold(km=-1)


class TestPMWorkOrderLifecycle:
    def test_initial_state(self) -> None:
        wo = _make_work_order()
        assert wo.status == PMWorkOrderStatus.SCHEDULED
        assert wo.is_terminal is False

    def test_trigger(self) -> None:
        wo = _make_work_order()
        now = datetime.now(tz=UTC)
        wo.trigger(triggered_at=now)
        assert wo.status == PMWorkOrderStatus.TRIGGERED
        assert wo.triggered_at == now

    def test_start(self) -> None:
        wo = _make_work_order(status=PMWorkOrderStatus.TRIGGERED)
        wo.start()
        assert wo.status == PMWorkOrderStatus.IN_PROGRESS

    def test_complete(self) -> None:
        wo = _make_work_order(status=PMWorkOrderStatus.IN_PROGRESS)
        now = datetime.now(tz=UTC)
        wo.complete(completed_at=now)
        assert wo.status == PMWorkOrderStatus.COMPLETED
        assert wo.is_terminal is True

    def test_cancel(self) -> None:
        wo = _make_work_order()
        wo.cancel()
        assert wo.status == PMWorkOrderStatus.CANCELLED

    def test_mark_overdue(self) -> None:
        wo = _make_work_order()
        wo.mark_overdue()
        assert wo.status == PMWorkOrderStatus.OVERDUE

    def test_overdue_can_start(self) -> None:
        wo = _make_work_order(status=PMWorkOrderStatus.OVERDUE)
        wo.start()
        assert wo.status == PMWorkOrderStatus.IN_PROGRESS

    def test_invalid_transition(self) -> None:
        wo = _make_work_order(status=PMWorkOrderStatus.COMPLETED)
        with pytest.raises(PMInvalidStateTransitionError):
            wo.trigger(triggered_at=datetime.now(tz=UTC))


class TestPMPlanOperations:
    def test_initial_active(self) -> None:
        plan = _make_plan()
        assert plan.is_active is True

    def test_suspend(self) -> None:
        plan = _make_plan()
        plan.suspend()
        assert plan.status == PMPlanStatus.SUSPENDED
        assert plan.is_active is False

    def test_deactivate(self) -> None:
        plan = _make_plan()
        plan.deactivate()
        assert plan.status == PMPlanStatus.INACTIVE

    def test_record_trigger(self) -> None:
        plan = _make_plan()
        now = datetime.now(tz=UTC)
        plan.record_trigger(triggered_at=now)
        assert plan.last_triggered_at == now


class TestPMExceptions:
    def test_plan_not_found(self) -> None:
        err = PMPlanNotFoundError("plan-id")
        assert "plan-id" in str(err)

    def test_work_order_not_found(self) -> None:
        err = PMWorkOrderNotFoundError("wo-id")
        assert "wo-id" in str(err)
