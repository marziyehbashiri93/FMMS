"""Application DTOs for SAP-synced central warehouse stock."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class CentralStockResponseDTO:
    """Output DTO for one central warehouse stock row."""

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


@dataclass(frozen=True)
class CentralStockSyncResultDTO:
    """Summary of a bulk SAP central-stock synchronisation."""

    total_received: int
    created: int
    updated: int
    failed: int
