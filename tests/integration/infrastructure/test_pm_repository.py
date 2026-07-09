"""Integration tests for DjangoPMPlanRepository and DjangoPMWorkOrderRepository."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

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
from apps.preventive_maintenance.infrastructure.repositories import (
    DjangoPMPlanRepository,
    DjangoPMWorkOrderRepository,
)

pytestmark = pytest.mark.django_db


def _make_plan(
    vehicle_id: uuid.UUID | None = None,
    status: PMPlanStatus = PMPlanStatus.ACTIVE,
) -> PMPlan:
    now = datetime.now(tz=UTC)
    repo = DjangoPMPlanRepository()
    plan = PMPlan(
        id=uuid.uuid4(),
        vehicle_id=vehicle_id or uuid.uuid4(),
        name="Oil Change Plan",
        description="Change engine oil every 10,000 km",
        interval=MaintenanceInterval(value=10000, unit=IntervalUnit.KM),
        trigger_condition=TriggerCondition(
            trigger_type=TriggerType.MILEAGE_BASED, threshold=10000
        ),
        status=status,
        created_by_id=uuid.uuid4(),
        created_at=now,
        updated_at=now,
    )
    return repo.save(plan)


def _make_work_order(
    plan_id: uuid.UUID | None = None,
    vehicle_id: uuid.UUID | None = None,
    status: PMWorkOrderStatus = PMWorkOrderStatus.SCHEDULED,
) -> PMWorkOrder:
    now = datetime.now(tz=UTC)
    repo = DjangoPMWorkOrderRepository()
    wo = PMWorkOrder(
        id=uuid.uuid4(),
        plan_id=plan_id or uuid.uuid4(),
        vehicle_id=vehicle_id or uuid.uuid4(),
        status=status,
        scheduled_date=now + timedelta(days=30),
        created_at=now,
        updated_at=now,
    )
    return repo.save(wo)


class TestPMPlanInterface:
    def test_satisfies_interface(self) -> None:
        assert isinstance(DjangoPMPlanRepository(), IPMPlanRepository)


class TestPMPlan:
    def test_save_and_get(self) -> None:
        repo = DjangoPMPlanRepository()
        plan = _make_plan()
        fetched = repo.get_by_id(plan.id)
        assert fetched.name == "Oil Change Plan"
        assert fetched.interval.value == 10000
        assert fetched.interval.unit == IntervalUnit.KM
        assert fetched.status == PMPlanStatus.ACTIVE

    def test_get_not_found(self) -> None:
        repo = DjangoPMPlanRepository()
        with pytest.raises(PMPlanNotFoundError):
            repo.get_by_id(uuid.uuid4())

    def test_status_update(self) -> None:
        repo = DjangoPMPlanRepository()
        plan = _make_plan()
        plan.suspend()
        repo.save(plan)
        fetched = repo.get_by_id(plan.id)
        assert fetched.status == PMPlanStatus.SUSPENDED

    def test_list_by_vehicle(self) -> None:
        repo = DjangoPMPlanRepository()
        vid = uuid.uuid4()
        _make_plan(vehicle_id=vid)
        _make_plan(vehicle_id=vid)
        _make_plan()
        result = repo.list_by_vehicle(vid)
        assert len(result) == 2

    def test_list_active(self) -> None:
        repo = DjangoPMPlanRepository()
        _make_plan(status=PMPlanStatus.ACTIVE)
        _make_plan(status=PMPlanStatus.SUSPENDED)
        active = repo.list_active()
        assert all(p.status == PMPlanStatus.ACTIVE for p in active)

    def test_delete_hides_plan(self) -> None:
        repo = DjangoPMPlanRepository()
        plan = _make_plan()
        repo.delete(plan.id)
        with pytest.raises(PMPlanNotFoundError):
            repo.get_by_id(plan.id)

    def test_delete_nonexistent_raises(self) -> None:
        repo = DjangoPMPlanRepository()
        with pytest.raises(PMPlanNotFoundError):
            repo.delete(uuid.uuid4())


class TestPMWorkOrderInterface:
    def test_satisfies_interface(self) -> None:
        assert isinstance(DjangoPMWorkOrderRepository(), IPMWorkOrderRepository)


class TestPMWorkOrder:
    def test_save_and_get(self) -> None:
        repo = DjangoPMWorkOrderRepository()
        wo = _make_work_order()
        fetched = repo.get_by_id(wo.id)
        assert fetched.id == wo.id
        assert fetched.status == PMWorkOrderStatus.SCHEDULED

    def test_get_not_found(self) -> None:
        repo = DjangoPMWorkOrderRepository()
        with pytest.raises(PMWorkOrderNotFoundError):
            repo.get_by_id(uuid.uuid4())

    def test_list_by_plan(self) -> None:
        repo = DjangoPMWorkOrderRepository()
        pid = uuid.uuid4()
        _make_work_order(plan_id=pid)
        _make_work_order(plan_id=pid)
        _make_work_order()
        result = repo.list_by_plan(pid)
        assert len(result) == 2

    def test_list_overdue(self) -> None:
        repo = DjangoPMWorkOrderRepository()
        _make_work_order(status=PMWorkOrderStatus.OVERDUE)
        _make_work_order(status=PMWorkOrderStatus.SCHEDULED)
        overdue = repo.list_overdue()
        assert all(wo.status == PMWorkOrderStatus.OVERDUE for wo in overdue)
        assert len(overdue) >= 1
