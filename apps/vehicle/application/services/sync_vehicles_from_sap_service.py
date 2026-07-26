"""Bulk synchronisation of SAP vehicle-driver data into FMMS.

SAP remains the master-data owner. FMMS imports ``ZC_VEHICLEDRIVER_CDS`` rows
and creates or updates local vehicle and driver records idempotently.
"""

from __future__ import annotations

import uuid
from contextlib import AbstractContextManager, nullcontext
from datetime import UTC, datetime

from django.db import IntegrityError, transaction

from apps.driver.domain.entities import Driver, DriverStatus
from apps.driver.domain.exceptions import DriverNotFoundError
from apps.driver.domain.interfaces.driver_repository import IDriverRepository
from apps.driver.domain.value_objects import CustomerNumber
from apps.vehicle.application.dto.vehicle_dto import VehicleSAPSyncResultDTO
from apps.vehicle.domain.entities import Vehicle, VehicleStatus
from apps.vehicle.domain.interfaces.vehicle_repository import IVehicleRepository
from apps.vehicle.domain.value_objects import PlateNumber, SAPVehicleNumber
from core.logging.structured_logger import get_structured_logger
from core.sap.dtos.vehicle_driver import SAPVehicleDriverDTO
from core.sap.ports.vehicle_driver_port import ISAPVehicleDriverPort

logger = get_structured_logger("vehicle", __name__)


def _deterministic_plate(vehicle_number: str) -> str:
    """Build a stable FMMS plate from SAP VehicleNumber.

    Args:
        vehicle_number: SAP VehicleNumber digits.

    Returns:
        Plate string within the PlateNumber length limit.
    """
    return f"VN{vehicle_number}"[-20:]


def _apply_sap_fields(vehicle: Vehicle, sap_dto: SAPVehicleDriverDTO) -> None:
    """Update mutable vehicle fields from an SAP vehicle-driver DTO.

    Args:
        vehicle: Target vehicle aggregate.
        sap_dto: Source SAP vehicle-driver row.
    """
    if sap_dto.license_plate:
        vehicle.license_plate = PlateNumber(sap_dto.license_plate)
    vehicle.vehicle_number = SAPVehicleNumber(sap_dto.vehicle_number)
    vehicle.commissioning_date = sap_dto.commissioning_date
    vehicle.driver1_customer_number = sap_dto.driver1_customer_number
    vehicle.driver2_customer_number = sap_dto.driver2_customer_number
    vehicle.updated_at = datetime.now(tz=UTC)


def _driver_customer_numbers_from_sap(sap_dto: SAPVehicleDriverDTO) -> set[str]:
    """Return valid SAP driver customer numbers carried by one SAP row."""
    seen: set[str] = set()
    for customer_no in (
        sap_dto.driver1_customer_number,
        sap_dto.driver2_customer_number,
    ):
        if customer_no:
            seen.add(CustomerNumber(customer_no).value)
    return seen


class SyncVehiclesFromSAPService:
    """Import/create/update FMMS vehicles and drivers from SAP vehicle-driver data.

    Args:
        vehicle_repository: Concrete ``IVehicleRepository``.
        sap_vehicle_driver_port: Concrete ``ISAPVehicleDriverPort``.
    """

    def __init__(
        self,
        vehicle_repository: IVehicleRepository,
        sap_vehicle_driver_port: ISAPVehicleDriverPort,
        driver_repository: IDriverRepository | None = None,
    ) -> None:
        self._repo = vehicle_repository
        self._sap = sap_vehicle_driver_port
        self._driver_repo = driver_repository

    def execute(
        self,
        request_id: str = "",
        plant: str | None = None,
    ) -> VehicleSAPSyncResultDTO:
        """Synchronise SAP vehicle-driver rows into FMMS.

        Matching key is SAP ``VehicleNumber``. Existing vehicles are
        updated; missing vehicles are created. Failures are counted and
        do not abort the remaining records.

        Args:
            request_id: Optional correlation ID for structured logging.
            plant: Optional reserved filter passed to the SAP port.

        Returns:
            ``VehicleSAPSyncResultDTO`` with create/update/fail counts.
        """
        logger.info(
            "Bulk syncing vehicles from SAP",
            extra={
                "domain": "vehicle",
                "service": "SyncVehiclesFromSAPService",
                "operation": "execute",
                "request_id": request_id,
                "plant": plant,
            },
        )

        sap_rows = self._sap.list_vehicle_drivers(plant=plant)
        if not sap_rows:
            logger.warning(
                "SAP vehicle-driver response was empty; skipping decommission",
                extra={
                    "domain": "vehicle",
                    "service": "SyncVehiclesFromSAPService",
                    "operation": "execute",
                    "request_id": request_id,
                    "plant": plant,
                    "review_status": "NEEDS_REVIEW",
                },
            )
            return VehicleSAPSyncResultDTO(
                total_received=0,
                created=0,
                updated=0,
                decommissioned=0,
                failed=1,
            )

        created = 0
        updated = 0
        decommissioned = 0
        failed = 0
        seen_vehicle_numbers: set[str] = set()
        seen_driver_customer_numbers: set[str] = set()
        sync_run_id = uuid.uuid4()
        synced_at = datetime.now(tz=UTC)

        for sap_dto in sap_rows:
            try:
                with self._atomic_if_supported():
                    seen_vehicle_numbers.add(
                        SAPVehicleNumber(sap_dto.vehicle_number).value
                    )
                    seen_driver_customer_numbers.update(
                        _driver_customer_numbers_from_sap(sap_dto)
                    )
                    was_created, vehicle = self._sync_one(sap_dto)
                    self._repo.record_driver_assignment_snapshot(
                        vehicle=vehicle,
                        sync_run_id=sync_run_id,
                        synced_at=synced_at,
                        request_id=request_id,
                    )
                    if was_created:
                        created += 1
                    else:
                        updated += 1
                    self._sync_drivers(sap_dto)
            except (ValueError, IntegrityError) as exc:
                failed += 1
                logger.error(
                    "Failed to sync SAP vehicle-driver row",
                    extra={
                        "domain": "vehicle",
                        "service": "SyncVehiclesFromSAPService",
                        "operation": "execute",
                        "request_id": request_id,
                        "vehicle_number": sap_dto.vehicle_number,
                        "exception": str(exc),
                    },
                    exc_info=True,
                )

        with self._atomic_if_supported():
            decommissioned = self._repo.decommission_missing_from_sap(
                seen_vehicle_numbers
            )
            if self._driver_repo is not None:
                self._driver_repo.decommission_missing_from_sap(
                    seen_driver_customer_numbers
                )

        result = VehicleSAPSyncResultDTO(
            total_received=len(sap_rows),
            created=created,
            updated=updated,
            decommissioned=decommissioned,
            failed=failed,
        )
        logger.info(
            "Bulk vehicle SAP sync completed",
            extra={
                "domain": "vehicle",
                "service": "SyncVehiclesFromSAPService",
                "operation": "execute",
                "request_id": request_id,
                "result": "success",
                "total_received": result.total_received,
                "created_count": result.created,
                "updated_count": result.updated,
                "decommissioned_count": result.decommissioned,
                "failed_count": result.failed,
            },
        )
        return result

    def _sync_one(self, sap_dto: SAPVehicleDriverDTO) -> tuple[bool, Vehicle]:
        """Create or update one vehicle from an SAP vehicle-driver DTO.

        Args:
            sap_dto: SAP vehicle-driver row.

        Returns:
            Tuple of created flag and saved vehicle.
        """
        sap_number = SAPVehicleNumber(sap_dto.vehicle_number)
        existing = self._repo.get_by_vehicle_number(sap_number)
        if existing is not None:
            _apply_sap_fields(existing, sap_dto)
            saved = self._repo.save(existing)
            return False, saved

        now = datetime.now(tz=UTC)
        vehicle = Vehicle(
            id=uuid.uuid4(),
            vehicle_number=sap_number,
            license_plate=PlateNumber(
                sap_dto.license_plate or _deterministic_plate(sap_dto.vehicle_number)
            ),
            status=VehicleStatus.ACTIVE,
            created_at=now,
            updated_at=now,
            commissioning_date=sap_dto.commissioning_date,
            driver1_customer_number=sap_dto.driver1_customer_number,
            driver2_customer_number=sap_dto.driver2_customer_number,
        )
        saved = self._repo.save(vehicle)
        return True, saved

    def _sync_drivers(self, sap_dto: SAPVehicleDriverDTO) -> None:
        if self._driver_repo is None:
            return
        driver_specs = [
            (
                sap_dto.driver1_customer_number,
                sap_dto.driver1_name,
                sap_dto.driver1_mobile,
                sap_dto.driver1_personnel_number,
                sap_dto.driver1_gender,
                sap_dto.driver1_nilofar_code,
            ),
            (
                sap_dto.driver2_customer_number,
                sap_dto.driver2_name,
                sap_dto.driver2_mobile,
                sap_dto.driver2_personnel_number,
                sap_dto.driver2_gender,
                sap_dto.driver2_nilofar_code,
            ),
        ]
        for (
            customer_no,
            name,
            mobile,
            personnel_no,
            gender,
            nilofar_code,
        ) in driver_specs:
            if not customer_no:
                continue
            customer_number = CustomerNumber(customer_no)
            try:
                driver = self._driver_repo.get_by_customer_number(customer_number)
            except DriverNotFoundError:
                now = datetime.now(tz=UTC)
                driver = Driver(
                    id=uuid.uuid4(),
                    customer_number=customer_number,
                    name=name or customer_no,
                    status=DriverStatus.ACTIVE,
                    created_at=now,
                    updated_at=now,
                )
            driver.name = name or driver.name
            driver.mobile = mobile
            driver.personnel_number = personnel_no
            driver.gender = gender
            driver.nilofar_code = nilofar_code
            if driver.status == DriverStatus.DECOMMISSIONED:
                driver.reactivate()
            driver.updated_at = datetime.now(tz=UTC)
            self._driver_repo.save(driver)

    def _atomic_if_supported(self) -> AbstractContextManager[object]:
        """Use database transactions only for repositories backed by Django ORM."""
        if getattr(self._repo, "uses_transactions", False):
            return transaction.atomic()
        return nullcontext()
