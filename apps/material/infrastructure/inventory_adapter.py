"""Stub inventory availability adapter."""

from __future__ import annotations

import os

from apps.material.domain.entities import MaterialRequestItem
from apps.material.domain.interfaces.inventory_availability_port import (
    IInventoryAvailabilityPort,
)


class StubInventoryAvailabilityAdapter(IInventoryAvailabilityPort):
    """Environment-configurable stock availability adapter."""

    def __init__(self, default_available: bool | None = None) -> None:
        if default_available is None:
            env_value = os.getenv("FMMS_INVENTORY_AVAILABLE_DEFAULT", "true").lower()
            self._default_available = env_value in {"1", "true", "yes", "on"}
        else:
            self._default_available = default_available

    def is_available(self, item: MaterialRequestItem) -> bool:
        """Return static availability value for all requested items."""
        _ = item
        return self._default_available
