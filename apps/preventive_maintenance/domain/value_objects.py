"""Immutable value objects for the Preventive Maintenance domain."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class IntervalUnit(StrEnum):
    """Unit of measurement for a maintenance interval.

    Attributes:
        DAYS: Calendar day interval.
        KM: Odometer kilometre interval.
        HOURS: Engine/operation hour interval.
    """

    DAYS = "DAYS"
    KM = "KM"
    HOURS = "HOURS"


class TriggerType(StrEnum):
    """The condition type that triggers a PM work order.

    Attributes:
        TIME_BASED: Triggered by elapsed calendar time.
        MILEAGE_BASED: Triggered by accumulated kilometres.
        HOURS_BASED: Triggered by accumulated operation hours.
    """

    TIME_BASED = "TIME_BASED"
    MILEAGE_BASED = "MILEAGE_BASED"
    HOURS_BASED = "HOURS_BASED"


@dataclass(frozen=True)
class MaintenanceInterval:
    """Defines the schedule interval for a preventive maintenance plan.

    Args:
        value: Positive interval magnitude.
        unit: The unit of the interval (DAYS, KM, or HOURS).

    Raises:
        ValueError: If value is not positive.

    Example:
        >>> interval = MaintenanceInterval(value=10000, unit=IntervalUnit.KM)
    """

    value: int
    unit: IntervalUnit

    def __post_init__(self) -> None:
        if self.value <= 0:
            raise ValueError(
                f"Maintenance interval value must be positive, got {self.value}."
            )

    def __str__(self) -> str:
        return f"Every {self.value} {self.unit.value}"


@dataclass(frozen=True)
class TriggerCondition:
    """Defines the threshold at which a PM work order should be generated.

    Args:
        trigger_type: The type of trigger condition.
        threshold: Positive threshold value (days, km, or hours).

    Raises:
        ValueError: If threshold is not positive.
    """

    trigger_type: TriggerType
    threshold: int

    def __post_init__(self) -> None:
        if self.threshold <= 0:
            raise ValueError(
                f"Trigger threshold must be positive, got {self.threshold}."
            )

    def __str__(self) -> str:
        return f"Trigger at {self.threshold} {self.trigger_type.value}"


@dataclass(frozen=True)
class OdometerThreshold:
    """An odometer reading threshold for mileage-based PM triggers.

    Args:
        km: Non-negative kilometre threshold.

    Raises:
        ValueError: If km is negative.
    """

    km: int

    def __post_init__(self) -> None:
        if self.km < 0:
            raise ValueError(f"Odometer threshold must be non-negative, got {self.km}.")

    def __str__(self) -> str:
        return f"{self.km} km"
