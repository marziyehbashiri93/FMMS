"""SAP Purchase Requisition Port — abstract contract for PR lifecycle.

A Purchase Requisition is raised when FMMS requires materials for repair
activities. SAP is responsible for PR approval and conversion to PO.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from core.sap.dtos.purchase_requisition import (
    CreatePRRequest,
    SAPPurchaseRequisitionDTO,
)


class ISAPPurchaseRequisitionPort(ABC):
    """Business contract for managing Purchase Requisition lifecycle in SAP.

    Every call through this port must be routed via SAPTransactionManager
    to ensure idempotency, retry, and audit trail.
    """

    @abstractmethod
    def create_purchase_requisition(
        self,
        request: CreatePRRequest,
    ) -> SAPPurchaseRequisitionDTO:
        """Create a new Purchase Requisition in SAP.

        Args:
            request: The PR creation request with line item details.

        Returns:
            A ``SAPPurchaseRequisitionDTO`` with the SAP-assigned PR number.

        Raises:
            SAPIntegrationError: If SAP rejects the PR creation.
        """

    @abstractmethod
    def get_purchase_requisition(self, pr_number: str) -> SAPPurchaseRequisitionDTO:
        """Retrieve the current state of a Purchase Requisition from SAP.

        Args:
            pr_number: The SAP PR document number.

        Returns:
            A ``SAPPurchaseRequisitionDTO`` with current status and line items.

        Raises:
            SAPIntegrationError: If SAP returns an error or the PR is not found.
        """
