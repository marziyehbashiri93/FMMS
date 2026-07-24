"""Unit tests for transport post-handover decision services."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from apps.fault.domain.entities import Fault, FaultStatus
from apps.fault.domain.interfaces.fault_repository import IFaultRepository
from apps.fault.domain.value_objects import FaultCode, FaultDescription, FaultSeverity
from apps.repair.application.dto.repair_dto import (
    TransportHandoverApproveDTO,
    TransportHandoverRejectDTO,
)
from apps.repair.application.services.transport_handover_decision_service import (
    ApproveTransportHandoverService,
    RejectTransportHandoverService,
)
from apps.repair.domain.entities import RepairOrder, RepairOrderStatus
from apps.repair.domain.interfaces.repair_repository import IRepairOrderRepository
from apps.vehicle.domain.entities import Vehicle, VehicleStatus
from apps.vehicle.domain.interfaces.vehicle_repository import IVehicleRepository
from apps.vehicle.domain.value_objects import PlateNumber, SAPVehicleNumber
from core.exceptions.base_exception import FMMSNotFoundError


def _make_order(*, status: RepairOrderStatus) -> RepairOrder:
    now = datetime.now(tz=UTC)
    return RepairOrder(
        id=uuid.uuid4(),
        vehicle_id=uuid.uuid4(),
        fault_id=uuid.uuid4(),
        status=status,
        created_by_id=uuid.uuid4(),
        created_at=now,
        updated_at=now,
        completed_at=(
            now
            if status == RepairOrderStatus.WAITING_TRANSPORT_FINAL_APPROVAL
            else None
        ),
    )


def _make_fault(*, fault_id: uuid.UUID, vehicle_id: uuid.UUID) -> Fault:
    now = datetime.now(tz=UTC)
    return Fault(
        id=fault_id,
        vehicle_id=vehicle_id,
        code=FaultCode("TRN-01"),
        description=FaultDescription("Transport handover test fault"),
        severity=FaultSeverity.MEDIUM,
        status=FaultStatus.OPEN,
        reported_by_id=uuid.uuid4(),
        reported_at=now,
        created_at=now,
        updated_at=now,
    )


def _make_vehicle(*, vehicle_id: uuid.UUID) -> Vehicle:
    now = datetime.now(tz=UTC)
    return Vehicle(
        id=vehicle_id,
        vehicle_number=SAPVehicleNumber("300004"),
        license_plate=PlateNumber("12TRN001"),
        status=VehicleStatus.WAITING_DRIVER_CONFIRMATION,
        created_at=now,
        updated_at=now,
    )


class FakeRepairRepository(IRepairOrderRepository):
    def __init__(self, initial: list[RepairOrder] | None = None) -> None:
        self._store: dict[uuid.UUID, RepairOrder] = {
            order.id: order for order in (initial or [])
        }

    def get_by_id(self, order_id: uuid.UUID) -> RepairOrder | None:
        return self._store.get(order_id)

    def list_by_vehicle(
        self, vehicle_id: uuid.UUID, status: RepairOrderStatus | None = None
    ) -> list[RepairOrder]:
        orders = [o for o in self._store.values() if o.vehicle_id == vehicle_id]
        if status is not None:
            orders = [o for o in orders if o.status == status]
        return orders

    def list_by_fault(self, fault_id: uuid.UUID) -> list[RepairOrder]:
        return [o for o in self._store.values() if o.fault_id == fault_id]

    def list_active_by_vehicle(self, vehicle_id: uuid.UUID) -> list[RepairOrder]:
        terminal = {
            RepairOrderStatus.COMPLETED,
            RepairOrderStatus.CANCELLED,
            RepairOrderStatus.REJECTED_BY_DRIVER,
        }
        return [
            o
            for o in self._store.values()
            if o.vehicle_id == vehicle_id and o.status not in terminal
        ]

    def has_open_repair_order_for_vehicle(self, vehicle_id: uuid.UUID) -> bool:
        return bool(self.list_active_by_vehicle(vehicle_id))

    def save(self, order: RepairOrder) -> RepairOrder:
        self._store[order.id] = order
        return order

    def delete(self, order_id: uuid.UUID) -> None:
        self._store.pop(order_id, None)


class FakeFaultRepository(IFaultRepository):
    def __init__(self, initial: list[Fault] | None = None) -> None:
        self._store: dict[uuid.UUID, Fault] = {fault.id: fault for fault in (initial or [])}

    def get_by_id(self, fault_id: uuid.UUID) -> Fault | None:
        return self._store.get(fault_id)

    def list_by_vehicle(self, vehicle_id: uuid.UUID) -> list[Fault]:
        return [f for f in self._store.values() if f.vehicle_id == vehicle_id]

    def list_open_by_severity(self, severity: FaultSeverity) -> list[Fault]:
        return [
            f
            for f in self._store.values()
            if f.severity == severity and f.status != FaultStatus.CLOSED
        ]

    def list_by_inspection(self, inspection_id: uuid.UUID) -> list[Fault]:
        return [f for f in self._store.values() if f.inspection_id == inspection_id]

    def has_open_fault_for_vehicle(self, vehicle_id: uuid.UUID) -> bool:
        return any(
            f.vehicle_id == vehicle_id and f.status != FaultStatus.CLOSED
            for f in self._store.values()
        )

    def save(self, fault: Fault) -> Fault:
        self._store[fault.id] = fault
        return fault

    def delete(self, fault_id: uuid.UUID) -> None:
        self._store.pop(fault_id, None)


class FakeVehicleRepository(IVehicleRepository):
    def __init__(self, initial: list[Vehicle] | None = None) -> None:
        self._store: dict[uuid.UUID, Vehicle] = {v.id: v for v in (initial or [])}

    def get_by_id(self, vehicle_id: uuid.UUID) -> Vehicle | None:
        return self._store.get(vehicle_id)

    def get_by_plate(self, plate_number: PlateNumber) -> Vehicle | None:
        return None

    def get_by_vehicle_number(self, vehicle_number) -> Vehicle | None:
        return None

    def exists_by_plate(self, plate_number: PlateNumber) -> bool:
        return False

    def list_active(self) -> list[Vehicle]:
        return [v for v in self._store.values() if v.status == VehicleStatus.ACTIVE]

    def list_by_status(self, status: VehicleStatus) -> list[Vehicle]:
        return [v for v in self._store.values() if v.status == status]

    def save(self, vehicle: Vehicle) -> Vehicle:
        self._store[vehicle.id] = vehicle
        return vehicle

    def decommission_missing_from_sap(self, seen_vehicle_numbers: set[str]) -> int:
        count = 0
        for vehicle in self._store.values():
            if vehicle.vehicle_number.value not in seen_vehicle_numbers:
                vehicle.decommission()
                count += 1
        return count

    def record_driver_assignment_snapshot(self, **kwargs: object) -> None:
        return None

    def delete(self, vehicle_id: uuid.UUID) -> None:
        self._store.pop(vehicle_id, None)


class TestApproveTransportHandoverService:
    def test_approves_and_closes_fault(self) -> None:
        order = _make_order(status=RepairOrderStatus.WAITING_TRANSPORT_FINAL_APPROVAL)
        fault = _make_fault(fault_id=order.fault_id, vehicle_id=order.vehicle_id)
        vehicle = _make_vehicle(vehicle_id=order.vehicle_id)
        repair_repo = FakeRepairRepository([order])
        fault_repo = FakeFaultRepository([fault])
        vehicle_repo = FakeVehicleRepository([vehicle])

        result = ApproveTransportHandoverService(
            repair_repo, vehicle_repo, fault_repo
        ).execute(
            TransportHandoverApproveDTO(
                repair_order_id=order.id,
                request_id="req-transport-approve",
                approved_by=uuid.uuid4(),
            )
        )

        assert result.status == RepairOrderStatus.COMPLETED
        assert repair_repo.get_by_id(order.id).status == RepairOrderStatus.COMPLETED
        assert fault_repo.get_by_id(fault.id).status == FaultStatus.CLOSED
        assert vehicle_repo.get_by_id(vehicle.id).status == VehicleStatus.ACTIVE

    def test_raises_not_found_for_missing_order(self) -> None:
        with pytest.raises(FMMSNotFoundError):
            ApproveTransportHandoverService(
                FakeRepairRepository(),
                FakeVehicleRepository(),
                FakeFaultRepository(),
            ).execute(
                TransportHandoverApproveDTO(
                    repair_order_id=uuid.uuid4(),
                    request_id="req-missing",
                    approved_by=uuid.uuid4(),
                )
            )


class TestRejectTransportHandoverService:
    def test_rejects_and_creates_follow_up_repair(self) -> None:
        order = _make_order(status=RepairOrderStatus.WAITING_TRANSPORT_FINAL_APPROVAL)
        vehicle = _make_vehicle(vehicle_id=order.vehicle_id)
        repair_repo = FakeRepairRepository([order])
        vehicle_repo = FakeVehicleRepository([vehicle])

        result = RejectTransportHandoverService(repair_repo, vehicle_repo).execute(
            TransportHandoverRejectDTO(
                repair_order_id=order.id,
                request_id="req-transport-reject",
                rejected_by=uuid.uuid4(),
                comment="quality issue",
            )
        )

        assert result.status == RepairOrderStatus.COMPLETED
        follow_ups = [
            item
            for item in repair_repo.list_by_fault(order.fault_id)
            if item.id != order.id
        ]
        assert len(follow_ups) == 1
        assert follow_ups[0].status == RepairOrderStatus.CREATED
        assert vehicle_repo.get_by_id(vehicle.id).status == VehicleStatus.UNDER_REPAIR
