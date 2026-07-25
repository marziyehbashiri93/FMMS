"""Concrete Django ORM implementation of IFaultRepository."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from django.db import transaction

from apps.fault.domain.entities import Fault, FaultItem, FaultStatus
from apps.fault.domain.exceptions import FaultNotFoundError
from apps.fault.domain.interfaces.fault_repository import IFaultRepository
from apps.fault.domain.value_objects import (
    FaultCode,
    FaultDescription,
    FaultSeverity,
    SAPDefectCode,
)
from apps.fault.infrastructure.models import FaultItemModel, FaultModel
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger(domain="fault", module=__name__)


def _item_to_domain(orm: FaultItemModel) -> FaultItem:
    """Map a FaultItemModel to a FaultItem domain entity."""
    return FaultItem(
        id=uuid.UUID(str(orm.id)),
        fault_id=orm.fault_id,
        inspection_item_id=orm.inspection_item_id,
        component=orm.component,
        description=orm.description,
        severity=FaultSeverity(orm.severity),
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


def _to_domain(orm: FaultModel, items: list[FaultItem] | None = None) -> Fault:
    """Map a FaultModel to a Fault domain entity."""
    return Fault(
        id=uuid.UUID(str(orm.id)),
        vehicle_id=orm.vehicle_id,
        code=FaultCode(orm.code),
        description=FaultDescription(orm.description),
        severity=FaultSeverity(orm.severity),
        status=FaultStatus(orm.status),
        reported_by_id=orm.reported_by_id,
        reported_at=orm.reported_at,
        inspection_id=orm.inspection_id,
        sap_defect_code=(
            SAPDefectCode(orm.sap_defect_code) if orm.sap_defect_code else None
        ),
        sap_notification_number=orm.sap_notification_number or None,
        assigned_to_id=orm.assigned_to_id,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
        items=items or [],
    )


def _to_orm_dict(fault: Fault) -> dict[str, object]:
    """Map a Fault domain entity to ORM field values."""
    return {
        "vehicle_id": fault.vehicle_id,
        "code": fault.code.value,
        "description": fault.description.value,
        "reported_at": fault.reported_at,
        "severity": fault.severity.value,
        "status": fault.status.value,
        "reported_by_id": fault.reported_by_id,
        "inspection_id": fault.inspection_id,
        "sap_defect_code": fault.sap_defect_code.value if fault.sap_defect_code else "",
        "sap_notification_number": fault.sap_notification_number or "",
        "assigned_to_id": fault.assigned_to_id,
        "updated_at": datetime.now(tz=UTC),
    }


def _item_to_orm_dict(item: FaultItem) -> dict[str, object]:
    """Map a FaultItem domain entity to ORM field values."""
    return {
        "fault_id": item.fault_id,
        "inspection_item_id": item.inspection_item_id,
        "component": item.component,
        "description": item.description,
        "severity": item.severity.value,
        "updated_at": datetime.now(tz=UTC),
    }


class DjangoFaultRepository(IFaultRepository):
    """Concrete repository for Fault aggregates backed by Django ORM."""

    def _load_items_for_faults(
        self, fault_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, list[FaultItem]]:
        """Batch-load fault items grouped by parent fault ID."""
        if not fault_ids:
            return {}
        item_rows = FaultItemModel.objects.filter(
            fault_id__in=fault_ids,
            is_deleted=False,
        ).order_by("created_at")
        grouped: dict[uuid.UUID, list[FaultItem]] = {
            fault_id: [] for fault_id in fault_ids
        }
        for orm in item_rows:
            grouped.setdefault(orm.fault_id, []).append(_item_to_domain(orm))
        return grouped

    def _attach_items(self, faults: list[Fault]) -> list[Fault]:
        """Populate ``items`` on each fault from persistence."""
        if not faults:
            return faults
        items_by_fault = self._load_items_for_faults([fault.id for fault in faults])
        for fault in faults:
            fault.items = items_by_fault.get(fault.id, [])
        return faults

    def get_by_id(self, fault_id: uuid.UUID) -> Fault:
        """Retrieve a fault by UUID."""
        try:
            orm = FaultModel.objects.get(id=fault_id, is_deleted=False)
        except FaultModel.DoesNotExist:
            raise FaultNotFoundError(fault_id) from None
        items = [
            _item_to_domain(item_orm)
            for item_orm in FaultItemModel.objects.filter(
                fault_id=fault_id,
                is_deleted=False,
            ).order_by("created_at")
        ]
        return _to_domain(orm, items)

    def list_by_vehicle(
        self,
        vehicle_id: uuid.UUID,
        status: FaultStatus | None = None,
    ) -> list[Fault]:
        """Return faults for a vehicle, optionally filtered by status."""
        qs = FaultModel.objects.filter(vehicle_id=vehicle_id, is_deleted=False)
        if status is not None:
            qs = qs.filter(status=status.value)
        faults = [_to_domain(orm) for orm in qs]
        return self._attach_items(faults)

    def list_all(self, status: FaultStatus | None = None) -> list[Fault]:
        """Return all non-deleted faults, optionally filtered by status."""
        qs = FaultModel.objects.filter(is_deleted=False).order_by("-reported_at")
        if status is not None:
            qs = qs.filter(status=status.value)
        faults = [_to_domain(orm) for orm in qs]
        return self._attach_items(faults)

    def has_open_fault_for_vehicle(self, vehicle_id: uuid.UUID) -> bool:
        """Return True when the vehicle has any fault that is not CLOSED."""
        return (
            FaultModel.objects.filter(vehicle_id=vehicle_id, is_deleted=False)
            .exclude(status=FaultStatus.CLOSED.value)
            .exists()
        )

    def list_open_by_severity(self, severity: FaultSeverity) -> list[Fault]:
        """Return all open (not CLOSED) faults with the given severity."""
        qs = FaultModel.objects.filter(
            severity=severity.value,
            is_deleted=False,
        ).exclude(status=FaultStatus.CLOSED.value)
        faults = [_to_domain(orm) for orm in qs]
        return self._attach_items(faults)

    def list_by_inspection(self, inspection_id: uuid.UUID) -> list[Fault]:
        """Return faults that originated from a given inspection."""
        qs = FaultModel.objects.filter(inspection_id=inspection_id, is_deleted=False)
        faults = [_to_domain(orm) for orm in qs]
        return self._attach_items(faults)

    def save(self, fault: Fault) -> Fault:
        """Persist a new or updated fault and its child items."""
        with transaction.atomic():
            obj, created = FaultModel.objects.update_or_create(
                id=fault.id,
                defaults=_to_orm_dict(fault),
            )
            if created:
                obj.created_at = fault.created_at
                obj.save(update_fields=["created_at"])

            if fault.items:
                for item in fault.items:
                    item_obj, item_created = FaultItemModel.objects.update_or_create(
                        id=item.id,
                        defaults=_item_to_orm_dict(item),
                    )
                    if item_created:
                        item_obj.created_at = item.created_at
                        item_obj.save(update_fields=["created_at"])

        logger.debug("saved", extra={"fault_id": str(fault.id), "is_new": created})
        return fault

    def delete(self, fault_id: uuid.UUID) -> None:
        """Soft-delete a fault record."""
        updated = FaultModel.objects.filter(id=fault_id, is_deleted=False).update(
            is_deleted=True,
            deleted_at=datetime.now(tz=UTC),
        )
        if updated == 0:
            raise FaultNotFoundError(fault_id)
