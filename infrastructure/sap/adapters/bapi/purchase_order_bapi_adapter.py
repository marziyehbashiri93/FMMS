"""Purchase Order BAPI Adapter — implements ISAPPurchaseOrderPort."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from apps.integration.domain.exceptions import SAPIntegrationError
from core.sap.dtos.purchase_order import CreatePORequest, SAPPurchaseOrderDTO
from core.sap.ports.purchase_order_port import ISAPPurchaseOrderPort
from infrastructure.sap.adapters.bapi._bapi_helper import assert_bapi_success
from infrastructure.sap.client.base import ISAPClient, SAPClientError

logger = logging.getLogger(__name__)

_FM_CREATE = "BAPI_PO_CREATE1"
_FM_APPROVE = "BAPI_PO_APPROVE"
_FM_GET = "BAPI_PO_GET_DETAIL"


class PurchaseOrderBAPIAdapter(ISAPPurchaseOrderPort):
    """Creates and manages Purchase Orders in SAP via BAPI.

    Args:
        client: An ``ISAPClient`` instance.
    """

    def __init__(self, client: ISAPClient) -> None:
        self._client = client

    def create_purchase_order(self, request: CreatePORequest) -> SAPPurchaseOrderDTO:
        """Create a Purchase Order in SAP.

        Args:
            request: PO creation request.

        Returns:
            ``SAPPurchaseOrderDTO`` with the SAP PO number.

        Raises:
            SAPIntegrationError: On SAP business error or transport failure.
        """
        params = self._build_create_params(request)
        logger.info(
            "Creating SAP Purchase Order",
            extra={"vendor_number": request.vendor_number, "domain": "integration"},
        )
        try:
            result = self._client.bapi_call(_FM_CREATE, params)
        except SAPClientError as exc:
            raise SAPIntegrationError(
                f"Transport failure creating Purchase Order: {exc}"
            ) from exc

        assert_bapi_success(result, context="Purchase Order create")

        return SAPPurchaseOrderDTO(
            po_number=result.get("PURCHASEORDER", ""),
            vendor_number=request.vendor_number,
            status="CREATED",
            created_at=date.today(),
        )

    def approve_purchase_order(self, po_number: str) -> SAPPurchaseOrderDTO:
        """Approve a Purchase Order in SAP.

        Args:
            po_number: The SAP PO document number.

        Returns:
            Updated ``SAPPurchaseOrderDTO`` with approved status.

        Raises:
            SAPIntegrationError: On SAP business error or transport failure.
        """
        logger.info(
            "Approving SAP Purchase Order",
            extra={"po_number": po_number, "domain": "integration"},
        )
        try:
            result = self._client.bapi_call(_FM_APPROVE, {"PURCHASEORDER": po_number})
        except SAPClientError as exc:
            raise SAPIntegrationError(
                f"Transport failure approving PO {po_number!r}: {exc}"
            ) from exc

        assert_bapi_success(result, context="Purchase Order approve")

        return SAPPurchaseOrderDTO(
            po_number=po_number,
            vendor_number="",
            status="APPROVED",
            created_at=date.today(),
        )

    def get_purchase_order(self, po_number: str) -> SAPPurchaseOrderDTO:
        """Retrieve a Purchase Order from SAP.

        Args:
            po_number: The SAP PO document number.

        Returns:
            ``SAPPurchaseOrderDTO`` with current status.

        Raises:
            SAPIntegrationError: On SAP business error or transport failure.
        """
        logger.info(
            "Fetching SAP Purchase Order",
            extra={"po_number": po_number, "domain": "integration"},
        )
        try:
            result = self._client.bapi_call(_FM_GET, {"PURCHASEORDER": po_number})
        except SAPClientError as exc:
            raise SAPIntegrationError(
                f"Transport failure fetching PO {po_number!r}: {exc}"
            ) from exc

        assert_bapi_success(result, context="Purchase Order get")

        header: dict[str, Any] = result.get("PO_HEADER", {})
        return SAPPurchaseOrderDTO(
            po_number=header.get("PO_NUMBER", po_number),
            vendor_number=header.get("VENDOR", ""),
            status="ACTIVE",
            created_at=date.today(),
        )

    @staticmethod
    def _build_create_params(request: CreatePORequest) -> dict[str, Any]:
        """Build BAPI parameters from the PO request DTO."""
        return {
            "POHEADER": {
                "DOC_TYPE": request.document_type,
                "VENDOR": request.vendor_number,
                "CURRENCY": request.currency,
                "PMNTTRMS": "",
            },
            "POITEM": [
                {
                    "PO_ITEM": item.item_number,
                    "MATERIAL": item.material_number,
                    "QUANTITY": str(item.quantity),
                    "PO_UNIT": item.unit,
                    "NET_PRICE": str(item.net_price),
                    "CURRENCY": item.currency,
                    "PLANT": item.plant,
                    "DELIV_DATE": item.delivery_date.strftime("%Y%m%d"),
                }
                for item in request.line_items
            ],
        }
