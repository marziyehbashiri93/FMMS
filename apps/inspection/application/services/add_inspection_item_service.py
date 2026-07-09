"""Service that orchestrates adding a checklist item to a DRAFT inspection.

The domain entity's ``add_item()`` enforces that only DRAFT inspections
can receive new items. This service is responsible for loading, delegating,
persisting, and logging.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from apps.inspection.application.dto.inspection_dto import (
    AddInspectionItemDTO,
    InspectionResponseDTO,
)
from apps.inspection.application.services.create_inspection_service import (
    _to_response_dto,
)
from apps.inspection.domain.entities import InspectionItem
from apps.inspection.domain.interfaces.inspection_repository import (
    IInspectionRepository,
)
from core.exceptions.base_exception import FMMSNotFoundError
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger("inspection", __name__)


class AddInspectionItemService:
    """Orchestrates addition of a checklist item to an existing DRAFT inspection.

    Args:
        inspection_repository: Concrete ``IInspectionRepository``.
    """

    def __init__(self, inspection_repository: IInspectionRepository) -> None:
        self._repo = inspection_repository

    def execute(self, dto: AddInspectionItemDTO) -> InspectionResponseDTO:
        """Add a checklist item to a DRAFT inspection.

        Args:
            dto: Item details.

        Returns:
            ``InspectionResponseDTO`` updated with the new item included.

        Raises:
            FMMSNotFoundError: If no inspection with ``dto.inspection_id`` exists.
            InspectionAlreadySubmittedError: If the inspection is not DRAFT
                (raised by the domain entity).
        """
        logger.info(
            "Adding inspection item",
            extra={
                "domain": "inspection",
                "service": "AddInspectionItemService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(dto.inspection_id),
                "category": dto.category,
            },
        )

        inspection = self._repo.get_by_id(dto.inspection_id)
        if inspection is None:
            raise FMMSNotFoundError(
                message=f"Inspection '{dto.inspection_id}' not found.",
                details={"inspection_id": str(dto.inspection_id)},
            )

        item = InspectionItem(
            id=uuid.uuid4(),
            category=dto.category,
            description=dto.description,
            result=dto.result,
            notes=dto.notes,
        )

        inspection.add_item(item)
        inspection.updated_at = datetime.now(tz=UTC)

        saved = self._repo.save(inspection)

        logger.info(
            "Inspection item added successfully",
            extra={
                "domain": "inspection",
                "service": "AddInspectionItemService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(saved.id),
                "result": "success",
                "item_count": len(saved.items),
            },
        )

        return _to_response_dto(saved)
