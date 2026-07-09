"""Goods Issue BAPI Adapter — implements ISAPGoodsIssuePort."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from apps.integration.domain.exceptions import SAPIntegrationError
from core.sap.dtos.goods_issue import PostGoodsIssueRequest, SAPGoodsIssueDTO
from core.sap.ports.goods_issue_port import ISAPGoodsIssuePort
from infrastructure.sap.adapters.bapi._bapi_helper import assert_bapi_success
from infrastructure.sap.client.base import ISAPClient, SAPClientError

logger = logging.getLogger(__name__)

_FM_POST = "BAPI_GOODSMVT_CREATE_GI"
_FM_REVERSE = "BAPI_GOODSMVT_CANCEL_GI"
_MOVEMENT_TYPE_GI = "261"


class GoodsIssueBAPIAdapter(ISAPGoodsIssuePort):
    """Posts and reverses Goods Issues in SAP via BAPI.

    Args:
        client: An ``ISAPClient`` instance.
    """

    def __init__(self, client: ISAPClient) -> None:
        self._client = client

    def post_goods_issue(self, request: PostGoodsIssueRequest) -> SAPGoodsIssueDTO:
        """Post a Goods Issue in SAP.

        Args:
            request: GI posting request with material and quantity details.

        Returns:
            ``SAPGoodsIssueDTO`` with the SAP material document number.

        Raises:
            SAPIntegrationError: On SAP business error or transport failure.
        """
        params = self._build_post_params(request)
        logger.info(
            "Posting SAP Goods Issue",
            extra={"line_count": len(request.line_items), "domain": "integration"},
        )
        try:
            result = self._client.bapi_call(_FM_POST, params)
        except SAPClientError as exc:
            raise SAPIntegrationError(
                f"Transport failure posting Goods Issue: {exc}"
            ) from exc

        assert_bapi_success(result, context="Goods Issue post")

        return SAPGoodsIssueDTO(
            material_document=result.get("MATERIALDOCUMENT", ""),
            posting_date=request.posting_date,
            created_at=date.today(),
        )

    def reverse_goods_issue(
        self,
        material_document: str,
        reversal_reason: str,
    ) -> SAPGoodsIssueDTO:
        """Reverse a Goods Issue in SAP.

        Args:
            material_document: The SAP material document to reverse.
            reversal_reason: Reason code or description.

        Returns:
            ``SAPGoodsIssueDTO`` representing the reversal document.

        Raises:
            SAPIntegrationError: On SAP business error or transport failure.
        """
        logger.info(
            "Reversing SAP Goods Issue",
            extra={"material_document": material_document, "domain": "integration"},
        )
        try:
            result = self._client.bapi_call(
                _FM_REVERSE,
                {
                    "MATERIALDOCUMENT": material_document,
                    "REASON_MVMT": reversal_reason,
                },
            )
        except SAPClientError as exc:
            raise SAPIntegrationError(
                f"Transport failure reversing GI {material_document!r}: {exc}"
            ) from exc

        assert_bapi_success(result, context="Goods Issue reverse")

        return SAPGoodsIssueDTO(
            material_document=result.get("MATERIALDOCUMENT", ""),
            posting_date=date.today(),
            created_at=date.today(),
        )

    @staticmethod
    def _build_post_params(request: PostGoodsIssueRequest) -> dict[str, Any]:
        """Build BAPI parameters from the GI posting request DTO."""
        return {
            "GOODSMVT_HEADER": {
                "PSTNG_DATE": request.posting_date.strftime("%Y%m%d"),
                "DOC_DATE": request.document_date.strftime("%Y%m%d"),
                "HEADER_TXT": request.header_text or "",
            },
            "GOODSMVT_ITEM": [
                {
                    "MATERIAL": item.material_number,
                    "MOVE_TYPE": _MOVEMENT_TYPE_GI,
                    "ENTRY_QNT": str(item.quantity),
                    "ENTRY_UOM": item.unit,
                    "PLANT": item.plant,
                    "STGE_LOC": item.storage_location,
                    "ORDERID": item.order_number or "",
                }
                for item in request.line_items
            ],
            "GOODSMVT_CODE": {"GM_CODE": "02"},
        }
