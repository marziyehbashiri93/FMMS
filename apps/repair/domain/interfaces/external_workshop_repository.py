"""Repository port for external workshop workflow records."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from apps.repair.domain.external_workshop_entities import (
    ExternalRepairReview,
    ExternalWorkshopAssignment,
    ExternalWorkshopAssignmentStatus,
    ExternalWorkshopDelivery,
    ExternalWorkshopPickup,
)


class IExternalWorkshopRepository(ABC):
    """Persist and query external workshop workflow records."""

    @abstractmethod
    def get_assignment_by_id(
        self, assignment_id: uuid.UUID
    ) -> ExternalWorkshopAssignment:
        """Return one assignment."""

    @abstractmethod
    def get_active_assignment_by_repair_order(
        self, repair_order_id: uuid.UUID
    ) -> ExternalWorkshopAssignment | None:
        """Return the active assignment for a repair order, when present."""

    @abstractmethod
    def list_assignments(
        self, status: ExternalWorkshopAssignmentStatus | None = None
    ) -> list[ExternalWorkshopAssignment]:
        """Return assignments, optionally filtered by status."""

    @abstractmethod
    def save_assignment(
        self, assignment: ExternalWorkshopAssignment
    ) -> ExternalWorkshopAssignment:
        """Create or update an assignment."""

    @abstractmethod
    def get_delivery_by_assignment(
        self, assignment_id: uuid.UUID
    ) -> ExternalWorkshopDelivery | None:
        """Return delivery confirmation for assignment, if present."""

    @abstractmethod
    def save_delivery(
        self, delivery: ExternalWorkshopDelivery
    ) -> ExternalWorkshopDelivery:
        """Persist delivery confirmation."""

    @abstractmethod
    def get_pickup_by_assignment(
        self, assignment_id: uuid.UUID
    ) -> ExternalWorkshopPickup | None:
        """Return pickup confirmation for assignment, if present."""

    @abstractmethod
    def save_pickup(self, pickup: ExternalWorkshopPickup) -> ExternalWorkshopPickup:
        """Persist pickup confirmation."""

    @abstractmethod
    def get_review_by_assignment(
        self, assignment_id: uuid.UUID
    ) -> ExternalRepairReview | None:
        """Return repair review for assignment, if present."""

    @abstractmethod
    def save_review(self, review: ExternalRepairReview) -> ExternalRepairReview:
        """Create or update repair review."""
