"""SAP Purchase Order Port — abstract contract for PO lifecycle.

A Purchase Order is created in SAP to formally commit to purchasing
materials or services from a vendor. FMMS may create POs directly
from approved Purchase Requisitions.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from core.sap.dtos.purchase_order import CreatePORequest, SAPPurchaseOrderDTO


class ISAPPurchaseOrderPort(ABC):
    """Business contract for managing Purchase Order lifecycle in SAP.

    Every call through this port must be routed via SAPTransactionManager
    to ensure idempotency, retry, and audit trail.
    """

    @abstractmethod
    def create_purchase_order(self, request: CreatePORequest) -> SAPPurchaseOrderDTO:
        """Create a new Purchase Order in SAP.

        Args:
            request: The PO creation request with vendor and line item details.

        Returns:
            A ``SAPPurchaseOrderDTO`` with the SAP-assigned PO number.

        Raises:
            SAPIntegrationError: If SAP rejects the PO creation.
        """

    @abstractmethod
    def approve_purchase_order(self, po_number: str) -> SAPPurchaseOrderDTO:
        """Approve an existing Purchase Order in SAP.

        Args:
            po_number: The SAP PO document number to approve.

        Returns:
            The updated ``SAPPurchaseOrderDTO`` reflecting the approved status.

        Raises:
            SAPIntegrationError: If SAP cannot approve the order.
        """

    @abstractmethod
    def get_purchase_order(self, po_number: str) -> SAPPurchaseOrderDTO:
        """Retrieve the current state of a Purchase Order from SAP.

        Args:
            po_number: The SAP PO document number.

        Returns:
            A ``SAPPurchaseOrderDTO`` with current status.

        Raises:
            SAPIntegrationError: If SAP returns an error or the PO is not found.
        """
