"""Domain entities for installed vehicle component history."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum


class ComponentType(StrEnum):
    """Replaceable vehicle component categories."""

    BATTERY = "BATTERY"
    TIRE = "TIRE"
    BRAKE_PAD = "BRAKE_PAD"
    ALTERNATOR = "ALTERNATOR"
    ENGINE = "ENGINE"
    OTHER = "OTHER"


@dataclass
class VehicleComponentHistory:
    """One installed/replaced component record for a vehicle."""

    id: uuid.UUID
    vehicle_id: uuid.UUID
    repair_order_id: uuid.UUID
    component_type: ComponentType
    material_number: str
    quantity: Decimal
    unit_of_measure: str
    description: str
    installed_at: datetime
    recorded_by_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
