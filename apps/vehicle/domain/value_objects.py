"""Immutable value objects for the Vehicle domain.

Value objects encapsulate validation logic and ensure data integrity.
They are frozen dataclasses — identity is defined by value, not by reference.
"""

from __future__ import annotations

import re
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
class VIN:
    """Vehicle Identification Number — exactly 17 alphanumeric characters.

    Args:
        value: 17-character VIN string (I, O, Q are excluded per ISO 3779).

    Raises:
        ValueError: If the VIN is not exactly 17 characters or contains
            invalid characters (I, O, Q).

    Example:
        >>> vin = VIN("1HGBH41JXMN109186")
    """

    value: str

    _INVALID_CHARS: frozenset[str] = frozenset({"I", "O", "Q"})
    _PATTERN: re.Pattern[str] = re.compile(r"^[A-HJ-NPR-Z0-9]{17}$")

    def __post_init__(self) -> None:
        upper = self.value.strip().upper()
        object.__setattr__(self, "value", upper)
        if not self._PATTERN.match(upper):
            raise ValueError(
                f"VIN must be exactly 17 alphanumeric characters "
                f"(I, O, Q not allowed), got: '{self.value}'."
            )

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class ChassisNumber:
    """Vehicle chassis number — free-form, non-empty, max 50 characters.

    Args:
        value: Chassis number string.

    Raises:
        ValueError: If empty or exceeds 50 characters.
    """

    value: str

    def __post_init__(self) -> None:
        stripped = self.value.strip()
        object.__setattr__(self, "value", stripped)
        if not stripped:
            raise ValueError("Chassis number must not be empty.")
        if len(stripped) > 50:
            raise ValueError(
                f"Chassis number must not exceed 50 characters, got {len(stripped)}."
            )

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class SAPEquipmentNumber:
    """SAP Equipment Number — 1 to 18 numeric digits.

    SAP stores equipment numbers as zero-padded numeric strings.

    Args:
        value: SAP equipment number string (digits only).

    Raises:
        ValueError: If blank, non-numeric, or exceeds 18 characters.

    Example:
        >>> eq = SAPEquipmentNumber("000000012345")
    """

    value: str

    def __post_init__(self) -> None:
        stripped = self.value.strip()
        object.__setattr__(self, "value", stripped)
        if not stripped:
            raise ValueError("SAP Equipment Number must not be empty.")
        if not stripped.isdigit():
            raise ValueError(
                f"SAP Equipment Number must contain only digits, got: '{stripped}'."
            )
        if len(stripped) > 18:
            raise ValueError(
                f"SAP Equipment Number must not exceed 18 digits, got {len(stripped)}."
            )

    def __str__(self) -> str:
        return self.value
