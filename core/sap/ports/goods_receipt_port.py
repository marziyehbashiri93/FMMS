"""SAP Goods Receipt Port — abstract contract for goods receipt posting.

A Goods Receipt is posted when materials ordered via a Purchase Order
arrive at the warehouse. FMMS triggers GR posting upon delivery confirmation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from core.sap.dtos.goods_receipt import PostGoodsReceiptRequest, SAPGoodsReceiptDTO


class ISAPGoodsReceiptPort(ABC):
    """Business contract for posting Goods Receipts in SAP.

    Every call through this port must be routed via SAPTransactionManager
    to ensure idempotency, retry, and audit trail.
    """

    @abstractmethod
    def post_goods_receipt(
        self,
        request: PostGoodsReceiptRequest,
    ) -> SAPGoodsReceiptDTO:
        """Post a Goods Receipt in SAP against a Purchase Order.

        Args:
            request: The GR posting request with PO reference and line items.

        Returns:
            A ``SAPGoodsReceiptDTO`` with the SAP material document number.

        Raises:
            SAPIntegrationError: If SAP rejects the goods receipt posting.
        """

    @abstractmethod
    def reverse_goods_receipt(
        self,
        material_document: str,
        reversal_reason: str,
    ) -> SAPGoodsReceiptDTO:
        """Reverse a previously posted Goods Receipt in SAP.

        Args:
            material_document: The SAP material document number to reverse.
            reversal_reason: A code or description explaining the reversal reason.

        Returns:
            A ``SAPGoodsReceiptDTO`` representing the reversal document.

        Raises:
            SAPIntegrationError: If SAP cannot reverse the goods receipt.
        """
