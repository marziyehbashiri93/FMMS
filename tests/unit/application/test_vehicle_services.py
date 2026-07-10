"""Unit tests for Vehicle application services.

All repository and SAP port dependencies are replaced with lightweight
in-memory fakes — no database, no network.

Design choices:
- ``FakeVehicleRepository`` stores entities in a ``dict`` keyed by UUID.
- ``FakeRepairOrderRepository`` allows tests to pre-seed active orders.
- ``FakeSAPEquipmentPort`` returns canned ``SAPEquipmentDTO`` responses.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from apps.fault.domain.entities import Fault, FaultStatus
from apps.fault.domain.exceptions import FaultNotFoundError
from apps.fault.domain.interfaces.fault_repository import IFaultRepository
from apps.fault.domain.value_objects import FaultCode, FaultDescription, FaultSeverity
from apps.repair.domain.entities import RepairOrder, RepairOrderStatus
from apps.repair.domain.interfaces.repair_repository import IRepairOrderRepository
from apps.repair.domain.value_objects import TechnicianAssignment
from apps.vehicle.application.dto.vehicle_dto import (
    ActivateVehicleDTO,
    CreateVehicleDTO,
    DeactivateVehicleDTO,
    UpdateVehicleDTO,
    VehicleResponseDTO,
)
from apps.vehicle.application.services.activate_vehicle_service import (
    ActivateVehicleService,
)
from apps.vehicle.application.services.create_vehicle_service import (
    CreateVehicleService,
)
from apps.vehicle.application.services.deactivate_vehicle_service import (
    DeactivateVehicleService,
)
from apps.vehicle.application.services.get_vehicle_service import (
    GetVehicleService,
    ListVehiclesService,
)
from apps.vehicle.application.services.sync_sap_equipment_service import (
    SyncSAPEquipmentService,
)
from apps.vehicle.application.services.sync_vehicles_from_sap_service import (
    SyncVehiclesFromSAPService,
)
from apps.vehicle.application.services.update_vehicle_service import (
    UpdateVehicleService,
)
from apps.vehicle.domain.entities import Vehicle, VehicleCategory, VehicleStatus
from apps.vehicle.domain.exceptions import VehicleInvalidStateTransitionError
from apps.vehicle.domain.interfaces.vehicle_repository import IVehicleRepository
from apps.vehicle.domain.value_objects import VIN, PlateNumber, SAPEquipmentNumber
from core.exceptions.base_exception import FMMSConflictError, FMMSNotFoundError
from core.sap.dtos.equipment import SAPEquipmentDTO
from core.sap.ports.equipment_port import ISAPEquipmentPort

# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


def _make_vehicle(
    plate: str = "12TEST34",
    vin: str = "1HGCM82633A004352",
    sap_eq: str | None = None,  # must be digits-only per SAPEquipmentNumber VO
    status: VehicleStatus = VehicleStatus.ACTIVE,
) -> Vehicle:
    return Vehicle(
        id=uuid.uuid4(),
        plate_number=PlateNumber(plate),
        vin=VIN(vin),
        make="Toyota",
        model="Hilux",
        year=2022,
        category=VehicleCategory.LIGHT,
        status=status,
        created_at=datetime.now(tz=UTC),
        updated_at=datetime.now(tz=UTC),
        sap_equipment_number=SAPEquipmentNumber(sap_eq) if sap_eq else None,
    )


class FakeVehicleRepository(IVehicleRepository):
    """In-memory repository stub."""

    def __init__(self, initial: list[Vehicle] | None = None) -> None:
        self._store: dict[uuid.UUID, Vehicle] = {v.id: v for v in (initial or [])}

    def get_by_id(self, vehicle_id: uuid.UUID) -> Vehicle | None:
        return self._store.get(vehicle_id)

    def get_by_plate(self, plate_number: PlateNumber) -> Vehicle | None:
        return next(
            (v for v in self._store.values() if v.plate_number == plate_number),
            None,
        )

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
        return self.get_by_plate(plate_number) is not None

    def list_active(self) -> list[Vehicle]:
        return [v for v in self._store.values() if v.status == VehicleStatus.ACTIVE]

    def list_by_status(self, status: VehicleStatus) -> list[Vehicle]:
        return [v for v in self._store.values() if v.status == status]

    def save(self, vehicle: Vehicle) -> Vehicle:
        self._store[vehicle.id] = vehicle
        return vehicle

    def delete(self, vehicle_id: uuid.UUID) -> None:
        self._store.pop(vehicle_id, None)


class FakeRepairOrderRepository(IRepairOrderRepository):
    """In-memory repair order stub with configurable active order list."""

    def __init__(self, initial: list[RepairOrder] | None = None) -> None:
        self._store: dict[uuid.UUID, RepairOrder] = {
            order.id: order for order in (initial or [])
        }

    def get_by_id(self, order_id: uuid.UUID):  # type: ignore[override]
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

    def list_by_fault(self, fault_id: uuid.UUID):  # type: ignore[override]
        return [o for o in self._store.values() if o.fault_id == fault_id]

    def list_active_by_vehicle(self, vehicle_id: uuid.UUID) -> list:
        return [o for o in self._store.values() if o.vehicle_id == vehicle_id and o.is_active]

    def has_open_repair_order_for_vehicle(self, vehicle_id: uuid.UUID) -> bool:
        return bool(self.list_active_by_vehicle(vehicle_id))

    def save(self, order):  # type: ignore[override]
        self._store[order.id] = order
        return order

    def delete(self, order_id: uuid.UUID) -> None:
        self._store.pop(order_id, None)


class FakeFaultRepository(IFaultRepository):
    """In-memory fault repository stub."""

    def __init__(self, initial: list[Fault] | None = None) -> None:
        self._store: dict[uuid.UUID, Fault] = {f.id: f for f in (initial or [])}

    def get_by_id(self, fault_id: uuid.UUID) -> Fault:
        fault = self._store.get(fault_id)
        if fault is None:
            raise FaultNotFoundError(fault_id)
        return fault

    def list_by_vehicle(
        self,
        vehicle_id: uuid.UUID,
        status: FaultStatus | None = None,
    ) -> list[Fault]:
        faults = [f for f in self._store.values() if f.vehicle_id == vehicle_id]
        if status is not None:
            faults = [f for f in faults if f.status == status]
        return faults

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


class FakeSAPEquipmentPort(ISAPEquipmentPort):
    """Returns canned SAP equipment DTO(s)."""

    def __init__(
        self,
        dto: SAPEquipmentDTO | None = None,
        equipment: list[SAPEquipmentDTO] | None = None,
    ) -> None:
        self._dto = dto
        self._equipment = equipment or ([dto] if dto is not None else [])

    def get_equipment(self, equipment_number: str) -> SAPEquipmentDTO:
        if self._dto is not None and self._dto.equipment_number == equipment_number:
            return self._dto
        for item in self._equipment:
            if item.equipment_number == equipment_number:
                return item
        return self._equipment[0]

    def list_equipment(self, plant: str | None = None) -> list[SAPEquipmentDTO]:
        return list(self._equipment)


# ---------------------------------------------------------------------------
# CreateVehicleService
# ---------------------------------------------------------------------------


class TestCreateVehicleService:
    def _dto(self, plate: str = "NEWPLATE1") -> CreateVehicleDTO:
        return CreateVehicleDTO(
            plate_number=plate,
            vin="1HGCM82633A004352",
            make="Toyota",
            model="Hilux",
            year=2022,
            category=VehicleCategory.LIGHT,
            request_id="req-001",
            created_by=uuid.uuid4(),
        )

    def test_creates_vehicle_and_returns_response_dto(self) -> None:
        repo = FakeVehicleRepository()
        service = CreateVehicleService(repo)

        result = service.execute(self._dto())

        assert isinstance(result, VehicleResponseDTO)
        assert result.plate_number == "NEWPLATE1"
        assert result.status == VehicleStatus.ACTIVE

    def test_persists_vehicle_in_repository(self) -> None:
        repo = FakeVehicleRepository()
        service = CreateVehicleService(repo)

        result = service.execute(self._dto())

        assert repo.get_by_id(result.id) is not None

    def test_raises_conflict_on_duplicate_plate(self) -> None:
        existing = _make_vehicle(plate="DUPPLATE1")
        repo = FakeVehicleRepository(initial=[existing])
        service = CreateVehicleService(repo)

        with pytest.raises(FMMSConflictError):
            service.execute(self._dto(plate="DUPPLATE1"))

    def test_optional_fields_are_none_by_default(self) -> None:
        repo = FakeVehicleRepository()
        result = CreateVehicleService(repo).execute(self._dto())

        assert result.chassis_number is None
        assert result.sap_equipment_number is None

    def test_sap_equipment_number_stored_when_provided(self) -> None:
        repo = FakeVehicleRepository()
        dto = CreateVehicleDTO(
            plate_number="SAPPLATE2",
            vin="1HGCM82633A004352",
            make="Toyota",
            model="Hilux",
            year=2022,
            category=VehicleCategory.LIGHT,
            request_id="req-sap",
            created_by=uuid.uuid4(),
            sap_equipment_number="9999",
        )
        result = CreateVehicleService(repo).execute(dto)

        assert result.sap_equipment_number == "9999"


# ---------------------------------------------------------------------------
# UpdateVehicleService
# ---------------------------------------------------------------------------


class TestUpdateVehicleService:
    def test_updates_make_and_model(self) -> None:
        vehicle = _make_vehicle()
        repo = FakeVehicleRepository(initial=[vehicle])
        service = UpdateVehicleService(repo)

        result = service.execute(
            UpdateVehicleDTO(
                vehicle_id=vehicle.id,
                request_id="req-upd",
                updated_by=uuid.uuid4(),
                make="Ford",
                model="Ranger",
            )
        )

        assert result.make == "Ford"
        assert result.model == "Ranger"

    def test_only_provided_fields_change(self) -> None:
        vehicle = _make_vehicle()
        repo = FakeVehicleRepository(initial=[vehicle])
        original_year = vehicle.year

        result = UpdateVehicleService(repo).execute(
            UpdateVehicleDTO(
                vehicle_id=vehicle.id,
                request_id="req-partial",
                updated_by=uuid.uuid4(),
                make="Nissan",
            )
        )

        assert result.make == "Nissan"
        assert result.year == original_year

    def test_raises_not_found_for_missing_vehicle(self) -> None:
        repo = FakeVehicleRepository()
        service = UpdateVehicleService(repo)

        with pytest.raises(FMMSNotFoundError):
            service.execute(
                UpdateVehicleDTO(
                    vehicle_id=uuid.uuid4(),
                    request_id="req-missing",
                    updated_by=uuid.uuid4(),
                    make="Ghost",
                )
            )


# ---------------------------------------------------------------------------
# DeactivateVehicleService
# ---------------------------------------------------------------------------


class TestDeactivateVehicleService:
    def _make_service(
        self,
        vehicle: Vehicle,
    ) -> DeactivateVehicleService:
        return DeactivateVehicleService(
            vehicle_repository=FakeVehicleRepository(initial=[vehicle]),
        )

    def test_deactivates_vehicle(self) -> None:
        vehicle = _make_vehicle()
        service = self._make_service(vehicle)

        result = service.execute(
            DeactivateVehicleDTO(
                vehicle_id=vehicle.id,
                request_id="req-deact-repair",
                requested_by=uuid.uuid4(),
            )
        )

        assert result.status == VehicleStatus.INACTIVE

    def test_raises_not_found_for_missing_vehicle(self) -> None:
        repo = FakeVehicleRepository()
        service = DeactivateVehicleService(vehicle_repository=repo)

        with pytest.raises(FMMSNotFoundError):
            service.execute(
                DeactivateVehicleDTO(
                    vehicle_id=uuid.uuid4(),
                    request_id="req-ghost",
                    requested_by=uuid.uuid4(),
                )
            )

    def test_raises_state_error_when_already_inactive(self) -> None:
        vehicle = _make_vehicle(status=VehicleStatus.INACTIVE)
        service = self._make_service(vehicle)

        with pytest.raises(VehicleInvalidStateTransitionError):
            service.execute(
                DeactivateVehicleDTO(
                    vehicle_id=vehicle.id,
                    request_id="req-already",
                    requested_by=uuid.uuid4(),
                )
            )


# ---------------------------------------------------------------------------
# GetVehicleService
# ---------------------------------------------------------------------------


class TestGetVehicleService:
    def test_returns_dto_for_existing_vehicle(self) -> None:
        vehicle = _make_vehicle()
        repo = FakeVehicleRepository(initial=[vehicle])

        result = GetVehicleService(repo).execute(vehicle.id, request_id="req-get")

        assert result.id == vehicle.id
        assert result.plate_number == vehicle.plate_number.value

    def test_raises_not_found_for_missing_vehicle(self) -> None:
        repo = FakeVehicleRepository()

        with pytest.raises(FMMSNotFoundError):
            GetVehicleService(repo).execute(uuid.uuid4())


class TestListVehiclesService:
    def test_lists_active_vehicles_by_default(self) -> None:
        active = _make_vehicle(plate="ACTIVE001", status=VehicleStatus.ACTIVE)
        inactive = _make_vehicle(plate="INACT0001", status=VehicleStatus.INACTIVE)
        repo = FakeVehicleRepository(initial=[active, inactive])

        results = ListVehiclesService(repo).execute()

        assert len(results) == 1
        assert results[0].plate_number == "ACTIVE001"

    def test_filters_by_status(self) -> None:
        v1 = _make_vehicle(plate="ACT00001", status=VehicleStatus.ACTIVE)
        v2 = _make_vehicle(
            plate="SUSPENDED", vin="2HGCM82633A004352", status=VehicleStatus.SUSPENDED
        )
        repo = FakeVehicleRepository(initial=[v1, v2])

        results = ListVehiclesService(repo).execute(status=VehicleStatus.SUSPENDED)

        assert len(results) == 1
        assert results[0].status == VehicleStatus.SUSPENDED

    def test_returns_empty_list_when_none_match(self) -> None:
        repo = FakeVehicleRepository()

        results = ListVehiclesService(repo).execute()

        assert results == []


# ---------------------------------------------------------------------------
# SyncSAPEquipmentService
# ---------------------------------------------------------------------------


class TestSyncSAPEquipmentService:
    def _sap_dto(
        self, equipment_number: str, description: str = "Synced Model"
    ) -> SAPEquipmentDTO:
        return SAPEquipmentDTO(
            equipment_number=equipment_number,
            description=description,
            plant="1000",
        )

    def test_updates_model_from_sap_description(self) -> None:
        vehicle = _make_vehicle(plate="SAPVEH001", sap_eq="100001")
        repo = FakeVehicleRepository(initial=[vehicle])
        sap_port = FakeSAPEquipmentPort(
            self._sap_dto("100001", description="Ranger XL")
        )

        result = SyncSAPEquipmentService(repo, sap_port).execute(
            "100001", request_id="req-sync"
        )

        assert result.model == "Ranger XL"

    def test_raises_not_found_when_no_vehicle_linked(self) -> None:
        repo = FakeVehicleRepository()
        sap_port = FakeSAPEquipmentPort(self._sap_dto("999999"))

        with pytest.raises(FMMSNotFoundError):
            SyncSAPEquipmentService(repo, sap_port).execute("999999")


# ---------------------------------------------------------------------------
# SyncVehiclesFromSAPService (bulk)
# ---------------------------------------------------------------------------


class TestSyncVehiclesFromSAPService:
    def test_creates_vehicles_from_sap_equipment(self) -> None:
        repo = FakeVehicleRepository()
        sap_port = FakeSAPEquipmentPort(
            equipment=[
                SAPEquipmentDTO(
                    equipment_number="10000001",
                    description="Fleet Vehicle — Toyota Land Cruiser",
                    plant="P001",
                    serial_number="SN-LC-001",
                    category="F",
                ),
                SAPEquipmentDTO(
                    equipment_number="10000002",
                    description="Fleet Vehicle — Isuzu D-Max",
                    plant="P001",
                    category="F",
                ),
            ]
        )

        result = SyncVehiclesFromSAPService(repo, sap_port).execute(
            request_id="req-bulk"
        )

        assert result.total_received == 2
        assert result.created == 2
        assert result.updated == 0
        assert result.failed == 0
        assert len(repo.list_active()) == 2

    def test_updates_existing_vehicle_by_sap_equipment_number(self) -> None:
        vehicle = _make_vehicle(plate="EQ10000001", sap_eq="10000001")
        vehicle.model = "Old"
        repo = FakeVehicleRepository(initial=[vehicle])
        sap_port = FakeSAPEquipmentPort(
            equipment=[
                SAPEquipmentDTO(
                    equipment_number="10000001",
                    description="Fleet Vehicle — Toyota Land Cruiser",
                    plant="P001",
                    category="F",
                )
            ]
        )

        result = SyncVehiclesFromSAPService(repo, sap_port).execute()

        assert result.created == 0
        assert result.updated == 1
        assert result.failed == 0
        assert repo.get_by_id(vehicle.id).model == "Land Cruiser"

    def test_sync_is_idempotent(self) -> None:
        repo = FakeVehicleRepository()
        sap_port = FakeSAPEquipmentPort(
            equipment=[
                SAPEquipmentDTO(
                    equipment_number="10000001",
                    description="Fleet Vehicle — Toyota Land Cruiser",
                    plant="P001",
                    category="F",
                )
            ]
        )
        service = SyncVehiclesFromSAPService(repo, sap_port)

        first = service.execute()
        second = service.execute()

        assert first.created == 1
        assert second.created == 0
        assert second.updated == 1
        assert len(repo.list_active()) == 1


# ---------------------------------------------------------------------------
# ActivateVehicleService
# ---------------------------------------------------------------------------


def _make_fault(
    vehicle_id: uuid.UUID,
    *,
    status: FaultStatus = FaultStatus.OPEN,
) -> Fault:
    now = datetime.now(tz=UTC)
    return Fault(
        id=uuid.uuid4(),
        vehicle_id=vehicle_id,
        code=FaultCode("BRK-01"),
        description=FaultDescription("Brake pad wear"),
        severity=FaultSeverity.MEDIUM,
        status=status,
        reported_by_id=uuid.uuid4(),
        reported_at=now,
        created_at=now,
        updated_at=now,
    )


def _make_completed_order(*, vehicle_id: uuid.UUID, fault_id: uuid.UUID) -> RepairOrder:
    now = datetime.now(tz=UTC)
    order = RepairOrder(
        id=uuid.uuid4(),
        vehicle_id=vehicle_id,
        fault_id=fault_id,
        status=RepairOrderStatus.CREATED,
        created_by_id=uuid.uuid4(),
        created_at=now,
        updated_at=now,
    )
    order.assign_technician(
        TechnicianAssignment(technician_id=uuid.uuid4(), assigned_at=now)
    )
    order.start_work()
    order.complete(completed_at=now)
    return order


class TestActivateVehicleService:
    def _service(
        self,
        vehicle: Vehicle,
        *,
        repair_orders: list[RepairOrder] | None = None,
        faults: list[Fault] | None = None,
    ) -> ActivateVehicleService:
        return ActivateVehicleService(
            vehicle_repository=FakeVehicleRepository(initial=[vehicle]),
            repair_order_repository=FakeRepairOrderRepository(repair_orders),
            fault_repository=FakeFaultRepository(faults),
        )

    def _dto(self, vehicle_id: uuid.UUID) -> ActivateVehicleDTO:
        return ActivateVehicleDTO(
            vehicle_id=vehicle_id,
            request_id="req-activate",
            requested_by=uuid.uuid4(),
        )

    def test_closes_open_fault_linked_to_completed_repair(self) -> None:
        vehicle = _make_vehicle(status=VehicleStatus.INACTIVE)
        fault = _make_fault(vehicle.id, status=FaultStatus.OPEN)
        order = _make_completed_order(vehicle_id=vehicle.id, fault_id=fault.id)
        fault_repo = FakeFaultRepository([fault])
        service = ActivateVehicleService(
            FakeVehicleRepository([vehicle]),
            FakeRepairOrderRepository([order]),
            fault_repo,
        )

        result = service.execute(self._dto(vehicle.id))

        assert result.status == VehicleStatus.ACTIVE
        assert fault_repo.get_by_id(fault.id).status == FaultStatus.CLOSED

    def test_skips_already_closed_fault_idempotently(self) -> None:
        vehicle = _make_vehicle(status=VehicleStatus.INACTIVE)
        fault = _make_fault(vehicle.id, status=FaultStatus.CLOSED)
        order = _make_completed_order(vehicle_id=vehicle.id, fault_id=fault.id)
        fault_repo = FakeFaultRepository([fault])
        service = self._service(vehicle, repair_orders=[order], faults=[fault])

        result = service.execute(self._dto(vehicle.id))

        assert result.status == VehicleStatus.ACTIVE
        assert fault_repo.get_by_id(fault.id).status == FaultStatus.CLOSED

    def test_closes_assigned_fault_via_in_repair_transition(self) -> None:
        vehicle = _make_vehicle(status=VehicleStatus.INACTIVE)
        fault = _make_fault(vehicle.id, status=FaultStatus.ASSIGNED)
        order = _make_completed_order(vehicle_id=vehicle.id, fault_id=fault.id)
        fault_repo = FakeFaultRepository([fault])
        service = self._service(vehicle, repair_orders=[order], faults=[fault])

        service.execute(self._dto(vehicle.id))

        assert fault_repo.get_by_id(fault.id).status == FaultStatus.CLOSED

    def test_raises_conflict_when_active_repair_orders_exist(self) -> None:
        vehicle = _make_vehicle(status=VehicleStatus.INACTIVE)
        fault = _make_fault(vehicle.id)
        active_order = RepairOrder(
            id=uuid.uuid4(),
            vehicle_id=vehicle.id,
            fault_id=fault.id,
            status=RepairOrderStatus.IN_PROGRESS,
            created_by_id=uuid.uuid4(),
            created_at=datetime.now(tz=UTC),
            updated_at=datetime.now(tz=UTC),
        )
        service = self._service(
            vehicle,
            repair_orders=[active_order],
            faults=[fault],
        )

        with pytest.raises(FMMSConflictError):
            service.execute(self._dto(vehicle.id))

    def test_returns_early_when_vehicle_already_active(self) -> None:
        vehicle = _make_vehicle(status=VehicleStatus.ACTIVE)
        fault = _make_fault(vehicle.id, status=FaultStatus.OPEN)
        order = _make_completed_order(vehicle_id=vehicle.id, fault_id=fault.id)
        fault_repo = FakeFaultRepository([fault])
        service = self._service(vehicle, repair_orders=[order], faults=[fault])

        result = service.execute(self._dto(vehicle.id))

        assert result.status == VehicleStatus.ACTIVE
        assert fault_repo.get_by_id(fault.id).status == FaultStatus.OPEN
