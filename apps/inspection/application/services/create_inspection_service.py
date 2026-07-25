"""Service that orchestrates the creation of a new inspection (DRAFT status).

Cross-domain checks:
- Vehicle must exist and be ACTIVE (operational).
- DRIVER actors must be linked via SAP personnel_number and may only inspect
  vehicles currently assigned to them.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from apps.driver.domain.entities import Driver
from apps.driver.domain.interfaces.driver_repository import IDriverRepository
from apps.inspection.application.dto.inspection_dto import (
    CreateInspectionDTO,
    InspectionResponseDTO,
)
from apps.inspection.domain.entities import Inspection, InspectionItem, InspectionStatus
from apps.inspection.domain.interfaces.inspection_repository import (
    IInspectionRepository,
)
from apps.inspection.domain.value_objects import OdometerReading
from apps.vehicle.domain.entities import Vehicle, VehicleStatus
from apps.vehicle.domain.interfaces.vehicle_repository import IVehicleRepository
from core.exceptions.base_exception import FMMSConflictError, FMMSValidationError
from core.exceptions.translation import load_or_not_found
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger("inspection", __name__)

_DRIVER_ROLE = "DRIVER"


def assert_vehicle_is_operational_for_checklist(
    *,
    vehicle_id: uuid.UUID,
    vehicle_repository: IVehicleRepository,
) -> Vehicle:
    """Return the vehicle when it is ACTIVE (عملیاتی).

    Args:
        vehicle_id: Target vehicle UUID.
        vehicle_repository: Vehicle persistence port.

    Returns:
        Loaded operational vehicle aggregate.

    Raises:
        FMMSNotFoundError: If the vehicle does not exist.
        FMMSConflictError: If the vehicle status is not ACTIVE.
    """
    vehicle = load_or_not_found(
        lambda: vehicle_repository.get_by_id(vehicle_id),
        message=f"Vehicle '{vehicle_id}' not found.",
        details={"vehicle_id": str(vehicle_id)},
    )
    if vehicle.status != VehicleStatus.ACTIVE:
        raise FMMSConflictError(
            message=(
                "Checklist can only be registered for operational (ACTIVE) vehicles."
            ),
            error_code="VEHICLE_NOT_OPERATIONAL",
            details={
                "vehicle_id": str(vehicle.id),
                "status": vehicle.status.value,
            },
        )
    return vehicle


def resolve_driver_actor_for_checklist(
    *,
    actor_role: str,
    actor_personnel_number: str,
    vehicle: Vehicle,
    driver_repository: IDriverRepository,
) -> Driver | None:
    """Resolve and authorize a DRIVER actor for checklist creation.

    Non-driver roles return ``None`` (no assignment restriction).

    Args:
        actor_role: Authenticated FMMS role code.
        actor_personnel_number: SAP personnel number from the login user.
        vehicle: Target operational vehicle.
        driver_repository: Driver persistence port.

    Returns:
        Linked driver when actor is DRIVER; otherwise ``None``.

    Raises:
        FMMSValidationError: If DRIVER has no personnel link or SAP driver.
        FMMSConflictError: If the vehicle is not assigned to that driver.
    """
    if actor_role != _DRIVER_ROLE:
        return None

    personnel = actor_personnel_number.strip()
    if not personnel:
        raise FMMSValidationError(
            message=(
                "Driver users must have a SAP personnel number "
                "(کد پرسنلی) linked on their FMMS account."
            ),
            error_code="PERSONNEL_NUMBER_REQUIRED",
            details={"role": actor_role},
        )

    driver = driver_repository.find_by_personnel_number(personnel)
    if driver is None:
        raise FMMSValidationError(
            message=(
                "No active SAP driver found for this personnel number. "
                "Sync drivers from SAP or verify the user link."
            ),
            error_code="DRIVER_LINK_NOT_FOUND",
            details={"personnel_number": personnel},
        )

    assigned = {
        vehicle.driver1_customer_number,
        vehicle.driver2_customer_number,
    }
    if driver.customer_number.value not in assigned:
        raise FMMSConflictError(
            message=(
                "Drivers may only register checklists for vehicles "
                "currently assigned to them."
            ),
            error_code="VEHICLE_NOT_ASSIGNED_TO_DRIVER",
            details={
                "vehicle_id": str(vehicle.id),
                "driver_id": str(driver.id),
                "customer_number": driver.customer_number.value,
            },
        )
    return driver


def _to_response_dto(inspection: Inspection) -> InspectionResponseDTO:
    """Map domain entity → response DTO."""
    from apps.inspection.application.dto.inspection_dto import (  # noqa: PLC0415
        InspectionItemResponseDTO,
    )

    return InspectionResponseDTO(
        id=inspection.id,
        vehicle_id=inspection.vehicle_id,
        inspection_type=inspection.inspection_type,
        odometer_value=inspection.odometer_reading.value,
        odometer_unit=inspection.odometer_reading.unit,
        status=inspection.status,
        inspected_at=inspection.inspected_at,
        created_at=inspection.created_at,
        updated_at=inspection.updated_at,
        driver_id=inspection.driver_id,
        reviewed_by_id=inspection.reviewed_by_id,
        review_notes=inspection.review_notes,
        has_failures=inspection.has_failures,
        items=[
            InspectionItemResponseDTO(
                id=item.id,
                category=item.category,
                description=item.description,
                result=item.result,
                notes=item.notes,
                severity=item.severity,
            )
            for item in inspection.items
        ],
    )


class CreateInspectionService:
    """Orchestrates creation of a new DRAFT inspection.

    Args:
        inspection_repository: Concrete ``IInspectionRepository``.
        vehicle_repository: Concrete ``IVehicleRepository``.
        driver_repository: Concrete ``IDriverRepository`` for DRIVER scoping.
    """

    def __init__(
        self,
        inspection_repository: IInspectionRepository,
        vehicle_repository: IVehicleRepository,
        driver_repository: IDriverRepository,
    ) -> None:
        self._inspection_repo = inspection_repository
        self._vehicle_repo = vehicle_repository
        self._driver_repo = driver_repository

    def execute(self, dto: CreateInspectionDTO) -> InspectionResponseDTO:
        """Create and persist a new DRAFT inspection.

        Optional ``dto.items`` are attached immediately so a driver can
        create + fill checklist results in one request after loading
        SAP-synced templates.

        Args:
            dto: Input data for the inspection to create.

        Returns:
            ``InspectionResponseDTO`` in DRAFT status.

        Raises:
            FMMSNotFoundError: If no vehicle with ``dto.vehicle_id`` exists.
            FMMSConflictError: If the vehicle is not operational / not assigned.
            FMMSValidationError: If DRIVER identity cannot be resolved.
        """
        logger.info(
            "Creating inspection",
            extra={
                "domain": "inspection",
                "service": "CreateInspectionService",
                "operation": "execute",
                "request_id": dto.request_id,
                "vehicle_id": str(dto.vehicle_id),
                "inspection_type": dto.inspection_type,
                "actor_role": dto.actor_role,
            },
        )

        vehicle = assert_vehicle_is_operational_for_checklist(
            vehicle_id=dto.vehicle_id,
            vehicle_repository=self._vehicle_repo,
        )
        linked_driver = resolve_driver_actor_for_checklist(
            actor_role=dto.actor_role,
            actor_personnel_number=dto.actor_personnel_number,
            vehicle=vehicle,
            driver_repository=self._driver_repo,
        )
        driver_id = linked_driver.id if linked_driver is not None else dto.driver_id

        now = datetime.now(tz=UTC)
        inspection = Inspection(
            id=uuid.uuid4(),
            vehicle_id=dto.vehicle_id,
            driver_id=driver_id,
            inspection_type=dto.inspection_type,
            odometer_reading=OdometerReading(
                value=int(dto.odometer_value), unit=dto.odometer_unit
            ),
            status=InspectionStatus.DRAFT,
            inspected_at=dto.inspected_at,
            created_at=now,
            updated_at=now,
        )
        for item_dto in dto.items:
            inspection.add_item(
                InspectionItem(
                    id=uuid.uuid4(),
                    category=item_dto.category,
                    description=item_dto.description,
                    result=item_dto.result,
                    notes=item_dto.notes,
                    severity=item_dto.severity,
                )
            )

        saved = self._inspection_repo.save(inspection)

        logger.info(
            "Inspection created successfully",
            extra={
                "domain": "inspection",
                "service": "CreateInspectionService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(saved.id),
                "result": "success",
                "item_count": len(saved.items),
            },
        )

        return _to_response_dto(saved)
