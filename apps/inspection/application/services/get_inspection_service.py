"""Read-only services for retrieving inspection data.

No mutations happen here. These services are query-side only.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from apps.driver.domain.interfaces.driver_repository import IDriverRepository
from apps.fault.domain.interfaces.fault_repository import IFaultRepository
from apps.inspection.application.dto.inspection_dto import InspectionResponseDTO
from apps.inspection.application.services.create_inspection_service import (
    _to_response_dto,
)
from apps.inspection.application.services.inspection_response_enricher import (
    enrich_inspection_response,
)
from apps.inspection.domain.interfaces.inspection_repository import (
    IInspectionRepository,
)
from core.exceptions.translation import load_or_not_found
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger("inspection", __name__)


class GetInspectionService:
    """Fetch a single inspection by its UUID.

    Args:
        inspection_repository: Concrete ``IInspectionRepository``.
        fault_repository: Optional fault repository for related fault IDs.
        driver_repository: Optional driver repository for driver summary.
    """

    def __init__(
        self,
        inspection_repository: IInspectionRepository,
        fault_repository: IFaultRepository | None = None,
        driver_repository: IDriverRepository | None = None,
    ) -> None:
        self._repo = inspection_repository
        self._fault_repo = fault_repository
        self._driver_repo = driver_repository

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

        inspection = load_or_not_found(
            lambda: self._repo.get_by_id(inspection_id),
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

        base = _to_response_dto(inspection)
        return enrich_inspection_response(
            inspection,
            base,
            self._fault_repo,
            self._driver_repo,
        )


class ListInspectionsService:
    """Fetch inspections, optionally filtered by vehicle and date range.

    Args:
        inspection_repository: Concrete ``IInspectionRepository``.
        fault_repository: Optional fault repository for related fault IDs.
        driver_repository: Optional driver repository for driver summary.
    """

    def __init__(
        self,
        inspection_repository: IInspectionRepository,
        fault_repository: IFaultRepository | None = None,
        driver_repository: IDriverRepository | None = None,
    ) -> None:
        self._repo = inspection_repository
        self._fault_repo = fault_repository
        self._driver_repo = driver_repository

    def execute(
        self,
        vehicle_id: uuid.UUID | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        request_id: str = "",
    ) -> list[InspectionResponseDTO]:
        """Return inspections with optional vehicle and date filtering.

        When ``vehicle_id`` is omitted, all inspections are returned.
        Date bounds filter ``inspected_at`` inclusively when provided.

        Args:
            vehicle_id: Optional target vehicle UUID.
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
                "vehicle_id": str(vehicle_id) if vehicle_id else None,
            },
        )

        inspections = (
            self._repo.list_by_vehicle(vehicle_id)
            if vehicle_id is not None
            else self._repo.list_all()
        )
        if from_date is not None:
            inspections = [
                inspection
                for inspection in inspections
                if inspection.inspected_at >= from_date
            ]
        if to_date is not None:
            inspections = [
                inspection
                for inspection in inspections
                if inspection.inspected_at <= to_date
            ]

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

        return [
            enrich_inspection_response(
                inspection,
                _to_response_dto(inspection),
                self._fault_repo,
                self._driver_repo,
            )
            for inspection in inspections
        ]
