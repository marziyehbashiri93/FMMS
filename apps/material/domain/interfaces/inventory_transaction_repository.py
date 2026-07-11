"""Port for inventory transaction records."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod


class IInventoryTransactionRepository(ABC):
    """Inventory transaction persistence port."""

    @abstractmethod
    def create_issue_for_material_request(self, material_request_id: uuid.UUID) -> None:
        """Create a placeholder stock-issue transaction."""
