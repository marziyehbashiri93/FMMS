"""Driver workflow service for vehicle exit from the fleet center."""

from __future__ import annotations

from datetime import UTC, datetime

from apps.driver.application.dto.driver_dto import DriverExitCenterDTO
from apps.driver.domain.interfaces.driver_repository import IDriverRepository
from apps.fault.domain.entities import FaultStatus
from apps.fault.domain.interfaces.fault_repository import IFaultRepository
from apps.inspection.domain.entities import InspectionStatus
from apps.inspection.domain.interfaces.inspection_repository import (
    IInspectionRepository,
)
from apps.repair.domain.interfaces.repair_repository import IRepairOrderRepository
from apps.vehicle.application.dto.vehicle_dto import VehicleResponseDTO
from apps.vehicle.application.mappers import vehicle_to_response_dto
from apps.vehicle.domain.entities import VehicleStatus
from apps.vehicle.domain.interfaces.vehicle_repository import IVehicleRepository
from core.exceptions.base_exception import FMMSConflictError, FMMSValidationError
from core.exceptions.translation import load_or_not_found
from core.logging.structured_logger import get_structured_logger
from core.workflow import assert_vehicle_has_no_open_flow

logger = get_structured_logger("driver", __name__)

_EXIT_ALLOWED_INSPECTION_STATUSES = frozenset(
    {
        InspectionStatus.SUBMITTED,
        InspectionStatus.APPROVED,
    }
)


class DriverExitCenterService:
    """Mark an assigned vehicle as exited after a valid daily checklist."""

    def __init__(
        self,
        driver_repository: IDriverRepository,
        vehicle_repository: IVehicleRepository,
        inspection_repository: IInspectionRepository,
        fault_repository: IFaultRepository,
        repair_order_repository: IRepairOrderRepository,
    ) -> None:
        self._driver_repo = driver_repository
        self._vehicle_repo = vehicle_repository
        self._inspection_repo = inspection_repository
        self._fault_repo = fault_repository
        self._repair_repo = repair_order_repository

    def execute(self, dto: DriverExitCenterDTO) -> VehicleResponseDTO:
        """Set a driver's assigned vehicle to ``EXITED_CENTER``.

        Args:
            dto: Driver, vehicle, and submitted checklist identifiers.

        Returns:
            Updated vehicle response DTO.

        Raises:
            FMMSNotFoundError: If driver, vehicle, or inspection does not exist.
            FMMSValidationError: If checklist or assignment data does not match.
            FMMSConflictError: If checklist failures are undisposed or vehicle is not ACTIVE.
            FMMSStateError: If the vehicle still has an open fault/repair flow.
            VehicleInvalidStateTransitionError: If the transition is not allowed.
        """
        logger.info(
            "Driver requesting vehicle center exit",
            extra={
                "domain": "driver",
                "service": "DriverExitCenterService",
                "operation": "execute",
                "request_id": dto.request_id,
                "driver_id": str(dto.driver_id),
                "vehicle_id": str(dto.vehicle_id),
                "inspection_id": str(dto.inspection_id),
                "user_id": str(dto.requested_by_user_id),
            },
        )

        driver = load_or_not_found(
            lambda: self._driver_repo.get_by_id(dto.driver_id),
            message=f"Driver '{dto.driver_id}' not found.",
            details={"driver_id": str(dto.driver_id)},
        )
        vehicle = load_or_not_found(
            lambda: self._vehicle_repo.get_by_id(dto.vehicle_id),
            message=f"Vehicle '{dto.vehicle_id}' not found.",
            details={"vehicle_id": str(dto.vehicle_id)},
        )
        inspection = load_or_not_found(
            lambda: self._inspection_repo.get_by_id(dto.inspection_id),
            message=f"Inspection '{dto.inspection_id}' not found.",
            details={"inspection_id": str(dto.inspection_id)},
        )

        customer_number = driver.customer_number.value
        if customer_number not in {
            vehicle.driver1_customer_number,
            vehicle.driver2_customer_number,
        }:
            raise FMMSValidationError(
                message="Driver is not assigned to this vehicle.",
                error_code="DRIVER_NOT_ASSIGNED_TO_VEHICLE",
                details={
                    "driver_id": str(dto.driver_id),
                    "vehicle_id": str(dto.vehicle_id),
                },
            )
        if inspection.vehicle_id != vehicle.id:
            raise FMMSValidationError(
                message="Checklist inspection does not belong to this vehicle.",
                error_code="CHECKLIST_VEHICLE_MISMATCH",
                details={
                    "vehicle_id": str(dto.vehicle_id),
                    "inspection_id": str(dto.inspection_id),
                },
            )
        if inspection.status not in _EXIT_ALLOWED_INSPECTION_STATUSES:
            raise FMMSConflictError(
                message="Vehicle exit requires a submitted daily checklist.",
                error_code="CHECKLIST_NOT_SUBMITTED",
                details={
                    "inspection_id": str(dto.inspection_id),
                    "status": inspection.status.value,
                },
            )
        assert_vehicle_has_no_open_flow(
            vehicle.id,
            fault_repository=self._fault_repo,
            repair_order_repository=self._repair_repo,
        )
        if inspection.failed_items():
            # Failures block exit until distribution disposes the reported fault.
            # After distribution-usable (fault CLOSED for this checklist), exit is
            # allowed on the same inspection — no new checklist is required.
            inspection_faults = self._fault_repo.list_by_inspection(inspection.id)
            disposition_cleared = bool(inspection_faults) and all(
                fault.status == FaultStatus.CLOSED for fault in inspection_faults
            )
            if not disposition_cleared:
                raise FMMSConflictError(
                    message="Vehicle cannot exit center with failed checklist items.",
                    error_code="CHECKLIST_HAS_FAILURES",
                    details={"inspection_id": str(dto.inspection_id)},
                )
        if vehicle.status != VehicleStatus.ACTIVE:
            raise FMMSConflictError(
                message="Only active vehicles can exit the fleet center.",
                error_code="VEHICLE_NOT_ACTIVE",
                details={
                    "vehicle_id": str(vehicle.id),
                    "status": vehicle.status.value,
                },
            )

        vehicle.transition_to(VehicleStatus.EXITED_CENTER)
        vehicle.updated_at = datetime.now(tz=UTC)
        saved = self._vehicle_repo.save(vehicle)

        logger.info(
            "Vehicle marked as exited center",
            extra={
                "domain": "driver",
                "service": "DriverExitCenterService",
                "operation": "execute",
                "request_id": dto.request_id,
                "vehicle_id": str(saved.id),
                "result": "success",
            },
        )
        return vehicle_to_response_dto(saved)
