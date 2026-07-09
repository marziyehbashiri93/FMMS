"""Immutable value objects for the Fault domain."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum


class FaultSeverity(StrEnum):
    """Severity level of a fault.

    Attributes:
        CRITICAL: Immediate attention required; vehicle must be grounded.
        HIGH: Significant issue; should be repaired at earliest opportunity.
        MEDIUM: Moderate issue; schedule for repair within normal cycle.
        LOW: Minor issue; note and monitor.
    """

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass(frozen=True)
class FaultCode:
    """Internal fault classification code.

    Format: uppercase letters and digits, 3–20 characters (e.g. "ENG001", "BRK-01").

    Args:
        value: The fault code string.

    Raises:
        ValueError: If the code is empty or does not match the expected pattern.
    """

    value: str

    _PATTERN: re.Pattern[str] = re.compile(r"^[A-Z0-9\-]{3,20}$")

    def __post_init__(self) -> None:
        upper = self.value.strip().upper()
        object.__setattr__(self, "value", upper)
        if not self._PATTERN.match(upper):
            raise ValueError(
                f"Fault code must be 3–20 characters (A-Z, 0-9, hyphen), got: '{upper}'."
            )

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class FaultDescription:
    """Human-readable description of a fault.

    Args:
        value: Non-empty description string, max 500 characters.

    Raises:
        ValueError: If blank or too long.
    """

    value: str

    def __post_init__(self) -> None:
        stripped = self.value.strip()
        object.__setattr__(self, "value", stripped)
        if not stripped:
            raise ValueError("Fault description must not be empty.")
        if len(stripped) > 500:
            raise ValueError(
                f"Fault description must not exceed 500 characters, got {len(stripped)}."
            )

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class SAPDefectCode:
    """SAP PM defect code linked to this fault for SAP notification creation.

    Args:
        value: SAP defect code string (alphanumeric, max 30 characters).

    Raises:
        ValueError: If blank or too long.
    """

    value: str

    def __post_init__(self) -> None:
        stripped = self.value.strip()
        object.__setattr__(self, "value", stripped)
        if not stripped:
            raise ValueError("SAP Defect Code must not be empty.")
        if len(stripped) > 30:
            raise ValueError(
                f"SAP Defect Code must not exceed 30 characters, got {len(stripped)}."
            )

    def __str__(self) -> str:
        return self.value
