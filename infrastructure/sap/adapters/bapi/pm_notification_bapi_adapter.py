"""PM Notification BAPI Adapter — implements ISAPPMNotificationPort.

Creates and closes SAP PM Notifications for fleet fault management.
Every call must be routed through SAPTransactionManager for idempotency
and retry guarantees.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from apps.integration.domain.exceptions import SAPIntegrationError
from core.sap.dtos.pm_notification import (
    CreatePMNotificationRequest,
    SAPNotificationDTO,
)
from core.sap.ports.pm_notification_port import ISAPPMNotificationPort
from infrastructure.sap.adapters.bapi._bapi_helper import assert_bapi_success
from infrastructure.sap.client.base import ISAPClient, SAPClientError

logger = logging.getLogger(__name__)

_FM_CREATE = "BAPI_ALM_NOTIF_CREATE"
_FM_CLOSE = "BAPI_ALM_NOTIF_CLOSE"


class PMNotificationBAPIAdapter(ISAPPMNotificationPort):
    """Creates and closes PM Notifications in SAP via BAPI.

    Args:
        client: An ``ISAPClient`` instance (mock or production BAPI client).
    """

    def __init__(self, client: ISAPClient) -> None:
        self._client = client

    def create_notification(
        self,
        request: CreatePMNotificationRequest,
    ) -> SAPNotificationDTO:
        """Create a PM Notification in SAP.

        Args:
            request: Notification creation request with fault details.

        Returns:
            ``SAPNotificationDTO`` with the SAP notification number.

        Raises:
            SAPIntegrationError: On SAP business error or transport failure.
        """
        params = self._build_create_params(request)
        logger.info(
            "Creating SAP PM Notification",
            extra={
                "equipment_number": request.equipment_number,
                "defect_code": request.defect_code,
                "domain": "integration",
            },
        )
        try:
            result = self._client.bapi_call(_FM_CREATE, params)
        except SAPClientError as exc:
            raise SAPIntegrationError(
                f"Transport failure creating PM Notification: {exc}"
            ) from exc

        assert_bapi_success(result, context="PM Notification create")

        return SAPNotificationDTO(
            notification_number=_notification_number_from_result(result),
            equipment_number=request.equipment_number,
            status="OPEN",
            created_at=datetime.now(tz=UTC),
        )

    def close_notification(self, notification_number: str) -> SAPNotificationDTO:
        """Close an existing PM Notification in SAP.

        Args:
            notification_number: The SAP notification number to close.

        Returns:
            Updated ``SAPNotificationDTO`` with closed status.

        Raises:
            SAPIntegrationError: On SAP business error or transport failure.
        """
        logger.info(
            "Closing SAP PM Notification",
            extra={
                "notification_number": notification_number,
                "domain": "integration",
            },
        )
        try:
            result = self._client.bapi_call(
                _FM_CLOSE,
                {"NOTIFNO": notification_number},
            )
        except SAPClientError as exc:
            raise SAPIntegrationError(
                f"Transport failure closing PM Notification {notification_number!r}: {exc}"
            ) from exc

        assert_bapi_success(result, context="PM Notification close")

        return SAPNotificationDTO(
            notification_number=notification_number,
            equipment_number="",
            status="CLOSED",
            created_at=datetime.now(tz=UTC),
        )

    @staticmethod
    def _build_create_params(request: CreatePMNotificationRequest) -> dict[str, Any]:
        """Build the BAPI import parameter dictionary from the request DTO."""
        reported_date = request.reported_at.strftime("%Y%m%d")
        return {
            "NOTIF_TYPE": request.notification_type,
            "EQUIPMENT": request.equipment_number,
            "DESCRIPT": request.fault_description[:40],
            "NOTIFHEADER": {
                "STRMLFNDATE": reported_date,
                "DESSTDATE": reported_date,
                "FUNCT_LOC": request.functional_location or "",
                "PRIOK": request.priority,
                "REPORTEDBY": request.reported_by,
            },
            "NOTIFCAUS": [
                {
                    "CAUSE_CODE": request.defect_code,
                    "CAUSE_CODEGROUP": request.code_group or "",
                }
            ],
        }


def _notification_number_from_result(result: dict[str, Any]) -> str:
    """Extract the notification number from known SAP response shapes."""
    header = result.get("NOTIFHEADER_EXPORT")
    if isinstance(header, dict):
        notification_number = header.get("NOTIF_NO")
        if notification_number:
            return str(notification_number)
    return str(result.get("NOTIFNO", ""))
