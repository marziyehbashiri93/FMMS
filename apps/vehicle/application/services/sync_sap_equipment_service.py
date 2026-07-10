"""Service that synchronises vehicle data with SAP PM equipment records.

This service is responsible for:
  1. Fetching equipment details from SAP via the ``ISAPEquipmentPort`` port.
  2. Mapping the SAP DTO to mutable vehicle fields.
  3. Persisting the updated vehicle via the repository.

It does NOT perform any SAP write operations; it is a read-and-sync flow.
All SAP write operations must go through ``SAPTransactionManager``.
"""

from __future__ import annotations

from datetime import UTC, datetime

from apps.vehicle.application.dto.vehicle_dto import VehicleResponseDTO
from apps.vehicle.domain.interfaces.vehicle_repository import IVehicleRepository
from apps.vehicle.domain.value_objects import ChassisNumber, SAPEquipmentNumber
from core.exceptions.base_exception import FMMSNotFoundError
from core.logging.structured_logger import get_structured_logger
from core.sap.ports.equipment_port import ISAPEquipmentPort

logger = get_structured_logger("vehicle", __name__)


class SyncSAPEquipmentService:
    """Synchronise a fleet vehicle with its corresponding SAP PM equipment record.

    Args:
        vehicle_repository: Concrete ``IVehicleRepository``.
        sap_equipment_port: Concrete implementation of ``ISAPEquipmentPort``
            (could be the real OData adapter or the mock during testing).
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
        sap_equipment_number: str,
        request_id: str = "",
    ) -> VehicleResponseDTO:
        """Fetch SAP equipment details and update the matching vehicle record.

        The vehicle is looked up by its SAP equipment number via the repository.
        If no matching vehicle exists, ``FMMSNotFoundError`` is raised.
        The only fields updated are those that can be sourced directly from the
        SAP ``SAPEquipmentDTO`` (description → model, serial → chassis).

        Args:
            sap_equipment_number: SAP PM equipment number to sync.
            request_id: Optional correlation ID for structured logging.

        Returns:
            ``VehicleResponseDTO`` with the updated model description.

        Raises:
            FMMSNotFoundError: If no vehicle is linked to the given equipment
                number.
        """
        logger.info(
            "Syncing vehicle with SAP equipment",
            extra={
                "domain": "vehicle",
                "service": "SyncSAPEquipmentService",
                "operation": "execute",
                "request_id": request_id,
                "sap_equipment_number": sap_equipment_number,
            },
        )

        sap_dto = self._sap.get_equipment(sap_equipment_number)
        matched_vehicle = self._repo.get_by_sap_equipment_number(
            SAPEquipmentNumber(sap_equipment_number)
        )

        if matched_vehicle is None:
            raise FMMSNotFoundError(
                message=f"No vehicle linked to SAP equipment '{sap_equipment_number}'.",
                details={"sap_equipment_number": sap_equipment_number},
            )

        if sap_dto.description:
            matched_vehicle.model = sap_dto.description
        if sap_dto.serial_number:
            matched_vehicle.chassis_number = ChassisNumber(sap_dto.serial_number[:50])
        matched_vehicle.sap_equipment_number = SAPEquipmentNumber(sap_equipment_number)
        matched_vehicle.updated_at = datetime.now(tz=UTC)
        saved = self._repo.save(matched_vehicle)

        logger.info(
            "Vehicle synced with SAP successfully",
            extra={
                "domain": "vehicle",
                "service": "SyncSAPEquipmentService",
                "operation": "execute",
                "request_id": request_id,
                "entity_id": str(saved.id),
                "result": "success",
            },
        )

        return VehicleResponseDTO(
            id=saved.id,
            plate_number=saved.plate_number.value,
            vin=saved.vin.value,
            make=saved.make,
            model=saved.model,
            year=saved.year,
            category=saved.category,
            status=saved.status,
            created_at=saved.created_at,
            updated_at=saved.updated_at,
            chassis_number=saved.chassis_number.value if saved.chassis_number else None,
            sap_equipment_number=(
                saved.sap_equipment_number.value if saved.sap_equipment_number else None
            ),
        )
