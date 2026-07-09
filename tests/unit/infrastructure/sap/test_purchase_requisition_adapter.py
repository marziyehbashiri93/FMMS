"""Unit tests for PurchaseRequisitionBAPIAdapter using MockSAPClient."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from apps.integration.domain.exceptions import SAPIntegrationError
from core.sap.dtos.purchase_requisition import CreatePRRequest, PRLineItemRequest
from infrastructure.sap.adapters.bapi.purchase_requisition_bapi_adapter import (
    PurchaseRequisitionBAPIAdapter,
)
from infrastructure.sap.client.mock.mock_client import MockSAPClient, SAPMockScenario


def _make_request() -> CreatePRRequest:
    return CreatePRRequest(
        document_type="NB",
        line_items=[
            PRLineItemRequest(
                item_number="00010",
                material_number="MAT-001",
                quantity=Decimal("10"),
                unit="L",
                delivery_date=date(2026, 8, 1),
                plant="P001",
                description="Engine oil for repair order",
            )
        ],
        header_text="PR for repair order RO-001",
    )


class TestPurchaseRequisitionAdapterSuccess:
    """Adapter creates PRs and maps responses to SAPPurchaseRequisitionDTO."""

    def test_create_pr_returns_dto_with_pr_number(self) -> None:
        adapter = PurchaseRequisitionBAPIAdapter(MockSAPClient(SAPMockScenario.SUCCESS))
        dto = adapter.create_purchase_requisition(_make_request())
        assert dto.pr_number == "10000200"

    def test_create_pr_returns_dto_with_line_items(self) -> None:
        adapter = PurchaseRequisitionBAPIAdapter(MockSAPClient(SAPMockScenario.SUCCESS))
        dto = adapter.create_purchase_requisition(_make_request())
        assert len(dto.line_items) >= 1
        assert dto.line_items[0].material_number == "MAT-001"

    def test_create_pr_line_items_are_tuple(self) -> None:
        """line_items must be a tuple (frozen dataclass constraint)."""
        adapter = PurchaseRequisitionBAPIAdapter(MockSAPClient(SAPMockScenario.SUCCESS))
        dto = adapter.create_purchase_requisition(_make_request())
        assert isinstance(dto.line_items, tuple)


class TestPurchaseRequisitionAdapterError:
    """Adapter raises SAPIntegrationError on BAPI error or transport failure."""

    def test_create_pr_raises_on_bapi_error(self) -> None:
        adapter = PurchaseRequisitionBAPIAdapter(
            MockSAPClient(SAPMockScenario.BAPI_ERROR)
        )
        with pytest.raises(SAPIntegrationError, match="Purchase Requisition create"):
            adapter.create_purchase_requisition(_make_request())

    def test_create_pr_raises_on_transport_error(self) -> None:
        adapter = PurchaseRequisitionBAPIAdapter(
            MockSAPClient(SAPMockScenario.TRANSPORT_ERROR)
        )
        with pytest.raises(SAPIntegrationError, match="Transport failure"):
            adapter.create_purchase_requisition(_make_request())

    def test_create_pr_raises_on_duplicate(self) -> None:
        adapter = PurchaseRequisitionBAPIAdapter(
            MockSAPClient(SAPMockScenario.DUPLICATE)
        )
        with pytest.raises(SAPIntegrationError):
            adapter.create_purchase_requisition(_make_request())
