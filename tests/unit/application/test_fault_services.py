"""Unit tests for Fault application services.

All dependencies are replaced with in-memory fakes — no DB, no network.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from apps.fault.application.dto.fault_dto import (
    AssignFaultDTO,
    CloseFaultDTO,
    FaultResponseDTO,
    ReportFaultDTO,
)
from apps.fault.application.services.assign_fault_service import AssignFaultService
from apps.fault.application.services.close_fault_service import CloseFaultService
from apps.fault.application.services.get_fault_service import (
    GetFaultService,
    ListFaultsService,
)
from apps.fault.application.services.report_fault_service import ReportFaultService
from apps.fault.domain.entities import Fault, FaultStatus
from apps.fault.domain.exceptions import (
    FaultAlreadyClosedError,
    FaultInvalidStateTransitionError,
)
from apps.fault.domain.interfaces.fault_repository import IFaultRepository
from apps.fault.domain.value_objects import FaultCode, FaultDescription, FaultSeverity
from apps.vehicle.domain.entities import Vehicle, VehicleCategory, VehicleStatus
from apps.vehicle.domain.interfaces.vehicle_repository import IVehicleRepository
from apps.vehicle.domain.value_objects import VIN, PlateNumber, SAPEquipmentNumber
from core.exceptions.base_exception import FMMSNotFoundError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_vehicle() -> Vehicle:
    return Vehicle(
        id=uuid.uuid4(),
        plate_number=PlateNumber("FLTPLT01"),
        vin=VIN("1HGCM82633A004352"),
        make="Toyota",
        model="Hilux",
        year=2022,
        category=VehicleCategory.LIGHT,
        status=VehicleStatus.ACTIVE,
        created_at=datetime.now(tz=UTC),
        updated_at=datetime.now(tz=UTC),
    )


def _make_fault(
    vehicle_id: uuid.UUID | None = None,
    status: FaultStatus = FaultStatus.OPEN,
    severity: FaultSeverity = FaultSeverity.MEDIUM,
) -> Fault:
    now = datetime.now(tz=UTC)
    return Fault(
        id=uuid.uuid4(),
        vehicle_id=vehicle_id or uuid.uuid4(),
        code=FaultCode("BRK-01"),
        description=FaultDescription("Brake pad wear"),
        severity=severity,
        status=status,
        reported_by_id=uuid.uuid4(),
        reported_at=now,
        created_at=now,
        updated_at=now,
    )


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeFaultRepository(IFaultRepository):
    def __init__(self, initial: list[Fault] | None = None) -> None:
        self._store: dict[uuid.UUID, Fault] = {f.id: f for f in (initial or [])}

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


# ---------------------------------------------------------------------------
# ReportFaultService
# ---------------------------------------------------------------------------


class TestReportFaultService:
    def _service(self, vehicle: Vehicle) -> ReportFaultService:
        return ReportFaultService(
            fault_repository=FakeFaultRepository(),
            vehicle_repository=FakeVehicleRepository(initial=[vehicle]),
        )

    def _dto(self, vehicle_id: uuid.UUID) -> ReportFaultDTO:
        return ReportFaultDTO(
            vehicle_id=vehicle_id,
            code="ENG-001",
            description="Engine oil pressure low",
            severity=FaultSeverity.HIGH,
            request_id="req-fault-001",
            reported_by=uuid.uuid4(),
        )

    def test_reports_fault_in_open_status(self) -> None:
        vehicle = _make_vehicle()
        result = self._service(vehicle).execute(self._dto(vehicle.id))

        assert isinstance(result, FaultResponseDTO)
        assert result.status == FaultStatus.OPEN
        assert result.vehicle_id == vehicle.id

    def test_code_is_normalised_to_uppercase(self) -> None:
        vehicle = _make_vehicle()
        result = self._service(vehicle).execute(self._dto(vehicle.id))

        assert result.code == "ENG-001"

    def test_raises_not_found_for_missing_vehicle(self) -> None:
        service = ReportFaultService(
            fault_repository=FakeFaultRepository(),
            vehicle_repository=FakeVehicleRepository(),
        )

        with pytest.raises(FMMSNotFoundError):
            service.execute(
                ReportFaultDTO(
                    vehicle_id=uuid.uuid4(),
                    code="ENG-001",
                    description="No vehicle",
                    severity=FaultSeverity.LOW,
                    request_id="req-noveh",
                    reported_by=uuid.uuid4(),
                )
            )

    def test_optional_inspection_id_stored(self) -> None:
        vehicle = _make_vehicle()
        insp_id = uuid.uuid4()
        dto = ReportFaultDTO(
            vehicle_id=vehicle.id,
            code="BRK-01",
            description="Brake failure detected during inspection",
            severity=FaultSeverity.CRITICAL,
            request_id="req-insp",
            reported_by=uuid.uuid4(),
            inspection_id=insp_id,
        )
        result = self._service(vehicle).execute(dto)

        assert result.inspection_id == insp_id


# ---------------------------------------------------------------------------
# AssignFaultService
# ---------------------------------------------------------------------------


class TestAssignFaultService:
    def test_assigns_open_fault_to_technician(self) -> None:
        fault = _make_fault()
        repo = FakeFaultRepository(initial=[fault])
        technician_id = uuid.uuid4()

        result = AssignFaultService(repo).execute(
            AssignFaultDTO(
                fault_id=fault.id,
                technician_id=technician_id,
                request_id="req-assign",
                assigned_by=uuid.uuid4(),
            )
        )

        assert result.status == FaultStatus.ASSIGNED
        assert result.assigned_to_id == technician_id

    def test_raises_not_found_for_missing_fault(self) -> None:
        repo = FakeFaultRepository()
        with pytest.raises(FMMSNotFoundError):
            AssignFaultService(repo).execute(
                AssignFaultDTO(
                    fault_id=uuid.uuid4(),
                    technician_id=uuid.uuid4(),
                    request_id="req-ghost",
                    assigned_by=uuid.uuid4(),
                )
            )

    def test_raises_state_error_when_already_assigned(self) -> None:
        fault = _make_fault(status=FaultStatus.ASSIGNED)
        repo = FakeFaultRepository(initial=[fault])

        with pytest.raises(FaultInvalidStateTransitionError):
            AssignFaultService(repo).execute(
                AssignFaultDTO(
                    fault_id=fault.id,
                    technician_id=uuid.uuid4(),
                    request_id="req-re-assign",
                    assigned_by=uuid.uuid4(),
                )
            )

    def test_raises_already_closed_when_closed(self) -> None:
        fault = _make_fault(status=FaultStatus.CLOSED)
        repo = FakeFaultRepository(initial=[fault])

        with pytest.raises(FaultAlreadyClosedError):
            AssignFaultService(repo).execute(
                AssignFaultDTO(
                    fault_id=fault.id,
                    technician_id=uuid.uuid4(),
                    request_id="req-closed",
                    assigned_by=uuid.uuid4(),
                )
            )


# ---------------------------------------------------------------------------
# CloseFaultService
# ---------------------------------------------------------------------------


class TestCloseFaultService:
    def test_closes_open_fault(self) -> None:
        fault = _make_fault()
        repo = FakeFaultRepository(initial=[fault])

        result = CloseFaultService(repo).execute(
            CloseFaultDTO(
                fault_id=fault.id,
                request_id="req-close",
                closed_by=uuid.uuid4(),
            )
        )

        assert result.status == FaultStatus.CLOSED

    def test_raises_not_found_for_missing_fault(self) -> None:
        repo = FakeFaultRepository()
        with pytest.raises(FMMSNotFoundError):
            CloseFaultService(repo).execute(
                CloseFaultDTO(
                    fault_id=uuid.uuid4(),
                    request_id="req-ghost",
                    closed_by=uuid.uuid4(),
                )
            )

    def test_raises_already_closed_when_closing_closed_fault(self) -> None:
        fault = _make_fault(status=FaultStatus.CLOSED)
        repo = FakeFaultRepository(initial=[fault])

        with pytest.raises(FaultAlreadyClosedError):
            CloseFaultService(repo).execute(
                CloseFaultDTO(
                    fault_id=fault.id,
                    request_id="req-re-close",
                    closed_by=uuid.uuid4(),
                )
            )

    def test_closes_fault_in_repair(self) -> None:
        fault = _make_fault(status=FaultStatus.IN_REPAIR)
        repo = FakeFaultRepository(initial=[fault])

        result = CloseFaultService(repo).execute(
            CloseFaultDTO(
                fault_id=fault.id,
                request_id="req-close-repair",
                closed_by=uuid.uuid4(),
            )
        )

        assert result.status == FaultStatus.CLOSED


# ---------------------------------------------------------------------------
# GetFaultService / ListFaultsService
# ---------------------------------------------------------------------------


class TestGetFaultService:
    def test_returns_dto_for_existing_fault(self) -> None:
        fault = _make_fault()
        repo = FakeFaultRepository(initial=[fault])

        result = GetFaultService(repo).execute(fault.id, request_id="req-get")

        assert result.id == fault.id
        assert result.code == "BRK-01"

    def test_raises_not_found_for_missing_fault(self) -> None:
        repo = FakeFaultRepository()
        with pytest.raises(FMMSNotFoundError):
            GetFaultService(repo).execute(uuid.uuid4())


class TestListFaultsService:
    def test_lists_faults_by_vehicle(self) -> None:
        vehicle_id = uuid.uuid4()
        f1 = _make_fault(vehicle_id=vehicle_id)
        f2 = _make_fault(vehicle_id=vehicle_id)
        other = _make_fault()
        repo = FakeFaultRepository(initial=[f1, f2, other])

        results = ListFaultsService(repo).execute(vehicle_id=vehicle_id)

        assert len(results) == 2

    def test_lists_open_faults_by_severity(self) -> None:
        critical = _make_fault(severity=FaultSeverity.CRITICAL)
        medium = _make_fault(severity=FaultSeverity.MEDIUM)
        closed_critical = _make_fault(
            severity=FaultSeverity.CRITICAL, status=FaultStatus.CLOSED
        )
        repo = FakeFaultRepository(initial=[critical, medium, closed_critical])

        results = ListFaultsService(repo).execute(
            open_by_severity=FaultSeverity.CRITICAL
        )

        assert len(results) == 1
        assert results[0].severity == FaultSeverity.CRITICAL

    def test_returns_empty_list_when_no_filter_provided(self) -> None:
        fault = _make_fault()
        repo = FakeFaultRepository(initial=[fault])

        results = ListFaultsService(repo).execute()

        assert results == []
