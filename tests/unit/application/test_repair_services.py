"""Unit tests for Repair application services.

All repository and SAP port dependencies are in-memory fakes —
no database, no network, no infrastructure imports.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from apps.fault.domain.entities import Fault, FaultStatus
from apps.fault.domain.interfaces.fault_repository import IFaultRepository
from apps.fault.domain.value_objects import FaultCode, FaultDescription, FaultSeverity
from apps.integration.domain.entities import (
    SAPObjectType,
    SAPTransaction,
    SAPTransactionStatus,
)
from apps.integration.domain.interfaces.sap_transaction_repository import (
    ISAPTransactionRepository,
)
from apps.repair.application.dto.repair_dto import (
    AddRepairActivityDTO,
    AddRepairPartDTO,
    AssignRepairOrderDTO,
    CloseRepairOrderDTO,
    CompleteRepairOrderDTO,
    CreateRepairOrderDTO,
    RepairOrderResponseDTO,
    SyncRepairToSAPDTO,
)
from apps.repair.application.services.add_repair_activity_service import (
    AddRepairActivityService,
    AddRepairPartService,
)
from apps.repair.application.services.assign_repair_order_service import (
    AssignRepairOrderService,
)
from apps.repair.application.services.create_repair_order_service import (
    CreateRepairOrderService,
)
from apps.repair.application.services.get_repair_order_service import (
    GetRepairOrderService,
    ListRepairOrdersService,
)
from apps.repair.application.services.sync_repair_to_sap_service import (
    SyncRepairToSAPService,
)
from apps.repair.application.services.update_repair_status_service import (
    CancelRepairOrderService,
    CompleteRepairOrderService,
    StartRepairService,
)
from apps.repair.domain.entities import RepairOrder, RepairOrderStatus
from apps.repair.domain.exceptions import (
    RepairOrderInvalidStateError,
    RepairOrderInvalidStateTransitionError,
)
from apps.repair.domain.interfaces.repair_repository import IRepairOrderRepository
from apps.repair.domain.value_objects import TechnicianAssignment
from apps.vehicle.domain.entities import Vehicle, VehicleCategory, VehicleStatus
from apps.vehicle.domain.interfaces.vehicle_repository import IVehicleRepository
from apps.vehicle.domain.value_objects import VIN, PlateNumber, SAPEquipmentNumber
from core.exceptions.base_exception import FMMSConflictError, FMMSNotFoundError
from core.sap.dtos.pm_order import CreatePMOrderRequest, SAPPMOrderDTO
from core.sap.ports.pm_order_port import ISAPPMOrderPort
from infrastructure.sap.transaction.sap_transaction_manager import SAPTransactionManager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class FakeSAPTransactionRepository(ISAPTransactionRepository):
    """In-memory SAP transaction store for write-gateway tests."""

    def __init__(self, initial: list[SAPTransaction] | None = None) -> None:
        self._store: dict[uuid.UUID, SAPTransaction] = {
            tx.id: tx for tx in (initial or [])
        }

    def get_by_id(self, transaction_id: uuid.UUID) -> SAPTransaction:
        return self._store[transaction_id]

    def get_by_idempotency_key(self, idempotency_key: str) -> SAPTransaction | None:
        return next(
            (
                tx
                for tx in self._store.values()
                if tx.idempotency_key == idempotency_key
            ),
            None,
        )

    def list_pending_for_retry(self) -> list[SAPTransaction]:
        return [
            tx
            for tx in self._store.values()
            if tx.status == SAPTransactionStatus.FAILED
            and tx.retry_count < tx.max_retries
        ]

    def list_by_object(
        self, object_type: SAPObjectType, object_id: uuid.UUID
    ) -> list[SAPTransaction]:
        return [
            tx
            for tx in self._store.values()
            if tx.object_type == object_type and tx.object_id == object_id
        ]

    def list_by_status(self, status: SAPTransactionStatus) -> list[SAPTransaction]:
        return [tx for tx in self._store.values() if tx.status == status]

    def save(self, transaction: SAPTransaction) -> SAPTransaction:
        self._store[transaction.id] = transaction
        return transaction


def _tx_manager(
    repo: FakeSAPTransactionRepository | None = None,
) -> SAPTransactionManager:
    """Wire the real SAP write gateway against an in-memory repo."""
    return SAPTransactionManager(repository=repo or FakeSAPTransactionRepository())


def _make_vehicle(*, with_sap: bool = False) -> Vehicle:
    return Vehicle(
        id=uuid.uuid4(),
        plate_number=PlateNumber("REPPLT01"),
        vin=VIN("1HGCM82633A004352"),
        make="Toyota",
        model="Hilux",
        year=2022,
        category=VehicleCategory.LIGHT,
        status=VehicleStatus.ACTIVE,
        created_at=datetime.now(tz=UTC),
        updated_at=datetime.now(tz=UTC),
        sap_equipment_number=SAPEquipmentNumber("100001") if with_sap else None,
    )


def _make_fault(vehicle_id: uuid.UUID) -> Fault:
    now = datetime.now(tz=UTC)
    return Fault(
        id=uuid.uuid4(),
        vehicle_id=vehicle_id,
        code=FaultCode("BRK-01"),
        description=FaultDescription("Brake pad wear"),
        severity=FaultSeverity.MEDIUM,
        status=FaultStatus.OPEN,
        reported_by_id=uuid.uuid4(),
        reported_at=now,
        created_at=now,
        updated_at=now,
    )


def _make_order(
    *,
    vehicle_id: uuid.UUID | None = None,
    fault_id: uuid.UUID | None = None,
    status: RepairOrderStatus = RepairOrderStatus.CREATED,
) -> RepairOrder:
    now = datetime.now(tz=UTC)
    order = RepairOrder(
        id=uuid.uuid4(),
        vehicle_id=vehicle_id or uuid.uuid4(),
        fault_id=fault_id or uuid.uuid4(),
        status=RepairOrderStatus.CREATED,
        created_by_id=uuid.uuid4(),
        created_at=now,
        updated_at=now,
    )
    if status == RepairOrderStatus.ASSIGNED:
        order.assign_technician(
            TechnicianAssignment(technician_id=uuid.uuid4(), assigned_at=now)
        )
    elif status == RepairOrderStatus.IN_PROGRESS:
        order.assign_technician(
            TechnicianAssignment(technician_id=uuid.uuid4(), assigned_at=now)
        )
        order.start_work()
    elif status == RepairOrderStatus.COMPLETED:
        order.assign_technician(
            TechnicianAssignment(technician_id=uuid.uuid4(), assigned_at=now)
        )
        order.start_work()
        order.complete(completed_at=now)
    elif status == RepairOrderStatus.CANCELLED:
        order.cancel()
    return order


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeRepairRepository(IRepairOrderRepository):
    def __init__(self, initial: list[RepairOrder] | None = None) -> None:
        self._store: dict[uuid.UUID, RepairOrder] = {o.id: o for o in (initial or [])}

    def get_by_id(self, order_id: uuid.UUID) -> RepairOrder | None:
        return self._store.get(order_id)

    def list_by_vehicle(
        self,
        vehicle_id: uuid.UUID,
        status: RepairOrderStatus | None = None,
    ) -> list[RepairOrder]:
        orders = [o for o in self._store.values() if o.vehicle_id == vehicle_id]
        if status is not None:
            orders = [o for o in orders if o.status == status]
        return orders

    def list_by_fault(self, fault_id: uuid.UUID) -> list[RepairOrder]:
        return [o for o in self._store.values() if o.fault_id == fault_id]

    def list_active_by_vehicle(self, vehicle_id: uuid.UUID) -> list[RepairOrder]:
        return [
            o
            for o in self._store.values()
            if o.vehicle_id == vehicle_id and o.is_active
        ]

    def has_open_repair_order_for_vehicle(self, vehicle_id: uuid.UUID) -> bool:
        return bool(self.list_active_by_vehicle(vehicle_id))

    def save(self, order: RepairOrder) -> RepairOrder:
        self._store[order.id] = order
        return order

    def delete(self, order_id: uuid.UUID) -> None:
        self._store.pop(order_id, None)


class FakeVehicleRepository(IVehicleRepository):
    def __init__(self, initial: list[Vehicle] | None = None) -> None:
        self._store: dict[uuid.UUID, Vehicle] = {v.id: v for v in (initial or [])}

    def get_by_id(self, vehicle_id: uuid.UUID) -> Vehicle | None:
        return self._store.get(vehicle_id)

    def get_by_plate(self, plate_number: PlateNumber) -> Vehicle | None:
        return None

    def get_by_sap_equipment_number(
        self, sap_equipment_number: SAPEquipmentNumber
    ) -> Vehicle | None:
        return next(
            (
                v
                for v in self._store.values()
                if v.sap_equipment_number is not None
                and v.sap_equipment_number == sap_equipment_number
            ),
            None,
        )

    def exists_by_plate(self, plate_number: PlateNumber) -> bool:
        return False

    def list_active(self) -> list[Vehicle]:
        return [v for v in self._store.values() if v.status == VehicleStatus.ACTIVE]

    def list_by_status(self, status: VehicleStatus) -> list[Vehicle]:
        return [v for v in self._store.values() if v.status == status]

    def save(self, vehicle: Vehicle) -> Vehicle:
        self._store[vehicle.id] = vehicle
        return vehicle

    def delete(self, vehicle_id: uuid.UUID) -> None:
        self._store.pop(vehicle_id, None)


class FakeFaultRepository(IFaultRepository):
    def __init__(self, initial: list[Fault] | None = None) -> None:
        self._store: dict[uuid.UUID, Fault] = {f.id: f for f in (initial or [])}

    def get_by_id(self, fault_id: uuid.UUID) -> Fault | None:
        return self._store.get(fault_id)

    def list_by_vehicle(
        self, vehicle_id: uuid.UUID, status: FaultStatus | None = None
    ) -> list[Fault]:
        return [f for f in self._store.values() if f.vehicle_id == vehicle_id]

    def list_open_by_severity(self, severity: FaultSeverity) -> list[Fault]:
        return []

    def list_by_inspection(self, inspection_id: uuid.UUID) -> list[Fault]:
        return []

    def has_open_fault_for_vehicle(self, vehicle_id: uuid.UUID) -> bool:
        return False

    def save(self, fault: Fault) -> Fault:
        self._store[fault.id] = fault
        return fault

    def delete(self, fault_id: uuid.UUID) -> None:
        self._store.pop(fault_id, None)


class FakeSAPPMOrderPort(ISAPPMOrderPort):
    def __init__(self, order_number: str = "40001234") -> None:
        self.order_number = order_number
        self.calls: list[CreatePMOrderRequest] = []

    def create_pm_order(self, request: CreatePMOrderRequest) -> SAPPMOrderDTO:
        self.calls.append(request)
        return SAPPMOrderDTO(
            order_number=self.order_number,
            equipment_number=request.equipment_number,
            order_type=request.order_type,
            status="CREATED",
            planned_start=request.planned_start,
        )

    def complete_pm_order(self, order_number: str) -> SAPPMOrderDTO:
        return SAPPMOrderDTO(
            order_number=order_number,
            equipment_number="100001",
            order_type="PM01",
            status="COMPLETED",
        )

    def get_pm_order(self, order_number: str) -> SAPPMOrderDTO:
        return SAPPMOrderDTO(
            order_number=order_number,
            equipment_number="100001",
            order_type="PM01",
            status="CREATED",
        )


# ---------------------------------------------------------------------------
# CreateRepairOrderService
# ---------------------------------------------------------------------------


class TestCreateRepairOrderService:
    def test_creates_order_in_created_status(self) -> None:
        vehicle = _make_vehicle()
        fault = _make_fault(vehicle.id)
        service = CreateRepairOrderService(
            FakeRepairRepository(),
            FakeVehicleRepository([vehicle]),
            FakeFaultRepository([fault]),
        )

        result = service.execute(
            CreateRepairOrderDTO(
                vehicle_id=vehicle.id,
                fault_id=fault.id,
                request_id="req-create",
                created_by=uuid.uuid4(),
            )
        )

        assert isinstance(result, RepairOrderResponseDTO)
        assert result.status == RepairOrderStatus.CREATED
        assert result.vehicle_id == vehicle.id
        assert result.fault_id == fault.id

    def test_raises_not_found_for_missing_vehicle(self) -> None:
        fault = _make_fault(uuid.uuid4())
        service = CreateRepairOrderService(
            FakeRepairRepository(),
            FakeVehicleRepository(),
            FakeFaultRepository([fault]),
        )

        with pytest.raises(FMMSNotFoundError):
            service.execute(
                CreateRepairOrderDTO(
                    vehicle_id=uuid.uuid4(),
                    fault_id=fault.id,
                    request_id="req-noveh",
                    created_by=uuid.uuid4(),
                )
            )

    def test_raises_not_found_for_missing_fault(self) -> None:
        vehicle = _make_vehicle()
        service = CreateRepairOrderService(
            FakeRepairRepository(),
            FakeVehicleRepository([vehicle]),
            FakeFaultRepository(),
        )

        with pytest.raises(FMMSNotFoundError):
            service.execute(
                CreateRepairOrderDTO(
                    vehicle_id=vehicle.id,
                    fault_id=uuid.uuid4(),
                    request_id="req-nofault",
                    created_by=uuid.uuid4(),
                )
            )

    def test_raises_conflict_when_fault_vehicle_mismatch(self) -> None:
        vehicle = _make_vehicle()
        other_vehicle = _make_vehicle()
        fault = _make_fault(other_vehicle.id)
        service = CreateRepairOrderService(
            FakeRepairRepository(),
            FakeVehicleRepository([vehicle, other_vehicle]),
            FakeFaultRepository([fault]),
        )

        with pytest.raises(FMMSConflictError):
            service.execute(
                CreateRepairOrderDTO(
                    vehicle_id=vehicle.id,
                    fault_id=fault.id,
                    request_id="req-mismatch",
                    created_by=uuid.uuid4(),
                )
            )


# ---------------------------------------------------------------------------
# Assign / Start / Complete / Cancel
# ---------------------------------------------------------------------------


class TestAssignRepairOrderService:
    def test_assigns_technician(self) -> None:
        order = _make_order()
        repo = FakeRepairRepository([order])
        technician_id = uuid.uuid4()

        result = AssignRepairOrderService(repo).execute(
            AssignRepairOrderDTO(
                repair_order_id=order.id,
                technician_id=technician_id,
                request_id="req-assign",
                assigned_by=uuid.uuid4(),
            )
        )

        assert result.status == RepairOrderStatus.ASSIGNED
        assert result.technician_id == technician_id

    def test_raises_not_found(self) -> None:
        with pytest.raises(FMMSNotFoundError):
            AssignRepairOrderService(FakeRepairRepository()).execute(
                AssignRepairOrderDTO(
                    repair_order_id=uuid.uuid4(),
                    technician_id=uuid.uuid4(),
                    request_id="req-ghost",
                    assigned_by=uuid.uuid4(),
                )
            )

    def test_raises_state_error_when_not_created(self) -> None:
        order = _make_order(status=RepairOrderStatus.ASSIGNED)
        with pytest.raises(RepairOrderInvalidStateTransitionError):
            AssignRepairOrderService(FakeRepairRepository([order])).execute(
                AssignRepairOrderDTO(
                    repair_order_id=order.id,
                    technician_id=uuid.uuid4(),
                    request_id="req-reassign",
                    assigned_by=uuid.uuid4(),
                )
            )


class TestStartRepairService:
    def test_starts_assigned_order(self) -> None:
        order = _make_order(status=RepairOrderStatus.ASSIGNED)
        result = StartRepairService(FakeRepairRepository([order])).execute(order.id)

        assert result.status == RepairOrderStatus.IN_PROGRESS

    def test_raises_when_not_assigned(self) -> None:
        order = _make_order(status=RepairOrderStatus.CREATED)
        with pytest.raises(RepairOrderInvalidStateTransitionError):
            StartRepairService(FakeRepairRepository([order])).execute(order.id)


class TestCompleteRepairOrderService:
    def test_completes_in_progress_order(self) -> None:
        order = _make_order(status=RepairOrderStatus.IN_PROGRESS)
        completed_at = datetime.now(tz=UTC)

        result = CompleteRepairOrderService(FakeRepairRepository([order])).execute(
            CompleteRepairOrderDTO(
                repair_order_id=order.id,
                completed_at=completed_at,
                request_id="req-complete",
                completed_by=uuid.uuid4(),
            )
        )

        assert result.status == RepairOrderStatus.COMPLETED
        assert result.completed_at == completed_at

    def test_raises_when_not_in_progress(self) -> None:
        order = _make_order(status=RepairOrderStatus.ASSIGNED)
        with pytest.raises(RepairOrderInvalidStateTransitionError):
            CompleteRepairOrderService(FakeRepairRepository([order])).execute(
                CompleteRepairOrderDTO(
                    repair_order_id=order.id,
                    completed_at=datetime.now(tz=UTC),
                    request_id="req-early",
                    completed_by=uuid.uuid4(),
                )
            )


class TestCancelRepairOrderService:
    def test_cancels_created_order(self) -> None:
        order = _make_order()
        result = CancelRepairOrderService(FakeRepairRepository([order])).execute(
            CloseRepairOrderDTO(
                repair_order_id=order.id,
                request_id="req-cancel",
                requested_by=uuid.uuid4(),
            )
        )

        assert result.status == RepairOrderStatus.CANCELLED

    def test_raises_when_already_completed(self) -> None:
        order = _make_order(status=RepairOrderStatus.COMPLETED)
        with pytest.raises(RepairOrderInvalidStateTransitionError):
            CancelRepairOrderService(FakeRepairRepository([order])).execute(
                CloseRepairOrderDTO(
                    repair_order_id=order.id,
                    request_id="req-late",
                    requested_by=uuid.uuid4(),
                )
            )


# ---------------------------------------------------------------------------
# Activities / Parts
# ---------------------------------------------------------------------------


class TestAddRepairActivityService:
    def test_adds_activity(self) -> None:
        order = _make_order(status=RepairOrderStatus.IN_PROGRESS)
        result = AddRepairActivityService(FakeRepairRepository([order])).execute(
            AddRepairActivityDTO(
                repair_order_id=order.id,
                description="Replaced brake pads",
                labor_hours=Decimal("2.5"),
                performed_by_id=uuid.uuid4(),
                performed_at=datetime.now(tz=UTC),
                request_id="req-act",
            )
        )

        assert len(result.activities) == 1
        assert result.activities[0].labor_hours == Decimal("2.5")

    def test_raises_when_order_completed(self) -> None:
        order = _make_order(status=RepairOrderStatus.COMPLETED)
        with pytest.raises(RepairOrderInvalidStateError):
            AddRepairActivityService(FakeRepairRepository([order])).execute(
                AddRepairActivityDTO(
                    repair_order_id=order.id,
                    description="Too late",
                    labor_hours=Decimal("1"),
                    performed_by_id=uuid.uuid4(),
                    performed_at=datetime.now(tz=UTC),
                    request_id="req-late",
                )
            )


class TestAddRepairPartService:
    def test_adds_part(self) -> None:
        order = _make_order(status=RepairOrderStatus.IN_PROGRESS)
        result = AddRepairPartService(FakeRepairRepository([order])).execute(
            AddRepairPartDTO(
                repair_order_id=order.id,
                material_number="MAT-001",
                quantity=2,
                unit_of_measure="EA",
                request_id="req-part",
            )
        )

        assert len(result.parts) == 1
        assert result.parts[0].material_number == "MAT-001"
        assert result.parts[0].quantity == 2


# ---------------------------------------------------------------------------
# SyncRepairToSAPService
# ---------------------------------------------------------------------------


class TestSyncRepairToSAPService:
    def test_syncs_and_stores_sap_order_number(self) -> None:
        vehicle = _make_vehicle(with_sap=True)
        order = _make_order(vehicle_id=vehicle.id)
        sap = FakeSAPPMOrderPort(order_number="40009999")

        result = SyncRepairToSAPService(
            FakeRepairRepository([order]),
            FakeVehicleRepository([vehicle]),
            _tx_manager(),
            sap,
        ).execute(
            SyncRepairToSAPDTO(
                repair_order_id=order.id,
                order_type="PM01",
                description="Corrective brake repair",
                planned_start=datetime.now(tz=UTC),
                request_id="req-sap",
                requested_by=uuid.uuid4(),
            )
        )

        assert result.sap_order_number == "40009999"
        assert len(sap.calls) == 1
        assert sap.calls[0].equipment_number == "100001"

    def test_raises_when_already_synced(self) -> None:
        vehicle = _make_vehicle(with_sap=True)
        order = _make_order(vehicle_id=vehicle.id)
        order.link_sap_order("40000001")

        with pytest.raises(FMMSConflictError):
            SyncRepairToSAPService(
                FakeRepairRepository([order]),
                FakeVehicleRepository([vehicle]),
                _tx_manager(),
                FakeSAPPMOrderPort(),
            ).execute(
                SyncRepairToSAPDTO(
                    repair_order_id=order.id,
                    order_type="PM01",
                    description="Duplicate",
                    planned_start=datetime.now(tz=UTC),
                    request_id="req-dup",
                    requested_by=uuid.uuid4(),
                )
            )

    def test_raises_when_vehicle_has_no_sap_equipment(self) -> None:
        vehicle = _make_vehicle(with_sap=False)
        order = _make_order(vehicle_id=vehicle.id)

        with pytest.raises(FMMSConflictError):
            SyncRepairToSAPService(
                FakeRepairRepository([order]),
                FakeVehicleRepository([vehicle]),
                _tx_manager(),
                FakeSAPPMOrderPort(),
            ).execute(
                SyncRepairToSAPDTO(
                    repair_order_id=order.id,
                    order_type="PM01",
                    description="No equipment",
                    planned_start=datetime.now(tz=UTC),
                    request_id="req-noeq",
                    requested_by=uuid.uuid4(),
                )
            )


# ---------------------------------------------------------------------------
# Get / List
# ---------------------------------------------------------------------------


class TestGetRepairOrderService:
    def test_returns_existing_order(self) -> None:
        order = _make_order()
        result = GetRepairOrderService(FakeRepairRepository([order])).execute(order.id)

        assert result.id == order.id

    def test_raises_not_found(self) -> None:
        with pytest.raises(FMMSNotFoundError):
            GetRepairOrderService(FakeRepairRepository()).execute(uuid.uuid4())


class TestListRepairOrdersService:
    def test_lists_by_vehicle(self) -> None:
        vehicle_id = uuid.uuid4()
        o1 = _make_order(vehicle_id=vehicle_id)
        o2 = _make_order(vehicle_id=vehicle_id)
        other = _make_order()
        repo = FakeRepairRepository([o1, o2, other])

        results = ListRepairOrdersService(repo).execute(vehicle_id=vehicle_id)

        assert len(results) == 2

    def test_filters_by_status(self) -> None:
        vehicle_id = uuid.uuid4()
        created = _make_order(vehicle_id=vehicle_id)
        assigned = _make_order(vehicle_id=vehicle_id, status=RepairOrderStatus.ASSIGNED)
        repo = FakeRepairRepository([created, assigned])

        results = ListRepairOrdersService(repo).execute(
            vehicle_id=vehicle_id, status=RepairOrderStatus.ASSIGNED
        )

        assert len(results) == 1
        assert results[0].status == RepairOrderStatus.ASSIGNED
