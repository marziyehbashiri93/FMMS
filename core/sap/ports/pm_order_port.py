"""SAP PM Order Port — abstract contract for maintenance order lifecycle.

A PM Order (Maintenance Order) is raised in SAP to authorize and plan
corrective or preventive maintenance work on fleet equipment.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from core.sap.dtos.pm_order import CreatePMOrderRequest, SAPPMOrderDTO


class ISAPPMOrderPort(ABC):
    """Business contract for managing PM Order lifecycle in SAP.

    Every call through this port must be routed via SAPTransactionManager
    to ensure idempotency, retry, and audit trail.
    """

    @abstractmethod
    def create_pm_order(self, request: CreatePMOrderRequest) -> SAPPMOrderDTO:
        """Create a new PM Order in SAP.

        Args:
            request: The order creation request with equipment and schedule details.

        Returns:
            A ``SAPPMOrderDTO`` with the SAP-assigned order number.

        Raises:
            SAPIntegrationError: If SAP rejects the order creation.
        """

    @abstractmethod
    def complete_pm_order(self, order_number: str) -> SAPPMOrderDTO:
        """Mark an existing PM Order as technically completed in SAP.

        Args:
            order_number: The SAP PM Order number to complete.

        Returns:
            The updated ``SAPPMOrderDTO`` reflecting the completed status.

        Raises:
            SAPIntegrationError: If SAP cannot complete the order.
        """

    @abstractmethod
    def get_pm_order(self, order_number: str) -> SAPPMOrderDTO:
        """Retrieve the current state of a PM Order from SAP.

        Args:
            order_number: The SAP PM Order number.

        Returns:
            A ``SAPPMOrderDTO`` with current status and schedule.

        Raises:
            SAPIntegrationError: If SAP returns an error or the order is not found.
        """
