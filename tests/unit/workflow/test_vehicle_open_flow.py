"""Unit tests for the one-open-flow-per-vehicle workflow guard."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from apps.fault.domain.entities import Fault, FaultStatus
from apps.fault.domain.interfaces.fault_repository import IFaultRepository
from apps.fault.domain.value_objects import FaultSeverity
from apps.repair.domain.entities import RepairOrder, RepairOrderStatus
from apps.repair.domain.interfaces.repair_repository import IRepairOrderRepository
from core.exceptions.base_exception import FMMSStateError
from core.workflow import (
    FAULT_OPEN_STATUSES,
    FAULT_TERMINAL_STATUSES,
    REPAIR_ORDER_OPEN_STATUSES,
    REPAIR_ORDER_TERMINAL_STATUSES,
    VEHICLE_OPEN_FLOW_ERROR_CODE,
    assert_vehicle_has_no_open_flow,
)


class FakeFaultRepository(IFaultRepository):
    def __init__(self, open_fault: bool = False) -> None:
        self._open_fault = open_fault

    def get_by_id(self, fault_id: uuid.UUID) -> Fault:
        raise NotImplementedError

    def list_by_vehicle(
        self, vehicle_id: uuid.UUID, status: FaultStatus | None = None
    ) -> list[Fault]:
        return []

    def list_all(self, status: FaultStatus | None = None) -> list[Fault]:
        return []

    def has_open_fault_for_vehicle(self, vehicle_id: uuid.UUID) -> bool:
        return self._open_fault

    def list_open_by_severity(self, severity: FaultSeverity) -> list[Fault]:
        return []

    def list_by_inspection(self, inspection_id: uuid.UUID) -> list[Fault]:
        return []

    def save(self, fault: Fault) -> Fault:
        return fault

    def delete(self, fault_id: uuid.UUID) -> None:
        return None


class FakeRepairOrderRepository(IRepairOrderRepository):
    def __init__(self, active_orders: list[RepairOrder] | None = None) -> None:
        self._active_orders = active_orders or []

    def get_by_id(self, order_id: uuid.UUID) -> RepairOrder:
        raise NotImplementedError

    def list_by_vehicle(
        self, vehicle_id: uuid.UUID, status: RepairOrderStatus | None = None
    ) -> list[RepairOrder]:
        return []

    def list_by_fault(self, fault_id: uuid.UUID) -> list[RepairOrder]:
        return []

    def list_all(self, status: RepairOrderStatus | None = None) -> list[RepairOrder]:
        return []

    def list_active_by_vehicle(self, vehicle_id: uuid.UUID) -> list[RepairOrder]:
        return self._active_orders

    def has_open_repair_order_for_vehicle(self, vehicle_id: uuid.UUID) -> bool:
        return bool(self._active_orders)

    def save(self, order: RepairOrder) -> RepairOrder:
        return order

    def delete(self, order_id: uuid.UUID) -> None:
        return None


def test_status_sets_cover_domain_enums() -> None:
    assert FaultStatus.CLOSED in FAULT_TERMINAL_STATUSES
    assert FaultStatus.OPEN in FAULT_OPEN_STATUSES
    assert RepairOrderStatus.COMPLETED in REPAIR_ORDER_TERMINAL_STATUSES
    assert RepairOrderStatus.CREATED in REPAIR_ORDER_OPEN_STATUSES


def test_guard_passes_when_vehicle_is_clear() -> None:
    vehicle_id = uuid.uuid4()
    assert_vehicle_has_no_open_flow(
        vehicle_id,
        fault_repository=FakeFaultRepository(open_fault=False),
        repair_order_repository=FakeRepairOrderRepository(),
    )


def test_guard_raises_for_open_fault() -> None:
    with pytest.raises(FMMSStateError) as exc_info:
        assert_vehicle_has_no_open_flow(
            uuid.uuid4(),
            fault_repository=FakeFaultRepository(open_fault=True),
            repair_order_repository=FakeRepairOrderRepository(),
        )

    assert exc_info.value.error_code == VEHICLE_OPEN_FLOW_ERROR_CODE
    assert exc_info.value.details["has_open_fault"] is True


def test_guard_raises_for_active_repair_order() -> None:
    now = datetime.now(tz=UTC)
    active = RepairOrder(
        id=uuid.uuid4(),
        vehicle_id=uuid.uuid4(),
        fault_id=uuid.uuid4(),
        status=RepairOrderStatus.APPROVED,
        created_by_id=uuid.uuid4(),
        created_at=now,
        updated_at=now,
    )

    with pytest.raises(FMMSStateError) as exc_info:
        assert_vehicle_has_no_open_flow(
            active.vehicle_id,
            fault_repository=FakeFaultRepository(open_fault=False),
            repair_order_repository=FakeRepairOrderRepository(active_orders=[active]),
        )

    assert "active_repair_order_ids" in exc_info.value.details
