"""Unit tests for VehicleDriverODataAdapter."""

from __future__ import annotations

from typing import Any

import pytest

from apps.integration.domain.exceptions import SAPIntegrationError
from infrastructure.sap.adapters.odata.vehicle_driver_odata_adapter import (
    VehicleDriverODataAdapter,
)
from infrastructure.sap.client.base import ISAPClient, SAPClientError
from infrastructure.sap.client.mock.mock_client import MockSAPClient, SAPMockScenario


SAMPLE_ROW: dict[str, Any] = {
    "VehicleNumber": "20320",
    "LicensePlate": "237ع51-11",
    "CommissioningDate": "/Date(1427328000000)/",
    "Driver1CustomerNo": "6000000250",
    "Driver1Name": "مجتبي  رحيم پناه",
    "Driver1Mobile": "09120000001",
    "Driver1PersonnelNo": "250",
    "Driver1Gender": "M",
    "Driver1NilofarCode": "N250",
    "Driver2CustomerNo": "6000000160",
    "Driver2Name": "اصغر مولائي باروق",
    "Driver2Mobile": "09120000002",
    "Driver2PersonnelNo": "160",
    "Driver2Gender": "M",
    "Driver2NilofarCode": "N160",
}


class TestVehicleDriverODataAdapterSuccess:
    """Adapter maps ``ZC_VEHICLEDRIVER_CDS`` JSON rows correctly."""

    def test_list_vehicle_drivers_reads_mock_json_fixture(self) -> None:
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

    def test_list_vehicle_drivers_calls_configured_cds_service_and_entity(self) -> None:
        client = RecordingODataClient({"d": {"results": [SAMPLE_ROW]}})
        adapter = VehicleDriverODataAdapter(client)

        dtos = adapter.list_vehicle_drivers()

        assert client.json_calls == [
            {
                "service": "ZC_VEHICLEDRIVER_CDS",
                "entity": "ZC_VehicleDriver",
                "params": None,
            }
        ]
        assert dtos[0].vehicle_number == "20320"

    def test_extracts_d_results_and_maps_complete_first_record(self) -> None:
        client = RecordingODataClient({"d": {"results": [SAMPLE_ROW]}})
        adapter = VehicleDriverODataAdapter(client)

        dto = adapter.list_vehicle_drivers()[0]

        assert dto.vehicle_number == "20320"
        assert dto.license_plate == "237ع51-11"
        assert dto.commissioning_date == "20150326"
        assert dto.driver1_customer_number == "6000000250"
        assert dto.driver1_name == "مجتبي  رحيم پناه"
        assert dto.driver1_mobile == "09120000001"
        assert dto.driver1_personnel_number == "250"
        assert dto.driver1_gender == "M"
        assert dto.driver1_nilofar_code == "N250"
        assert dto.driver2_customer_number == "6000000160"
        assert dto.driver2_name == "اصغر مولائي باروق"
        assert dto.driver2_mobile == "09120000002"
        assert dto.driver2_personnel_number == "160"
        assert dto.driver2_gender == "M"
        assert dto.driver2_nilofar_code == "N160"

    @pytest.mark.parametrize(
        ("raw_date", "expected"),
        [
            ("/Date(1427328000000)/", "20150326"),
            ("20150326", "20150326"),
            (None, None),
            ("not-a-date", None),
        ],
    )
    def test_normalizes_commissioning_date(
        self,
        raw_date: str | None,
        expected: str | None,
    ) -> None:
        row = {**SAMPLE_ROW, "CommissioningDate": raw_date}
        client = RecordingODataClient({"d": {"results": [row]}})
        adapter = VehicleDriverODataAdapter(client)

        dto = adapter.list_vehicle_drivers()[0]

        assert dto.commissioning_date == expected

    def test_reads_multiple_pages_from_d_next(self) -> None:
        first_page = {
            "d": {
                "results": [{**SAMPLE_ROW, "VehicleNumber": "20320"}],
                "__next": (
                    "http://sap.example/sap/opu/odata/sap/"
                    "ZC_VEHICLEDRIVER_CDS/ZC_VehicleDriver?$skiptoken=2"
                    "&sap-client=100&$format=json"
                ),
            }
        }
        second_page = {"d": {"results": [{**SAMPLE_ROW, "VehicleNumber": "20321"}]}}
        client = RecordingODataClient(first_page, second_page)
        adapter = VehicleDriverODataAdapter(client)

        dtos = adapter.list_vehicle_drivers()

        assert [dto.vehicle_number for dto in dtos] == ["20320", "20321"]
        assert client.json_calls == [
            {
                "service": "ZC_VEHICLEDRIVER_CDS",
                "entity": "ZC_VehicleDriver",
                "params": None,
            },
            {
                "service": "ZC_VEHICLEDRIVER_CDS",
                "entity": "ZC_VehicleDriver",
                "params": {"$skiptoken": "2"},
            },
        ]

    def test_stops_pagination_when_next_is_missing(self) -> None:
        client = RecordingODataClient({"d": {"results": [SAMPLE_ROW]}})
        adapter = VehicleDriverODataAdapter(client)

        adapter.list_vehicle_drivers()

        assert len(client.json_calls) == 1

    def test_get_vehicle_driver_reads_from_json(self) -> None:
        adapter = VehicleDriverODataAdapter(MockSAPClient(SAPMockScenario.SUCCESS))

        dto = adapter.get_vehicle_driver("20320")

        assert dto.vehicle_number == "20320"
        assert dto.license_plate == "237ع51-11"


class TestVehicleDriverODataAdapterErrors:
    """Adapter rejects invalid responses and translates transport errors."""

    def test_list_vehicle_drivers_raises_integration_error(self) -> None:
        adapter = VehicleDriverODataAdapter(
            MockSAPClient(SAPMockScenario.TRANSPORT_ERROR)
        )

        with pytest.raises(SAPIntegrationError, match="Failed to list vehicle-driver"):
            adapter.list_vehicle_drivers()

    def test_invalid_response_without_d_results_raises(self) -> None:
        client = RecordingODataClient({"d": {"items": []}})
        adapter = VehicleDriverODataAdapter(client)

        with pytest.raises(SAPIntegrationError, match="missing d.results"):
            adapter.list_vehicle_drivers()

    def test_get_vehicle_driver_raises_when_missing(self) -> None:
        client = RecordingODataClient({"d": {"results": []}})
        adapter = VehicleDriverODataAdapter(client)

        with pytest.raises(SAPIntegrationError, match="was not found"):
            adapter.get_vehicle_driver("99999")


class RecordingODataClient(ISAPClient):
    """Minimal SAP client stub for adapter tests."""

    def __init__(self, *json_responses: dict[str, Any]) -> None:
        self._json_responses = list(json_responses)
        self.json_calls: list[dict[str, Any]] = []

    def odata_get(
        self,
        service: str,
        entity: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.json_calls.append({"service": service, "entity": entity, "params": params})
        if not self._json_responses:
            raise SAPClientError("No recorded JSON response left.")
        return self._json_responses.pop(0)

    def odata_get_xml(
        self,
        service: str,
        entity: str = "",
        params: dict[str, Any] | None = None,
    ) -> str:
        raise NotImplementedError

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
