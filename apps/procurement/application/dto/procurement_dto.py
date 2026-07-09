"""Application-layer DTOs for the Procurement domain.

Rules:
- No ORM models, no Django objects, no database objects.
- Mapping DTO <-> Domain Entity happens explicitly inside each service.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

from apps.procurement.domain.entities import POStatus, PRStatus


@dataclass(frozen=True)
class CreatePurchaseRequisitionDTO:
    """Input DTO for creating a DRAFT purchase requisition.

    Attributes:
        repair_order_id: UUID of the originating repair order.
        request_id: Correlation ID for tracing.
        requested_by: UUID of the requesting user.
    """

    repair_order_id: uuid.UUID
    request_id: str
    requested_by: uuid.UUID


@dataclass(frozen=True)
class AddPRLineItemDTO:
    """Input DTO for adding a line item to a DRAFT PR.

    Attributes:
        pr_id: Target purchase requisition UUID.
        material_number: SAP material number (digits).
        quantity: Positive decimal quantity.
        unit_of_measure: Unit of measure (e.g. EA).
        description: Human-readable requirement description.
        request_id: Correlation ID for tracing.
        estimated_amount: Optional estimated unit price amount.
        currency: ISO currency when estimated_amount is provided.
    """

    pr_id: uuid.UUID
    material_number: str
    quantity: Decimal
    unit_of_measure: str
    description: str
    request_id: str
    estimated_amount: Decimal | None = field(default=None)
    currency: str | None = field(default=None)


@dataclass(frozen=True)
class SubmitPRToSAPDTO:
    """Input DTO for submitting a PR to SAP.

    The service orchestrates procurement workflow only. SAP writes go through
    ``ISAPTransactionManager`` → ``ISAPPurchaseRequisitionPort``. Concrete
    adapters and the manager implementation are wired at the composition root.

    Attributes:
        pr_id: Purchase requisition UUID.
        document_type: SAP PR document type (e.g. NB).
        plant: SAP plant for all line items.
        delivery_date: Required delivery date for line items.
        request_id: Correlation ID for tracing.
        submitted_by: UUID of the user submitting to SAP.
        idempotency_key: Optional explicit key; defaults to
            ``pr-submit:{pr_id}`` when omitted.
        header_text: Optional SAP header text.
    """

    pr_id: uuid.UUID
    document_type: str
    plant: str
    delivery_date: date
    request_id: str
    submitted_by: uuid.UUID
    idempotency_key: str | None = field(default=None)
    header_text: str | None = field(default=None)


@dataclass(frozen=True)
class ReceivePOLineItemDTO:
    """A single line item when receiving a PO from SAP."""

    material_number: str
    quantity: Decimal
    unit_of_measure: str
    unit_price: Decimal
    currency: str


@dataclass(frozen=True)
class ReceivePOFromSAPDTO:
    """Input DTO for recording a Purchase Order received from SAP.

    Attributes:
        pr_id: Originating purchase requisition UUID.
        sap_po_number: SAP-assigned PO document number.
        vendor_number: SAP vendor account number.
        line_items: Ordered materials with unit prices.
        request_id: Correlation ID for tracing.
        created_by: UUID of the user/system recording the PO.
    """

    pr_id: uuid.UUID
    sap_po_number: str
    vendor_number: str
    line_items: tuple[ReceivePOLineItemDTO, ...]
    request_id: str
    created_by: uuid.UUID


@dataclass(frozen=True)
class PRLineItemResponseDTO:
    """Output DTO for a PR line item."""

    id: uuid.UUID
    material_number: str
    quantity: Decimal
    unit_of_measure: str
    description: str
    estimated_amount: Decimal | None = field(default=None)
    currency: str | None = field(default=None)


@dataclass(frozen=True)
class PurchaseRequisitionResponseDTO:
    """Output DTO for purchase requisition operations."""

    id: uuid.UUID
    repair_order_id: uuid.UUID
    status: PRStatus
    requested_by_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    line_items: list[PRLineItemResponseDTO] = field(default_factory=list)
    sap_pr_number: str | None = field(default=None)
    approved_by_id: uuid.UUID | None = field(default=None)
    sap_transaction_id: uuid.UUID | None = field(default=None)
    sap_transaction_status: str | None = field(default=None)


@dataclass(frozen=True)
class PurchaseOrderResponseDTO:
    """Output DTO for purchase order operations."""

    id: uuid.UUID
    pr_id: uuid.UUID
    vendor_number: str
    status: POStatus
    created_by_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    sap_po_number: str | None = field(default=None)
    approved_by_id: uuid.UUID | None = field(default=None)
