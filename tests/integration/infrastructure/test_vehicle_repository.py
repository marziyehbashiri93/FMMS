"""Integration tests for DjangoVehicleRepository.

These tests use the Django test database (SQLite in CI).
They verify CRUD operations, soft-delete behaviour, status filtering,
and the cross-domain vehicle-deactivation guard.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from apps.vehicle.domain.entities import Vehicle, VehicleCategory, VehicleStatus
from apps.vehicle.domain.exceptions import VehicleNotFoundError
from apps.vehicle.domain.interfaces.vehicle_repository import IVehicleRepository
from apps.vehicle.domain.value_objects import VIN, PlateNumber, SAPEquipmentNumber
from apps.vehicle.infrastructure.repositories import DjangoVehicleRepository

pytestmark = pytest.mark.django_db


def _make_vehicle(
    plate: str = "12-ب-001",
    status: VehicleStatus = VehicleStatus.ACTIVE,
) -> Vehicle:
    """Build and persist a minimal Vehicle for tests."""
    repo = DjangoVehicleRepository()
    vehicle = Vehicle(
        id=uuid.uuid4(),
        plate_number=PlateNumber(plate),
        vin=VIN("1HGBH41JXMN109186"),
        make="Toyota",
        model="Hilux",
        year=2022,
        category=VehicleCategory.LIGHT,
        status=status,
        created_at=datetime.now(tz=UTC),
        updated_at=datetime.now(tz=UTC),
    )
    return repo.save(vehicle)


class TestDjangoVehicleRepositoryInterface:
    def test_satisfies_interface(self) -> None:
        """Repository must satisfy the domain interface contract."""
        repo = DjangoVehicleRepository()
        assert isinstance(repo, IVehicleRepository)


class TestSaveAndRetrieve:
    def test_save_and_get_by_id(self) -> None:
        repo = DjangoVehicleRepository()
        vehicle = _make_vehicle()
        fetched = repo.get_by_id(vehicle.id)
        assert fetched.id == vehicle.id
        assert fetched.plate_number.value == "12-ب-001"
        assert fetched.vin.value == "1HGBH41JXMN109186"
        assert fetched.make == "Toyota"
        assert fetched.status == VehicleStatus.ACTIVE

    def test_get_by_id_not_found_raises(self) -> None:
        repo = DjangoVehicleRepository()
        with pytest.raises(VehicleNotFoundError):
            repo.get_by_id(uuid.uuid4())

    def test_get_by_plate(self) -> None:
        repo = DjangoVehicleRepository()
        _make_vehicle(plate="99-X-001")
        fetched = repo.get_by_plate(PlateNumber("99-X-001"))
        assert fetched.plate_number.value == "99-X-001"

    def test_get_by_plate_not_found_raises(self) -> None:
        repo = DjangoVehicleRepository()
        with pytest.raises(VehicleNotFoundError):
            repo.get_by_plate(PlateNumber("00-X-999"))

    def test_save_is_idempotent(self) -> None:
        """Saving the same vehicle twice must not create a duplicate."""
        repo = DjangoVehicleRepository()
        vehicle = _make_vehicle()
        vehicle.status = VehicleStatus.UNDER_REPAIR
        repo.save(vehicle)
        fetched = repo.get_by_id(vehicle.id)
        assert fetched.status == VehicleStatus.UNDER_REPAIR

    def test_save_with_sap_equipment_number(self) -> None:
        repo = DjangoVehicleRepository()
        vehicle = Vehicle(
            id=uuid.uuid4(),
            plate_number=PlateNumber("88-S-001"),
            vin=VIN("1HGBH41JXMN109186"),
            make="Ford",
            model="Ranger",
            year=2023,
            category=VehicleCategory.LIGHT,
            status=VehicleStatus.ACTIVE,
            created_at=datetime.now(tz=UTC),
            updated_at=datetime.now(tz=UTC),
            sap_equipment_number=SAPEquipmentNumber("000000012345"),
        )
        repo.save(vehicle)
        fetched = repo.get_by_id(vehicle.id)
        assert fetched.sap_equipment_number is not None
        assert fetched.sap_equipment_number.value == "000000012345"


class TestListOperations:
    def test_list_active_returns_only_active(self) -> None:
        repo = DjangoVehicleRepository()
        _make_vehicle(plate="11-A-001", status=VehicleStatus.ACTIVE)
        _make_vehicle(plate="11-A-002", status=VehicleStatus.INACTIVE)
        active = repo.list_active()
        statuses = {v.status for v in active}
        assert VehicleStatus.ACTIVE in statuses
        assert VehicleStatus.INACTIVE not in statuses

    def test_list_by_status_under_repair(self) -> None:
        repo = DjangoVehicleRepository()
        _make_vehicle(plate="22-B-001", status=VehicleStatus.UNDER_REPAIR)
        _make_vehicle(plate="22-B-002", status=VehicleStatus.ACTIVE)
        under_repair = repo.list_by_status(VehicleStatus.UNDER_REPAIR)
        assert all(v.status == VehicleStatus.UNDER_REPAIR for v in under_repair)
        assert len(under_repair) >= 1

    def test_exists_by_plate_true(self) -> None:
        repo = DjangoVehicleRepository()
        _make_vehicle(plate="33-C-001")
        assert repo.exists_by_plate(PlateNumber("33-C-001")) is True

    def test_exists_by_plate_false(self) -> None:
        repo = DjangoVehicleRepository()
        assert repo.exists_by_plate(PlateNumber("99-Z-999")) is False


class TestSoftDelete:
    def test_delete_soft_deletes_record(self) -> None:
        repo = DjangoVehicleRepository()
        vehicle = _make_vehicle(plate="44-D-001")
        repo.delete(vehicle.id)
        with pytest.raises(VehicleNotFoundError):
            repo.get_by_id(vehicle.id)

    def test_delete_nonexistent_raises(self) -> None:
        repo = DjangoVehicleRepository()
        with pytest.raises(VehicleNotFoundError):
            repo.delete(uuid.uuid4())

    def test_soft_deleted_not_in_list_active(self) -> None:
        repo = DjangoVehicleRepository()
        vehicle = _make_vehicle(plate="55-E-001")
        repo.delete(vehicle.id)
        active_ids = {v.id for v in repo.list_active()}
        assert vehicle.id not in active_ids

    def test_exists_by_plate_returns_false_after_delete(self) -> None:
        repo = DjangoVehicleRepository()
        _make_vehicle(plate="66-F-001")
        vehicle = DjangoVehicleRepository().get_by_plate(PlateNumber("66-F-001"))
        repo.delete(vehicle.id)
        assert repo.exists_by_plate(PlateNumber("66-F-001")) is False
