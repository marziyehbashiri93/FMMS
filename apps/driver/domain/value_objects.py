"""Immutable value objects for the Driver domain."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class CustomerNumber:
    """SAP ``CustomerNumber`` for a driver."""

    value: str

    _PATTERN: re.Pattern[str] = re.compile(r"^[0-9]{1,20}$")

    def __post_init__(self) -> None:
        stripped = self.value.strip()
        object.__setattr__(self, "value", stripped)
        if not self._PATTERN.match(stripped):
            raise ValueError(
                f"CustomerNumber must contain 1-20 numeric digits, got: '{stripped}'."
            )

    def __str__(self) -> str:
        return self.value
