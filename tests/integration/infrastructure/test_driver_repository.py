"""Integration tests for DjangoDriverRepository."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from apps.driver.domain.entities import Driver, DriverStatus
from apps.driver.domain.exceptions import DriverNotFoundError
from apps.driver.domain.interfaces.driver_repository import IDriverRepository
from apps.driver.domain.value_objects import DriverContact, LicenseClass, LicenseNumber
from apps.driver.infrastructure.repositories import DjangoDriverRepository

pytestmark = pytest.mark.django_db


def _make_driver(
    license: str = "LIC001",
    status: DriverStatus = DriverStatus.ACTIVE,
) -> Driver:
    repo = DjangoDriverRepository()
    driver = Driver(
        id=uuid.uuid4(),
        full_name="Ahmad Rezaei",
        license_number=LicenseNumber(license),
        license_class=LicenseClass.B,
        contact=DriverContact(phone="+989121234567", email="ahmad@example.com"),
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
        assert fetched.license_number.value == "LIC001"
        assert fetched.full_name == "Ahmad Rezaei"

    def test_get_by_id_not_found(self) -> None:
        repo = DjangoDriverRepository()
        with pytest.raises(DriverNotFoundError):
            repo.get_by_id(uuid.uuid4())

    def test_get_by_license(self) -> None:
        repo = DjangoDriverRepository()
        _make_driver(license="LIC002")
        driver = repo.get_by_license(LicenseNumber("LIC002"))
        assert driver.license_number.value == "LIC002"

    def test_contact_preserved(self) -> None:
        repo = DjangoDriverRepository()
        driver = _make_driver()
        fetched = repo.get_by_id(driver.id)
        assert fetched.contact.phone == "+989121234567"
        assert fetched.contact.email == "ahmad@example.com"

    def test_update_status(self) -> None:
        repo = DjangoDriverRepository()
        driver = _make_driver()
        driver.suspend()
        repo.save(driver)
        fetched = repo.get_by_id(driver.id)
        assert fetched.status == DriverStatus.SUSPENDED


class TestVehicleAssignment:
    def test_get_by_vehicle_assigned(self) -> None:
        repo = DjangoDriverRepository()
        vehicle_id = uuid.uuid4()
        driver = _make_driver(license="LIC003")
        driver.assign_vehicle(vehicle_id)
        repo.save(driver)
        found = repo.get_by_vehicle(vehicle_id)
        assert found is not None
        assert found.assigned_vehicle_id == vehicle_id

    def test_get_by_vehicle_none(self) -> None:
        repo = DjangoDriverRepository()
        result = repo.get_by_vehicle(uuid.uuid4())
        assert result is None


class TestListAndExists:
    def test_list_by_status(self) -> None:
        repo = DjangoDriverRepository()
        _make_driver(license="LIC004", status=DriverStatus.ACTIVE)
        _make_driver(license="LIC005", status=DriverStatus.SUSPENDED)
        active = repo.list_by_status(DriverStatus.ACTIVE)
        assert all(d.status == DriverStatus.ACTIVE for d in active)

    def test_exists_by_license_true(self) -> None:
        repo = DjangoDriverRepository()
        _make_driver(license="LIC006")
        assert repo.exists_by_license(LicenseNumber("LIC006")) is True

    def test_exists_by_license_false(self) -> None:
        repo = DjangoDriverRepository()
        assert repo.exists_by_license(LicenseNumber("ZZZZZZ")) is False


class TestSoftDelete:
    def test_delete_hides_record(self) -> None:
        repo = DjangoDriverRepository()
        driver = _make_driver(license="LIC007")
        repo.delete(driver.id)
        with pytest.raises(DriverNotFoundError):
            repo.get_by_id(driver.id)

    def test_delete_nonexistent_raises(self) -> None:
        repo = DjangoDriverRepository()
        with pytest.raises(DriverNotFoundError):
            repo.delete(uuid.uuid4())
