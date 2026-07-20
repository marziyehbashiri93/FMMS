"""Integration tests for DjangoDriverRepository."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from apps.driver.domain.entities import Driver, DriverStatus
from apps.driver.domain.exceptions import DriverNotFoundError
from apps.driver.domain.interfaces.driver_repository import IDriverRepository
from apps.driver.domain.value_objects import CustomerNumber
from apps.driver.infrastructure.models import DriverModel
from apps.driver.infrastructure.repositories import DjangoDriverRepository

pytestmark = pytest.mark.django_db


def _make_driver(
    customer_number: str = "6000000001",
    status: DriverStatus = DriverStatus.ACTIVE,
) -> Driver:
    repo = DjangoDriverRepository()
    driver = Driver(
        id=uuid.uuid4(),
        customer_number=CustomerNumber(customer_number),
        name="Ahmad Rezaei",
        mobile="09121234567",
        personnel_number="21000001",
        gender="مذکر",
        nilofar_code="520000001",
        status=status,
        created_at=datetime.now(tz=UTC),
        updated_at=datetime.now(tz=UTC),
    )
    return repo.save(driver)


class TestInterface:
    def test_satisfies_interface(self) -> None:
        assert isinstance(DjangoDriverRepository(), IDriverRepository)


class TestSaveAndRetrieve:
    def test_save_and_get_by_id(self) -> None:
        repo = DjangoDriverRepository()
        driver = _make_driver()
        fetched = repo.get_by_id(driver.id)
        assert fetched.id == driver.id
        assert fetched.customer_number.value == "6000000001"
        assert fetched.name == "Ahmad Rezaei"

    def test_get_by_id_not_found(self) -> None:
        repo = DjangoDriverRepository()
        with pytest.raises(DriverNotFoundError):
            repo.get_by_id(uuid.uuid4())

    def test_get_by_customer_number(self) -> None:
        repo = DjangoDriverRepository()
        _make_driver(customer_number="6000000002")
        driver = repo.get_by_customer_number(CustomerNumber("6000000002"))
        assert driver.customer_number.value == "6000000002"

    def test_sap_contact_fields_preserved(self) -> None:
        repo = DjangoDriverRepository()
        driver = _make_driver()
        fetched = repo.get_by_id(driver.id)
        assert fetched.mobile == "09121234567"
        assert fetched.personnel_number == "21000001"

    def test_update_status(self) -> None:
        repo = DjangoDriverRepository()
        driver = _make_driver()
        driver.decommission()
        repo.save(driver)
        fetched = repo.get_by_id(driver.id)
        assert fetched.status == DriverStatus.DECOMMISSIONED


class TestListAndExists:
    def test_list_by_status(self) -> None:
        repo = DjangoDriverRepository()
        _make_driver(customer_number="6000000004", status=DriverStatus.ACTIVE)
        _make_driver(
            customer_number="6000000005",
            status=DriverStatus.DECOMMISSIONED,
        )
        active = repo.list_by_status(DriverStatus.ACTIVE)
        assert all(d.status == DriverStatus.ACTIVE for d in active)


class TestDecommission:
    def test_decommission_missing_from_sap_preserves_rows(self) -> None:
        repo = DjangoDriverRepository()
        kept = _make_driver(customer_number="6000000008")
        missing = _make_driver(customer_number="6000000009")

        count = repo.decommission_missing_from_sap({kept.customer_number.value})

        assert count == 1
        assert repo.get_by_id(kept.id).status == DriverStatus.ACTIVE
        assert repo.get_by_id(missing.id).status == DriverStatus.DECOMMISSIONED
        assert DriverModel.objects.get(id=missing.id).is_deleted is False
