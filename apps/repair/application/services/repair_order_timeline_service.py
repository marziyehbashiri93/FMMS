"""Record and query repair-order workflow timeline events."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from apps.repair.application.dto.repair_dto import RepairOrderTimelineEventDTO
from apps.repair.domain.entities import RepairOrderEvent, RepairOrderEventType
from apps.repair.domain.interfaces.repair_order_event_repository import (
    IRepairOrderEventRepository,
)
from apps.repair.domain.interfaces.repair_repository import IRepairOrderRepository
from core.exceptions.translation import load_or_not_found
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger("repair", __name__)


class RecordRepairOrderEventService:
    """Append a workflow event to a repair order timeline."""

    def __init__(self, event_repository: IRepairOrderEventRepository) -> None:
        self._events = event_repository

    def execute(
        self,
        repair_order_id: uuid.UUID,
        event_type: RepairOrderEventType,
        description: str,
        created_by_id: uuid.UUID | None = None,
        request_id: str = "",
    ) -> RepairOrderEvent:
        """Persist a timeline event."""
        event = RepairOrderEvent(
            id=uuid.uuid4(),
            repair_order_id=repair_order_id,
            event_type=event_type,
            description=description,
            created_at=datetime.now(tz=UTC),
            created_by_id=created_by_id,
        )
        saved = self._events.append(event)
        logger.info(
            "Repair order event recorded",
            extra={
                "domain": "repair",
                "service": "RecordRepairOrderEventService",
                "operation": "execute",
                "request_id": request_id,
                "entity_id": str(repair_order_id),
                "event_type": event_type.value,
            },
        )
        return saved


class GetRepairOrderTimelineService:
    """Return chronological timeline events for a repair order."""

    def __init__(
        self,
        repair_order_repository: IRepairOrderRepository,
        event_repository: IRepairOrderEventRepository,
    ) -> None:
        self._orders = repair_order_repository
        self._events = event_repository

    def execute(
        self, repair_order_id: uuid.UUID, request_id: str = ""
    ) -> list[RepairOrderTimelineEventDTO]:
        """Fetch timeline events for an existing repair order."""
        load_or_not_found(
            lambda: self._orders.get_by_id(repair_order_id),
            message=f"Repair order '{repair_order_id}' not found.",
            details={"repair_order_id": str(repair_order_id)},
        )
        events = self._events.list_by_repair_order(repair_order_id)
        logger.info(
            "Repair order timeline fetched",
            extra={
                "domain": "repair",
                "service": "GetRepairOrderTimelineService",
                "operation": "execute",
                "request_id": request_id,
                "entity_id": str(repair_order_id),
                "count": len(events),
            },
        )
        return [
            RepairOrderTimelineEventDTO(
                event=e.event_type.value,
                description=e.description,
                created_at=e.created_at,
                created_by_id=e.created_by_id,
            )
            for e in events
        ]
