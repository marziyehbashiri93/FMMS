"""Unit tests for fault catalog OData adapter."""

from __future__ import annotations

from infrastructure.sap.adapters.odata.fault_catalog_odata_adapter import (
    FaultCatalogODataAdapter,
)
from infrastructure.sap.client.mock.mock_client import MockSAPClient, SAPMockScenario


class TestFaultCatalogODataAdapter:
    """Cover XML-backed SAP fault catalog reads."""

    def test_reads_fault_catalog_from_xml_fixture(self) -> None:
        client = MockSAPClient(scenario=SAPMockScenario.SUCCESS)
        adapter = FaultCatalogODataAdapter(client)

        result = adapter.list_defect_codes()

        assert len(result) >= 4
        code_texts = {item.code_text for item in result}
        assert "ترمز ضعیف" in code_texts
        assert "چراغ جلو معیوب" in code_texts
        assert {item.defect_class for item in result}
        assert {item.defect_class_text for item in result}

    def test_get_defect_code_by_code_and_group(self) -> None:
        client = MockSAPClient(scenario=SAPMockScenario.SUCCESS)
        adapter = FaultCatalogODataAdapter(client)

        result = adapter.get_defect_code("B001", "BRAKE-D")

        assert result.code_text == "ترمز ضعیف"
        assert result.defect_class == "S1"
