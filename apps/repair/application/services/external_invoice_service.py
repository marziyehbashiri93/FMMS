"""Application services for external repair invoices."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from apps.repair.application.dto.repair_dto import (
    ApproveExternalInvoiceDTO,
    ExternalInvoiceResponseDTO,
    UploadExternalInvoiceDTO,
)
from apps.repair.application.services._timeline_helper import (
    record_repair_timeline_event,
)
from apps.repair.application.services.repair_order_timeline_service import (
    RecordRepairOrderEventService,
)
from apps.repair.domain.entities import RepairOrderEventType
from apps.repair.domain.interfaces.external_invoice_repository import (
    IExternalRepairInvoiceRepository,
)
from apps.repair.domain.interfaces.repair_repository import IRepairOrderRepository
from apps.repair.domain.invoice_entities import (
    ExternalRepairInvoice,
    ExternalRepairInvoiceStatus,
)
from core.exceptions.translation import load_or_not_found


def _to_dto(invoice: ExternalRepairInvoice) -> ExternalInvoiceResponseDTO:
    """Map invoice aggregate to response DTO."""
    return ExternalInvoiceResponseDTO(
        id=invoice.id,
        repair_order_id=invoice.repair_order_id,
        amount=Decimal(str(invoice.amount)),
        currency=invoice.currency,
        status=invoice.status,
        created_by_id=invoice.created_by_id,
        created_at=invoice.created_at,
        updated_at=invoice.updated_at,
        vendor_id=invoice.vendor_id,
        document=invoice.document,
    )


class UploadExternalInvoiceService:
    """Create uploaded external repair invoice."""

    def __init__(
        self,
        invoice_repository: IExternalRepairInvoiceRepository,
        repair_order_repository: IRepairOrderRepository,
        event_recorder: RecordRepairOrderEventService | None = None,
    ) -> None:
        self._repo = invoice_repository
        self._repair_repo = repair_order_repository
        self._event_recorder = event_recorder

    def execute(self, dto: UploadExternalInvoiceDTO) -> ExternalInvoiceResponseDTO:
        """Upload external invoice."""
        load_or_not_found(
            lambda: self._repair_repo.get_by_id(dto.repair_order_id),
            message=f"Repair order '{dto.repair_order_id}' not found.",
            details={"repair_order_id": str(dto.repair_order_id)},
        )
        now = datetime.now(tz=UTC)
        saved = self._repo.save(
            ExternalRepairInvoice(
                id=uuid.uuid4(),
                repair_order_id=dto.repair_order_id,
                amount=float(dto.amount),
                currency=dto.currency,
                status=ExternalRepairInvoiceStatus.UPLOADED,
                created_by_id=dto.uploaded_by,
                created_at=now,
                updated_at=now,
                vendor_id=dto.vendor_id,
                document=dto.document,
            )
        )
        record_repair_timeline_event(
            self._event_recorder,
            saved.repair_order_id,
            RepairOrderEventType.INVOICE_UPLOADED,
            "فاکتور تعمیرگاه خارجی بارگذاری شد.",
            created_by_id=dto.uploaded_by,
            request_id=dto.request_id,
        )
        return _to_dto(saved)


class ListExternalInvoicesService:
    """List external repair invoices."""

    def __init__(self, invoice_repository: IExternalRepairInvoiceRepository) -> None:
        self._repo = invoice_repository

    def execute(self) -> list[ExternalInvoiceResponseDTO]:
        """List all external invoices."""
        return [_to_dto(item) for item in self._repo.list_all()]


class ApproveExternalInvoiceService:
    """Approve uploaded external invoice."""

    def __init__(
        self,
        invoice_repository: IExternalRepairInvoiceRepository,
        event_recorder: RecordRepairOrderEventService | None = None,
    ) -> None:
        self._repo = invoice_repository
        self._event_recorder = event_recorder

    def execute(self, dto: ApproveExternalInvoiceDTO) -> ExternalInvoiceResponseDTO:
        """Approve external invoice."""
        invoice = load_or_not_found(
            lambda: self._repo.get_by_id(dto.invoice_id),
            message=f"External invoice '{dto.invoice_id}' not found.",
            details={"invoice_id": str(dto.invoice_id)},
        )
        invoice.approve()
        invoice.updated_at = datetime.now(tz=UTC)
        saved = self._repo.save(invoice)
        record_repair_timeline_event(
            self._event_recorder,
            saved.repair_order_id,
            RepairOrderEventType.INVOICE_APPROVED,
            "فاکتور تعمیرگاه خارجی تایید شد.",
            created_by_id=dto.approved_by,
            request_id=dto.request_id,
        )
        return _to_dto(saved)
