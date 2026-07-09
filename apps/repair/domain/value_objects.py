"""Immutable value objects for the Repair domain."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class TechnicianAssignment:
    """Records the assignment of a technician to a repair order.

    Args:
        technician_id: UUID of the assigned user/technician.
        assigned_at: UTC timestamp when the assignment was made.

    Raises:
        ValueError: If technician_id is not a valid UUID.
    """

    technician_id: uuid.UUID
    assigned_at: datetime

    def __str__(self) -> str:
        return f"Technician {self.technician_id} assigned at {self.assigned_at.isoformat()}"


@dataclass(frozen=True)
class PartQuantity:
    """Quantity of a spare part required for a repair activity.

    Args:
        material_number: SAP material number for the part (non-empty, max 18 chars).
        quantity: Positive integer number of units required.
        unit_of_measure: Unit of measure (e.g. "EA", "KG", "L").

    Raises:
        ValueError: If material_number is blank, quantity is not positive,
            or unit_of_measure is blank.
    """

    material_number: str
    quantity: int
    unit_of_measure: str

    def __post_init__(self) -> None:
        mat = self.material_number.strip()
        uom = self.unit_of_measure.strip()
        object.__setattr__(self, "material_number", mat)
        object.__setattr__(self, "unit_of_measure", uom)
        if not mat:
            raise ValueError("Material number must not be empty.")
        if len(mat) > 18:
            raise ValueError(
                f"Material number must not exceed 18 characters, got {len(mat)}."
            )
        if self.quantity <= 0:
            raise ValueError(f"Part quantity must be positive, got {self.quantity}.")
        if not uom:
            raise ValueError("Unit of measure must not be empty.")

    def __str__(self) -> str:
        return f"{self.quantity} {self.unit_of_measure} of {self.material_number}"


@dataclass(frozen=True)
class LaborHours:
    """Labor hours expended on a repair activity.

    Args:
        hours: Non-negative decimal number of hours.

    Raises:
        ValueError: If hours is negative.
    """

    hours: Decimal

    def __post_init__(self) -> None:
        if self.hours < Decimal("0"):
            raise ValueError(f"Labor hours must be non-negative, got {self.hours}.")

    def __str__(self) -> str:
        return f"{self.hours} hr(s)"
