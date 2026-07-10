"""Internal helper for recording repair-order timeline events from services."""

from __future__ import annotations

import uuid

from apps.repair.application.services.repair_order_timeline_service import (
    RecordRepairOrderEventService,
)
from apps.repair.domain.entities import RepairOrderEventType


def record_repair_timeline_event(
    recorder: RecordRepairOrderEventService | None,
    repair_order_id: uuid.UUID,
    event_type: RepairOrderEventType,
    description: str,
    created_by_id: uuid.UUID | None = None,
    request_id: str = "",
) -> None:
    """Record a timeline event when a recorder is configured."""
    if recorder is None:
        return
    recorder.execute(
        repair_order_id=repair_order_id,
        event_type=event_type,
        description=description,
        created_by_id=created_by_id,
        request_id=request_id,
    )
