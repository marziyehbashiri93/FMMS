"""Immutable value objects for the Vehicle domain.

Value objects encapsulate validation logic and ensure data integrity.
They are frozen dataclasses — identity is defined by value, not by reference.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlateNumber:
    """Validated vehicle plate number.

    Args:
        value: Raw plate number string. Stripped of surrounding whitespace.

    Raises:
        ValueError: If the plate number is empty or exceeds 20 characters.

    Example:
        >>> plate = PlateNumber("12-ب-345-تهران")
    """

    value: str

    def __post_init__(self) -> None:
        stripped = self.value.strip()
        object.__setattr__(self, "value", stripped)
        if not stripped:
            raise ValueError("Plate number must not be empty.")
        if len(stripped) > 20:
            raise ValueError(
                f"Plate number must not exceed 20 characters, got {len(stripped)}."
            )

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class SAPVehicleNumber:
    """SAP VehicleNumber — 1 to 18 numeric digits.

    SAP stores vehicle numbers as zero-padded numeric strings.

    Args:
        value: SAP VehicleNumber string (digits only).

    Raises:
        ValueError: If blank, non-numeric, or exceeds 18 characters.

    Example:
        >>> vehicle_number = SAPVehicleNumber("000000012345")
    """

    value: str

    def __post_init__(self) -> None:
        stripped = self.value.strip()
        object.__setattr__(self, "value", stripped)
        if not stripped:
            raise ValueError("SAP VehicleNumber must not be empty.")
        if not stripped.isdigit():
            raise ValueError(
                f"SAP VehicleNumber must contain only digits, got: '{stripped}'."
            )
        if len(stripped) > 18:
            raise ValueError(
                f"SAP Equipment Number must not exceed 18 digits, got {len(stripped)}."
            )

    def __str__(self) -> str:
        return self.value
