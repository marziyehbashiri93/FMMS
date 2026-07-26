"""Unit tests for VehicleDriverODataAdapter."""

from __future__ import annotations

from typing import Any

import pytest

from apps.integration.domain.exceptions import SAPIntegrationError
from infrastructure.sap.adapters.odata.vehicle_driver_odata_adapter import (
    VehicleDriverODataAdapter,
)
from infrastructure.sap.client.base import ISAPClient
from infrastructure.sap.client.mock.mock_client import MockSAPClient, SAPMockScenario


class TestVehicleDriverODataAdapterSuccess:
    """Adapter maps ``ZC_VEHICLEDRIVER_CDS`` XML rows correctly."""

    def test_list_vehicle_drivers_reads_mock_xml_fixture(self) -> None:
        adapter = VehicleDriverODataAdapter(MockSAPClient(SAPMockScenario.SUCCESS))

        dtos = adapter.list_vehicle_drivers()

        assert len(dtos) >= 1
        assert dtos[0].vehicle_number == "20320"
        assert dtos[0].license_plate == "237ع51-11"
        assert dtos[0].commissioning_date == "20150326"
        assert dtos[0].driver1_customer_number == "6000000250"
        assert dtos[0].driver1_name == "مجتبي  رحيم پناه"
        assert dtos[0].driver2_customer_number == "6000000160"
        assert dtos[0].driver2_name == "اصغر مولائي باروق"

    def test_list_vehicle_drivers_calls_configured_cds_service(self) -> None:
        client = RecordingODataClient(
            xml_response="""<?xml version="1.0"?>
<Root>
<Columns>
    <Column Name="VehicleNumber"></Column>
    <Column Name="LicensePlate"></Column>
    <Column Name="CommissioningDate"></Column>
    <Column Name="Driver1CustomerNo"></Column>
    <Column Name="Driver1Name"></Column>
    <Column Name="Driver2CustomerNo"></Column>
</Columns>
<Rows>
    <Row>
        <Value>20320</Value>
        <Value>237ع51-11</Value>
        <Value>20150326</Value>
        <Value>6000000250</Value>
        <Value>مجتبي رحيم پناه</Value>
        <Value>6000000160</Value>
    </Row>
</Rows>
</Root>""",
        )
        adapter = VehicleDriverODataAdapter(client)

        dtos = adapter.list_vehicle_drivers()

        assert client.xml_calls == [
            {
                "service": "ZC_VEHICLEDRIVER_CDS",
                "entity": "",
                "params": None,
            }
        ]
        assert dtos[0].vehicle_number == "20320"
        assert dtos[0].license_plate == "237ع51-11"
        assert dtos[0].driver1_customer_number == "6000000250"
        assert dtos[0].driver2_customer_number == "6000000160"

    def test_get_vehicle_driver_reads_from_xml(self) -> None:
        adapter = VehicleDriverODataAdapter(MockSAPClient(SAPMockScenario.SUCCESS))

        dto = adapter.get_vehicle_driver("20320")

        assert dto.vehicle_number == "20320"
        assert dto.license_plate == "237ع51-11"


class TestVehicleDriverODataAdapterErrors:
    """Adapter translates transport errors to SAPIntegrationError."""

    def test_list_vehicle_drivers_raises_integration_error(self) -> None:
        adapter = VehicleDriverODataAdapter(MockSAPClient(SAPMockScenario.TRANSPORT_ERROR))

        with pytest.raises(SAPIntegrationError, match="Failed to list vehicle-driver"):
            adapter.list_vehicle_drivers()

    def test_get_vehicle_driver_raises_when_missing(self) -> None:
        client = RecordingODataClient(
            xml_response="""<?xml version="1.0"?>
<Root><Columns><Column Name="VehicleNumber"></Column></Columns><Rows></Rows></Root>""",
        )
        adapter = VehicleDriverODataAdapter(client)

        with pytest.raises(SAPIntegrationError, match="was not found"):
            adapter.get_vehicle_driver("99999")


class RecordingODataClient(ISAPClient):
    """Minimal SAP client stub for adapter tests."""

    def __init__(self, xml_response: str) -> None:
        self.xml_response = xml_response
        self.xml_calls: list[dict[str, Any]] = []

    def odata_get(
        self,
        service: str,
        entity: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError

    def odata_get_xml(
        self,
        service: str,
        entity: str = "",
        params: dict[str, Any] | None = None,
    ) -> str:
        self.xml_calls.append({"service": service, "entity": entity, "params": params})
        return self.xml_response

    def odata_post(
        self,
        service: str,
        entity: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        raise NotImplementedError

    def bapi_call(
        self,
        function_module: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        raise NotImplementedError
