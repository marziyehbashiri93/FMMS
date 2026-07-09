"""Service PO BAPI Adapter — implements ISAPServicePOPort."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from apps.integration.domain.exceptions import SAPIntegrationError
from core.sap.dtos.service_po import CreateServicePORequest, SAPServicePODTO
from core.sap.ports.service_po_port import ISAPServicePOPort
from infrastructure.sap.adapters.bapi._bapi_helper import assert_bapi_success
from infrastructure.sap.client.base import ISAPClient, SAPClientError

logger = logging.getLogger(__name__)

_FM_CREATE = "BAPI_SERVICE_PO_CREATE"
_FM_CONFIRM = "BAPI_SERVICE_PO_CONFIRM"
_FM_GET = "BAPI_SERVICE_PO_GET"


class ServicePOBAPIAdapter(ISAPServicePOPort):
    """Creates and manages Service Purchase Orders in SAP via BAPI.

    Args:
        client: An ``ISAPClient`` instance.
    """

    def __init__(self, client: ISAPClient) -> None:
        self._client = client

    def create_service_po(self, request: CreateServicePORequest) -> SAPServicePODTO:
        """Create a Service Purchase Order in SAP.

        Args:
            request: Service PO creation request.

        Returns:
            ``SAPServicePODTO`` with the SAP PO number.

        Raises:
            SAPIntegrationError: On SAP business error or transport failure.
        """
        params = self._build_create_params(request)
        logger.info(
            "Creating SAP Service PO",
            extra={"vendor_number": request.vendor_number, "domain": "integration"},
        )
        try:
            result = self._client.bapi_call(_FM_CREATE, params)
        except SAPClientError as exc:
            raise SAPIntegrationError(
                f"Transport failure creating Service PO: {exc}"
            ) from exc

        assert_bapi_success(result, context="Service PO create")

        return SAPServicePODTO(
            po_number=result.get("PURCHASEORDER", ""),
            vendor_number=request.vendor_number,
            status="CREATED",
            created_at=date.today(),
        )

    def confirm_service(self, po_number: str) -> SAPServicePODTO:
        """Record service acceptance for a Service PO in SAP.

        Args:
            po_number: The SAP service PO document number.

        Returns:
            Updated ``SAPServicePODTO`` with confirmed status.

        Raises:
            SAPIntegrationError: On SAP business error or transport failure.
        """
        logger.info(
            "Confirming SAP Service PO",
            extra={"po_number": po_number, "domain": "integration"},
        )
        try:
            result = self._client.bapi_call(_FM_CONFIRM, {"PURCHASEORDER": po_number})
        except SAPClientError as exc:
            raise SAPIntegrationError(
                f"Transport failure confirming Service PO {po_number!r}: {exc}"
            ) from exc

        assert_bapi_success(result, context="Service PO confirm")

        return SAPServicePODTO(
            po_number=po_number,
            vendor_number="",
            status="CONFIRMED",
            created_at=date.today(),
        )

    def get_service_po(self, po_number: str) -> SAPServicePODTO:
        """Retrieve a Service Purchase Order from SAP.

        Args:
            po_number: The SAP service PO document number.

        Returns:
            ``SAPServicePODTO`` with current status.

        Raises:
            SAPIntegrationError: On SAP business error or transport failure.
        """
        logger.info(
            "Fetching SAP Service PO",
            extra={"po_number": po_number, "domain": "integration"},
        )
        try:
            result = self._client.bapi_call(_FM_GET, {"PURCHASEORDER": po_number})
        except SAPClientError as exc:
            raise SAPIntegrationError(
                f"Transport failure fetching Service PO {po_number!r}: {exc}"
            ) from exc

        assert_bapi_success(result, context="Service PO get")

        header: dict[str, Any] = result.get("PO_HEADER", {})
        return SAPServicePODTO(
            po_number=header.get("PO_NUMBER", po_number),
            vendor_number=header.get("VENDOR", ""),
            status="ACTIVE",
            created_at=date.today(),
        )

    @staticmethod
    def _build_create_params(request: CreateServicePORequest) -> dict[str, Any]:
        """Build BAPI parameters from the service PO request DTO."""
        return {
            "POHEADER": {
                "DOC_TYPE": request.document_type,
                "VENDOR": request.vendor_number,
                "CURRENCY": request.currency,
                "WERKS": request.plant,
            },
            "POITEM": [
                {
                    "SERVICE": line.service_number,
                    "QUANTITY": str(line.quantity),
                    "C_UOM": line.unit,
                    "GROSS_PRICE": str(line.gross_price),
                    "CURRENCY": line.currency,
                    "SHORT_TEXT": line.description or "",
                }
                for line in request.service_lines
            ],
        }
