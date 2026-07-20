"""P1 — Driver domain edge cases (state machine + value objects)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from apps.driver.domain.entities import Driver, DriverStatus
from apps.driver.domain.exceptions import DriverInvalidStateTransitionError
from apps.driver.domain.value_objects import CustomerNumber


def _driver(*, status: DriverStatus = DriverStatus.ACTIVE) -> Driver:
    now = datetime.now(tz=UTC)
    return Driver(
        id=uuid.uuid4(),
        customer_number=CustomerNumber("6000001234"),
        name="Ali Driver",
        mobile="09121111111",
        status=status,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.unit
class TestDriverDomainEdges:
    """Driver lifecycle and value-object boundaries."""

    def test_decommission_and_reactivate(self) -> None:
        """ACTIVE -> DECOMMISSIONED -> ACTIVE is allowed."""
        driver = _driver()
        driver.decommission()
        assert driver.status == DriverStatus.DECOMMISSIONED
        driver.reactivate()
        assert driver.status == DriverStatus.ACTIVE

    def test_cannot_reactivate_active_driver(self) -> None:
        """ACTIVE -> ACTIVE is not a meaningful lifecycle transition."""
        driver = _driver()
        with pytest.raises(DriverInvalidStateTransitionError):
            driver.reactivate()

    def test_decommission_from_active(self) -> None:
        """ACTIVE may move to DECOMMISSIONED when absent from SAP."""
        driver = _driver()
        driver.decommission()
        assert driver.status == DriverStatus.DECOMMISSIONED

    def test_customer_number_rejects_non_numeric(self) -> None:
        """SAP CustomerNumber must be numeric."""
        with pytest.raises(ValueError, match="numeric"):
            CustomerNumber("LIC-TECH-1")

    def test_customer_number_rejects_blank(self) -> None:
        """SAP CustomerNumber must not be blank."""
        with pytest.raises(ValueError, match="numeric"):
            CustomerNumber("")
