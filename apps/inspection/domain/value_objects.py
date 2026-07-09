"""Immutable value objects for the Inspection domain."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ChecklistResult(StrEnum):
    """Result of a single inspection checklist item.

    Attributes:
        PASS: The item passed inspection.
        FAIL: The item failed inspection and may require attention.
        NOT_APPLICABLE: The item is not applicable for this vehicle type.
    """

    PASS = "PASS"
    FAIL = "FAIL"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class OdometerUnit(StrEnum):
    """Unit of measurement for odometer readings.

    Attributes:
        KM: Kilometres.
        MILES: Miles.
    """

    KM = "KM"
    MILES = "MILES"


@dataclass(frozen=True)
class OdometerReading:
    """Validated odometer reading at the time of inspection.

    Args:
        value: Non-negative integer reading.
        unit: Unit of measurement.

    Raises:
        ValueError: If value is negative.
    """

    value: int
    unit: OdometerUnit

    def __post_init__(self) -> None:
        if self.value < 0:
            raise ValueError(
                f"Odometer reading must be non-negative, got {self.value}."
            )

    def __str__(self) -> str:
        return f"{self.value} {self.unit.value}"


@dataclass(frozen=True)
class InspectionScore:
    """Computed inspection score expressed as a percentage (0–100).

    Args:
        value: Score between 0 and 100 inclusive.

    Raises:
        ValueError: If value is outside the valid range.
    """

    value: float

    def __post_init__(self) -> None:
        if not (0.0 <= self.value <= 100.0):
            raise ValueError(
                f"Inspection score must be between 0 and 100, got {self.value}."
            )

    @classmethod
    def compute(cls, passed: int, total: int) -> InspectionScore:
        """Compute the inspection score from pass/total counts.

        Args:
            passed: Number of checklist items that passed.
            total: Total number of applicable checklist items.

        Returns:
            An ``InspectionScore`` instance.

        Raises:
            ValueError: If total is zero.
        """
        if total == 0:
            raise ValueError(
                "Cannot compute score: total items must be greater than 0."
            )
        return cls(value=round((passed / total) * 100, 2))

    def __str__(self) -> str:
        return f"{self.value:.2f}%"
