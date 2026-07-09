"""Read-only services for retrieving inspection data.

No mutations happen here. These services are query-side only.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from apps.inspection.application.dto.inspection_dto import InspectionResponseDTO
from apps.inspection.application.services.create_inspection_service import (
    _to_response_dto,
)
from apps.inspection.domain.interfaces.inspection_repository import (
    IInspectionRepository,
)
from core.exceptions.base_exception import FMMSNotFoundError
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger("inspection", __name__)


class GetInspectionService:
    """Fetch a single inspection by its UUID.

    Args:
        inspection_repository: Concrete ``IInspectionRepository``.
    """

    def __init__(self, inspection_repository: IInspectionRepository) -> None:
        self._repo = inspection_repository

    def execute(
        self, inspection_id: uuid.UUID, request_id: str = ""
    ) -> InspectionResponseDTO:
        """Return the inspection identified by ``inspection_id``.

        Args:
            inspection_id: Target inspection UUID.
            request_id: Optional correlation ID for structured logging.

        Returns:
            ``InspectionResponseDTO`` for the requested inspection.

        Raises:
            FMMSNotFoundError: If no inspection with ``inspection_id`` exists.
        """
        logger.info(
            "Fetching inspection",
            extra={
                "domain": "inspection",
                "service": "GetInspectionService",
                "operation": "execute",
                "request_id": request_id,
                "entity_id": str(inspection_id),
            },
        )

        inspection = self._repo.get_by_id(inspection_id)
        if inspection is None:
            raise FMMSNotFoundError(
                message=f"Inspection '{inspection_id}' not found.",
                details={"inspection_id": str(inspection_id)},
            )

        logger.info(
            "Inspection fetched",
            extra={
                "domain": "inspection",
                "service": "GetInspectionService",
                "operation": "execute",
                "request_id": request_id,
                "entity_id": str(inspection_id),
                "result": "success",
            },
        )

        return _to_response_dto(inspection)


class ListInspectionsService:
    """Fetch inspections for a vehicle, optionally filtered by date range.

    Args:
        inspection_repository: Concrete ``IInspectionRepository``.
    """

    def __init__(self, inspection_repository: IInspectionRepository) -> None:
        self._repo = inspection_repository

    def execute(
        self,
        vehicle_id: uuid.UUID,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        request_id: str = "",
    ) -> list[InspectionResponseDTO]:
        """Return inspections for ``vehicle_id``, with optional date filtering.

        When both ``from_date`` and ``to_date`` are provided the repository's
        ``list_by_date_range()`` is used; otherwise ``list_by_vehicle()``
        returns all inspections for the vehicle.

        Args:
            vehicle_id: Target vehicle UUID.
            from_date: Optional inclusive start of date range.
            to_date: Optional inclusive end of date range.
            request_id: Optional correlation ID for structured logging.

        Returns:
            Ordered list of ``InspectionResponseDTO`` objects.
        """
        logger.info(
            "Listing inspections",
            extra={
                "domain": "inspection",
                "service": "ListInspectionsService",
                "operation": "execute",
                "request_id": request_id,
                "vehicle_id": str(vehicle_id),
            },
        )

        if from_date is not None and to_date is not None:
            all_in_range = self._repo.list_by_date_range(
                start=from_date,
                end=to_date,
            )
            inspections = [i for i in all_in_range if i.vehicle_id == vehicle_id]
        else:
            inspections = self._repo.list_by_vehicle(vehicle_id)

        logger.info(
            "Inspections listed",
            extra={
                "domain": "inspection",
                "service": "ListInspectionsService",
                "operation": "execute",
                "request_id": request_id,
                "result": "success",
                "count": len(inspections),
            },
        )

        return [_to_response_dto(i) for i in inspections]
