"""P1 — Driver domain edge cases (state machine + value objects)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from apps.driver.domain.entities import Driver, DriverStatus
from apps.driver.domain.exceptions import DriverInvalidStateTransitionError
from apps.driver.domain.value_objects import DriverContact, LicenseClass, LicenseNumber


def _driver(*, status: DriverStatus = DriverStatus.ACTIVE) -> Driver:
    now = datetime.now(tz=UTC)
    return Driver(
        id=uuid.uuid4(),
        full_name="Ali Driver",
        license_number=LicenseNumber("LIC12345"),
        license_class=LicenseClass.B,
        contact=DriverContact(phone="+989121111111"),
        status=status,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.unit
class TestDriverDomainEdges:
    """Driver lifecycle and value-object boundaries."""

    def test_suspend_and_reinstate(self) -> None:
        """ACTIVE → SUSPENDED → ACTIVE is allowed."""
        driver = _driver()
        driver.suspend()
        assert driver.status == DriverStatus.SUSPENDED
        driver.reinstate()
        assert driver.status == DriverStatus.ACTIVE

    def test_cannot_reinstate_inactive(self) -> None:
        """INACTIVE is terminal for reinstate."""
        driver = _driver(status=DriverStatus.INACTIVE)
        with pytest.raises(DriverInvalidStateTransitionError):
            driver.reinstate()

    def test_deactivate_from_active(self) -> None:
        """ACTIVE may deactivate to INACTIVE."""
        driver = _driver()
        driver.deactivate()
        assert driver.status == DriverStatus.INACTIVE

    def test_assign_and_unassign_vehicle(self) -> None:
        """Vehicle assignment is recorded by ID only."""
        driver = _driver()
        vehicle_id = uuid.uuid4()
        driver.assign_vehicle(vehicle_id)
        assert driver.assigned_vehicle_id == vehicle_id
        driver.unassign_vehicle()
        assert driver.assigned_vehicle_id is None

    def test_license_rejects_hyphen(self) -> None:
        """License numbers must be alphanumeric (no punctuation)."""
        with pytest.raises(ValueError, match="alphanumeric"):
            LicenseNumber("LIC-TECH-1")

    def test_license_rejects_too_short(self) -> None:
        """License numbers require at least 5 characters."""
        with pytest.raises(ValueError, match="alphanumeric"):
            LicenseNumber("AB12")
