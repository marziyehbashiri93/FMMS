"""Abstract repository interface for the Fault aggregate."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from apps.fault.domain.entities import Fault, FaultStatus
from apps.fault.domain.value_objects import FaultSeverity


class IFaultRepository(ABC):
    """Port (interface) for persisting and retrieving Fault aggregates."""

    @abstractmethod
    def get_by_id(self, fault_id: uuid.UUID) -> Fault:
        """Retrieve a fault by its unique identifier.

        Args:
            fault_id: The UUID of the fault.

        Returns:
            The matching ``Fault`` aggregate.

        Raises:
            FaultNotFoundError: If no fault exists with this ID.
        """

    @abstractmethod
    def list_by_vehicle(
        self,
        vehicle_id: uuid.UUID,
        status: FaultStatus | None = None,
    ) -> list[Fault]:
        """Return faults for a given vehicle, optionally filtered by status.

        Args:
            vehicle_id: UUID of the vehicle.
            status: Optional status filter.

        Returns:
            A list of ``Fault`` aggregates.
        """

    @abstractmethod
    def list_open_by_severity(self, severity: FaultSeverity) -> list[Fault]:
        """Return all open faults with a given severity.

        Args:
            severity: The ``FaultSeverity`` to filter by.

        Returns:
            A list of ``Fault`` aggregates.
        """

    @abstractmethod
    def list_by_inspection(self, inspection_id: uuid.UUID) -> list[Fault]:
        """Return all faults that originated from a given inspection.

        Args:
            inspection_id: UUID of the originating inspection.

        Returns:
            A list of ``Fault`` aggregates.
        """

    @abstractmethod
    def save(self, fault: Fault) -> Fault:
        """Persist a new or updated fault aggregate.

        Args:
            fault: The ``Fault`` aggregate to save.

        Returns:
            The saved ``Fault`` aggregate.
        """

    @abstractmethod
    def delete(self, fault_id: uuid.UUID) -> None:
        """Soft-delete a fault record.

        Args:
            fault_id: The UUID of the fault to delete.

        Raises:
            FaultNotFoundError: If no fault exists with this ID.
        """
