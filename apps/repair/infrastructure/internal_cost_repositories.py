"""ORM repository for internal repair costs."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from apps.repair.domain.interfaces.internal_cost_repository import (
    IInternalRepairCostRepository,
)
from apps.repair.domain.internal_cost_entities import (
    InternalRepairCost,
    InternalRepairCostStatus,
)
from apps.repair.infrastructure.models import InternalRepairCostModel
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger(domain="repair", module=__name__)


def _to_domain(orm: InternalRepairCostModel) -> InternalRepairCost:
    """Map ORM row to domain entity."""
    return InternalRepairCost(
        id=uuid.UUID(str(orm.id)),
        repair_order_id=uuid.UUID(str(orm.repair_order_id)),
        invoice_number=orm.invoice_number,
        labor_cost=Decimal(orm.labor_cost),
        parts_cost=Decimal(orm.parts_cost),
        service_cost=Decimal(orm.service_cost),
        currency=orm.currency,
        status=InternalRepairCostStatus(orm.status),
        notes=orm.notes,
        registered_by_id=uuid.UUID(str(orm.registered_by_id)),
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


class DjangoInternalRepairCostRepository(IInternalRepairCostRepository):
    """Django-backed internal repair cost repository."""

    def save(self, cost: InternalRepairCost) -> InternalRepairCost:
        """Create or update a cost document."""
        defaults = {
            "repair_order_id": cost.repair_order_id,
            "invoice_number": cost.invoice_number,
            "labor_cost": cost.labor_cost,
            "parts_cost": cost.parts_cost,
            "service_cost": cost.service_cost,
            "currency": cost.currency,
            "status": cost.status.value,
            "notes": cost.notes,
            "registered_by_id": cost.registered_by_id,
            "updated_at": datetime.now(tz=UTC),
        }
        obj, created = InternalRepairCostModel.objects.update_or_create(
            id=cost.id,
            defaults=defaults,
        )
        if created:
            obj.created_at = cost.created_at
            obj.save(update_fields=["created_at"])
        logger.debug(
            "saved internal repair cost",
            extra={"cost_id": str(cost.id), "is_new": created},
        )
        return cost

    def get_by_repair_order(self, repair_order_id: uuid.UUID) -> InternalRepairCost | None:
        """Return the cost document for a repair order, if any."""
        orm = InternalRepairCostModel.objects.filter(
            repair_order_id=repair_order_id,
            is_deleted=False,
        ).first()
        return _to_domain(orm) if orm else None
