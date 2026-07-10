"""Unit tests for Driver application services.

All repository dependencies are replaced with lightweight in-memory fakes —
no database, no network.

Fakes:
- ``FakeDriverRepository``: in-memory dict keyed by UUID.
- ``FakeVehicleRepository``: minimal stub for cross-domain vehicle availability checks.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from apps.driver.application.dto.driver_dto import (
    AssignDriverToVehicleDTO,
    DriverResponseDTO,
    RegisterDriverDTO,
    SuspendDriverDTO,
)
from apps.driver.application.services.assign_driver_to_vehicle_service import (
    AssignDriverToVehicleService,
)
from apps.driver.application.services.get_driver_service import (
    GetDriverService,
    ListDriversService,
)
from apps.driver.application.services.register_driver_service import (
    RegisterDriverService,
)
from apps.driver.application.services.suspend_driver_service import SuspendDriverService
from apps.driver.domain.entities import Driver, DriverStatus
from apps.driver.domain.exceptions import DriverInvalidStateTransitionError
from apps.driver.domain.interfaces.driver_repository import IDriverRepository
from apps.driver.domain.value_objects import DriverContact, LicenseClass, LicenseNumber
from apps.vehicle.domain.entities import Vehicle, VehicleCategory, VehicleStatus
from apps.vehicle.domain.interfaces.vehicle_repository import IVehicleRepository
from apps.vehicle.domain.value_objects import VIN, PlateNumber, SAPEquipmentNumber
from core.exceptions.base_exception import FMMSConflictError, FMMSNotFoundError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_driver(
    license_num: str = "LIC12345",
    status: DriverStatus = DriverStatus.ACTIVE,
    assigned_vehicle_id: uuid.UUID | None = None,
) -> Driver:
    return Driver(
        id=uuid.uuid4(),
        full_name="Ali Ahmadi",
        license_number=LicenseNumber(license_num),
        license_class=LicenseClass.B,
        contact=DriverContact(phone="+989123456789"),
        status=status,
        created_at=datetime.now(tz=UTC),
        updated_at=datetime.now(tz=UTC),
        assigned_vehicle_id=assigned_vehicle_id,
    )


def _make_vehicle(
    status: VehicleStatus = VehicleStatus.ACTIVE,
) -> Vehicle:
    return Vehicle(
        id=uuid.uuid4(),
        plate_number=PlateNumber("VEHPLATE1"),
        vin=VIN("1HGCM82633A004352"),
        make="Toyota",
        model="Hilux",
        year=2022,
        category=VehicleCategory.LIGHT,
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

    def get_by_id(self, driver_id: uuid.UUID) -> Driver | None:
        return self._store.get(driver_id)

    def get_by_license(self, license_number: LicenseNumber) -> Driver | None:
        return next(
            (d for d in self._store.values() if d.license_number == license_number),
            None,
        )

    def get_by_vehicle(self, vehicle_id: uuid.UUID) -> Driver | None:
        return next(
            (d for d in self._store.values() if d.assigned_vehicle_id == vehicle_id),
            None,
        )

    def list_by_status(self, status: DriverStatus) -> list[Driver]:
        return [d for d in self._store.values() if d.status == status]

    def exists_by_license(self, license_number: LicenseNumber) -> bool:
        return self.get_by_license(license_number) is not None

    def save(self, driver: Driver) -> Driver:
        self._store[driver.id] = driver
        return driver

    def delete(self, driver_id: uuid.UUID) -> None:
        self._store.pop(driver_id, None)


class FakeVehicleRepository(IVehicleRepository):
    def __init__(self, initial: list[Vehicle] | None = None) -> None:
        self._store: dict[uuid.UUID, Vehicle] = {v.id: v for v in (initial or [])}

    def get_by_id(self, vehicle_id: uuid.UUID) -> Vehicle | None:
        return self._store.get(vehicle_id)

    def get_by_plate(self, plate_number: PlateNumber) -> Vehicle | None:
        return None

    def get_by_sap_equipment_number(
        self, sap_equipment_number: SAPEquipmentNumber
    ) -> Vehicle | None:
        return next(
            (
                v
                for v in self._store.values()
                if v.sap_equipment_number is not None
                and v.sap_equipment_number == sap_equipment_number
            ),
            None,
        )

    def exists_by_plate(self, plate_number: PlateNumber) -> bool:
        return False

    def list_active(self) -> list[Vehicle]:
        return [v for v in self._store.values() if v.status == VehicleStatus.ACTIVE]

    def list_by_status(self, status: VehicleStatus) -> list[Vehicle]:
        return [v for v in self._store.values() if v.status == status]

    def save(self, vehicle: Vehicle) -> Vehicle:
        self._store[vehicle.id] = vehicle
        return vehicle

    def delete(self, vehicle_id: uuid.UUID) -> None:
        self._store.pop(vehicle_id, None)


# ---------------------------------------------------------------------------
# RegisterDriverService
# ---------------------------------------------------------------------------


class TestRegisterDriverService:
    def _dto(self, license_num: str = "LIC99999") -> RegisterDriverDTO:
        return RegisterDriverDTO(
            full_name="Ali Ahmadi",
            license_number=license_num,
            license_class=LicenseClass.B,
            phone="+989123456789",
            request_id="req-drv-001",
            created_by=uuid.uuid4(),
        )

    def test_registers_driver_and_returns_response_dto(self) -> None:
        repo = FakeDriverRepository()
        result = RegisterDriverService(repo).execute(self._dto())

        assert isinstance(result, DriverResponseDTO)
        assert result.status == DriverStatus.ACTIVE
        assert result.license_number == "LIC99999"

    def test_persists_driver_in_repository(self) -> None:
        repo = FakeDriverRepository()
        result = RegisterDriverService(repo).execute(self._dto())

        assert repo.get_by_id(result.id) is not None

    def test_raises_conflict_on_duplicate_license(self) -> None:
        existing = _make_driver(license_num="DUPLIC01")
        repo = FakeDriverRepository(initial=[existing])

        with pytest.raises(FMMSConflictError):
            RegisterDriverService(repo).execute(self._dto(license_num="DUPLIC01"))

    def test_email_stored_when_provided(self) -> None:
        repo = FakeDriverRepository()
        dto = RegisterDriverDTO(
            full_name="Sara Hosseini",
            license_number="LIC88888",
            license_class=LicenseClass.C,
            phone="+989129876543",
            request_id="req-email",
            created_by=uuid.uuid4(),
            email="sara@example.com",
        )
        result = RegisterDriverService(repo).execute(dto)

        assert result.email == "sara@example.com"

    def test_no_vehicle_assigned_on_registration(self) -> None:
        repo = FakeDriverRepository()
        result = RegisterDriverService(repo).execute(self._dto())

        assert result.assigned_vehicle_id is None


# ---------------------------------------------------------------------------
# AssignDriverToVehicleService
# ---------------------------------------------------------------------------


class TestAssignDriverToVehicleService:
    def _service(
        self,
        drivers: list[Driver] | None = None,
        vehicles: list[Vehicle] | None = None,
    ) -> AssignDriverToVehicleService:
        return AssignDriverToVehicleService(
            driver_repository=FakeDriverRepository(initial=drivers or []),
            vehicle_repository=FakeVehicleRepository(initial=vehicles or []),
        )

    def test_assigns_driver_to_active_vehicle(self) -> None:
        driver = _make_driver()
        vehicle = _make_vehicle()
        service = self._service(drivers=[driver], vehicles=[vehicle])

        result = service.execute(
            AssignDriverToVehicleDTO(
                driver_id=driver.id,
                vehicle_id=vehicle.id,
                request_id="req-assign",
                assigned_by=uuid.uuid4(),
            )
        )

        assert result.assigned_vehicle_id == vehicle.id

    def test_raises_not_found_for_missing_driver(self) -> None:
        vehicle = _make_vehicle()
        service = self._service(vehicles=[vehicle])

        with pytest.raises(FMMSNotFoundError):
            service.execute(
                AssignDriverToVehicleDTO(
                    driver_id=uuid.uuid4(),
                    vehicle_id=vehicle.id,
                    request_id="req-ghost",
                    assigned_by=uuid.uuid4(),
                )
            )

    def test_raises_not_found_for_missing_vehicle(self) -> None:
        driver = _make_driver()
        service = self._service(drivers=[driver])

        with pytest.raises(FMMSNotFoundError):
            service.execute(
                AssignDriverToVehicleDTO(
                    driver_id=driver.id,
                    vehicle_id=uuid.uuid4(),
                    request_id="req-noveh",
                    assigned_by=uuid.uuid4(),
                )
            )

    def test_raises_conflict_when_driver_already_assigned(self) -> None:
        some_vehicle_id = uuid.uuid4()
        driver = _make_driver(assigned_vehicle_id=some_vehicle_id)
        new_vehicle = _make_vehicle()
        service = self._service(drivers=[driver], vehicles=[new_vehicle])

        with pytest.raises(FMMSConflictError):
            service.execute(
                AssignDriverToVehicleDTO(
                    driver_id=driver.id,
                    vehicle_id=new_vehicle.id,
                    request_id="req-busy",
                    assigned_by=uuid.uuid4(),
                )
            )

    def test_raises_conflict_when_vehicle_not_active(self) -> None:
        driver = _make_driver()
        vehicle = _make_vehicle(status=VehicleStatus.UNDER_REPAIR)
        service = self._service(drivers=[driver], vehicles=[vehicle])

        with pytest.raises(FMMSConflictError):
            service.execute(
                AssignDriverToVehicleDTO(
                    driver_id=driver.id,
                    vehicle_id=vehicle.id,
                    request_id="req-repair",
                    assigned_by=uuid.uuid4(),
                )
            )

    def test_raises_conflict_when_vehicle_already_has_driver(self) -> None:
        vehicle = _make_vehicle()
        existing_driver = _make_driver(
            license_num="EXIST001", assigned_vehicle_id=vehicle.id
        )
        new_driver = _make_driver(license_num="NEW00001")
        service = self._service(
            drivers=[existing_driver, new_driver], vehicles=[vehicle]
        )

        with pytest.raises(FMMSConflictError):
            service.execute(
                AssignDriverToVehicleDTO(
                    driver_id=new_driver.id,
                    vehicle_id=vehicle.id,
                    request_id="req-double",
                    assigned_by=uuid.uuid4(),
                )
            )


# ---------------------------------------------------------------------------
# SuspendDriverService
# ---------------------------------------------------------------------------


class TestSuspendDriverService:
    def test_suspends_active_driver(self) -> None:
        driver = _make_driver()
        repo = FakeDriverRepository(initial=[driver])
        result = SuspendDriverService(repo).execute(
            SuspendDriverDTO(
                driver_id=driver.id,
                request_id="req-susp",
                requested_by=uuid.uuid4(),
            )
        )

        assert result.status == DriverStatus.SUSPENDED

    def test_raises_not_found_for_missing_driver(self) -> None:
        repo = FakeDriverRepository()
        with pytest.raises(FMMSNotFoundError):
            SuspendDriverService(repo).execute(
                SuspendDriverDTO(
                    driver_id=uuid.uuid4(),
                    request_id="req-ghost",
                    requested_by=uuid.uuid4(),
                )
            )

    def test_raises_state_error_when_already_suspended(self) -> None:
        driver = _make_driver(status=DriverStatus.SUSPENDED)
        repo = FakeDriverRepository(initial=[driver])

        with pytest.raises(DriverInvalidStateTransitionError):
            SuspendDriverService(repo).execute(
                SuspendDriverDTO(
                    driver_id=driver.id,
                    request_id="req-re-susp",
                    requested_by=uuid.uuid4(),
                )
            )

    def test_raises_state_error_when_inactive(self) -> None:
        driver = _make_driver(status=DriverStatus.INACTIVE)
        repo = FakeDriverRepository(initial=[driver])

        with pytest.raises(DriverInvalidStateTransitionError):
            SuspendDriverService(repo).execute(
                SuspendDriverDTO(
                    driver_id=driver.id,
                    request_id="req-inactive",
                    requested_by=uuid.uuid4(),
                )
            )


# ---------------------------------------------------------------------------
# GetDriverService / ListDriversService
# ---------------------------------------------------------------------------


class TestGetDriverService:
    def test_returns_dto_for_existing_driver(self) -> None:
        driver = _make_driver()
        repo = FakeDriverRepository(initial=[driver])

        result = GetDriverService(repo).execute(driver.id, request_id="req-get")

        assert result.id == driver.id
        assert result.license_number == driver.license_number.value

    def test_raises_not_found_for_missing_driver(self) -> None:
        repo = FakeDriverRepository()
        with pytest.raises(FMMSNotFoundError):
            GetDriverService(repo).execute(uuid.uuid4())


class TestListDriversService:
    def test_lists_active_drivers_by_default(self) -> None:
        active = _make_driver(license_num="ACTDR001")
        suspended = _make_driver(license_num="SUSDR001", status=DriverStatus.SUSPENDED)
        repo = FakeDriverRepository(initial=[active, suspended])

        results = ListDriversService(repo).execute()

        assert len(results) == 1
        assert results[0].license_number == "ACTDR001"

    def test_filters_by_suspended_status(self) -> None:
        active = _make_driver(license_num="ACTDR002")
        suspended = _make_driver(license_num="SUSDR002", status=DriverStatus.SUSPENDED)
        repo = FakeDriverRepository(initial=[active, suspended])

        results = ListDriversService(repo).execute(status=DriverStatus.SUSPENDED)

        assert len(results) == 1
        assert results[0].status == DriverStatus.SUSPENDED

    def test_returns_empty_list_when_none_match(self) -> None:
        repo = FakeDriverRepository()
        assert ListDriversService(repo).execute() == []
