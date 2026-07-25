"""Integration tests for DjangoFaultRepository."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from apps.fault.domain.entities import Fault, FaultItem, FaultStatus
from apps.fault.domain.exceptions import FaultNotFoundError
from apps.fault.domain.interfaces.fault_repository import IFaultRepository
from apps.fault.domain.value_objects import (
    FaultCode,
    FaultDescription,
    FaultSeverity,
    SAPDefectCode,
)
from apps.fault.infrastructure.repositories import DjangoFaultRepository

pytestmark = pytest.mark.django_db


def _make_fault(
    severity: FaultSeverity = FaultSeverity.MEDIUM,
    status: FaultStatus = FaultStatus.OPEN,
    vehicle_id: uuid.UUID | None = None,
    inspection_id: uuid.UUID | None = None,
) -> Fault:
    repo = DjangoFaultRepository()
    now = datetime.now(tz=UTC)
    fault = Fault(
        id=uuid.uuid4(),
        vehicle_id=vehicle_id or uuid.uuid4(),
        code=FaultCode("ENG001"),
        description=FaultDescription("Engine oil leak detected"),
        severity=severity,
        status=status,
        reported_by_id=uuid.uuid4(),
        reported_at=now,
        inspection_id=inspection_id,
        created_at=now,
        updated_at=now,
    )
    return repo.save(fault)


class TestInterface:
    def test_satisfies_interface(self) -> None:
        assert isinstance(DjangoFaultRepository(), IFaultRepository)


class TestSaveAndRetrieve:
    def test_save_and_get_by_id(self) -> None:
        repo = DjangoFaultRepository()
        fault = _make_fault()
        fetched = repo.get_by_id(fault.id)
        assert fetched.id == fault.id
        assert fetched.severity == FaultSeverity.MEDIUM
        assert fetched.description.value == "Engine oil leak detected"

    def test_get_by_id_not_found(self) -> None:
        repo = DjangoFaultRepository()
        with pytest.raises(FaultNotFoundError):
            repo.get_by_id(uuid.uuid4())

    def test_update_status(self) -> None:
        repo = DjangoFaultRepository()
        fault = _make_fault()
        fault.mark_awaiting_transport()
        repo.save(fault)
        fetched = repo.get_by_id(fault.id)
        assert fetched.status == FaultStatus.AWAITING_TRANSPORT

    def test_sap_fields_persisted(self) -> None:
        repo = DjangoFaultRepository()
        fault = _make_fault()
        fault.sap_defect_code = SAPDefectCode("AB001")
        fault.sap_notification_number = "40001234"
        repo.save(fault)
        fetched = repo.get_by_id(fault.id)
        assert fetched.sap_defect_code is not None
        assert fetched.sap_defect_code.value == "AB001"
        assert fetched.sap_notification_number == "40001234"

    def test_save_and_load_fault_items(self) -> None:
        repo = DjangoFaultRepository()
        now = datetime.now(tz=UTC)
        fault_id = uuid.uuid4()
        fault = Fault(
            id=fault_id,
            vehicle_id=uuid.uuid4(),
            code=FaultCode("INSP-FAIL"),
            description=FaultDescription("Multiple inspection failures"),
            severity=FaultSeverity.MEDIUM,
            status=FaultStatus.OPEN,
            reported_by_id=uuid.uuid4(),
            reported_at=now,
            created_at=now,
            updated_at=now,
            items=[
                FaultItem(
                    id=uuid.uuid4(),
                    fault_id=fault_id,
                    inspection_item_id=uuid.uuid4(),
                    component="Front light",
                    description="Broken",
                    severity=FaultSeverity.MEDIUM,
                    created_at=now,
                    updated_at=now,
                ),
                FaultItem(
                    id=uuid.uuid4(),
                    fault_id=fault_id,
                    inspection_item_id=uuid.uuid4(),
                    component="Refrigerator",
                    description="Cooling failure",
                    severity=FaultSeverity.MEDIUM,
                    created_at=now,
                    updated_at=now,
                ),
            ],
        )
        repo.save(fault)
        fetched = repo.get_by_id(fault.id)
        assert len(fetched.items) == 2
        assert fetched.items[0].component == "Front light"
        assert fetched.items[1].component == "Refrigerator"


class TestListOperations:
    def test_list_by_vehicle(self) -> None:
        repo = DjangoFaultRepository()
        vid = uuid.uuid4()
        _make_fault(vehicle_id=vid)
        _make_fault(vehicle_id=vid)
        _make_fault()
        result = repo.list_by_vehicle(vid)
        assert len(result) == 2

    def test_list_by_vehicle_status_filter(self) -> None:
        repo = DjangoFaultRepository()
        vid = uuid.uuid4()
        _make_fault(vehicle_id=vid, status=FaultStatus.OPEN)
        fault_ip = _make_fault(vehicle_id=vid, status=FaultStatus.OPEN)
        fault_ip.mark_awaiting_transport()
        repo.save(fault_ip)
        open_faults = repo.list_by_vehicle(vid, status=FaultStatus.OPEN)
        assert all(f.status == FaultStatus.OPEN for f in open_faults)

    def test_list_open_by_severity(self) -> None:
        repo = DjangoFaultRepository()
        _make_fault(severity=FaultSeverity.CRITICAL)
        _make_fault(severity=FaultSeverity.LOW)
        critical = repo.list_open_by_severity(FaultSeverity.CRITICAL)
        assert all(f.severity == FaultSeverity.CRITICAL for f in critical)
        assert len(critical) >= 1

    def test_list_by_inspection(self) -> None:
        repo = DjangoFaultRepository()
        insp_id = uuid.uuid4()
        _make_fault(inspection_id=insp_id)
        _make_fault(inspection_id=insp_id)
        _make_fault()
        result = repo.list_by_inspection(insp_id)
        assert len(result) == 2


class TestSoftDelete:
    def test_delete_hides_fault(self) -> None:
        repo = DjangoFaultRepository()
        fault = _make_fault()
        repo.delete(fault.id)
        with pytest.raises(FaultNotFoundError):
            repo.get_by_id(fault.id)

    def test_delete_nonexistent_raises(self) -> None:
        repo = DjangoFaultRepository()
        with pytest.raises(FaultNotFoundError):
            repo.delete(uuid.uuid4())
