"""Repository port for external-workshop referral requests."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from apps.repair.domain.entities import (
    ExternalWorkshopReferralRequest,
    ExternalWorkshopReferralStatus,
)


class IExternalWorkshopReferralRepository(ABC):
    """Persist and query external-workshop referral permission requests."""

    @abstractmethod
    def get_by_id(self, request_id: uuid.UUID) -> ExternalWorkshopReferralRequest:
        """Return one referral request by ID."""

    @abstractmethod
    def get_open_by_repair_order(
        self, repair_order_id: uuid.UUID
    ) -> ExternalWorkshopReferralRequest | None:
        """Return the active referral request for a repair order, when present."""

    @abstractmethod
    def list_all(
        self, status: ExternalWorkshopReferralStatus | None = None
    ) -> list[ExternalWorkshopReferralRequest]:
        """Return referral requests, optionally filtered by status."""

    @abstractmethod
    def save(
        self, request: ExternalWorkshopReferralRequest
    ) -> ExternalWorkshopReferralRequest:
        """Persist a referral request."""
