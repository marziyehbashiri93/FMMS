"""Purchase Requisition BAPI Adapter — implements ISAPPurchaseRequisitionPort."""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from typing import Any

from apps.integration.domain.exceptions import SAPIntegrationError
from core.sap.dtos.purchase_requisition import (
    CreatePRRequest,
    SAPPRLineItemDTO,
    SAPPurchaseRequisitionDTO,
)
from core.sap.ports.purchase_requisition_port import ISAPPurchaseRequisitionPort
from infrastructure.sap.adapters.bapi._bapi_helper import assert_bapi_success
from infrastructure.sap.client.base import ISAPClient, SAPClientError

logger = logging.getLogger(__name__)

_FM_CREATE = "BAPI_PR_CREATE"


class PurchaseRequisitionBAPIAdapter(ISAPPurchaseRequisitionPort):
    """Creates Purchase Requisitions in SAP via BAPI.

    Args:
        client: An ``ISAPClient`` instance.
    """

    def __init__(self, client: ISAPClient) -> None:
        self._client = client

    def create_purchase_requisition(
        self,
        request: CreatePRRequest,
    ) -> SAPPurchaseRequisitionDTO:
        """Create a Purchase Requisition in SAP.

        Args:
            request: PR creation request with line items.

        Returns:
            ``SAPPurchaseRequisitionDTO`` with the SAP PR number.

        Raises:
            SAPIntegrationError: On SAP business error or transport failure.
        """
        params = self._build_params(request)
        logger.info(
            "Creating SAP Purchase Requisition",
            extra={
                "line_count": len(request.line_items),
                "domain": "integration",
            },
        )
        try:
            result = self._client.bapi_call(_FM_CREATE, params)
        except SAPClientError as exc:
            raise SAPIntegrationError(
                f"Transport failure creating Purchase Requisition: {exc}"
            ) from exc

        assert_bapi_success(result, context="Purchase Requisition create")

        pr_number: str = result.get("NUMBER", "")
        raw_items: list[dict[str, Any]] = result.get("PRITEM", [])

        line_items = [
            SAPPRLineItemDTO(
                item_number=item.get("PREQ_ITEM", ""),
                material_number=item.get("MATERIAL", ""),
                quantity=Decimal(item.get("QUANTITY", "0")),
                unit=item.get("UNIT", ""),
            )
            for item in raw_items
        ]

        return SAPPurchaseRequisitionDTO(
            pr_number=pr_number,
            line_items=line_items,
            created_at=date.today(),
        )

    def get_purchase_requisition(self, pr_number: str) -> SAPPurchaseRequisitionDTO:
        """Retrieve a Purchase Requisition from SAP.

        Args:
            pr_number: The SAP PR document number.

        Returns:
            ``SAPPurchaseRequisitionDTO`` with current line items.

        Raises:
            SAPIntegrationError: On SAP business error or transport failure.
        """
        logger.info(
            "Fetching SAP Purchase Requisition",
            extra={"pr_number": pr_number, "domain": "integration"},
        )
        try:
            result = self._client.bapi_call(
                "BAPI_PR_GET_DETAIL",
                {"NUMBER": pr_number},
            )
        except SAPClientError as exc:
            raise SAPIntegrationError(
                f"Transport failure fetching PR {pr_number!r}: {exc}"
            ) from exc

        assert_bapi_success(result, context="Purchase Requisition get")

        raw_items: list[dict[str, Any]] = result.get("PRITEM", [])
        line_items = [
            SAPPRLineItemDTO(
                item_number=item.get("PREQ_ITEM", ""),
                material_number=item.get("MATERIAL", ""),
                quantity=Decimal(item.get("QUANTITY", "0")),
                unit=item.get("UNIT", ""),
            )
            for item in raw_items
        ]

        return SAPPurchaseRequisitionDTO(
            pr_number=pr_number,
            line_items=line_items,
            created_at=date.today(),
        )

    @staticmethod
    def _build_params(request: CreatePRRequest) -> dict[str, Any]:
        """Build BAPI parameters from the PR request DTO."""
        return {
            "PRHEADER": {
                "DOC_TYPE": request.document_type,
                "HEADER_TXT": request.header_text or "",
            },
            "PRITEM": [
                {
                    "PREQ_ITEM": item.item_number,
                    "MATERIAL": item.material_number,
                    "QUANTITY": str(item.quantity),
                    "UNIT": item.unit,
                    "DELIV_DATE": item.delivery_date.strftime("%Y%m%d"),
                    "PLANT": item.plant,
                    "SHORT_TEXT": item.description or "",
                }
                for item in request.line_items
            ],
        }
