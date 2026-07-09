"""Abstract repository interfaces for the Procurement bounded context."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from apps.procurement.domain.entities import (
    POStatus,
    PRStatus,
    PurchaseOrder,
    PurchaseRequisition,
)


class IPurchaseRequisitionRepository(ABC):
    """Port (interface) for persisting and retrieving PurchaseRequisition aggregates."""

    @abstractmethod
    def get_by_id(self, pr_id: uuid.UUID) -> PurchaseRequisition:
        """Retrieve a PR by its unique identifier.

        Args:
            pr_id: The UUID of the Purchase Requisition.

        Returns:
            The matching ``PurchaseRequisition`` aggregate.

        Raises:
            PRNotFoundError: If no PR exists with this ID.
        """

    @abstractmethod
    def list_by_repair_order(
        self, repair_order_id: uuid.UUID
    ) -> list[PurchaseRequisition]:
        """Return all PRs linked to a given repair order.

        Args:
            repair_order_id: UUID of the repair order.

        Returns:
            A list of ``PurchaseRequisition`` aggregates.
        """

    @abstractmethod
    def list_by_status(self, status: PRStatus) -> list[PurchaseRequisition]:
        """Return all PRs matching a given status.

        Args:
            status: The ``PRStatus`` to filter by.

        Returns:
            A list of ``PurchaseRequisition`` aggregates.
        """

    @abstractmethod
    def save(self, pr: PurchaseRequisition) -> PurchaseRequisition:
        """Persist a new or updated PR aggregate.

        Args:
            pr: The ``PurchaseRequisition`` aggregate to save.

        Returns:
            The saved ``PurchaseRequisition`` aggregate.
        """

    @abstractmethod
    def delete(self, pr_id: uuid.UUID) -> None:
        """Soft-delete a PR record.

        Args:
            pr_id: The UUID of the PR to delete.

        Raises:
            PRNotFoundError: If no PR exists with this ID.
        """


class IPurchaseOrderRepository(ABC):
    """Port (interface) for persisting and retrieving PurchaseOrder aggregates."""

    @abstractmethod
    def get_by_id(self, po_id: uuid.UUID) -> PurchaseOrder:
        """Retrieve a PO by its unique identifier.

        Args:
            po_id: The UUID of the Purchase Order.

        Returns:
            The matching ``PurchaseOrder`` aggregate.

        Raises:
            PONotFoundError: If no PO exists with this ID.
        """

    @abstractmethod
    def list_by_pr(self, pr_id: uuid.UUID) -> list[PurchaseOrder]:
        """Return all POs created from a given PR.

        Args:
            pr_id: UUID of the originating Purchase Requisition.

        Returns:
            A list of ``PurchaseOrder`` aggregates.
        """

    @abstractmethod
    def list_by_status(self, status: POStatus) -> list[PurchaseOrder]:
        """Return all POs matching a given status.

        Args:
            status: The ``POStatus`` to filter by.

        Returns:
            A list of ``PurchaseOrder`` aggregates.
        """

    @abstractmethod
    def save(self, po: PurchaseOrder) -> PurchaseOrder:
        """Persist a new or updated PO aggregate.

        Args:
            po: The ``PurchaseOrder`` aggregate to save.

        Returns:
            The saved ``PurchaseOrder`` aggregate.
        """

    @abstractmethod
    def delete(self, po_id: uuid.UUID) -> None:
        """Soft-delete a PO record.

        Args:
            po_id: The UUID of the PO to delete.

        Raises:
            PONotFoundError: If no PO exists with this ID.
        """
