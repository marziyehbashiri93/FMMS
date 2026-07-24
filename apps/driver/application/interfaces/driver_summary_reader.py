"""Read port for driver dashboard summary data."""

from __future__ import annotations

from abc import ABC, abstractmethod

from apps.driver.application.dto.driver_dto import DriverSummaryDTO


class IDriverSummaryReader(ABC):
    """Read model port for driver dashboard summary values."""

    @abstractmethod
    def get_summary(self) -> DriverSummaryDTO:
        """Return driver dashboard summary values."""
