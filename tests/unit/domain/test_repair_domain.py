"""Unit tests for the Repair domain layer."""

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
from apps.repair.domain.exceptions import (
    RepairOrderInvalidStateError,
    RepairOrderInvalidStateTransitionError,
    RepairOrderNotFoundError,
)
from apps.repair.domain.value_objects import (
    LaborHours,
    PartQuantity,
    TechnicianAssignment,
)


def _make_order(**kwargs: object) -> RepairOrder:
    defaults: dict[str, object] = {
        "id": uuid.uuid4(),
        "vehicle_id": uuid.uuid4(),
        "fault_id": uuid.uuid4(),
        "status": RepairOrderStatus.CREATED,
        "created_by_id": uuid.uuid4(),
        "created_at": datetime.now(tz=UTC),
        "updated_at": datetime.now(tz=UTC),
    }
    defaults.update(kwargs)
    return RepairOrder(**defaults)  # type: ignore[arg-type]


def _make_assignment() -> TechnicianAssignment:
    return TechnicianAssignment(
        technician_id=uuid.uuid4(),
        assigned_at=datetime.now(tz=UTC),
    )


def _make_activity() -> RepairActivity:
    return RepairActivity(
        id=uuid.uuid4(),
        description="Replaced brake pads.",
        labor_hours=LaborHours(hours=Decimal("2.5")),
        performed_by_id=uuid.uuid4(),
        performed_at=datetime.now(tz=UTC),
    )


def _make_part() -> RepairPart:
    return RepairPart(
        id=uuid.uuid4(),
        part_quantity=PartQuantity(
            material_number="000000123456",
            quantity=4,
            unit_of_measure="EA",
        ),
    )


class TestPartQuantity:
    def test_valid(self) -> None:
        pq = PartQuantity(
            material_number="000000123456", quantity=2, unit_of_measure="EA"
        )
        assert pq.quantity == 2

    def test_zero_quantity_raises(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            PartQuantity(
                material_number="000000123456", quantity=0, unit_of_measure="EA"
            )

    def test_empty_material_raises(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            PartQuantity(material_number="", quantity=1, unit_of_measure="EA")

    def test_material_too_long_raises(self) -> None:
        with pytest.raises(ValueError, match="18"):
            PartQuantity(material_number="1" * 19, quantity=1, unit_of_measure="EA")


class TestLaborHours:
    def test_valid_hours(self) -> None:
        lh = LaborHours(hours=Decimal("3.5"))
        assert lh.hours == Decimal("3.5")

    def test_zero_valid(self) -> None:
        lh = LaborHours(hours=Decimal("0"))
        assert lh.hours == Decimal("0")

    def test_negative_raises(self) -> None:
        with pytest.raises(ValueError, match="non-negative"):
            LaborHours(hours=Decimal("-1"))


class TestRepairOrderLifecycle:
    def test_initial_state(self) -> None:
        order = _make_order()
        assert order.status == RepairOrderStatus.CREATED
        assert order.is_active is True

    def test_assign_technician(self) -> None:
        order = _make_order()
        assignment = _make_assignment()
        order.assign_technician(assignment)
        assert order.status == RepairOrderStatus.ASSIGNED
        assert order.assignment == assignment

    def test_approve_from_created(self) -> None:
        order = _make_order()
        order.approve()
        assert order.status == RepairOrderStatus.APPROVED

    def test_assign_workshop_after_approval(self) -> None:
        from apps.repair.domain.entities import WorkshopType

        order = _make_order()
        order.approve()
        order.assign_workshop(WorkshopType.INTERNAL)
        assert order.status == RepairOrderStatus.WORKSHOP_ASSIGNED
        assert order.workshop_type == WorkshopType.INTERNAL

    def test_cannot_assign_workshop_before_approval(self) -> None:
        from apps.repair.domain.entities import WorkshopType

        order = _make_order()
        with pytest.raises(RepairOrderInvalidStateTransitionError):
            order.assign_workshop(WorkshopType.EXTERNAL)

    def test_assign_technician_after_workshop_assigned(self) -> None:
        from apps.repair.domain.entities import WorkshopType

        order = _make_order()
        order.approve()
        order.assign_workshop(WorkshopType.INTERNAL)
        assignment = _make_assignment()
        order.assign_technician(assignment)
        assert order.status == RepairOrderStatus.ASSIGNED

    def test_assign_external_workshop_waits_for_referral_approval(self) -> None:
        from apps.repair.domain.entities import WorkshopType

        order = _make_order()
        order.approve()
        order.assign_workshop(WorkshopType.EXTERNAL, workshop_id="EXT-001")
        assert order.status == RepairOrderStatus.WAITING_EXTERNAL_REFERRAL_APPROVAL
        assert order.workshop_type == WorkshopType.EXTERNAL
        assert order.workshop_id == "EXT-001"

    def test_transport_reject_from_created(self) -> None:
        order = _make_order()
        order.reject_by_transport("Not required")
        assert order.status == RepairOrderStatus.REJECTED_BY_TRANSPORT
        assert order.transport_rejection_reason == "Not required"

    def test_start_work_from_workshop_assigned(self) -> None:
        from apps.repair.domain.entities import WorkshopType

        order = _make_order()
        order.approve()
        order.assign_workshop(WorkshopType.INTERNAL)
        order.start_work()
        assert order.status == RepairOrderStatus.IN_PROGRESS

    def test_start_work(self) -> None:
        order = _make_order(status=RepairOrderStatus.ASSIGNED)
        order.start_work()
        assert order.status == RepairOrderStatus.IN_PROGRESS

    def test_complete(self) -> None:
        order = _make_order(status=RepairOrderStatus.IN_PROGRESS)
        completed_at = datetime.now(tz=UTC)
        order.complete(completed_at=completed_at)
        assert order.status == RepairOrderStatus.COMPLETED
        assert order.is_active is False
        assert order.completed_at == completed_at

    def test_cancel_from_created(self) -> None:
        order = _make_order()
        order.cancel()
        assert order.status == RepairOrderStatus.CANCELLED

    def test_cannot_add_activity_to_completed(self) -> None:
        order = _make_order(status=RepairOrderStatus.COMPLETED)
        with pytest.raises(RepairOrderInvalidStateError):
            order.add_activity(_make_activity())

    def test_cannot_add_part_to_cancelled(self) -> None:
        order = _make_order(status=RepairOrderStatus.CANCELLED)
        with pytest.raises(RepairOrderInvalidStateError):
            order.add_part(_make_part())

    def test_add_activity_in_progress(self) -> None:
        order = _make_order(status=RepairOrderStatus.IN_PROGRESS)
        order.add_activity(_make_activity())
        assert len(order.activities) == 1

    def test_add_part(self) -> None:
        order = _make_order(status=RepairOrderStatus.ASSIGNED)
        order.add_part(_make_part())
        assert len(order.parts) == 1

    def test_total_labor_hours(self) -> None:
        order = _make_order(status=RepairOrderStatus.IN_PROGRESS)
        order.add_activity(_make_activity())
        order.add_activity(_make_activity())
        assert order.total_labor_hours == Decimal("5.0")

    def test_complete_after_transport_handover(self) -> None:
        order = _make_order(status=RepairOrderStatus.WAITING_TRANSPORT_FINAL_APPROVAL)
        completed_at = datetime.now(tz=UTC)
        order.complete_after_transport_handover(completed_at=completed_at)
        assert order.status == RepairOrderStatus.COMPLETED
        assert order.completed_at == completed_at

    def test_invalid_transition(self) -> None:
        order = _make_order(status=RepairOrderStatus.CREATED)
        with pytest.raises(RepairOrderInvalidStateTransitionError):
            order.start_work()

    def test_link_sap_order(self) -> None:
        order = _make_order()
        order.link_sap_order("PM-ORD-0001")
        assert order.sap_order_number == "PM-ORD-0001"


class TestRepairExceptions:
    def test_not_found(self) -> None:
        err = RepairOrderNotFoundError("id-1")
        assert "id-1" in str(err)
