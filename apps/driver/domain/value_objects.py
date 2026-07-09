"""Immutable value objects for the Driver domain."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum


class LicenseClass(StrEnum):
    """Iranian commercial driver license classes.

    Attributes:
        A: Motorcycles.
        B: Passenger cars and light vehicles.
        C: Heavy trucks and articulated vehicles.
        D: Buses and minibuses.
        E: Special-purpose and heavy equipment.
    """

    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"


@dataclass(frozen=True)
class LicenseNumber:
    """Validated driver license number.

    Args:
        value: License number string (alphanumeric, 5–20 characters).

    Raises:
        ValueError: If the value is empty, too short, or too long.
    """

    value: str

    _PATTERN: re.Pattern[str] = re.compile(r"^[A-Z0-9]{5,20}$")

    def __post_init__(self) -> None:
        upper = self.value.strip().upper()
        object.__setattr__(self, "value", upper)
        if not self._PATTERN.match(upper):
            raise ValueError(
                f"License number must be 5–20 alphanumeric characters, got: '{upper}'."
            )

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class DriverContact:
    """Contact information for a driver.

    Args:
        phone: Contact phone number (7–15 digits, optional leading +).
        email: Optional contact email address.

    Raises:
        ValueError: If the phone number format is invalid.
    """

    phone: str
    email: str | None = None

    _PHONE_PATTERN: re.Pattern[str] = re.compile(r"^\+?[0-9]{7,15}$")

    def __post_init__(self) -> None:
        stripped_phone = self.phone.strip()
        object.__setattr__(self, "phone", stripped_phone)
        if not self._PHONE_PATTERN.match(stripped_phone):
            raise ValueError(
                f"Phone number must be 7–15 digits with optional leading '+', "
                f"got: '{stripped_phone}'."
            )
        if self.email is not None:
            stripped_email = self.email.strip()
            object.__setattr__(self, "email", stripped_email or None)
