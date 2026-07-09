"""SAP Goods Receipt DTOs.

A Goods Receipt (GR) is posted in SAP when materials ordered on a Purchase
Order are physically received. FMMS triggers GR posting upon delivery confirmation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class GRLineItemRequest:
    """A single line item in a Goods Receipt posting request.

    Attributes:
        po_number: The SAP Purchase Order number being received against.
        po_item: The PO line item number (e.g. "00010").
        quantity: Quantity being received.
        unit: Unit of measure.
        plant: Receiving plant.
        storage_location: Storage location within the plant.
    """

    po_number: str
    po_item: str
    quantity: Decimal
    unit: str
    plant: str
    storage_location: str


@dataclass(frozen=True)
class PostGoodsReceiptRequest:
    """Request data required to post a Goods Receipt in SAP.

    Attributes:
        po_number: The originating PO number (header reference).
        posting_date: The accounting posting date.
        document_date: The physical document/delivery date.
        line_items: One or more goods receipt line items.
        header_text: Optional header note.
    """

    po_number: str
    posting_date: date
    document_date: date
    line_items: tuple[GRLineItemRequest, ...]
    header_text: str | None = None

    def __init__(
        self,
        po_number: str,
        posting_date: date,
        document_date: date,
        line_items: list[GRLineItemRequest],
        header_text: str | None = None,
    ) -> None:
        object.__setattr__(self, "po_number", po_number)
        object.__setattr__(self, "posting_date", posting_date)
        object.__setattr__(self, "document_date", document_date)
        object.__setattr__(self, "line_items", tuple(line_items))
        object.__setattr__(self, "header_text", header_text)


@dataclass(frozen=True)
class SAPGoodsReceiptDTO:
    """Result returned by SAP after posting a Goods Receipt.

    Attributes:
        material_document: The SAP material document number created by the posting.
        posting_date: The date the posting was made in SAP.
        created_at: Date the material document was created.
    """

    material_document: str
    posting_date: date
    created_at: date
