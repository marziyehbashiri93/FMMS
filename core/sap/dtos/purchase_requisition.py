"""SAP Purchase Requisition DTOs.

A Purchase Requisition (PR) is raised in SAP when FMMS requires materials
or services for repair activities. SAP then converts PRs to Purchase Orders.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class PRLineItemRequest:
    """A single line item within a Purchase Requisition request.

    Attributes:
        item_number: Sequential line item number (e.g. "00010", "00020").
        material_number: SAP material number being requested.
        quantity: Required quantity of the material.
        unit: Unit of measure for the quantity (e.g. "EA", "KG").
        delivery_date: Required delivery date for this line item.
        plant: SAP plant code where the material is needed.
        description: Optional free-text description overriding material text.
    """

    item_number: str
    material_number: str
    quantity: Decimal
    unit: str
    delivery_date: date
    plant: str
    description: str | None = None


@dataclass(frozen=True)
class CreatePRRequest:
    """Request data required to create a Purchase Requisition in SAP.

    Attributes:
        document_type: SAP PR document type (e.g. "NB" for standard).
        line_items: One or more line items to include in the PR.
        header_text: Optional header-level free text note.
    """

    document_type: str
    line_items: tuple[PRLineItemRequest, ...]
    header_text: str | None = None

    def __init__(
        self,
        document_type: str,
        line_items: list[PRLineItemRequest],
        header_text: str | None = None,
    ) -> None:
        object.__setattr__(self, "document_type", document_type)
        object.__setattr__(self, "line_items", tuple(line_items))
        object.__setattr__(self, "header_text", header_text)


@dataclass(frozen=True)
class SAPPRLineItemDTO:
    """A single line item from a SAP Purchase Requisition response.

    Attributes:
        item_number: The line item number as assigned by SAP.
        material_number: The material number on this line.
        quantity: The requested quantity.
        unit: The unit of measure.
    """

    item_number: str
    material_number: str
    quantity: Decimal
    unit: str


@dataclass(frozen=True)
class SAPPurchaseRequisitionDTO:
    """Result returned by SAP after creating a Purchase Requisition.

    Attributes:
        pr_number: The SAP-assigned PR document number.
        line_items: The confirmed line items from SAP.
        created_at: UTC datetime when the PR was created in SAP.
    """

    pr_number: str
    line_items: tuple[SAPPRLineItemDTO, ...]
    created_at: date

    def __init__(
        self,
        pr_number: str,
        line_items: list[SAPPRLineItemDTO],
        created_at: date,
    ) -> None:
        object.__setattr__(self, "pr_number", pr_number)
        object.__setattr__(self, "line_items", tuple(line_items))
        object.__setattr__(self, "created_at", created_at)
