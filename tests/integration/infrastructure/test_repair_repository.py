"""Integration tests for DjangoRepairOrderRepository."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from apps.repair.domain.entities import (
    RepairActivity,
    RepairOrder,
    RepairOrderStatus,
    RepairPart,
)
from apps.repair.domain.exceptions import RepairOrderNotFoundError
from apps.repair.domain.interfaces.repair_repository import IRepairOrderRepository
from apps.repair.domain.value_objects import (
    LaborHours,
    PartQuantity,
    TechnicianAssignment,
)
from apps.repair.infrastructure.repositories import DjangoRepairOrderRepository

pytestmark = pytest.mark.django_db


def _make_order(
    vehicle_id: uuid.UUID | None = None,
    fault_id: uuid.UUID | None = None,
    status: RepairOrderStatus = RepairOrderStatus.CREATED,
) -> RepairOrder:
    now = datetime.now(tz=UTC)
    repo = DjangoRepairOrderRepository()
    order = RepairOrder(
        id=uuid.uuid4(),
        vehicle_id=vehicle_id or uuid.uuid4(),
        fault_id=fault_id or uuid.uuid4(),
        status=status,
        created_by_id=uuid.uuid4(),
        created_at=now,
        updated_at=now,
    )
    return repo.save(order)


def _activity() -> RepairActivity:
    return RepairActivity(
        id=uuid.uuid4(),
        description="Replace brake pads",
        labor_hours=LaborHours(hours=Decimal("2.5")),
        performed_by_id=uuid.uuid4(),
        performed_at=datetime.now(tz=UTC),
    )


def _part() -> RepairPart:
    return RepairPart(
        id=uuid.uuid4(),
        part_quantity=PartQuantity(
            material_number="MAT-001234",
            quantity=2,
            unit_of_measure="EA",
        ),
    )


class TestInterface:
    def test_satisfies_interface(self) -> None:
        assert isinstance(DjangoRepairOrderRepository(), IRepairOrderRepository)


class TestSaveAndRetrieve:
    def test_save_and_get_by_id(self) -> None:
        repo = DjangoRepairOrderRepository()
        order = _make_order()
        fetched = repo.get_by_id(order.id)
        assert fetched.id == order.id
        assert fetched.status == RepairOrderStatus.CREATED

    def test_get_by_id_not_found(self) -> None:
        repo = DjangoRepairOrderRepository()
        with pytest.raises(RepairOrderNotFoundError):
            repo.get_by_id(uuid.uuid4())

    def test_activities_persisted(self) -> None:
        repo = DjangoRepairOrderRepository()
        order = _make_order()
        order.activities = [_activity(), _activity()]
        repo.save(order)
        fetched = repo.get_by_id(order.id)
        assert len(fetched.activities) == 2

    def test_parts_persisted(self) -> None:
        repo = DjangoRepairOrderRepository()
        order = _make_order()
        order.parts = [_part()]
        repo.save(order)
        fetched = repo.get_by_id(order.id)
        assert len(fetched.parts) == 1
        assert fetched.parts[0].part_quantity.material_number == "MAT-001234"

    def test_technician_assignment_persisted(self) -> None:
        repo = DjangoRepairOrderRepository()
        order = _make_order()
        tech_id = uuid.uuid4()
        assignment = TechnicianAssignment(
            technician_id=tech_id,
            assigned_at=datetime.now(tz=UTC),
        )
        order.assign_technician(assignment)
        repo.save(order)
        fetched = repo.get_by_id(order.id)
        assert fetched.assignment is not None
        assert fetched.assignment.technician_id == tech_id

    def test_status_transition_persisted(self) -> None:
        repo = DjangoRepairOrderRepository()
        order = _make_order()
        tech_id = uuid.uuid4()
        order.assign_technician(
            TechnicianAssignment(
                technician_id=tech_id, assigned_at=datetime.now(tz=UTC)
            )
        )
        repo.save(order)
        order.transition_to(RepairOrderStatus.IN_PROGRESS)
        repo.save(order)
        fetched = repo.get_by_id(order.id)
        assert fetched.status == RepairOrderStatus.IN_PROGRESS


class TestListOperations:
    def test_list_by_vehicle(self) -> None:
        repo = DjangoRepairOrderRepository()
        vid = uuid.uuid4()
        _make_order(vehicle_id=vid)
        _make_order(vehicle_id=vid)
        _make_order()
        result = repo.list_by_vehicle(vid)
        assert len(result) == 2

    def test_list_by_fault(self) -> None:
        repo = DjangoRepairOrderRepository()
        fid = uuid.uuid4()
        _make_order(fault_id=fid)
        _make_order(fault_id=fid)
        _make_order()
        result = repo.list_by_fault(fid)
        assert len(result) == 2

    def test_list_active_by_vehicle_excludes_terminal(self) -> None:
        """Active guard: COMPLETED and CANCELLED orders must be excluded."""
        repo = DjangoRepairOrderRepository()
        vid = uuid.uuid4()
        _make_order(vehicle_id=vid, status=RepairOrderStatus.CREATED)
        # Walk through required transitions to reach COMPLETED
        completed = _make_order(vehicle_id=vid, status=RepairOrderStatus.CREATED)
        tech = TechnicianAssignment(
            technician_id=uuid.uuid4(), assigned_at=datetime.now(tz=UTC)
        )
        completed.assign_technician(tech)
        completed.transition_to(RepairOrderStatus.IN_PROGRESS)
        completed.complete(completed_at=datetime.now(tz=UTC))
        repo.save(completed)
        active = repo.list_active_by_vehicle(vid)
        ids = {o.id for o in active}
        assert completed.id not in ids
        assert len(active) == 1


class TestSoftDelete:
    def test_delete_hides_order(self) -> None:
        repo = DjangoRepairOrderRepository()
        order = _make_order()
        repo.delete(order.id)
        with pytest.raises(RepairOrderNotFoundError):
            repo.get_by_id(order.id)

    def test_delete_nonexistent_raises(self) -> None:
        repo = DjangoRepairOrderRepository()
        with pytest.raises(RepairOrderNotFoundError):
            repo.delete(uuid.uuid4())
