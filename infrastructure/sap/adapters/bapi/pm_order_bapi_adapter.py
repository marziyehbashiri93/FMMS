"""PM Order BAPI Adapter — implements ISAPPMOrderPort.

Creates, completes, and reads SAP PM Maintenance Orders for repair
and preventive maintenance workflows.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from apps.integration.domain.exceptions import SAPIntegrationError
from core.sap.dtos.pm_order import CreatePMOrderRequest, SAPPMOrderDTO
from core.sap.ports.pm_order_port import ISAPPMOrderPort
from infrastructure.sap.adapters.bapi._bapi_helper import assert_bapi_success
from infrastructure.sap.client.base import ISAPClient, SAPClientError

logger = logging.getLogger(__name__)

_FM_CREATE = "BAPI_ALM_ORDER_MAINTAIN"
_FM_COMPLETE = "BAPI_ALM_ORDER_COMPLETE"
_FM_READ = "BAPI_ALM_ORDER_READ"


class PMOrderBAPIAdapter(ISAPPMOrderPort):
    """Creates and manages PM Orders in SAP via BAPI.

    Args:
        client: An ``ISAPClient`` instance.
    """

    def __init__(self, client: ISAPClient) -> None:
        self._client = client

    def create_pm_order(self, request: CreatePMOrderRequest) -> SAPPMOrderDTO:
        """Create a new PM Order in SAP.

        Args:
            request: PM Order creation request.

        Returns:
            ``SAPPMOrderDTO`` with the SAP order number.

        Raises:
            SAPIntegrationError: On SAP business error or transport failure.
        """
        params = self._build_create_params(request)
        logger.info(
            "Creating SAP PM Order",
            extra={
                "equipment_number": request.equipment_number,
                "order_type": request.order_type,
                "domain": "integration",
            },
        )
        try:
            result = self._client.bapi_call(_FM_CREATE, params)
        except SAPClientError as exc:
            raise SAPIntegrationError(
                f"Transport failure creating PM Order: {exc}"
            ) from exc

        assert_bapi_success(result, context="PM Order create")

        return SAPPMOrderDTO(
            order_number=result.get("ORDER_NUMBER", ""),
            equipment_number=request.equipment_number,
            order_type=request.order_type,
            status="CREATED",
            planned_start=request.planned_start,
            planned_end=request.planned_end,
            notification_number=request.notification_number,
        )

    def complete_pm_order(self, order_number: str) -> SAPPMOrderDTO:
        """Mark a PM Order as technically completed in SAP.

        Args:
            order_number: The SAP PM Order number.

        Returns:
            Updated ``SAPPMOrderDTO`` with completed status.

        Raises:
            SAPIntegrationError: On SAP business error or transport failure.
        """
        logger.info(
            "Completing SAP PM Order",
            extra={"order_number": order_number, "domain": "integration"},
        )
        try:
            result = self._client.bapi_call(
                _FM_COMPLETE,
                {"ORDER_NUMBER": order_number},
            )
        except SAPClientError as exc:
            raise SAPIntegrationError(
                f"Transport failure completing PM Order {order_number!r}: {exc}"
            ) from exc

        assert_bapi_success(result, context="PM Order complete")

        return SAPPMOrderDTO(
            order_number=order_number,
            equipment_number="",
            order_type="",
            status="COMPLETED",
        )

    def get_pm_order(self, order_number: str) -> SAPPMOrderDTO:
        """Retrieve the current state of a PM Order from SAP.

        Args:
            order_number: The SAP PM Order number.

        Returns:
            ``SAPPMOrderDTO`` with current status.

        Raises:
            SAPIntegrationError: On SAP business error or transport failure.
        """
        logger.info(
            "Fetching SAP PM Order",
            extra={"order_number": order_number, "domain": "integration"},
        )
        try:
            result = self._client.bapi_call(
                _FM_READ,
                {"ORDER_NUMBER": order_number},
            )
        except SAPClientError as exc:
            raise SAPIntegrationError(
                f"Transport failure fetching PM Order {order_number!r}: {exc}"
            ) from exc

        assert_bapi_success(result, context="PM Order read")
        return self._map_get_result(result)

    @staticmethod
    def _build_create_params(request: CreatePMOrderRequest) -> dict[str, Any]:
        """Build the BAPI import parameters from the request DTO."""
        return {
            "ORDER_HEADER_DATA": {
                "EQUNR": request.equipment_number,
                "AUART": request.order_type,
                "KTEXT": request.description[:40],
                "QMNUM": request.notification_number or "",
                "ARBPL": request.work_center or "",
                "WERKS": request.plant or "",
                "GSTRP": request.planned_start.strftime("%Y%m%d"),
                "GLTRP": (
                    request.planned_end.strftime("%Y%m%d")
                    if request.planned_end
                    else ""
                ),
            },
        }

    @staticmethod
    def _map_get_result(result: dict[str, Any]) -> SAPPMOrderDTO:
        """Map a BAPI_ALM_ORDER_READ result to ``SAPPMOrderDTO``."""
        header: dict[str, Any] = result.get("ORDER_HEADER_DATA", {})
        planned_start_raw = header.get("GSTRP", "")
        planned_end_raw = header.get("GLTRP", "")

        def parse_date(raw: str) -> datetime | None:
            if raw and raw != "00000000":
                try:
                    return datetime.strptime(raw, "%Y%m%d").replace(tzinfo=UTC)
                except ValueError:
                    return None
            return None

        return SAPPMOrderDTO(
            order_number=header.get("ORDERID", ""),
            equipment_number=header.get("EQUNR", ""),
            order_type=header.get("AUART", ""),
            status=header.get("SYSST", ""),
            planned_start=parse_date(planned_start_raw),
            planned_end=parse_date(planned_end_raw),
            notification_number=header.get("QMNUM") or None,
        )
