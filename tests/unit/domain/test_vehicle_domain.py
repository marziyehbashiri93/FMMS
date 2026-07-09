"""Unit tests for the Vehicle domain layer."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from apps.vehicle.domain.entities import Vehicle, VehicleCategory, VehicleStatus
from apps.vehicle.domain.exceptions import (
    VehicleInvalidStateTransitionError,
    VehicleNotFoundError,
)
from apps.vehicle.domain.value_objects import (
    VIN,
    PlateNumber,
    SAPEquipmentNumber,
)


def _make_vehicle(**kwargs: object) -> Vehicle:
    """Build a minimal valid Vehicle for tests."""
    defaults: dict[str, object] = {
        "id": uuid.uuid4(),
        "plate_number": PlateNumber("12-ب-345"),
        "vin": VIN("1HGBH41JXMN109186"),
        "make": "Toyota",
        "model": "Hilux",
        "year": 2022,
        "category": VehicleCategory.LIGHT,
        "status": VehicleStatus.ACTIVE,
        "created_at": datetime.now(tz=UTC),
        "updated_at": datetime.now(tz=UTC),
    }
    defaults.update(kwargs)
    return Vehicle(**defaults)  # type: ignore[arg-type]


class TestPlateNumber:
    def test_valid_plate(self) -> None:
        p = PlateNumber("12-ب-345")
        assert p.value == "12-ب-345"

    def test_strips_whitespace(self) -> None:
        p = PlateNumber("  ABC  ")
        assert p.value == "ABC"

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            PlateNumber("")

    def test_too_long_raises(self) -> None:
        with pytest.raises(ValueError, match="exceed 20"):
            PlateNumber("A" * 21)


class TestVIN:
    def test_valid_vin(self) -> None:
        v = VIN("1HGBH41JXMN109186")
        assert v.value == "1HGBH41JXMN109186"

    def test_lowercase_normalised(self) -> None:
        v = VIN("1hgbh41jxmn109186")
        assert v.value == "1HGBH41JXMN109186"

    def test_invalid_length(self) -> None:
        with pytest.raises(ValueError, match="exactly 17"):
            VIN("SHORT")

    def test_forbidden_char_i(self) -> None:
        with pytest.raises(ValueError, match="exactly 17"):
            VIN("1HGBH41JXMNI0918")

    def test_str(self) -> None:
        assert str(VIN("1HGBH41JXMN109186")) == "1HGBH41JXMN109186"


class TestSAPEquipmentNumber:
    def test_valid(self) -> None:
        eq = SAPEquipmentNumber("000000012345")
        assert eq.value == "000000012345"

    def test_non_numeric_raises(self) -> None:
        with pytest.raises(ValueError, match="only digits"):
            SAPEquipmentNumber("EQ-12345")

    def test_too_long_raises(self) -> None:
        with pytest.raises(ValueError, match="18 digits"):
            SAPEquipmentNumber("1" * 19)


class TestVehicleEntity:
    def test_initial_status(self) -> None:
        v = _make_vehicle()
        assert v.status == VehicleStatus.ACTIVE
        assert v.is_available is True

    def test_mark_under_repair(self) -> None:
        v = _make_vehicle()
        v.mark_under_repair()
        assert v.status == VehicleStatus.UNDER_REPAIR
        assert v.is_available is False

    def test_complete_repair_returns_active(self) -> None:
        v = _make_vehicle(status=VehicleStatus.UNDER_REPAIR)
        v.complete_repair()
        assert v.status == VehicleStatus.ACTIVE

    def test_suspend(self) -> None:
        v = _make_vehicle()
        v.suspend()
        assert v.status == VehicleStatus.SUSPENDED

    def test_deactivate(self) -> None:
        v = _make_vehicle()
        v.deactivate()
        assert v.status == VehicleStatus.INACTIVE

    def test_cannot_reactivate_inactive(self) -> None:
        v = _make_vehicle(status=VehicleStatus.INACTIVE)
        with pytest.raises(VehicleInvalidStateTransitionError):
            v.transition_to(VehicleStatus.ACTIVE)

    def test_inactive_is_terminal(self) -> None:
        v = _make_vehicle(status=VehicleStatus.INACTIVE)
        with pytest.raises(VehicleInvalidStateTransitionError):
            v.deactivate()

    def test_optional_fields_default_none(self) -> None:
        v = _make_vehicle()
        assert v.chassis_number is None
        assert v.sap_equipment_number is None

    def test_with_sap_number(self) -> None:
        v = _make_vehicle(sap_equipment_number=SAPEquipmentNumber("000123"))
        assert v.sap_equipment_number is not None
        assert v.sap_equipment_number.value == "000123"


class TestVehicleExceptions:
    def test_not_found_error(self) -> None:
        err = VehicleNotFoundError("abc-123")
        assert "abc-123" in str(err)
        assert err.vehicle_id == "abc-123"

    def test_transition_error(self) -> None:
        err = VehicleInvalidStateTransitionError("INACTIVE", "ACTIVE")
        assert "INACTIVE" in str(err)
        assert "ACTIVE" in str(err)
