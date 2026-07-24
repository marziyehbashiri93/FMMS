"""Unit tests for object-part catalog OData adapter."""

from __future__ import annotations

from infrastructure.sap.adapters.odata.object_part_catalog_odata_adapter import (
    ObjectPartCatalogODataAdapter,
)
from infrastructure.sap.client.mock.mock_client import MockSAPClient, SAPMockScenario


class TestObjectPartCatalogODataAdapter:
    """Cover XML-backed SAP object-part catalog reads."""

    def test_reads_catalog_from_xml_fixture(self) -> None:
        client = MockSAPClient(scenario=SAPMockScenario.SUCCESS)
        adapter = ObjectPartCatalogODataAdapter(
            client,
            service="ZI_FLEET_CAT_B_CDS",
        )

        result = adapter.get_catalog("B")

        assert len(result) >= 4
        descriptions = {item.code_text for item in result}
        assert "ترمز جلو" in descriptions
        assert "چراغ جلو" in descriptions
        assert {item.group_text for item in result}
