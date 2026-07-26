"""Unit tests for VehicleAssignmentBAPIAdapter."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from apps.integration.domain.exceptions import SAPIntegrationError
from core.sap.dtos.vehicle_assignment import (
    RequestReplacementVehicleAssignmentRequest,
)
from infrastructure.sap.adapters.bapi.vehicle_assignment_bapi_adapter import (
    VehicleAssignmentBAPIAdapter,
)
from infrastructure.sap.client.mock.mock_client import MockSAPClient, SAPMockScenario


def _make_request() -> RequestReplacementVehicleAssignmentRequest:
    return RequestReplacementVehicleAssignmentRequest(
        driver_customer_number="6000001001",
        unavailable_vehicle_number="300001",
        fault_id="fault-1",
        requested_at=datetime(2026, 7, 24, 11, 15, 30, tzinfo=UTC),
        reason="خودرو قابل استفاده نیست",
    )


class TestVehicleAssignmentBAPIAdapter:
    """Adapter requests replacement vehicle assignment through SAP client."""

    def test_request_replacement_assignment_returns_request_number(self) -> None:
        adapter = VehicleAssignmentBAPIAdapter(MockSAPClient(SAPMockScenario.SUCCESS))

        dto = adapter.request_replacement_assignment(_make_request())

        assert dto.assignment_request_number == "VA-REQ-0001"
        assert dto.driver_customer_number == "6000001001"
        assert dto.unavailable_vehicle_number == "300001"

    def test_request_replacement_assignment_builds_sap_payload(self) -> None:
        params = VehicleAssignmentBAPIAdapter._build_params(_make_request())

        assert params["DRIVER_CUSTOMER_NUMBER"] == "6000001001"
        assert params["UNAVAILABLE_VEHICLE"] == "300001"
        assert params["FAULT_ID"] == "fault-1"
        assert params["REQUEST_DATE"] == "20260724"
        assert params["REQUEST_TIME"] == "111530"
        assert params["REASON"] == "خودرو قابل استفاده نیست"

    def test_request_replacement_assignment_raises_on_sap_error(self) -> None:
        adapter = VehicleAssignmentBAPIAdapter(
            MockSAPClient(SAPMockScenario.BAPI_ERROR)
        )

        with pytest.raises(SAPIntegrationError, match="Replacement vehicle assignment"):
            adapter.request_replacement_assignment(_make_request())
