"""Concrete Django ORM implementations for the Procurement bounded context.

Both save() methods use transaction.atomic() because they write a parent
record plus child line items atomically.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from django.db import transaction

from apps.procurement.domain.entities import (
    POLineItem,
    POStatus,
    PRLineItem,
    PRStatus,
    PurchaseOrder,
    PurchaseRequisition,
)
from apps.procurement.domain.exceptions import PONotFoundError, PRNotFoundError
from apps.procurement.domain.interfaces.procurement_repository import (
    IPurchaseOrderRepository,
    IPurchaseRequisitionRepository,
)
from apps.procurement.domain.value_objects import (
    MaterialNumber,
    Money,
    Quantity,
    SAPDocumentNumber,
    VendorNumber,
)
from apps.procurement.infrastructure.models import (
    POLineItemModel,
    PRLineItemModel,
    PurchaseOrderModel,
    PurchaseRequisitionModel,
)
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger(domain="procurement", module=__name__)


def _pr_to_domain(orm: PurchaseRequisitionModel) -> PurchaseRequisition:
    """Map PurchaseRequisitionModel to PurchaseRequisition domain aggregate."""
    items = [
        PRLineItem(
            id=li.item_id,
            material_number=MaterialNumber(li.material_number),
            quantity=Quantity(
                value=li.quantity_value,
                unit_of_measure=li.quantity_uom,
            ),
            description=li.description,
            estimated_price=(
                Money(
                    amount=li.estimated_price_amount,
                    currency=li.estimated_price_currency,
                )
                if li.estimated_price_amount is not None
                else None
            ),
        )
        for li in orm.line_items.all()
    ]
    return PurchaseRequisition(
        id=uuid.UUID(str(orm.id)),
        repair_order_id=orm.repair_order_id,
        status=PRStatus(orm.status),
        requested_by_id=orm.requested_by_id,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
        line_items=items,
        sap_pr_number=(
            SAPDocumentNumber(orm.sap_pr_number) if orm.sap_pr_number else None
        ),
        approved_by_id=orm.approved_by_id,
    )


def _po_to_domain(orm: PurchaseOrderModel) -> PurchaseOrder:
    """Map PurchaseOrderModel to PurchaseOrder domain aggregate."""
    items = [
        POLineItem(
            id=li.item_id,
            material_number=MaterialNumber(li.material_number),
            quantity=Quantity(
                value=li.quantity_value,
                unit_of_measure=li.quantity_uom,
            ),
            unit_price=Money(
                amount=li.unit_price_amount,
                currency=li.unit_price_currency,
            ),
            received_quantity=li.received_quantity,
        )
        for li in orm.line_items.all()
    ]
    return PurchaseOrder(
        id=uuid.UUID(str(orm.id)),
        pr_id=orm.pr_id,
        vendor_number=VendorNumber(orm.vendor_number),
        status=POStatus(orm.status),
        created_by_id=orm.po_initiator_id,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
        line_items=items,
        sap_po_number=(
            SAPDocumentNumber(orm.sap_po_number) if orm.sap_po_number else None
        ),
        approved_by_id=orm.approved_by_id,
    )


class DjangoPurchaseRequisitionRepository(IPurchaseRequisitionRepository):
    """Concrete repository for PurchaseRequisition aggregates backed by Django ORM."""

    def get_by_id(self, pr_id: uuid.UUID) -> PurchaseRequisition:
        """Retrieve a PR by UUID."""
        try:
            orm = PurchaseRequisitionModel.objects.get(id=pr_id, is_deleted=False)
        except PurchaseRequisitionModel.DoesNotExist:
            raise PRNotFoundError(pr_id) from None
        return _pr_to_domain(orm)

    def list_by_repair_order(
        self, repair_order_id: uuid.UUID
    ) -> list[PurchaseRequisition]:
        """Return PRs linked to a repair order."""
        qs = PurchaseRequisitionModel.objects.filter(
            repair_order_id=repair_order_id, is_deleted=False
        )
        return [_pr_to_domain(orm) for orm in qs]

    def list_by_status(self, status: PRStatus) -> list[PurchaseRequisition]:
        """Return all PRs matching a status."""
        qs = PurchaseRequisitionModel.objects.filter(
            status=status.value, is_deleted=False
        )
        return [_pr_to_domain(orm) for orm in qs]

    def save(self, pr: PurchaseRequisition) -> PurchaseRequisition:
        """Atomically persist the PR and its line items."""
        with transaction.atomic():
            obj, created = PurchaseRequisitionModel.objects.update_or_create(
                id=pr.id,
                defaults={
                    "repair_order_id": pr.repair_order_id,
                    "status": pr.status.value,
                    "requested_by_id": pr.requested_by_id,
                    "sap_pr_number": (
                        pr.sap_pr_number.value if pr.sap_pr_number else ""
                    ),
                    "approved_by_id": pr.approved_by_id,
                    "updated_at": datetime.now(tz=UTC),
                },
            )
            if created:
                obj.created_at = pr.created_at
                obj.save(update_fields=["created_at"])

            obj.line_items.all().delete()
            PRLineItemModel.objects.bulk_create(
                [
                    PRLineItemModel(
                        pr=obj,
                        item_id=item.id,
                        material_number=item.material_number.value,
                        quantity_value=item.quantity.value,
                        quantity_uom=item.quantity.unit_of_measure,
                        description=item.description,
                        estimated_price_amount=(
                            item.estimated_price.amount
                            if item.estimated_price
                            else None
                        ),
                        estimated_price_currency=(
                            item.estimated_price.currency
                            if item.estimated_price
                            else ""
                        ),
                    )
                    for item in pr.line_items
                ]
            )
        logger.debug("pr saved", extra={"pr_id": str(pr.id), "is_new": created})
        return pr

    def delete(self, pr_id: uuid.UUID) -> None:
        """Soft-delete a PR record."""
        updated = PurchaseRequisitionModel.objects.filter(
            id=pr_id, is_deleted=False
        ).update(
            is_deleted=True,
            deleted_at=datetime.now(tz=UTC),
        )
        if updated == 0:
            raise PRNotFoundError(pr_id)


class DjangoPurchaseOrderRepository(IPurchaseOrderRepository):
    """Concrete repository for PurchaseOrder aggregates backed by Django ORM."""

    def get_by_id(self, po_id: uuid.UUID) -> PurchaseOrder:
        """Retrieve a PO by UUID."""
        try:
            orm = PurchaseOrderModel.objects.get(id=po_id, is_deleted=False)
        except PurchaseOrderModel.DoesNotExist:
            raise PONotFoundError(po_id) from None
        return _po_to_domain(orm)

    def list_by_pr(self, pr_id: uuid.UUID) -> list[PurchaseOrder]:
        """Return POs created from a given PR."""
        qs = PurchaseOrderModel.objects.filter(pr_id=pr_id, is_deleted=False)
        return [_po_to_domain(orm) for orm in qs]

    def list_by_status(self, status: POStatus) -> list[PurchaseOrder]:
        """Return all POs matching a status."""
        qs = PurchaseOrderModel.objects.filter(status=status.value, is_deleted=False)
        return [_po_to_domain(orm) for orm in qs]

    def save(self, po: PurchaseOrder) -> PurchaseOrder:
        """Atomically persist the PO and its line items."""
        with transaction.atomic():
            obj, created = PurchaseOrderModel.objects.update_or_create(
                id=po.id,
                defaults={
                    "pr_id": po.pr_id,
                    "vendor_number": po.vendor_number.value,
                    "status": po.status.value,
                    "po_initiator_id": po.created_by_id,
                    "sap_po_number": (
                        po.sap_po_number.value if po.sap_po_number else ""
                    ),
                    "approved_by_id": po.approved_by_id,
                    "updated_at": datetime.now(tz=UTC),
                },
            )
            if created:
                obj.created_at = po.created_at
                obj.save(update_fields=["created_at"])

            obj.line_items.all().delete()
            POLineItemModel.objects.bulk_create(
                [
                    POLineItemModel(
                        po=obj,
                        item_id=item.id,
                        material_number=item.material_number.value,
                        quantity_value=item.quantity.value,
                        quantity_uom=item.quantity.unit_of_measure,
                        unit_price_amount=item.unit_price.amount,
                        unit_price_currency=item.unit_price.currency,
                        received_quantity=item.received_quantity,
                    )
                    for item in po.line_items
                ]
            )
        logger.debug("po saved", extra={"po_id": str(po.id), "is_new": created})
        return po

    def delete(self, po_id: uuid.UUID) -> None:
        """Soft-delete a PO record."""
        updated = PurchaseOrderModel.objects.filter(id=po_id, is_deleted=False).update(
            is_deleted=True,
            deleted_at=datetime.now(tz=UTC),
        )
        if updated == 0:
            raise PONotFoundError(po_id)
