"""Abstract repository interfaces for the Repair aggregate."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from apps.repair.domain.entities import RepairOrder, RepairOrderStatus, WorkshopType


class IRepairOrderRepository(ABC):
    """Port (interface) for persisting and retrieving RepairOrder aggregates."""

    @abstractmethod
    def get_by_id(self, order_id: uuid.UUID) -> RepairOrder:
        """Retrieve a repair order by its unique identifier.

        Args:
            order_id: The UUID of the repair order.

        Returns:
            The matching ``RepairOrder`` aggregate.

        Raises:
            RepairOrderNotFoundError: If no repair order exists with this ID.
        """

    @abstractmethod
    def list_by_vehicle(
        self,
        vehicle_id: uuid.UUID,
        status: RepairOrderStatus | None = None,
    ) -> list[RepairOrder]:
        """Return repair orders for a given vehicle, optionally filtered by status.

        Args:
            vehicle_id: UUID of the vehicle.
            status: Optional status filter.

        Returns:
            A list of ``RepairOrder`` aggregates.
        """

    @abstractmethod
    def list_by_fault(self, fault_id: uuid.UUID) -> list[RepairOrder]:
        """Return all repair orders linked to a given fault.

        Args:
            fault_id: UUID of the originating fault.

        Returns:
            A list of ``RepairOrder`` aggregates.
        """

    @abstractmethod
    def list_all(
        self,
        status: RepairOrderStatus | None = None,
        workshop_type: WorkshopType | None = None,
    ) -> list[RepairOrder]:
        """Return all repair orders, optionally filtered by status/workshop."""

    @abstractmethod
    def list_active_by_vehicle(self, vehicle_id: uuid.UUID) -> list[RepairOrder]:
        """Return all active (non-terminal) repair orders for a vehicle.

        This method is used by the Application Service to enforce the
        cross-domain invariant "vehicle cannot be deactivated with active
        repair orders".

        Args:
            vehicle_id: UUID of the vehicle.

        Returns:
            A list of active ``RepairOrder`` aggregates.
        """

    @abstractmethod
    def has_open_repair_order_for_vehicle(self, vehicle_id: uuid.UUID) -> bool:
        """Return True when the vehicle has any non-terminal repair order.

        Args:
            vehicle_id: UUID of the vehicle.

        Returns:
            ``True`` when at least one open repair order exists for the vehicle.
        """

    @abstractmethod
    def save(self, order: RepairOrder) -> RepairOrder:
        """Persist a new or updated repair order aggregate.

        Args:
            order: The ``RepairOrder`` aggregate to save.

        Returns:
            The saved ``RepairOrder`` aggregate.
        """

    @abstractmethod
    def delete(self, order_id: uuid.UUID) -> None:
        """Soft-delete a repair order record.

        Args:
            order_id: The UUID of the repair order to delete.

        Raises:
            RepairOrderNotFoundError: If no repair order exists with this ID.
        """
