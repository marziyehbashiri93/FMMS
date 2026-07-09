"""Domain entities for the Procurement bounded context.

Repair and Vehicle domains are referenced by UUID only — no cross-domain imports.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from apps.procurement.domain.exceptions import ProcurementInvalidStateTransitionError
from apps.procurement.domain.value_objects import (
    MaterialNumber,
    Money,
    Quantity,
    SAPDocumentNumber,
    VendorNumber,
)


class PRStatus(StrEnum):
    """Lifecycle states of a Purchase Requisition.

    Attributes:
        DRAFT: PR is being created; line items may be added.
        SUBMITTED: PR has been submitted for approval.
        APPROVED: PR has been approved; a PO may now be created.
        REJECTED: PR has been rejected and requires revision.
        CANCELLED: PR was cancelled before approval.
    """

    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class POStatus(StrEnum):
    """Lifecycle states of a Purchase Order.

    Attributes:
        CREATED: PO has been created from an approved PR.
        APPROVED: PO has been approved and sent to vendor.
        PARTIALLY_RECEIVED: Some items have been received.
        RECEIVED: All items have been received.
        CANCELLED: PO was cancelled.
    """

    CREATED = "CREATED"
    APPROVED = "APPROVED"
    PARTIALLY_RECEIVED = "PARTIALLY_RECEIVED"
    RECEIVED = "RECEIVED"
    CANCELLED = "CANCELLED"


_PR_ALLOWED_TRANSITIONS: dict[PRStatus, frozenset[PRStatus]] = {
    PRStatus.DRAFT: frozenset({PRStatus.SUBMITTED, PRStatus.CANCELLED}),
    PRStatus.SUBMITTED: frozenset(
        {PRStatus.APPROVED, PRStatus.REJECTED, PRStatus.CANCELLED}
    ),
    PRStatus.REJECTED: frozenset({PRStatus.DRAFT, PRStatus.CANCELLED}),
    PRStatus.APPROVED: frozenset({PRStatus.CANCELLED}),
    PRStatus.CANCELLED: frozenset(),
}

_PO_ALLOWED_TRANSITIONS: dict[POStatus, frozenset[POStatus]] = {
    POStatus.CREATED: frozenset({POStatus.APPROVED, POStatus.CANCELLED}),
    POStatus.APPROVED: frozenset(
        {POStatus.PARTIALLY_RECEIVED, POStatus.RECEIVED, POStatus.CANCELLED}
    ),
    POStatus.PARTIALLY_RECEIVED: frozenset({POStatus.RECEIVED, POStatus.CANCELLED}),
    POStatus.RECEIVED: frozenset(),
    POStatus.CANCELLED: frozenset(),
}


@dataclass
class PRLineItem:
    """A single line item within a Purchase Requisition.

    Attributes:
        id: Unique identifier for this line item.
        material_number: The SAP material number being requested.
        quantity: Quantity and unit of measure.
        estimated_price: Estimated unit price (optional).
        description: Human-readable description of the requirement.
    """

    id: uuid.UUID
    material_number: MaterialNumber
    quantity: Quantity
    description: str
    estimated_price: Money | None = field(default=None)


@dataclass
class PurchaseRequisition:
    """Aggregate root representing a Purchase Requisition (PR).

    Attributes:
        id: Unique identifier for this PR.
        repair_order_id: UUID of the originating repair order (cross-domain by ID).
        status: Current lifecycle status.
        line_items: List of requested materials.
        sap_pr_number: SAP PR document number after SAP sync (optional).
        requested_by_id: UUID of the requesting user.
        approved_by_id: UUID of the approving user (optional).
        created_at: UTC timestamp of creation.
        updated_at: UTC timestamp of last update.
    """

    id: uuid.UUID
    repair_order_id: uuid.UUID
    status: PRStatus
    requested_by_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    line_items: list[PRLineItem] = field(default_factory=list)
    sap_pr_number: SAPDocumentNumber | None = field(default=None)
    approved_by_id: uuid.UUID | None = field(default=None)

    def transition_to(self, target: PRStatus) -> None:
        """Guard and apply a PR status transition.

        Args:
            target: The desired new status.

        Raises:
            ProcurementInvalidStateTransitionError: If the transition is not allowed.
        """
        allowed = _PR_ALLOWED_TRANSITIONS.get(self.status, frozenset())
        if target not in allowed:
            raise ProcurementInvalidStateTransitionError(
                document_type="PurchaseRequisition",
                current_status=self.status.value,
                target_status=target.value,
            )
        self.status = target

    def add_line_item(self, item: PRLineItem) -> None:
        """Add a line item to a DRAFT requisition.

        Args:
            item: The ``PRLineItem`` to add.

        Raises:
            ProcurementInvalidStateTransitionError: If the PR is not in DRAFT status.
        """
        if self.status != PRStatus.DRAFT:
            raise ProcurementInvalidStateTransitionError(
                document_type="PurchaseRequisition",
                current_status=self.status.value,
                target_status="DRAFT (required for add_line_item)",
            )
        self.line_items.append(item)

    def submit(self) -> None:
        """Submit the PR for approval."""
        self.transition_to(PRStatus.SUBMITTED)

    def approve(self, approved_by_id: uuid.UUID) -> None:
        """Approve the submitted PR.

        Args:
            approved_by_id: UUID of the approving user.
        """
        self.transition_to(PRStatus.APPROVED)
        self.approved_by_id = approved_by_id

    def reject(self) -> None:
        """Reject the submitted PR."""
        self.transition_to(PRStatus.REJECTED)

    def link_sap_pr(self, sap_pr_number: SAPDocumentNumber) -> None:
        """Record the SAP PR document number after SAP sync.

        Args:
            sap_pr_number: The SAP-assigned PR document number.
        """
        self.sap_pr_number = sap_pr_number


@dataclass
class POLineItem:
    """A single line item within a Purchase Order.

    Attributes:
        id: Unique identifier.
        material_number: SAP material number.
        quantity: Ordered quantity.
        unit_price: Agreed unit price.
        received_quantity: Quantity received to date.
    """

    id: uuid.UUID
    material_number: MaterialNumber
    quantity: Quantity
    unit_price: Money
    received_quantity: Decimal = field(default=Decimal("0"))

    @property
    def is_fully_received(self) -> bool:
        """Return True if the full ordered quantity has been received."""
        return self.received_quantity >= self.quantity.value


@dataclass
class PurchaseOrder:
    """Aggregate root representing a Purchase Order (PO).

    Attributes:
        id: Unique identifier for this PO.
        pr_id: UUID of the originating Purchase Requisition.
        vendor_number: SAP vendor account number.
        status: Current lifecycle status.
        line_items: List of ordered materials.
        sap_po_number: SAP PO document number after SAP sync (optional).
        created_by_id: UUID of the user who created this PO.
        approved_by_id: UUID of the approving user (optional).
        created_at: UTC timestamp of creation.
        updated_at: UTC timestamp of last update.
    """

    id: uuid.UUID
    pr_id: uuid.UUID
    vendor_number: VendorNumber
    status: POStatus
    created_by_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    line_items: list[POLineItem] = field(default_factory=list)
    sap_po_number: SAPDocumentNumber | None = field(default=None)
    approved_by_id: uuid.UUID | None = field(default=None)

    def transition_to(self, target: POStatus) -> None:
        """Guard and apply a PO status transition.

        Args:
            target: The desired new status.

        Raises:
            ProcurementInvalidStateTransitionError: If the transition is not allowed.
        """
        allowed = _PO_ALLOWED_TRANSITIONS.get(self.status, frozenset())
        if target not in allowed:
            raise ProcurementInvalidStateTransitionError(
                document_type="PurchaseOrder",
                current_status=self.status.value,
                target_status=target.value,
            )
        self.status = target

    def approve(self, approved_by_id: uuid.UUID) -> None:
        """Approve the PO.

        Args:
            approved_by_id: UUID of the approving user.
        """
        self.transition_to(POStatus.APPROVED)
        self.approved_by_id = approved_by_id

    def record_partial_receipt(self) -> None:
        """Mark the PO as partially received."""
        self.transition_to(POStatus.PARTIALLY_RECEIVED)

    def record_full_receipt(self) -> None:
        """Mark the PO as fully received."""
        self.transition_to(POStatus.RECEIVED)

    def cancel(self) -> None:
        """Cancel the PO."""
        self.transition_to(POStatus.CANCELLED)

    def link_sap_po(self, sap_po_number: SAPDocumentNumber) -> None:
        """Record the SAP PO document number after SAP sync.

        Args:
            sap_po_number: The SAP-assigned PO document number.
        """
        self.sap_po_number = sap_po_number

    @property
    def total_value(self) -> Decimal:
        """Compute total PO value across all line items."""
        return sum(
            (item.unit_price.amount * item.quantity.value for item in self.line_items),
            Decimal("0"),
        )
