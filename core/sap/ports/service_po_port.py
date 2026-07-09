"""SAP Service PO Port — abstract contract for service purchase order lifecycle.

A Service PO is raised when FMMS requires external contracted services
(e.g. specialist vehicle repairs). The service is confirmed in SAP upon
completion of the contracted work.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from core.sap.dtos.service_po import CreateServicePORequest, SAPServicePODTO


class ISAPServicePOPort(ABC):
    """Business contract for managing Service Purchase Order lifecycle in SAP.

    Every call through this port must be routed via SAPTransactionManager
    to ensure idempotency, retry, and audit trail.
    """

    @abstractmethod
    def create_service_po(self, request: CreateServicePORequest) -> SAPServicePODTO:
        """Create a new Service Purchase Order in SAP.

        Args:
            request: The service PO creation request with vendor and service details.

        Returns:
            A ``SAPServicePODTO`` with the SAP-assigned service PO number.

        Raises:
            SAPIntegrationError: If SAP rejects the service PO creation.
        """

    @abstractmethod
    def confirm_service(self, po_number: str) -> SAPServicePODTO:
        """Record service confirmation (acceptance) for a Service PO in SAP.

        Args:
            po_number: The SAP service PO document number.

        Returns:
            The updated ``SAPServicePODTO`` reflecting the confirmed status.

        Raises:
            SAPIntegrationError: If SAP cannot record the service confirmation.
        """

    @abstractmethod
    def get_service_po(self, po_number: str) -> SAPServicePODTO:
        """Retrieve the current state of a Service Purchase Order from SAP.

        Args:
            po_number: The SAP service PO document number.

        Returns:
            A ``SAPServicePODTO`` with current status.

        Raises:
            SAPIntegrationError: If SAP returns an error or the PO is not found.
        """
