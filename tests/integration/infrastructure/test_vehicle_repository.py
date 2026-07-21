"""Integration tests for DjangoVehicleRepository.

These tests use the Django test database (SQLite in CI).
They verify SAP-key persistence, status filtering, and assignment history.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from apps.vehicle.domain.entities import Vehicle, VehicleStatus
from apps.vehicle.domain.exceptions import VehicleNotFoundError
from apps.vehicle.domain.interfaces.vehicle_repository import IVehicleRepository
from apps.vehicle.domain.value_objects import PlateNumber, SAPVehicleNumber
from apps.vehicle.infrastructure.models import (
    VehicleDriverAssignmentHistoryModel,
    VehicleModel,
)
from apps.vehicle.infrastructure.repositories import DjangoVehicleRepository

pytestmark = pytest.mark.django_db


def _make_vehicle(
    plate: str = "12-ب-001",
    status: VehicleStatus = VehicleStatus.ACTIVE,
) -> Vehicle:
    """Build and persist a minimal Vehicle for tests."""
    repo = DjangoVehicleRepository()
    vehicle_number = str(abs(hash(plate)) % 10**12)
    vehicle = Vehicle(
        id=uuid.uuid4(),
        vehicle_number=SAPVehicleNumber(vehicle_number),
        license_plate=PlateNumber(plate),
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
        assert fetched.license_plate.value == "12-ب-001"
        assert fetched.vehicle_number.value == vehicle.vehicle_number.value
        assert fetched.status == VehicleStatus.ACTIVE

    def test_get_by_id_not_found_raises(self) -> None:
        repo = DjangoVehicleRepository()
        with pytest.raises(VehicleNotFoundError):
            repo.get_by_id(uuid.uuid4())

    def test_save_is_idempotent(self) -> None:
        """Saving the same vehicle twice must not create a duplicate."""
        repo = DjangoVehicleRepository()
        vehicle = _make_vehicle()
        vehicle.status = VehicleStatus.UNDER_REPAIR
        repo.save(vehicle)
        fetched = repo.get_by_id(vehicle.id)
        assert fetched.status == VehicleStatus.UNDER_REPAIR

    def test_save_with_vehicle_number(self) -> None:
        repo = DjangoVehicleRepository()
        vehicle = Vehicle(
            id=uuid.uuid4(),
            vehicle_number=SAPVehicleNumber("000000012345"),
            license_plate=PlateNumber("88-S-001"),
            status=VehicleStatus.ACTIVE,
            created_at=datetime.now(tz=UTC),
            updated_at=datetime.now(tz=UTC),
        )
        repo.save(vehicle)
        fetched = repo.get_by_id(vehicle.id)
        assert fetched.vehicle_number is not None
        assert fetched.vehicle_number.value == "000000012345"


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

class TestSAPDecommission:
    def test_decommission_missing_from_sap_preserves_rows(self) -> None:
        repo = DjangoVehicleRepository()
        kept = _make_vehicle(plate="55-E-001")
        missing = _make_vehicle(plate="66-F-001")

        count = repo.decommission_missing_from_sap({kept.vehicle_number.value})

        assert count == 1
        assert repo.get_by_id(kept.id).status == VehicleStatus.ACTIVE
        assert repo.get_by_id(missing.id).status == VehicleStatus.DECOMMISSIONED
        assert VehicleModel.objects.get(id=missing.id).is_deleted is False


class TestDriverAssignmentHistory:
    def test_records_both_driver_roles_for_every_snapshot(self) -> None:
        repo = DjangoVehicleRepository()
        vehicle = _make_vehicle(plate="77-H-001")
        vehicle.driver1_customer_number = "6000000250"
        vehicle.driver2_customer_number = "6000000160"
        repo.save(vehicle)
        sync_run_id = uuid.uuid4()
        synced_at = datetime.now(tz=UTC)

        repo.record_driver_assignment_snapshot(
            vehicle=vehicle,
            sync_run_id=sync_run_id,
            synced_at=synced_at,
            request_id="req-history",
        )

        rows = VehicleDriverAssignmentHistoryModel.objects.filter(
            sync_run_id=sync_run_id,
            vehicle_number=vehicle.vehicle_number.value,
        ).order_by("driver_role")
        assert rows.count() == 2
        assert {row.driver_role for row in rows} == {"ASSISTANT", "DRIVER"}
        assert {row.driver_customer_number for row in rows} == {
            "6000000160",
            "6000000250",
        }
