"""Goods Receipt BAPI Adapter — implements ISAPGoodsReceiptPort."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from apps.integration.domain.exceptions import SAPIntegrationError
from core.sap.dtos.goods_receipt import PostGoodsReceiptRequest, SAPGoodsReceiptDTO
from core.sap.ports.goods_receipt_port import ISAPGoodsReceiptPort
from infrastructure.sap.adapters.bapi._bapi_helper import assert_bapi_success
from infrastructure.sap.client.base import ISAPClient, SAPClientError

logger = logging.getLogger(__name__)

_FM_POST = "BAPI_GOODSMVT_CREATE_GR"
_FM_REVERSE = "BAPI_GOODSMVT_CANCEL_GR"
_MOVEMENT_TYPE_GR = "101"


class GoodsReceiptBAPIAdapter(ISAPGoodsReceiptPort):
    """Posts and reverses Goods Receipts in SAP via BAPI.

    Args:
        client: An ``ISAPClient`` instance.
    """

    def __init__(self, client: ISAPClient) -> None:
        self._client = client

    def post_goods_receipt(
        self,
        request: PostGoodsReceiptRequest,
    ) -> SAPGoodsReceiptDTO:
        """Post a Goods Receipt in SAP.

        Args:
            request: GR posting request with PO reference and line items.

        Returns:
            ``SAPGoodsReceiptDTO`` with the SAP material document number.

        Raises:
            SAPIntegrationError: On SAP business error or transport failure.
        """
        params = self._build_post_params(request)
        logger.info(
            "Posting SAP Goods Receipt",
            extra={"po_number": request.po_number, "domain": "integration"},
        )
        try:
            result = self._client.bapi_call(_FM_POST, params)
        except SAPClientError as exc:
            raise SAPIntegrationError(
                f"Transport failure posting Goods Receipt for PO {request.po_number!r}: {exc}"
            ) from exc

        assert_bapi_success(result, context="Goods Receipt post")

        return SAPGoodsReceiptDTO(
            material_document=result.get("MATERIALDOCUMENT", ""),
            posting_date=request.posting_date,
            created_at=date.today(),
        )

    def reverse_goods_receipt(
        self,
        material_document: str,
        reversal_reason: str,
    ) -> SAPGoodsReceiptDTO:
        """Reverse a Goods Receipt in SAP.

        Args:
            material_document: The SAP material document to reverse.
            reversal_reason: Reason code or description.

        Returns:
            ``SAPGoodsReceiptDTO`` representing the reversal document.

        Raises:
            SAPIntegrationError: On SAP business error or transport failure.
        """
        logger.info(
            "Reversing SAP Goods Receipt",
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
                f"Transport failure reversing GR {material_document!r}: {exc}"
            ) from exc

        assert_bapi_success(result, context="Goods Receipt reverse")

        return SAPGoodsReceiptDTO(
            material_document=result.get("MATERIALDOCUMENT", ""),
            posting_date=date.today(),
            created_at=date.today(),
        )

    @staticmethod
    def _build_post_params(request: PostGoodsReceiptRequest) -> dict[str, Any]:
        """Build BAPI parameters from the GR posting request DTO."""
        return {
            "GOODSMVT_HEADER": {
                "PSTNG_DATE": request.posting_date.strftime("%Y%m%d"),
                "DOC_DATE": request.document_date.strftime("%Y%m%d"),
                "HEADER_TXT": request.header_text or "",
            },
            "GOODSMVT_ITEM": [
                {
                    "PO_NUMBER": item.po_number,
                    "PO_ITEM": item.po_item,
                    "MOVE_TYPE": _MOVEMENT_TYPE_GR,
                    "ENTRY_QNT": str(item.quantity),
                    "ENTRY_UOM": item.unit,
                    "PLANT": item.plant,
                    "STGE_LOC": item.storage_location,
                }
                for item in request.line_items
            ],
            "GOODSMVT_CODE": {"GM_CODE": "01"},
        }
