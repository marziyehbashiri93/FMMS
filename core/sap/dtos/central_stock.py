"""SAP central spare-parts warehouse stock DTOs (ZI_STOCK_KH08_CDS)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class SAPCentralStockDTO:
    """One stock row from the central warehouse OData CDS view.

    Attributes:
        material: SAP material number (padded).
        plant: SAP plant code.
        storage_location: Storage location (e.g. KH08).
        inventory_stock_type: Stock type code (e.g. 01).
        material_code: Short material code without leading zeros.
        inventory_stock_type_text: Human-readable stock type.
        quantity: Warehouse stock quantity in material base unit.
        base_unit: Material base unit of measure.
        stock_value: Stock value in display currency.
        display_currency: Currency code for stock value.
    """

    material: str
    plant: str
    storage_location: str
    inventory_stock_type: str
    material_code: str
    inventory_stock_type_text: str
    quantity: Decimal
    base_unit: str
    stock_value: Decimal
    display_currency: str
