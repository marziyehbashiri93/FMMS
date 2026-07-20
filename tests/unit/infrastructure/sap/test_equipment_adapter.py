"""Unit tests for EquipmentODataAdapter using MockSAPClient."""

from __future__ import annotations

from typing import Any

import pytest

from apps.integration.domain.exceptions import SAPIntegrationError
from infrastructure.sap.adapters.odata.equipment_odata_adapter import (
    EquipmentODataAdapter,
)
from infrastructure.sap.client.base import ISAPClient
from infrastructure.sap.client.mock.mock_client import MockSAPClient, SAPMockScenario


class TestEquipmentODataAdapterSuccess:
    """Adapter maps SAP OData responses to SAPEquipmentDTO correctly."""

    def test_get_equipment_returns_dto_with_correct_fields(self) -> None:
        adapter = EquipmentODataAdapter(MockSAPClient(SAPMockScenario.SUCCESS))
        dto = adapter.get_equipment("10000001")
        assert dto.equipment_number == "10000001"
        assert dto.description == "Fleet Vehicle — Toyota Land Cruiser"
        assert dto.plant == "P001"
        assert dto.functional_location == "FLEET-001"
        assert dto.serial_number == "SN-LC-2024-001"
        assert dto.category == "F"
        assert dto.object_type == "VEHICLE"

    def test_list_equipment_returns_list_of_dtos(self) -> None:
        adapter = EquipmentODataAdapter(MockSAPClient(SAPMockScenario.SUCCESS))
        dtos = adapter.list_equipment(plant="P001")
        assert len(dtos) >= 2
        numbers = [d.equipment_number for d in dtos]
        assert "10000001" in numbers
        assert "10000002" in numbers

    def test_list_equipment_without_plant_filter(self) -> None:
        adapter = EquipmentODataAdapter(MockSAPClient(SAPMockScenario.SUCCESS))
        dtos = adapter.list_equipment()
        assert isinstance(dtos, list)

    def test_list_equipment_maps_real_equipment_entity_fields(self) -> None:
        client = RecordingODataClient(
            {
                "d": {
                    "results": [
                        {
                            "Equipment": "000000000010000123",
                            "EquipmentName": "Fleet Vehicle — Toyota Hilux",
                            "MaintenancePlant": "1000",
                            "FunctionalLocation": "GOL-FLEET-01",
                            "ManufacturerSerialNumber": "CH-123",
                            "EquipmentCategory": "F",
                            "TechnicalObjectType": "VEHICLE",
                        }
                    ]
                }
            }
        )
        adapter = EquipmentODataAdapter(
            client,
            service="API_EQUIPMENT",
            entity_set="Equipment",
            page_size=100,
        )

        dtos = adapter.list_equipment()

        assert client.calls[0]["service"] == "API_EQUIPMENT"
        assert client.calls[0]["entity"] == "Equipment"
        assert client.calls[0]["params"]["$top"] == 100
        assert dtos[0].equipment_number == "000000000010000123"
        assert dtos[0].description == "Fleet Vehicle — Toyota Hilux"
        assert dtos[0].plant == "1000"
        assert dtos[0].functional_location == "GOL-FLEET-01"
        assert dtos[0].serial_number == "CH-123"
        assert dtos[0].category == "F"
        assert dtos[0].object_type == "VEHICLE"

    def test_list_equipment_maps_vehicle_driver_xml_fields(self) -> None:
        client = RecordingODataClient(
            response={},
            xml_response="""<?xml version="1.0"?>
<Root>
<Columns>
    <Column Name="VehicleNumber"></Column>
    <Column Name="LicensePlate"></Column>
    <Column Name="CommissioningDate"></Column>
    <Column Name="Driver1CustomerNo"></Column>
    <Column Name="Driver1Name"></Column>
    <Column Name="Driver1Mobile"></Column>
    <Column Name="Driver1PersonnelNo"></Column>
    <Column Name="Driver1Gender"></Column>
    <Column Name="Driver1NilofarCode"></Column>
    <Column Name="Driver2CustomerNo"></Column>
</Columns>
<Rows>
    <Row>
        <Value>20320</Value>
        <Value>237ع51-11</Value>
        <Value>20150326</Value>
        <Value>6000000250</Value>
        <Value>مجتبي رحيم پناه</Value>
        <Value>56717083</Value>
        <Value>21007837</Value>
        <Value>مذکر</Value>
        <Value>520009174</Value>
        <Value>6000000160</Value>
    </Row>
</Rows>
</Root>""",
        )
        adapter = EquipmentODataAdapter(
            client,
            service="ZC_VEHICLEDRIVER_CDS",
            entity_set="",
            response_format="xml",
        )

        dtos = adapter.list_equipment()

        assert client.xml_calls[0]["service"] == "ZC_VEHICLEDRIVER_CDS"
        assert dtos[0].equipment_number == "20320"
        assert dtos[0].license_plate == "237ع51-11"
        assert dtos[0].commissioning_date == "20150326"
        assert dtos[0].driver1_customer_number == "6000000250"
        assert dtos[0].driver2_customer_number == "6000000160"

    def test_get_equipment_reads_from_xml_when_configured(self) -> None:
        client = RecordingODataClient(
            response={},
            xml_response="""<?xml version="1.0"?>
<Root>
<Columns>
    <Column Name="VehicleNumber"></Column>
    <Column Name="LicensePlate"></Column>
    <Column Name="Driver1CustomerNo"></Column>
    <Column Name="Driver2CustomerNo"></Column>
</Columns>
<Rows>
    <Row>
        <Value>20320</Value>
        <Value>237ع51-11</Value>
        <Value>6000000250</Value>
        <Value>6000000160</Value>
    </Row>
</Rows>
</Root>""",
        )
        adapter = EquipmentODataAdapter(
            client,
            service="ZC_VEHICLEDRIVER_CDS",
            entity_set="",
            response_format="xml",
        )

        dto = adapter.get_equipment("20320")

        assert client.calls == []
        assert client.xml_calls[0]["service"] == "ZC_VEHICLEDRIVER_CDS"
        assert dto.equipment_number == "20320"
        assert dto.license_plate == "237ع51-11"


class TestEquipmentODataAdapterTransportError:
    """Adapter translates SAPClientError to SAPIntegrationError."""

    def test_get_equipment_raises_integration_error_on_transport_failure(self) -> None:
        adapter = EquipmentODataAdapter(MockSAPClient(SAPMockScenario.TRANSPORT_ERROR))
        with pytest.raises(SAPIntegrationError, match="Failed to fetch equipment"):
            adapter.get_equipment("10000001")

    def test_list_equipment_raises_integration_error_on_transport_failure(self) -> None:
        adapter = EquipmentODataAdapter(MockSAPClient(SAPMockScenario.TRANSPORT_ERROR))
        with pytest.raises(SAPIntegrationError, match="Failed to list equipment"):
            adapter.list_equipment(plant="P001")


class RecordingODataClient(ISAPClient):
    def __init__(self, response: dict[str, Any], xml_response: str = "") -> None:
        self.response = response
        self.xml_response = xml_response
        self.calls: list[dict[str, Any]] = []
        self.xml_calls: list[dict[str, Any]] = []

    def odata_get(
        self,
        service: str,
        entity: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.calls.append({"service": service, "entity": entity, "params": params})
        return self.response

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

    def odata_get_xml(
        self,
        service: str,
        entity: str = "",
        params: dict[str, Any] | None = None,
    ) -> str:
        self.xml_calls.append({"service": service, "entity": entity, "params": params})
        return self.xml_response
