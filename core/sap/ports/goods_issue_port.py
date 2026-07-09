"""SAP Goods Issue Port — abstract contract for goods issue posting.

A Goods Issue is posted when materials are consumed from stock for a
maintenance activity. FMMS triggers GI posting when repair parts are
recorded as consumed against a repair order.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from core.sap.dtos.goods_issue import PostGoodsIssueRequest, SAPGoodsIssueDTO


class ISAPGoodsIssuePort(ABC):
    """Business contract for posting Goods Issues in SAP.

    Every call through this port must be routed via SAPTransactionManager
    to ensure idempotency, retry, and audit trail.
    """

    @abstractmethod
    def post_goods_issue(self, request: PostGoodsIssueRequest) -> SAPGoodsIssueDTO:
        """Post a Goods Issue in SAP to consume materials from stock.

        Args:
            request: The GI posting request with material and quantity details.

        Returns:
            A ``SAPGoodsIssueDTO`` with the SAP material document number.

        Raises:
            SAPIntegrationError: If SAP rejects the goods issue posting.
        """

    @abstractmethod
    def reverse_goods_issue(
        self,
        material_document: str,
        reversal_reason: str,
    ) -> SAPGoodsIssueDTO:
        """Reverse a previously posted Goods Issue in SAP.

        Args:
            material_document: The SAP material document number to reverse.
            reversal_reason: A code or description explaining the reversal reason.

        Returns:
            A ``SAPGoodsIssueDTO`` representing the reversal document.

        Raises:
            SAPIntegrationError: If SAP cannot reverse the goods issue.
        """
