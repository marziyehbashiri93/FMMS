"""Service that synchronises vehicle data with SAP PM equipment records.

This service is responsible for:
  1. Fetching equipment details from SAP via the ``ISAPEquipmentPort`` port.
  2. Mapping the SAP DTO to mutable vehicle fields.
  3. Persisting the updated vehicle via the repository.

It does NOT perform any SAP write operations; it is a read-and-sync flow.
All SAP write operations must go through ``SAPTransactionManager``.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from apps.vehicle.application.dto.vehicle_dto import VehicleResponseDTO
from apps.vehicle.domain.entities import VEHICLE_STATUS_LABELS
from apps.vehicle.domain.interfaces.vehicle_repository import IVehicleRepository
from apps.vehicle.domain.value_objects import PlateNumber, SAPVehicleNumber
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
        vehicle_number: str,
        request_id: str = "",
    ) -> VehicleResponseDTO:
        """Fetch SAP equipment details and update the matching vehicle record.

        The vehicle is looked up by its SAP equipment number via the repository.
        If no matching vehicle exists, ``FMMSNotFoundError`` is raised.
        The only fields updated are those that can be sourced directly from the
        SAP vehicle-driver OData view.

        Args:
            vehicle_number: SAP VehicleNumber to sync.
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
                "vehicle_number": vehicle_number,
            },
        )

        sap_dto = self._sap.get_equipment(vehicle_number)
        matched_vehicle = self._repo.get_by_vehicle_number(
            SAPVehicleNumber(vehicle_number)
        )

        if matched_vehicle is None:
            raise FMMSNotFoundError(
                message=f"No vehicle linked to SAP VehicleNumber '{vehicle_number}'.",
                details={"vehicle_number": vehicle_number},
            )

        if sap_dto.license_plate:
            matched_vehicle.license_plate = PlateNumber(sap_dto.license_plate)
        matched_vehicle.vehicle_number = SAPVehicleNumber(vehicle_number)
        matched_vehicle.commissioning_date = sap_dto.commissioning_date
        matched_vehicle.driver1_customer_number = sap_dto.driver1_customer_number
        matched_vehicle.driver2_customer_number = sap_dto.driver2_customer_number
        matched_vehicle.updated_at = datetime.now(tz=UTC)
        saved = self._repo.save(matched_vehicle)
        self._repo.record_driver_assignment_snapshot(
            vehicle=saved,
            sync_run_id=uuid.uuid4(),
            synced_at=saved.updated_at,
            request_id=request_id,
        )

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
            vehicle_number=saved.vehicle_number.value,
            license_plate=saved.license_plate.value,
            status=saved.status,
            status_label=VEHICLE_STATUS_LABELS[saved.status],
            created_at=saved.created_at,
            updated_at=saved.updated_at,
            commissioning_date=saved.commissioning_date,
            driver1_customer_number=saved.driver1_customer_number,
            driver2_customer_number=saved.driver2_customer_number,
        )
