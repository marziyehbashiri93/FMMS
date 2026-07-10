"""Django repository for repair-order timeline events."""

from __future__ import annotations

import uuid

from apps.repair.domain.entities import RepairOrderEvent, RepairOrderEventType
from apps.repair.domain.interfaces.repair_order_event_repository import (
    IRepairOrderEventRepository,
)
from apps.repair.infrastructure.models import RepairOrderEventModel, RepairOrderModel


def _to_domain(orm: RepairOrderEventModel) -> RepairOrderEvent:
    return RepairOrderEvent(
        id=orm.id,
        repair_order_id=orm.repair_order_id,
        event_type=RepairOrderEventType(orm.event_type),
        description=orm.description,
        created_at=orm.created_at,
        created_by_id=orm.actor_id,
    )


class DjangoRepairOrderEventRepository(IRepairOrderEventRepository):
    """Persist repair-order timeline events via Django ORM."""

    def append(self, event: RepairOrderEvent) -> RepairOrderEvent:
        """Insert a new timeline event row."""
        orm = RepairOrderEventModel.objects.create(
            id=event.id,
            repair_order_id=event.repair_order_id,
            event_type=event.event_type.value,
            description=event.description,
            actor_id=event.created_by_id,
            created_at=event.created_at,
        )
        return _to_domain(orm)

    def list_by_repair_order(
        self, repair_order_id: uuid.UUID
    ) -> list[RepairOrderEvent]:
        """List events in chronological order."""
        if not RepairOrderModel.objects.filter(
            id=repair_order_id, is_deleted=False
        ).exists():
            return []
        qs = RepairOrderEventModel.objects.filter(
            repair_order_id=repair_order_id,
            is_deleted=False,
        ).order_by("created_at")
        return [_to_domain(row) for row in qs]
