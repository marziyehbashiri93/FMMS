"""Unit tests for central warehouse stock OData adapter."""

from __future__ import annotations

from decimal import Decimal

from infrastructure.sap.adapters.odata.central_stock_odata_adapter import (
    CentralStockODataAdapter,
)
from infrastructure.sap.client.mock.mock_client import MockSAPClient, SAPMockScenario


class TestCentralStockODataAdapter:
    """Cover XML-backed SAP central stock reads."""

    def test_reads_central_stock_from_xml_fixture(self) -> None:
        client = MockSAPClient(scenario=SAPMockScenario.SUCCESS)
        adapter = CentralStockODataAdapter(client)

        result = adapter.list_stock()

        assert len(result) >= 10
        first = result[0]
        assert first.material == "000000000060001764"
        assert first.plant == "1000"
        assert first.storage_location == "KH08"
        assert first.inventory_stock_type == "01"
        assert first.material_code == "60001764"
        assert first.material_name
        assert first.quantity == Decimal("149.500")
        assert first.base_unit == "L"
        assert first.display_currency == "IRR"
        assert {row.storage_location for row in result} == {"KH08"}
