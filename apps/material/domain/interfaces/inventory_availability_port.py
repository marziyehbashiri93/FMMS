"""Port for checking inventory availability."""

from __future__ import annotations

from abc import ABC, abstractmethod

from apps.material.domain.entities import MaterialRequestItem


class IInventoryAvailabilityPort(ABC):
    """Abstraction for stock availability checks."""

    @abstractmethod
    def is_available(self, item: MaterialRequestItem) -> bool:
        """Return whether the requested item is available in stock."""
