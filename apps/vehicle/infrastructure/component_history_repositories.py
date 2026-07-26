"""ORM repository for vehicle component history."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from apps.vehicle.domain.component_history_entities import (
    ComponentType,
    VehicleComponentHistory,
)
from apps.vehicle.domain.interfaces.component_history_repository import (
    IVehicleComponentHistoryRepository,
)
from apps.vehicle.infrastructure.models import VehicleComponentHistoryModel
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger(domain="vehicle", module=__name__)


def _to_domain(orm: VehicleComponentHistoryModel) -> VehicleComponentHistory:
    """Map ORM row to domain entity."""
    return VehicleComponentHistory(
        id=uuid.UUID(str(orm.id)),
        vehicle_id=uuid.UUID(str(orm.vehicle_id)),
        repair_order_id=uuid.UUID(str(orm.repair_order_id)),
        component_type=ComponentType(orm.component_type),
        material_number=orm.material_number,
        quantity=Decimal(orm.quantity),
        unit_of_measure=orm.unit_of_measure,
        description=orm.description,
        installed_at=orm.installed_at,
        recorded_by_id=uuid.UUID(str(orm.recorded_by_id)),
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


class DjangoVehicleComponentHistoryRepository(IVehicleComponentHistoryRepository):
    """Django-backed component history repository."""

    def save(self, entry: VehicleComponentHistory) -> VehicleComponentHistory:
        """Create or update one history row."""
        defaults = {
            "vehicle_id": entry.vehicle_id,
            "repair_order_id": entry.repair_order_id,
            "component_type": entry.component_type.value,
            "material_number": entry.material_number,
            "quantity": entry.quantity,
            "unit_of_measure": entry.unit_of_measure,
            "description": entry.description,
            "installed_at": entry.installed_at,
            "recorded_by_id": entry.recorded_by_id,
            "updated_at": datetime.now(tz=UTC),
        }
        obj, created = VehicleComponentHistoryModel.objects.update_or_create(
            id=entry.id,
            defaults=defaults,
        )
        if created:
            obj.created_at = entry.created_at
            obj.save(update_fields=["created_at"])
        logger.debug(
            "saved vehicle component history",
            extra={"entry_id": str(entry.id), "is_new": created},
        )
        return entry

    def list_by_vehicle(self, vehicle_id: uuid.UUID) -> list[VehicleComponentHistory]:
        """Return history for a vehicle, newest first."""
        qs = VehicleComponentHistoryModel.objects.filter(
            vehicle_id=vehicle_id,
            is_deleted=False,
        ).order_by("-installed_at")
        return [_to_domain(orm) for orm in qs]

    def list_by_repair_order(
        self, repair_order_id: uuid.UUID
    ) -> list[VehicleComponentHistory]:
        """Return history rows created from one repair order."""
        qs = VehicleComponentHistoryModel.objects.filter(
            repair_order_id=repair_order_id,
            is_deleted=False,
        ).order_by("-installed_at")
        return [_to_domain(orm) for orm in qs]
