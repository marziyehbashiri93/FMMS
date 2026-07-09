"""Abstract repository interfaces for the Preventive Maintenance aggregate."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from apps.preventive_maintenance.domain.entities import (
    PMPlan,
    PMPlanStatus,
    PMWorkOrder,
    PMWorkOrderStatus,
)


class IPMPlanRepository(ABC):
    """Port (interface) for persisting and retrieving PMPlan aggregates."""

    @abstractmethod
    def get_by_id(self, plan_id: uuid.UUID) -> PMPlan:
        """Retrieve a PM plan by its unique identifier.

        Args:
            plan_id: The UUID of the PM plan.

        Returns:
            The matching ``PMPlan`` aggregate.

        Raises:
            PMPlanNotFoundError: If no plan exists with this ID.
        """

    @abstractmethod
    def list_by_vehicle(
        self,
        vehicle_id: uuid.UUID,
        status: PMPlanStatus | None = None,
    ) -> list[PMPlan]:
        """Return PM plans for a given vehicle, optionally filtered by status.

        Args:
            vehicle_id: UUID of the vehicle.
            status: Optional status filter.

        Returns:
            A list of ``PMPlan`` aggregates.
        """

    @abstractmethod
    def list_active(self) -> list[PMPlan]:
        """Return all active PM plans across all vehicles.

        Returns:
            A list of active ``PMPlan`` aggregates.
        """

    @abstractmethod
    def save(self, plan: PMPlan) -> PMPlan:
        """Persist a new or updated PM plan aggregate.

        Args:
            plan: The ``PMPlan`` aggregate to save.

        Returns:
            The saved ``PMPlan`` aggregate.
        """

    @abstractmethod
    def delete(self, plan_id: uuid.UUID) -> None:
        """Soft-delete a PM plan record.

        Args:
            plan_id: The UUID of the plan to delete.

        Raises:
            PMPlanNotFoundError: If no plan exists with this ID.
        """


class IPMWorkOrderRepository(ABC):
    """Port (interface) for persisting and retrieving PMWorkOrder aggregates."""

    @abstractmethod
    def get_by_id(self, work_order_id: uuid.UUID) -> PMWorkOrder:
        """Retrieve a PM work order by its unique identifier.

        Args:
            work_order_id: The UUID of the work order.

        Returns:
            The matching ``PMWorkOrder`` aggregate.

        Raises:
            PMWorkOrderNotFoundError: If no work order exists with this ID.
        """

    @abstractmethod
    def list_by_plan(
        self,
        plan_id: uuid.UUID,
        status: PMWorkOrderStatus | None = None,
    ) -> list[PMWorkOrder]:
        """Return work orders for a given plan, optionally filtered by status.

        Args:
            plan_id: UUID of the parent PM plan.
            status: Optional status filter.

        Returns:
            A list of ``PMWorkOrder`` aggregates.
        """

    @abstractmethod
    def list_overdue(self) -> list[PMWorkOrder]:
        """Return all work orders in OVERDUE status.

        Returns:
            A list of overdue ``PMWorkOrder`` aggregates.
        """

    @abstractmethod
    def save(self, work_order: PMWorkOrder) -> PMWorkOrder:
        """Persist a new or updated PM work order aggregate.

        Args:
            work_order: The ``PMWorkOrder`` aggregate to save.

        Returns:
            The saved ``PMWorkOrder`` aggregate.
        """
