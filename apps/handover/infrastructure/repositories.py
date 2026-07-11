"""Infrastructure repository for handovers."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from apps.handover.domain.entities import VehicleHandover, VehicleHandoverStatus
from apps.handover.domain.exceptions import VehicleHandoverNotFoundError
from apps.handover.domain.interfaces.handover_repository import (
    IVehicleHandoverRepository,
)
from apps.handover.infrastructure.models import VehicleHandoverModel


def _to_domain(orm: VehicleHandoverModel) -> VehicleHandover:
    """Map ORM model to aggregate."""
    return VehicleHandover(
        id=orm.id,
        repair_order_id=orm.repair_order_id,
        vehicle_id=orm.vehicle_id,
        status=VehicleHandoverStatus(orm.status),
        created_at=orm.created_at,
        updated_at=orm.updated_at,
        driver_id=orm.driver_id,
        comment=orm.comment or None,
        confirmed_at=orm.confirmed_at,
    )


class DjangoVehicleHandoverRepository(IVehicleHandoverRepository):
    """Django-backed vehicle handover repository."""

    def get_by_id(self, handover_id: uuid.UUID) -> VehicleHandover:
        """Get one handover by id."""
        try:
            orm = VehicleHandoverModel.objects.get(id=handover_id, is_deleted=False)
        except VehicleHandoverModel.DoesNotExist:
            raise VehicleHandoverNotFoundError(handover_id) from None
        return _to_domain(orm)

    def get_by_repair_order(self, repair_order_id: uuid.UUID) -> VehicleHandover | None:
        """Get handover by repair order."""
        orm = VehicleHandoverModel.objects.filter(
            repair_order_id=repair_order_id, is_deleted=False
        ).first()
        return _to_domain(orm) if orm else None

    def list_all(self) -> list[VehicleHandover]:
        """List all handovers."""
        return [
            _to_domain(item)
            for item in VehicleHandoverModel.objects.filter(is_deleted=False).order_by(
                "-created_at"
            )
        ]

    def save(self, handover: VehicleHandover) -> VehicleHandover:
        """Persist handover aggregate."""
        orm, created = VehicleHandoverModel.objects.update_or_create(
            id=handover.id,
            defaults={
                "repair_order_id": handover.repair_order_id,
                "vehicle_id": handover.vehicle_id,
                "driver_id": handover.driver_id,
                "status": handover.status.value,
                "comment": handover.comment or "",
                "confirmed_at": handover.confirmed_at,
                "updated_at": datetime.now(tz=UTC),
            },
        )
        if created:
            orm.created_at = handover.created_at
            orm.save(update_fields=["created_at"])
        return handover
