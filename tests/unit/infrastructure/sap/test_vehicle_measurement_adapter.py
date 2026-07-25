"""Unit tests for VehicleMeasurementBAPIAdapter."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from apps.integration.domain.exceptions import SAPIntegrationError
from core.sap.dtos.measurement_document import UpdateVehicleMeasurementRequest
from infrastructure.sap.adapters.bapi.vehicle_measurement_bapi_adapter import (
    VehicleMeasurementBAPIAdapter,
)
from infrastructure.sap.client.mock.mock_client import MockSAPClient, SAPMockScenario


def _make_request() -> UpdateVehicleMeasurementRequest:
    return UpdateVehicleMeasurementRequest(
        equipment_number="300001",
        notification_number="10000099",
        odometer_km=125000,
        recorded_at=datetime(2026, 7, 24, 10, 30, 45, tzinfo=UTC),
    )


class TestVehicleMeasurementBAPIAdapter:
    """Adapter writes latest odometer values through the SAP client."""

    def test_update_vehicle_odometer_returns_document_number(self) -> None:
        adapter = VehicleMeasurementBAPIAdapter(MockSAPClient(SAPMockScenario.SUCCESS))

        dto = adapter.update_vehicle_odometer(_make_request())

        assert dto.measurement_document_number == "490000001"
        assert dto.equipment_number == "300001"
        assert dto.notification_number == "10000099"
        assert dto.odometer_km == 125000

    def test_update_vehicle_odometer_builds_sap_payload(self) -> None:
        params = VehicleMeasurementBAPIAdapter._build_update_params(_make_request())

        assert params["MEASUREMENT_POINT"]["IMRC_POINT"] == "125000"
        assert params["MEASUREMENT_POINT"]["IMRC_IDATE"] == "20260724"
        assert params["MEASUREMENT_POINT"]["IMRC_ITIME"] == "103045"
        assert params["Notification_Type"]["SHN_EQUIPMENT"] == "300001"
        assert params["Notification_Type"]["QMNUM"] == "10000099"
        assert params["Notification_Type"]["QMART"] == "EM"

    def test_update_vehicle_odometer_raises_on_sap_error(self) -> None:
        adapter = VehicleMeasurementBAPIAdapter(
            MockSAPClient(SAPMockScenario.BAPI_ERROR)
        )

        with pytest.raises(SAPIntegrationError, match="Vehicle measurement update"):
            adapter.update_vehicle_odometer(_make_request())
