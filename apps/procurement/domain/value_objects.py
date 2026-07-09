"""Immutable value objects for the Procurement domain."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class MaterialNumber:
    """SAP material number for a procured item.

    SAP material numbers are numeric strings, zero-padded, up to 18 digits.

    Args:
        value: SAP material number string (digits only, max 18 characters).

    Raises:
        ValueError: If blank, non-numeric, or exceeds 18 characters.
    """

    value: str

    def __post_init__(self) -> None:
        stripped = self.value.strip()
        object.__setattr__(self, "value", stripped)
        if not stripped:
            raise ValueError("Material number must not be empty.")
        if not stripped.isdigit():
            raise ValueError(
                f"Material number must contain only digits, got: '{stripped}'."
            )
        if len(stripped) > 18:
            raise ValueError(
                f"Material number must not exceed 18 digits, got {len(stripped)}."
            )

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class Quantity:
    """A quantity with a unit of measure.

    Args:
        value: Positive decimal quantity.
        unit_of_measure: SAP unit of measure code (e.g. "EA", "KG", "L").

    Raises:
        ValueError: If value is not positive or unit is blank.
    """

    value: Decimal
    unit_of_measure: str

    def __post_init__(self) -> None:
        uom = self.unit_of_measure.strip()
        object.__setattr__(self, "unit_of_measure", uom)
        if self.value <= Decimal("0"):
            raise ValueError(f"Quantity must be positive, got {self.value}.")
        if not uom:
            raise ValueError("Unit of measure must not be empty.")

    def __str__(self) -> str:
        return f"{self.value} {self.unit_of_measure}"


@dataclass(frozen=True)
class Money:
    """A monetary amount with a currency code.

    Args:
        amount: Non-negative decimal amount.
        currency: ISO 4217 currency code (exactly 3 uppercase letters).

    Raises:
        ValueError: If amount is negative or currency code is invalid.

    Example:
        >>> price = Money(amount=Decimal("1500.00"), currency="IRR")
    """

    amount: Decimal
    currency: str

    _CURRENCY_PATTERN: re.Pattern[str] = re.compile(r"^[A-Z]{3}$")

    def __post_init__(self) -> None:
        currency = self.currency.strip().upper()
        object.__setattr__(self, "currency", currency)
        if self.amount < Decimal("0"):
            raise ValueError(
                f"Monetary amount must be non-negative, got {self.amount}."
            )
        if not self._CURRENCY_PATTERN.match(currency):
            raise ValueError(
                f"Currency must be a valid ISO 4217 code (3 uppercase letters), "
                f"got: '{currency}'."
            )

    def __str__(self) -> str:
        return f"{self.amount:.2f} {self.currency}"


@dataclass(frozen=True)
class VendorNumber:
    """SAP vendor account number.

    Args:
        value: SAP vendor number string (alphanumeric, max 10 characters).

    Raises:
        ValueError: If blank or exceeds 10 characters.
    """

    value: str

    def __post_init__(self) -> None:
        stripped = self.value.strip()
        object.__setattr__(self, "value", stripped)
        if not stripped:
            raise ValueError("Vendor number must not be empty.")
        if len(stripped) > 10:
            raise ValueError(
                f"Vendor number must not exceed 10 characters, got {len(stripped)}."
            )

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class SAPDocumentNumber:
    """SAP document number for procurement postings (PR, PO, GR, GI).

    Args:
        value: SAP document number string (alphanumeric, max 10 characters).

    Raises:
        ValueError: If blank or exceeds 10 characters.
    """

    value: str

    def __post_init__(self) -> None:
        stripped = self.value.strip()
        object.__setattr__(self, "value", stripped)
        if not stripped:
            raise ValueError("SAP Document Number must not be empty.")
        if len(stripped) > 10:
            raise ValueError(
                f"SAP Document Number must not exceed 10 characters, got {len(stripped)}."
            )

    def __str__(self) -> str:
        return self.value
