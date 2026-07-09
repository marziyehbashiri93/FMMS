"""SAP Goods Issue DTOs.

A Goods Issue (GI) is posted in SAP when materials are consumed from stock
(e.g. spare parts issued to a maintenance order). FMMS triggers GI posting
when repair parts are recorded as consumed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class GILineItemRequest:
    """A single line item in a Goods Issue posting request.

    Attributes:
        material_number: The SAP material number being issued.
        quantity: Quantity being issued from stock.
        unit: Unit of measure.
        plant: Issuing plant.
        storage_location: Storage location within the plant.
        order_number: Optional PM Order number that the material is issued to.
    """

    material_number: str
    quantity: Decimal
    unit: str
    plant: str
    storage_location: str
    order_number: str | None = None


@dataclass(frozen=True)
class PostGoodsIssueRequest:
    """Request data required to post a Goods Issue in SAP.

    Attributes:
        posting_date: The accounting posting date.
        document_date: The physical document date.
        line_items: One or more goods issue line items.
        header_text: Optional header note.
    """

    posting_date: date
    document_date: date
    line_items: tuple[GILineItemRequest, ...]
    header_text: str | None = None

    def __init__(
        self,
        posting_date: date,
        document_date: date,
        line_items: list[GILineItemRequest],
        header_text: str | None = None,
    ) -> None:
        object.__setattr__(self, "posting_date", posting_date)
        object.__setattr__(self, "document_date", document_date)
        object.__setattr__(self, "line_items", tuple(line_items))
        object.__setattr__(self, "header_text", header_text)


@dataclass(frozen=True)
class SAPGoodsIssueDTO:
    """Result returned by SAP after posting a Goods Issue.

    Attributes:
        material_document: The SAP material document number created by the posting.
        posting_date: The date the posting was made in SAP.
        created_at: Date the material document was created.
    """

    material_document: str
    posting_date: date
    created_at: date
