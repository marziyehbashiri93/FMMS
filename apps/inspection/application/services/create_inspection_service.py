"""Service that orchestrates the creation of a new inspection (DRAFT status).

Cross-domain check performed here:
- Vehicle must exist (verified via IVehicleRepository).

Driver existence is intentionally NOT verified — inspections may be created
by administrators without a driver present (e.g. workshop entry checks).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from apps.inspection.application.dto.inspection_dto import (
    CreateInspectionDTO,
    InspectionResponseDTO,
)
from apps.inspection.domain.entities import Inspection, InspectionStatus
from apps.inspection.domain.interfaces.inspection_repository import (
    IInspectionRepository,
)
from apps.inspection.domain.value_objects import OdometerReading
from apps.vehicle.domain.interfaces.vehicle_repository import IVehicleRepository
from core.exceptions.base_exception import FMMSNotFoundError
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger("inspection", __name__)


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
            )
            for item in inspection.items
        ],
    )


class CreateInspectionService:
    """Orchestrates creation of a new DRAFT inspection.

    Args:
        inspection_repository: Concrete ``IInspectionRepository``.
        vehicle_repository: Concrete ``IVehicleRepository`` for cross-domain
            vehicle existence check.
    """

    def __init__(
        self,
        inspection_repository: IInspectionRepository,
        vehicle_repository: IVehicleRepository,
    ) -> None:
        self._inspection_repo = inspection_repository
        self._vehicle_repo = vehicle_repository

    def execute(self, dto: CreateInspectionDTO) -> InspectionResponseDTO:
        """Create and persist a new DRAFT inspection.

        Args:
            dto: Input data for the inspection to create.

        Returns:
            ``InspectionResponseDTO`` in DRAFT status with no items.

        Raises:
            FMMSNotFoundError: If no vehicle with ``dto.vehicle_id`` exists.
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
            },
        )

        vehicle = self._vehicle_repo.get_by_id(dto.vehicle_id)
        if vehicle is None:
            raise FMMSNotFoundError(
                message=f"Vehicle '{dto.vehicle_id}' not found.",
                details={"vehicle_id": str(dto.vehicle_id)},
            )

        now = datetime.now(tz=UTC)
        inspection = Inspection(
            id=uuid.uuid4(),
            vehicle_id=dto.vehicle_id,
            driver_id=dto.driver_id,
            inspection_type=dto.inspection_type,
            odometer_reading=OdometerReading(
                value=int(dto.odometer_value), unit=dto.odometer_unit
            ),
            status=InspectionStatus.DRAFT,
            inspected_at=dto.inspected_at,
            created_at=now,
            updated_at=now,
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
            },
        )

        return _to_response_dto(saved)
