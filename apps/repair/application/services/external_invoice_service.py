"""Application services for external repair invoices."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from apps.fault.domain.entities import Fault, FaultStatus
from apps.fault.domain.exceptions import FaultNotFoundError
from apps.fault.domain.interfaces.fault_repository import IFaultRepository
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
from apps.repair.domain.entities import (
    RepairOrder,
    RepairOrderEventType,
    RepairOrderStatus,
    WorkshopType,
)
from apps.repair.domain.interfaces.external_invoice_repository import (
    IExternalRepairInvoiceRepository,
)
from apps.repair.domain.interfaces.repair_repository import IRepairOrderRepository
from apps.repair.domain.invoice_entities import (
    ExternalRepairInvoice,
    ExternalRepairInvoiceStatus,
)
from apps.vehicle.domain.entities import VehicleStatus
from apps.vehicle.domain.interfaces.vehicle_repository import IVehicleRepository
from core.exceptions.base_exception import FMMSConflictError
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
        order = load_or_not_found(
            lambda: self._repair_repo.get_by_id(dto.repair_order_id),
            message=f"Repair order '{dto.repair_order_id}' not found.",
            details={"repair_order_id": str(dto.repair_order_id)},
        )
        _assert_external_invoice_upload_allowed(order)
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
        repair_order_repository: IRepairOrderRepository,
        fault_repository: IFaultRepository,
        vehicle_repository: IVehicleRepository,
        event_recorder: RecordRepairOrderEventService | None = None,
    ) -> None:
        self._repo = invoice_repository
        self._repair_repo = repair_order_repository
        self._fault_repo = fault_repository
        self._vehicle_repo = vehicle_repository
        self._event_recorder = event_recorder

    def execute(self, dto: ApproveExternalInvoiceDTO) -> ExternalInvoiceResponseDTO:
        """Approve external invoice and finalize the external repair workflow."""
        invoice = load_or_not_found(
            lambda: self._repo.get_by_id(dto.invoice_id),
            message=f"External invoice '{dto.invoice_id}' not found.",
            details={"invoice_id": str(dto.invoice_id)},
        )
        order = load_or_not_found(
            lambda: self._repair_repo.get_by_id(invoice.repair_order_id),
            message=f"Repair order '{invoice.repair_order_id}' not found.",
            details={"repair_order_id": str(invoice.repair_order_id)},
        )
        _assert_external_invoice_approval_allowed(order)
        now = datetime.now(tz=UTC)
        invoice.approve()
        invoice.updated_at = now
        saved = self._repo.save(invoice)
        order.complete_after_transport_handover(completed_at=order.completed_at or now)
        order.updated_at = now
        finalized_order = self._repair_repo.save(order)
        _close_fault_for_completed_external_repair(
            fault_id=finalized_order.fault_id,
            fault_repository=self._fault_repo,
        )
        vehicle = load_or_not_found(
            lambda: self._vehicle_repo.get_by_id(finalized_order.vehicle_id),
            message=f"Vehicle '{finalized_order.vehicle_id}' not found.",
            details={"vehicle_id": str(finalized_order.vehicle_id)},
        )
        if vehicle.status != VehicleStatus.ACTIVE:
            vehicle.activate()
            vehicle.updated_at = now
            self._vehicle_repo.save(vehicle)
        record_repair_timeline_event(
            self._event_recorder,
            saved.repair_order_id,
            RepairOrderEventType.INVOICE_APPROVED,
            "فاکتور تعمیرگاه خارجی تایید شد.",
            created_by_id=dto.approved_by,
            request_id=dto.request_id,
        )
        record_repair_timeline_event(
            self._event_recorder,
            saved.repair_order_id,
            RepairOrderEventType.EXTERNAL_INVOICE_APPROVED,
            "تعمیر خارجی تکمیل و خودرو فعال شد.",
            created_by_id=dto.approved_by,
            request_id=dto.request_id,
        )
        return _to_dto(saved)


def _assert_external_invoice_upload_allowed(order: RepairOrder) -> None:
    """Require an external repair accepted by driver before invoice upload."""
    if order.workshop_type != WorkshopType.EXTERNAL:
        raise FMMSConflictError(
            message="External invoice can only be uploaded for external repair orders.",
            error_code="EXTERNAL_INVOICE_REQUIRES_EXTERNAL_REPAIR",
            details={"repair_order_id": str(order.id)},
        )
    if order.status != RepairOrderStatus.WAITING_TRANSPORT_FINAL_APPROVAL:
        raise FMMSConflictError(
            message="External invoice can only be uploaded after driver handover confirmation.",
            error_code="EXTERNAL_INVOICE_REQUIRES_DRIVER_CONFIRMATION",
            details={
                "repair_order_id": str(order.id),
                "status": order.status.value,
            },
        )


def _assert_external_invoice_approval_allowed(order: RepairOrder) -> None:
    """Require a driver-confirmed external repair before invoice approval."""
    if order.workshop_type != WorkshopType.EXTERNAL:
        raise FMMSConflictError(
            message="External invoice can only be approved for external repair orders.",
            error_code="EXTERNAL_INVOICE_APPROVAL_REQUIRES_EXTERNAL_REPAIR",
            details={"repair_order_id": str(order.id)},
        )
    if order.status != RepairOrderStatus.WAITING_TRANSPORT_FINAL_APPROVAL:
        raise FMMSConflictError(
            message="External invoice can only be approved while waiting for transport final approval.",
            error_code="EXTERNAL_INVOICE_APPROVAL_INVALID_REPAIR_STATE",
            details={
                "repair_order_id": str(order.id),
                "status": order.status.value,
            },
        )


def _close_fault_for_completed_external_repair(
    *,
    fault_id: uuid.UUID,
    fault_repository: IFaultRepository,
) -> None:
    """Close the repair fault after external invoice approval."""
    try:
        fault = fault_repository.get_by_id(fault_id)
    except FaultNotFoundError:
        return
    if fault.status == FaultStatus.CLOSED:
        return
    _close_open_fault(fault)
    fault.updated_at = datetime.now(tz=UTC)
    fault_repository.save(fault)


def _close_open_fault(fault: Fault) -> None:
    """Transition a non-closed fault to CLOSED through valid domain states."""
    if fault.status in {FaultStatus.ASSIGNED, FaultStatus.AWAITING_TRANSPORT}:
        fault.start_repair()
    fault.close()
