"""SAP Purchase Order DTOs.

A Purchase Order (PO) is raised in SAP to procure materials or services
from an external vendor. FMMS may create POs directly from approved
Purchase Requisitions.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class POLineItemRequest:
    """A single line item within a Purchase Order request.

    Attributes:
        item_number: Sequential line item number (e.g. "00010").
        material_number: SAP material number being ordered.
        quantity: Quantity to order.
        unit: Unit of measure (e.g. "EA").
        net_price: Net price per unit.
        currency: Currency code (e.g. "IRR", "USD").
        delivery_date: Required delivery date.
        plant: SAP plant receiving the goods.
    """

    item_number: str
    material_number: str
    quantity: Decimal
    unit: str
    net_price: Decimal
    currency: str
    delivery_date: date
    plant: str


@dataclass(frozen=True)
class CreatePORequest:
    """Request data required to create a Purchase Order in SAP.

    Attributes:
        vendor_number: SAP vendor account number.
        document_type: SAP PO document type (e.g. "NB" for standard).
        currency: PO header currency code.
        line_items: One or more line items to include.
        pr_number: Optional originating Purchase Requisition number.
        header_text: Optional header-level free text note.
    """

    vendor_number: str
    document_type: str
    currency: str
    line_items: tuple[POLineItemRequest, ...]
    pr_number: str | None = None
    header_text: str | None = None

    def __init__(
        self,
        vendor_number: str,
        document_type: str,
        currency: str,
        line_items: list[POLineItemRequest],
        pr_number: str | None = None,
        header_text: str | None = None,
    ) -> None:
        object.__setattr__(self, "vendor_number", vendor_number)
        object.__setattr__(self, "document_type", document_type)
        object.__setattr__(self, "currency", currency)
        object.__setattr__(self, "line_items", tuple(line_items))
        object.__setattr__(self, "pr_number", pr_number)
        object.__setattr__(self, "header_text", header_text)


@dataclass(frozen=True)
class SAPPurchaseOrderDTO:
    """Result returned by SAP after creating a Purchase Order.

    Attributes:
        po_number: The SAP-assigned PO document number.
        vendor_number: The vendor the PO is addressed to.
        status: Current SAP document status.
        created_at: Date when the PO was created in SAP.
    """

    po_number: str
    vendor_number: str
    status: str
    created_at: date
