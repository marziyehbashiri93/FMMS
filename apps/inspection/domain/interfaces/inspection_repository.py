"""Abstract repository interface for the Inspection aggregate."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import datetime

from apps.inspection.domain.entities import Inspection, InspectionStatus


class IInspectionRepository(ABC):
    """Port (interface) for persisting and retrieving Inspection aggregates."""

    @abstractmethod
    def get_by_id(self, inspection_id: uuid.UUID) -> Inspection:
        """Retrieve an inspection by its unique identifier.

        Args:
            inspection_id: The UUID of the inspection.

        Returns:
            The matching ``Inspection`` aggregate.

        Raises:
            InspectionNotFoundError: If no inspection exists with this ID.
        """

    @abstractmethod
    def list_by_vehicle(
        self,
        vehicle_id: uuid.UUID,
        status: InspectionStatus | None = None,
    ) -> list[Inspection]:
        """Return inspections for a given vehicle, optionally filtered by status.

        Args:
            vehicle_id: UUID of the vehicle.
            status: Optional status filter.

        Returns:
            A list of ``Inspection`` aggregates.
        """

    @abstractmethod
    def list_by_date_range(
        self,
        start: datetime,
        end: datetime,
    ) -> list[Inspection]:
        """Return all inspections conducted within a date range.

        Args:
            start: Start of the date range (inclusive, UTC).
            end: End of the date range (inclusive, UTC).

        Returns:
            A list of ``Inspection`` aggregates.
        """

    @abstractmethod
    def save(self, inspection: Inspection) -> Inspection:
        """Persist a new or updated inspection aggregate.

        Args:
            inspection: The ``Inspection`` aggregate to save.

        Returns:
            The saved ``Inspection`` aggregate.
        """

    @abstractmethod
    def delete(self, inspection_id: uuid.UUID) -> None:
        """Soft-delete an inspection record.

        Args:
            inspection_id: The UUID of the inspection to delete.

        Raises:
            InspectionNotFoundError: If no inspection exists with this ID.
        """
