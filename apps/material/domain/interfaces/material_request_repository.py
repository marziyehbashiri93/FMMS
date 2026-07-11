"""Repository interfaces for material requests."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from apps.material.domain.entities import MaterialRequest, MaterialRequestStatus


class IMaterialRequestRepository(ABC):
    """Material request persistence port."""

    @abstractmethod
    def get_by_id(self, request_id: uuid.UUID) -> MaterialRequest:
        """Get one material request."""

    @abstractmethod
    def list_all(
        self, *, status: MaterialRequestStatus | None = None
    ) -> list[MaterialRequest]:
        """List material requests with optional status filter."""

    @abstractmethod
    def list_by_repair_order(self, repair_order_id: uuid.UUID) -> list[MaterialRequest]:
        """List material requests for one repair order."""

    @abstractmethod
    def save(self, material_request: MaterialRequest) -> MaterialRequest:
        """Persist material request aggregate."""
