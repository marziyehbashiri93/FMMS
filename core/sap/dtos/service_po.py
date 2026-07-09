"""SAP Service Purchase Order DTOs.

A Service PO is raised in SAP to procure external services
(e.g. specialist vehicle repairs contracted to a third party).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class ServiceLineItemRequest:
    """A single service line item in a Service PO request.

    Attributes:
        service_number: SAP service master number.
        quantity: Quantity of the service (e.g. hours or units).
        unit: Unit of measure for the service (e.g. "HR").
        gross_price: Gross price per unit.
        currency: Currency code (e.g. "IRR").
        description: Optional free-text service description override.
    """

    service_number: str
    quantity: Decimal
    unit: str
    gross_price: Decimal
    currency: str
    description: str | None = None


@dataclass(frozen=True)
class CreateServicePORequest:
    """Request data required to create a Service Purchase Order in SAP.

    Attributes:
        vendor_number: SAP vendor account number supplying the service.
        document_type: SAP service PO document type.
        currency: PO header currency code.
        plant: SAP plant where the service is consumed.
        service_lines: One or more service line items.
        header_text: Optional header-level free text note.
    """

    vendor_number: str
    document_type: str
    currency: str
    plant: str
    service_lines: tuple[ServiceLineItemRequest, ...]
    header_text: str | None = None

    def __init__(
        self,
        vendor_number: str,
        document_type: str,
        currency: str,
        plant: str,
        service_lines: list[ServiceLineItemRequest],
        header_text: str | None = None,
    ) -> None:
        object.__setattr__(self, "vendor_number", vendor_number)
        object.__setattr__(self, "document_type", document_type)
        object.__setattr__(self, "currency", currency)
        object.__setattr__(self, "plant", plant)
        object.__setattr__(self, "service_lines", tuple(service_lines))
        object.__setattr__(self, "header_text", header_text)


@dataclass(frozen=True)
class SAPServicePODTO:
    """Result returned by SAP after creating a Service Purchase Order.

    Attributes:
        po_number: The SAP-assigned service PO document number.
        vendor_number: The vendor the service PO is addressed to.
        status: Current SAP document status.
        created_at: Date when the service PO was created in SAP.
    """

    po_number: str
    vendor_number: str
    status: str
    created_at: date
