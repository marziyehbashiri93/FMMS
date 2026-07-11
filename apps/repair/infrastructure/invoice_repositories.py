"""Django repository for external repair invoices."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from apps.repair.domain.exceptions import ExternalRepairInvoiceNotFoundError
from apps.repair.domain.interfaces.external_invoice_repository import (
    IExternalRepairInvoiceRepository,
)
from apps.repair.domain.invoice_entities import (
    ExternalRepairInvoice,
    ExternalRepairInvoiceStatus,
)
from apps.repair.infrastructure.models import ExternalRepairInvoiceModel


def _to_domain(orm: ExternalRepairInvoiceModel) -> ExternalRepairInvoice:
    """Map ORM invoice to domain entity."""
    return ExternalRepairInvoice(
        id=orm.id,
        repair_order_id=orm.repair_order_id,
        amount=float(orm.amount),
        currency=orm.currency,
        status=ExternalRepairInvoiceStatus(orm.status),
        created_by_id=orm.uploaded_by_id,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
        vendor_id=orm.vendor_id or None,
        document=orm.document or None,
    )


class DjangoExternalRepairInvoiceRepository(IExternalRepairInvoiceRepository):
    """Django-backed external invoice repository."""

    def get_by_id(self, invoice_id: uuid.UUID) -> ExternalRepairInvoice:
        """Get one external invoice."""
        try:
            orm = ExternalRepairInvoiceModel.objects.get(
                id=invoice_id, is_deleted=False
            )
        except ExternalRepairInvoiceModel.DoesNotExist:
            raise ExternalRepairInvoiceNotFoundError(invoice_id) from None
        return _to_domain(orm)

    def list_all(self) -> list[ExternalRepairInvoice]:
        """List all external invoices."""
        return [
            _to_domain(item)
            for item in ExternalRepairInvoiceModel.objects.filter(
                is_deleted=False
            ).order_by("-created_at")
        ]

    def save(self, invoice: ExternalRepairInvoice) -> ExternalRepairInvoice:
        """Persist external invoice."""
        orm, created = ExternalRepairInvoiceModel.objects.update_or_create(
            id=invoice.id,
            defaults={
                "repair_order_id": invoice.repair_order_id,
                "vendor_id": invoice.vendor_id or "",
                "amount": invoice.amount,
                "currency": invoice.currency,
                "document": invoice.document or "",
                "status": invoice.status.value,
                "uploaded_by_id": invoice.created_by_id,
                "updated_at": datetime.now(tz=UTC),
            },
        )
        if created:
            orm.created_at = invoice.created_at
            orm.save(update_fields=["created_at"])
        return invoice
