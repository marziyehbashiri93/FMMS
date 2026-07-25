"""Unit tests for the Fault domain layer."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from apps.fault.domain.entities import Fault, FaultStatus
from apps.fault.domain.exceptions import (
    FaultAlreadyClosedError,
    FaultInvalidStateTransitionError,
    FaultNotFoundError,
)
from apps.fault.domain.value_objects import (
    FaultCode,
    FaultDescription,
    FaultSeverity,
    SAPDefectCode,
)


def _make_fault(**kwargs: object) -> Fault:
    defaults: dict[str, object] = {
        "id": uuid.uuid4(),
        "vehicle_id": uuid.uuid4(),
        "code": FaultCode("ENG001"),
        "description": FaultDescription("Engine oil leak detected."),
        "severity": FaultSeverity.HIGH,
        "status": FaultStatus.OPEN,
        "reported_by_id": uuid.uuid4(),
        "reported_at": datetime.now(tz=UTC),
        "created_at": datetime.now(tz=UTC),
        "updated_at": datetime.now(tz=UTC),
    }
    defaults.update(kwargs)
    return Fault(**defaults)  # type: ignore[arg-type]


class TestFaultCode:
    def test_valid_code(self) -> None:
        assert FaultCode("ENG001").value == "ENG001"

    def test_normalised_to_uppercase(self) -> None:
        assert FaultCode("eng001").value == "ENG001"

    def test_too_short(self) -> None:
        with pytest.raises(ValueError):
            FaultCode("AB")

    def test_too_long(self) -> None:
        with pytest.raises(ValueError):
            FaultCode("A" * 21)

    def test_with_hyphen(self) -> None:
        assert FaultCode("BRK-01").value == "BRK-01"


class TestFaultDescription:
    def test_valid(self) -> None:
        d = FaultDescription("Oil leak.")
        assert d.value == "Oil leak."

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            FaultDescription("   ")

    def test_too_long_raises(self) -> None:
        with pytest.raises(ValueError, match="500"):
            FaultDescription("x" * 501)


class TestSAPDefectCode:
    def test_valid(self) -> None:
        assert SAPDefectCode("DFCT001").value == "DFCT001"

    def test_too_long_raises(self) -> None:
        with pytest.raises(ValueError):
            SAPDefectCode("x" * 31)


class TestFaultEntityLifecycle:
    def test_initial_state(self) -> None:
        f = _make_fault()
        assert f.status == FaultStatus.OPEN
        assert f.is_open is True

    def test_mark_awaiting_transport(self) -> None:
        f = _make_fault()
        f.mark_awaiting_transport()
        assert f.status == FaultStatus.AWAITING_TRANSPORT

    def test_assign(self) -> None:
        f = _make_fault(status=FaultStatus.AWAITING_TRANSPORT)
        tech_id = uuid.uuid4()
        f.assign(tech_id)
        assert f.status == FaultStatus.ASSIGNED
        assert f.assigned_to_id == tech_id

    def test_assign_from_open_is_invalid(self) -> None:
        f = _make_fault(status=FaultStatus.OPEN)
        with pytest.raises(FaultInvalidStateTransitionError):
            f.assign(uuid.uuid4())

    def test_start_repair(self) -> None:
        f = _make_fault(status=FaultStatus.ASSIGNED)
        f.start_repair()
        assert f.status == FaultStatus.IN_REPAIR

    def test_close(self) -> None:
        f = _make_fault(status=FaultStatus.IN_REPAIR)
        f.close()
        assert f.status == FaultStatus.CLOSED
        assert f.is_open is False

    def test_close_from_open(self) -> None:
        f = _make_fault(status=FaultStatus.OPEN)
        f.close()
        assert f.status == FaultStatus.CLOSED

    def test_cannot_transition_closed_fault(self) -> None:
        f = _make_fault(status=FaultStatus.CLOSED)
        with pytest.raises(FaultAlreadyClosedError):
            f.assign(uuid.uuid4())

    def test_invalid_transition_open_to_in_repair(self) -> None:
        f = _make_fault(status=FaultStatus.OPEN)
        with pytest.raises(FaultInvalidStateTransitionError):
            f.start_repair()

    def test_is_critical(self) -> None:
        f = _make_fault(severity=FaultSeverity.CRITICAL)
        assert f.is_critical is True

    def test_link_sap_notification(self) -> None:
        f = _make_fault()
        f.link_sap_notification("SAP-NOT-12345")
        assert f.sap_notification_number == "SAP-NOT-12345"


class TestFaultExceptions:
    def test_not_found(self) -> None:
        err = FaultNotFoundError("abc")
        assert "abc" in str(err)

    def test_already_closed(self) -> None:
        err = FaultAlreadyClosedError("fault-id")
        assert "fault-id" in str(err)
