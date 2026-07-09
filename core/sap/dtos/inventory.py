"""SAP Inventory / Stock DTOs.

Represents stock data received from SAP.
Used to verify material availability before raising purchase requisitions.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class SAPStockDTO:
    """Current unrestricted stock for a material at a plant/storage location.

    Attributes:
        material_number: The SAP material number.
        plant: The SAP plant code.
        storage_location: Optional storage location within the plant.
        unrestricted_qty: The available (unrestricted-use) quantity.
        unit: The unit of measure for the quantity (e.g. "EA").
    """

    material_number: str
    plant: str
    unrestricted_qty: Decimal
    unit: str
    storage_location: str | None = None
