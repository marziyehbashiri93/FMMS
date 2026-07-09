"""SAP PM Notification Port — abstract contract for notification lifecycle.

A PM Notification is raised in SAP when a fault is identified against a
fleet vehicle. FMMS creates and closes notifications as part of the fault
management workflow.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from core.sap.dtos.pm_notification import (
    CreatePMNotificationRequest,
    SAPNotificationDTO,
)


class ISAPPMNotificationPort(ABC):
    """Business contract for managing PM Notification lifecycle in SAP.

    Every call through this port must be routed via SAPTransactionManager
    to ensure idempotency, retry, and audit trail.
    """

    @abstractmethod
    def create_notification(
        self,
        request: CreatePMNotificationRequest,
    ) -> SAPNotificationDTO:
        """Create a new PM Notification in SAP for a reported fault.

        Args:
            request: The notification creation request containing fault details.

        Returns:
            A ``SAPNotificationDTO`` with the SAP-assigned notification number.

        Raises:
            SAPIntegrationError: If SAP rejects the notification or returns an error.
        """

    @abstractmethod
    def close_notification(self, notification_number: str) -> SAPNotificationDTO:
        """Close an existing PM Notification in SAP.

        Closing a notification signals that the fault has been resolved.

        Args:
            notification_number: The SAP PM Notification number to close.

        Returns:
            The updated ``SAPNotificationDTO`` reflecting the closed status.

        Raises:
            SAPIntegrationError: If SAP cannot close the notification.
        """
