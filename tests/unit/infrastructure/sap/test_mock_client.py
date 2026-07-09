"""Unit tests for MockSAPClient — all four simulation scenarios."""

from __future__ import annotations

import pytest

from infrastructure.sap.client.base import SAPClientError
from infrastructure.sap.client.mock.mock_client import MockSAPClient, SAPMockScenario


class TestMockClientSuccess:
    """MockSAPClient returns valid canned responses in SUCCESS scenario."""

    def test_odata_get_equipment_single_returns_dict_with_d_key(self) -> None:
        client = MockSAPClient(scenario=SAPMockScenario.SUCCESS)
        result = client.odata_get("API_EQUIPMENT", "Equipment('10000001')")
        assert "d" in result
        assert result["d"]["EquipmentId"] == "10000001"

    def test_odata_get_equipment_list_returns_results_array(self) -> None:
        client = MockSAPClient(scenario=SAPMockScenario.SUCCESS)
        result = client.odata_get("API_EQUIPMENT", "EquipmentSet")
        assert "d" in result
        assert isinstance(result["d"]["results"], list)
        assert len(result["d"]["results"]) >= 1

    def test_odata_get_defect_code_single(self) -> None:
        client = MockSAPClient(scenario=SAPMockScenario.SUCCESS)
        result = client.odata_get("API_DEFECTCODE_SRV", "DefectCode('E0001')")
        assert result["d"]["DefectCode"] == "E0001"

    def test_odata_get_defect_code_list(self) -> None:
        client = MockSAPClient(scenario=SAPMockScenario.SUCCESS)
        result = client.odata_get("API_DEFECTCODE_SRV", "DefectCodeSet")
        assert len(result["d"]["results"]) >= 3

    def test_odata_get_material_single(self) -> None:
        client = MockSAPClient(scenario=SAPMockScenario.SUCCESS)
        result = client.odata_get("API_PRODUCT_SRV", "A_Product('MAT-001')")
        assert result["d"]["Product"] == "MAT-001"

    def test_odata_get_stock_single(self) -> None:
        client = MockSAPClient(scenario=SAPMockScenario.SUCCESS)
        result = client.odata_get(
            "API_MATERIAL_STOCK_SRV",
            "MatlStkInAcctMod(Material='MAT-001',Plant='P001')",
        )
        assert result["d"]["Material"] == "MAT-001"

    def test_bapi_call_pm_notification_create_success(self) -> None:
        client = MockSAPClient(scenario=SAPMockScenario.SUCCESS)
        result = client.bapi_call("BAPI_ALM_NOTIF_CREATE", {})
        assert result["NOTIFNO"] == "10000099"
        assert result["RETURN"][0]["TYPE"] == "S"

    def test_bapi_call_pm_order_create_success(self) -> None:
        client = MockSAPClient(scenario=SAPMockScenario.SUCCESS)
        result = client.bapi_call("BAPI_ALM_ORDER_MAINTAIN", {})
        assert result["ORDER_NUMBER"] == "20000001"

    def test_bapi_call_pr_create_success(self) -> None:
        client = MockSAPClient(scenario=SAPMockScenario.SUCCESS)
        result = client.bapi_call("BAPI_PR_CREATE", {})
        assert result["NUMBER"] == "10000200"
        assert isinstance(result["PRITEM"], list)

    def test_bapi_call_po_create_success(self) -> None:
        client = MockSAPClient(scenario=SAPMockScenario.SUCCESS)
        result = client.bapi_call("BAPI_PO_CREATE1", {})
        assert result["PURCHASEORDER"] == "45000100"

    def test_bapi_call_goods_receipt_success(self) -> None:
        client = MockSAPClient(scenario=SAPMockScenario.SUCCESS)
        result = client.bapi_call("BAPI_GOODSMVT_CREATE_GR", {})
        assert result["MATERIALDOCUMENT"] == "5000012345"

    def test_bapi_call_goods_issue_success(self) -> None:
        client = MockSAPClient(scenario=SAPMockScenario.SUCCESS)
        result = client.bapi_call("BAPI_GOODSMVT_CREATE_GI", {})
        assert result["MATERIALDOCUMENT"] == "4900012345"


class TestMockClientBAPIError:
    """MockSAPClient returns RETURN table with TYPE='E' in BAPI_ERROR scenario."""

    def test_bapi_call_pm_notification_returns_error_return(self) -> None:
        client = MockSAPClient(scenario=SAPMockScenario.BAPI_ERROR)
        result = client.bapi_call("BAPI_ALM_NOTIF_CREATE", {})
        assert result["RETURN"][0]["TYPE"] == "E"
        assert result["NOTIFNO"] == ""

    def test_bapi_call_pr_create_returns_error_return(self) -> None:
        client = MockSAPClient(scenario=SAPMockScenario.BAPI_ERROR)
        result = client.bapi_call("BAPI_PR_CREATE", {})
        assert result["RETURN"][0]["TYPE"] == "E"
        assert result["NUMBER"] == ""

    def test_odata_get_still_succeeds_in_bapi_error_scenario(self) -> None:
        """BAPI_ERROR scenario only affects BAPI calls; OData reads still succeed."""
        client = MockSAPClient(scenario=SAPMockScenario.BAPI_ERROR)
        result = client.odata_get("API_EQUIPMENT", "EquipmentSet")
        assert "d" in result


class TestMockClientTransportError:
    """MockSAPClient raises SAPClientError in TRANSPORT_ERROR scenario."""

    def test_odata_get_raises_sap_client_error(self) -> None:
        client = MockSAPClient(scenario=SAPMockScenario.TRANSPORT_ERROR)
        with pytest.raises(SAPClientError, match="Transport error"):
            client.odata_get("API_EQUIPMENT", "EquipmentSet")

    def test_odata_post_raises_sap_client_error(self) -> None:
        client = MockSAPClient(scenario=SAPMockScenario.TRANSPORT_ERROR)
        with pytest.raises(SAPClientError, match="Transport error"):
            client.odata_post("API_EQUIPMENT", "EquipmentSet", {})

    def test_bapi_call_raises_sap_client_error(self) -> None:
        client = MockSAPClient(scenario=SAPMockScenario.TRANSPORT_ERROR)
        with pytest.raises(SAPClientError, match="Transport error"):
            client.bapi_call("BAPI_ALM_NOTIF_CREATE", {})


class TestMockClientDuplicate:
    """MockSAPClient returns duplicate error RETURN table in DUPLICATE scenario."""

    def test_bapi_call_pm_notification_returns_duplicate_message(self) -> None:
        client = MockSAPClient(scenario=SAPMockScenario.DUPLICATE)
        result = client.bapi_call("BAPI_ALM_NOTIF_CREATE", {})
        message = result["RETURN"][0]["MESSAGE"]
        assert "already exists" in message.lower() or result["RETURN"][0]["TYPE"] == "E"

    def test_bapi_call_pr_create_returns_duplicate_error(self) -> None:
        client = MockSAPClient(scenario=SAPMockScenario.DUPLICATE)
        result = client.bapi_call("BAPI_PR_CREATE", {})
        assert result["RETURN"][0]["TYPE"] == "E"


class TestMockClientPerCallScenarioOverride:
    """Per-call _scenario parameter overrides the instance-level default."""

    def test_per_call_override_success_on_error_instance(self) -> None:
        client = MockSAPClient(scenario=SAPMockScenario.BAPI_ERROR)
        result = client.bapi_call(
            "BAPI_ALM_NOTIF_CREATE", {}, _scenario=SAPMockScenario.SUCCESS
        )
        assert result["RETURN"][0]["TYPE"] == "S"

    def test_per_call_override_transport_error_on_success_instance(self) -> None:
        client = MockSAPClient(scenario=SAPMockScenario.SUCCESS)
        with pytest.raises(SAPClientError):
            client.bapi_call(
                "BAPI_ALM_NOTIF_CREATE",
                {},
                _scenario=SAPMockScenario.TRANSPORT_ERROR,
            )

    def test_unknown_service_returns_empty_results(self) -> None:
        client = MockSAPClient(scenario=SAPMockScenario.SUCCESS)
        result = client.odata_get("UNKNOWN_SERVICE", "UnknownEntity")
        assert result["d"]["results"] == []
