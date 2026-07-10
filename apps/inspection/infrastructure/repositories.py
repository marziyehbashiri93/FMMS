"""Concrete Django ORM implementation of IInspectionRepository."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from django.db import transaction

from apps.inspection.domain.entities import (
    Inspection,
    InspectionItem,
    InspectionStatus,
    InspectionType,
)
from apps.inspection.domain.exceptions import InspectionNotFoundError
from apps.inspection.domain.interfaces.inspection_repository import (
    IInspectionRepository,
)
from apps.inspection.domain.value_objects import (
    ChecklistResult,
    FailureSeverity,
    OdometerReading,
    OdometerUnit,
)
from apps.inspection.infrastructure.models import InspectionItemModel, InspectionModel
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger(domain="inspection", module=__name__)


def _items_to_domain(orm_items: list[InspectionItemModel]) -> list[InspectionItem]:
    """Map a list of InspectionItemModel instances to domain InspectionItem objects."""
    return [
        InspectionItem(
            id=item.item_id,
            category=item.category,
            description=item.description,
            result=ChecklistResult(item.result),
            notes=item.notes or None,
            severity=FailureSeverity(item.severity)
            if item.severity
            else None,
        )
        for item in orm_items
    ]


def _to_domain(orm: InspectionModel, items: list[InspectionItemModel]) -> Inspection:
    """Map InspectionModel + items to the Inspection domain entity."""
    return Inspection(
        id=uuid.UUID(str(orm.id)),
        vehicle_id=orm.vehicle_id,
        driver_id=orm.driver_id,
        inspection_type=InspectionType(orm.inspection_type),
        odometer_reading=OdometerReading(
            value=orm.odometer_value,
            unit=OdometerUnit(orm.odometer_unit),
        ),
        status=InspectionStatus(orm.status),
        inspected_at=orm.inspected_at,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
        reviewed_by_id=orm.reviewed_by_id,
        review_notes=orm.review_notes or None,
        items=_items_to_domain(list(items)),
    )


def _fetch_orm(inspection_id: uuid.UUID) -> InspectionModel:
    """Fetch a non-deleted InspectionModel or raise InspectionNotFoundError."""
    try:
        return InspectionModel.objects.get(id=inspection_id, is_deleted=False)
    except InspectionModel.DoesNotExist:
        raise InspectionNotFoundError(inspection_id) from None


class DjangoInspectionRepository(IInspectionRepository):
    """Concrete repository for Inspection aggregates backed by Django ORM.

    ``save()`` uses an atomic transaction because it writes both the
    ``InspectionModel`` header and all ``InspectionItemModel`` children.
    """

    def get_by_id(self, inspection_id: uuid.UUID) -> Inspection:
        """Retrieve an inspection by UUID, including all checklist items."""
        orm = _fetch_orm(inspection_id)
        items = list(orm.items.all())
        return _to_domain(orm, items)

    def list_by_vehicle(
        self,
        vehicle_id: uuid.UUID,
        status: InspectionStatus | None = None,
    ) -> list[Inspection]:
        """Return inspections for a vehicle, optionally filtered by status."""
        qs = InspectionModel.objects.filter(vehicle_id=vehicle_id, is_deleted=False)
        if status is not None:
            qs = qs.filter(status=status.value)
        qs = qs.order_by("-inspected_at")
        return [_to_domain(orm, list(orm.items.all())) for orm in qs]

    def save(self, inspection: Inspection) -> Inspection:
        """Persist the inspection aggregate atomically.

        Replaces all checklist items on every save to stay consistent with
        the in-memory entity (which owns the item list).
        """
        with transaction.atomic():
            obj, created = InspectionModel.objects.update_or_create(
                id=inspection.id,
                defaults={
                    "vehicle_id": inspection.vehicle_id,
                    "driver_id": inspection.driver_id,
                    "inspection_type": inspection.inspection_type.value,
                    "odometer_value": inspection.odometer_reading.value,
                    "odometer_unit": inspection.odometer_reading.unit.value,
                    "status": inspection.status.value,
                    "inspected_at": inspection.inspected_at,
                    "reviewed_by_id": inspection.reviewed_by_id,
                    "review_notes": inspection.review_notes or "",
                    "updated_at": datetime.now(tz=UTC),
                },
            )
            if created:
                obj.created_at = inspection.created_at
                obj.save(update_fields=["created_at"])

            obj.items.all().delete()
            InspectionItemModel.objects.bulk_create(
                [
                    InspectionItemModel(
                        inspection=obj,
                        item_id=item.id,
                        category=item.category,
                        description=item.description,
                        result=item.result.value,
                        notes=item.notes or "",
                        severity=item.severity.value if item.severity else "",
                    )
                    for item in inspection.items
                ]
            )
        logger.debug(
            "saved", extra={"inspection_id": str(inspection.id), "is_new": created}
        )
        return inspection

    def list_by_date_range(
        self,
        start: datetime,
        end: datetime,
    ) -> list[Inspection]:
        """Return all inspections conducted within a date range (inclusive).

        Args:
            start: Start of the range (UTC).
            end: End of the range (UTC).

        Returns:
            A list of non-deleted ``Inspection`` aggregates.
        """
        qs = InspectionModel.objects.filter(
            inspected_at__gte=start,
            inspected_at__lte=end,
            is_deleted=False,
        ).order_by("inspected_at")
        return [_to_domain(orm, list(orm.items.all())) for orm in qs]

    def delete(self, inspection_id: uuid.UUID) -> None:
        """Soft-delete an inspection (items are hidden via cascade logic)."""
        updated = InspectionModel.objects.filter(
            id=inspection_id, is_deleted=False
        ).update(
            is_deleted=True,
            deleted_at=datetime.now(tz=UTC),
        )
        if updated == 0:
            raise InspectionNotFoundError(inspection_id)
