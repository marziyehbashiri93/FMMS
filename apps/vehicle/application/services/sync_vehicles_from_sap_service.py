"""Bulk synchronisation of SAP PM equipment master data into FMMS vehicles.

SAP remains the master-data owner. FMMS imports equipment records and
creates or updates local vehicle aggregates idempotently by SAP equipment
number.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from apps.vehicle.application.dto.vehicle_dto import VehicleSAPSyncResultDTO
from apps.vehicle.domain.entities import Vehicle, VehicleCategory, VehicleStatus
from apps.vehicle.domain.interfaces.vehicle_repository import IVehicleRepository
from apps.vehicle.domain.value_objects import (
    VIN,
    ChassisNumber,
    PlateNumber,
    SAPEquipmentNumber,
)
from core.logging.structured_logger import get_structured_logger
from core.sap.dtos.equipment import SAPEquipmentDTO
from core.sap.ports.equipment_port import ISAPEquipmentPort

logger = get_structured_logger("vehicle", __name__)

_DEFAULT_YEAR = 2024
_DEFAULT_MAKE = "SAP"


def _parse_make_model(description: str) -> tuple[str, str]:
    """Derive make/model from an SAP equipment description.

    Args:
        description: Free-text SAP equipment description.

    Returns:
        ``(make, model)`` pair.
    """
    text = (description or "").strip()
    if " — " in text:
        left, right = text.split(" — ", 1)
        if "Toyota" in right or "Isuzu" in right or " " in right:
            parts = right.split(None, 1)
            if len(parts) == 2:
                return parts[0], parts[1]
            return _DEFAULT_MAKE, right
        return left.strip() or _DEFAULT_MAKE, right.strip() or text
    if not text:
        return _DEFAULT_MAKE, "Unknown"
    return _DEFAULT_MAKE, text


def _map_category(sap_category: str | None) -> VehicleCategory:
    """Map SAP equipment category codes to FMMS vehicle categories.

    Args:
        sap_category: Optional SAP equipment category code.

    Returns:
        Matching ``VehicleCategory``.
    """
    if sap_category in {"F", "L", "LIGHT"}:
        return VehicleCategory.LIGHT
    if sap_category in {"H", "HEAVY"}:
        return VehicleCategory.HEAVY
    if sap_category in {"M", "MOTORCYCLE"}:
        return VehicleCategory.MOTORCYCLE
    return VehicleCategory.SPECIAL


def _deterministic_plate(equipment_number: str) -> str:
    """Build a stable FMMS plate from the SAP equipment number.

    Args:
        equipment_number: SAP equipment number digits.

    Returns:
        Plate string within the PlateNumber length limit.
    """
    return f"EQ{equipment_number}"[-20:]


def _deterministic_vin(equipment_number: str) -> str:
    """Build a stable ISO-3779-compatible VIN from the SAP equipment number.

    Args:
        equipment_number: SAP equipment number digits.

    Returns:
        Exactly 17 alphanumeric characters without I/O/Q.
    """
    digits = "".join(ch for ch in equipment_number if ch.isdigit()).zfill(12)[-12:]
    return f"FMMS0{digits}"


def _apply_sap_fields(vehicle: Vehicle, sap_dto: SAPEquipmentDTO) -> None:
    """Update mutable vehicle fields from an SAP equipment DTO.

    Args:
        vehicle: Target vehicle aggregate.
        sap_dto: Source SAP equipment record.
    """
    make, model = _parse_make_model(sap_dto.description)
    vehicle.make = make
    vehicle.model = model
    vehicle.category = _map_category(sap_dto.category)
    if sap_dto.serial_number:
        vehicle.chassis_number = ChassisNumber(sap_dto.serial_number[:50])
    vehicle.sap_equipment_number = SAPEquipmentNumber(sap_dto.equipment_number)
    vehicle.updated_at = datetime.now(tz=UTC)


class SyncVehiclesFromSAPService:
    """Import/create/update FMMS vehicles from SAP equipment master data.

    Args:
        vehicle_repository: Concrete ``IVehicleRepository``.
        sap_equipment_port: Concrete ``ISAPEquipmentPort``.
    """

    def __init__(
        self,
        vehicle_repository: IVehicleRepository,
        sap_equipment_port: ISAPEquipmentPort,
    ) -> None:
        self._repo = vehicle_repository
        self._sap = sap_equipment_port

    def execute(
        self,
        request_id: str = "",
        plant: str | None = None,
    ) -> VehicleSAPSyncResultDTO:
        """Synchronise all SAP equipment records into FMMS vehicles.

        Matching key is ``sap_equipment_number``. Existing vehicles are
        updated; missing vehicles are created. Failures are counted and
        do not abort the remaining records.

        Args:
            request_id: Optional correlation ID for structured logging.
            plant: Optional SAP plant filter for ``list_equipment``.

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

        equipment_list = self._sap.list_equipment(plant=plant)
        created = 0
        updated = 0
        failed = 0

        for sap_dto in equipment_list:
            try:
                if self._sync_one(sap_dto):
                    created += 1
                else:
                    updated += 1
            except Exception as exc:  # noqa: BLE001 — per-record isolation
                failed += 1
                logger.error(
                    "Failed to sync SAP equipment record",
                    extra={
                        "domain": "vehicle",
                        "service": "SyncVehiclesFromSAPService",
                        "operation": "execute",
                        "request_id": request_id,
                        "sap_equipment_number": sap_dto.equipment_number,
                        "exception": str(exc),
                    },
                    exc_info=True,
                )

        result = VehicleSAPSyncResultDTO(
            total_received=len(equipment_list),
            created=created,
            updated=updated,
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
                "failed_count": result.failed,
            },
        )
        return result

    def _sync_one(self, sap_dto: SAPEquipmentDTO) -> bool:
        """Create or update one vehicle from an SAP equipment DTO.

        Args:
            sap_dto: SAP equipment master record.

        Returns:
            ``True`` when a new vehicle was created, ``False`` when updated.
        """
        sap_number = SAPEquipmentNumber(sap_dto.equipment_number)
        existing = self._repo.get_by_sap_equipment_number(sap_number)
        if existing is not None:
            _apply_sap_fields(existing, sap_dto)
            self._repo.save(existing)
            return False

        now = datetime.now(tz=UTC)
        make, model = _parse_make_model(sap_dto.description)
        vehicle = Vehicle(
            id=uuid.uuid4(),
            plate_number=PlateNumber(_deterministic_plate(sap_dto.equipment_number)),
            vin=VIN(_deterministic_vin(sap_dto.equipment_number)),
            make=make,
            model=model,
            year=_DEFAULT_YEAR,
            category=_map_category(sap_dto.category),
            status=VehicleStatus.ACTIVE,
            created_at=now,
            updated_at=now,
            chassis_number=(
                ChassisNumber(sap_dto.serial_number[:50])
                if sap_dto.serial_number
                else None
            ),
            sap_equipment_number=sap_number,
        )
        self._repo.save(vehicle)
        return True
