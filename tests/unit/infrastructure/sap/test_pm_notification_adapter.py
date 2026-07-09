"""Unit tests for PMNotificationBAPIAdapter using MockSAPClient."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from apps.integration.domain.exceptions import SAPIntegrationError
from core.sap.dtos.pm_notification import CreatePMNotificationRequest
from infrastructure.sap.adapters.bapi.pm_notification_bapi_adapter import (
    PMNotificationBAPIAdapter,
)
from infrastructure.sap.client.mock.mock_client import MockSAPClient, SAPMockScenario


def _make_request() -> CreatePMNotificationRequest:
    return CreatePMNotificationRequest(
        equipment_number="10000001",
        fault_description="Engine oil leak detected during inspection",
        defect_code="E0001",
        priority="2",
        reported_by="inspector01",
        reported_at=datetime(2026, 7, 9, 10, 0, 0, tzinfo=UTC),
        functional_location="FLEET-001",
        code_group="ENGINE",
    )


class TestPMNotificationBAPIAdapterSuccess:
    """Adapter creates and closes PM Notifications via mock BAPI client."""

    def test_create_notification_returns_dto_with_notification_number(self) -> None:
        adapter = PMNotificationBAPIAdapter(MockSAPClient(SAPMockScenario.SUCCESS))
        dto = adapter.create_notification(_make_request())
        assert dto.notification_number == "10000099"
        assert dto.equipment_number == "10000001"
        assert dto.status == "OPEN"

    def test_create_notification_dto_has_created_at_timestamp(self) -> None:
        adapter = PMNotificationBAPIAdapter(MockSAPClient(SAPMockScenario.SUCCESS))
        dto = adapter.create_notification(_make_request())
        assert dto.created_at is not None
        assert dto.created_at.tzinfo is not None

    def test_close_notification_returns_closed_status(self) -> None:
        adapter = PMNotificationBAPIAdapter(MockSAPClient(SAPMockScenario.SUCCESS))
        dto = adapter.close_notification("10000099")
        assert dto.notification_number == "10000099"
        assert dto.status == "CLOSED"


class TestPMNotificationBAPIAdapterError:
    """Adapter raises SAPIntegrationError on BAPI error responses."""

    def test_create_notification_raises_on_bapi_error(self) -> None:
        adapter = PMNotificationBAPIAdapter(MockSAPClient(SAPMockScenario.BAPI_ERROR))
        with pytest.raises(SAPIntegrationError, match="PM Notification create"):
            adapter.create_notification(_make_request())

    def test_create_notification_raises_on_transport_error(self) -> None:
        adapter = PMNotificationBAPIAdapter(
            MockSAPClient(SAPMockScenario.TRANSPORT_ERROR)
        )
        with pytest.raises(SAPIntegrationError, match="Transport failure"):
            adapter.create_notification(_make_request())

    def test_create_notification_raises_on_duplicate(self) -> None:
        adapter = PMNotificationBAPIAdapter(MockSAPClient(SAPMockScenario.DUPLICATE))
        with pytest.raises(SAPIntegrationError):
            adapter.create_notification(_make_request())
