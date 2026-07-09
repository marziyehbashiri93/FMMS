"""Unit tests for EquipmentODataAdapter using MockSAPClient."""

from __future__ import annotations

import pytest

from apps.integration.domain.exceptions import SAPIntegrationError
from infrastructure.sap.adapters.odata.equipment_odata_adapter import (
    EquipmentODataAdapter,
)
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
