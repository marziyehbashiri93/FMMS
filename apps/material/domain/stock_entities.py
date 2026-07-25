"""Domain entities for SAP-synced central warehouse stock rows."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass
class CentralStock:
    """Local cache of one SAP central warehouse stock row (KH08)."""

    id: uuid.UUID
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
    is_active: bool
    created_at: datetime
    updated_at: datetime
