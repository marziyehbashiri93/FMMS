"""Unit tests for Driver application services.

All repository dependencies are replaced with lightweight in-memory fakes —
no database, no network.

Fakes:
- ``FakeDriverRepository``: in-memory dict keyed by UUID.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from apps.driver.application.dto.driver_dto import (
    DriverResponseDTO,
)
from apps.driver.application.services.get_driver_service import (
    GetDriverService,
    ListDriversService,
)
from apps.driver.domain.entities import Driver, DriverStatus
from apps.driver.domain.exceptions import DriverNotFoundError
from apps.driver.domain.interfaces.driver_repository import IDriverRepository
from apps.driver.domain.value_objects import CustomerNumber
from core.exceptions.base_exception import FMMSNotFoundError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_driver(
    customer_num: str = "6000000001",
    status: DriverStatus = DriverStatus.ACTIVE,
) -> Driver:
    return Driver(
        id=uuid.uuid4(),
        customer_number=CustomerNumber(customer_num),
        name="Ali Ahmadi",
        mobile="09123456789",
        status=status,
        created_at=datetime.now(tz=UTC),
        updated_at=datetime.now(tz=UTC),
    )


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeDriverRepository(IDriverRepository):
    def __init__(self, initial: list[Driver] | None = None) -> None:
        self._store: dict[uuid.UUID, Driver] = {d.id: d for d in (initial or [])}

    def get_by_id(self, driver_id: uuid.UUID) -> Driver:
        driver = self._store.get(driver_id)
        if driver is None:
            raise DriverNotFoundError(driver_id)
        return driver

    def get_by_customer_number(self, customer_number: CustomerNumber) -> Driver:
        for driver in self._store.values():
            if driver.customer_number == customer_number:
                return driver
        raise DriverNotFoundError(customer_number.value)

    def list_by_status(self, status: DriverStatus) -> list[Driver]:
        return [d for d in self._store.values() if d.status == status]

    def decommission_missing_from_sap(self, seen_customer_numbers: set[str]) -> int:
        count = 0
        for driver in self._store.values():
            if (
                driver.customer_number.value not in seen_customer_numbers
                and driver.status != DriverStatus.DECOMMISSIONED
            ):
                driver.decommission()
                count += 1
        return count

    def save(self, driver: Driver) -> Driver:
        self._store[driver.id] = driver
        return driver


# ---------------------------------------------------------------------------
# GetDriverService / ListDriversService
# ---------------------------------------------------------------------------


class TestGetDriverService:
    def test_returns_dto_for_existing_driver(self) -> None:
        driver = _make_driver()
        repo = FakeDriverRepository(initial=[driver])

        result = GetDriverService(repo).execute(driver.id, request_id="req-get")

        assert isinstance(result, DriverResponseDTO)
        assert result.id == driver.id
        assert result.customer_number == driver.customer_number.value

    def test_raises_not_found_for_missing_driver(self) -> None:
        repo = FakeDriverRepository()
        with pytest.raises(FMMSNotFoundError):
            GetDriverService(repo).execute(uuid.uuid4())


class TestListDriversService:
    def test_lists_active_drivers_by_default(self) -> None:
        active = _make_driver(customer_num="6000001001")
        decommissioned = _make_driver(
            customer_num="6000001002",
            status=DriverStatus.DECOMMISSIONED,
        )
        repo = FakeDriverRepository(initial=[active, decommissioned])

        results = ListDriversService(repo).execute()

        assert len(results) == 1
        assert results[0].customer_number == active.customer_number.value

    def test_filters_by_decommissioned_status(self) -> None:
        active = _make_driver(customer_num="6000001003")
        decommissioned = _make_driver(
            customer_num="6000001004",
            status=DriverStatus.DECOMMISSIONED,
        )
        repo = FakeDriverRepository(initial=[active, decommissioned])

        results = ListDriversService(repo).execute(status=DriverStatus.DECOMMISSIONED)

        assert len(results) == 1
        assert results[0].status == DriverStatus.DECOMMISSIONED

    def test_returns_empty_list_when_none_match(self) -> None:
        repo = FakeDriverRepository()
        assert ListDriversService(repo).execute() == []
