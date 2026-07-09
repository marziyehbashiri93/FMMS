"""MockSAPClient — full SAP simulation for development and testing.

Simulates four scenarios configurable per-instance or per-call:

- ``SUCCESS``:   Returns canned responses matching real SAP OData/BAPI shapes.
- ``BAPI_ERROR``: Returns a BAPI RETURN table with ``TYPE='E'`` (business error).
- ``TRANSPORT_ERROR``: Raises ``SAPClientError`` immediately (network failure).
- ``DUPLICATE``: Returns a BAPI RETURN table signalling a duplicate document.

Usage::

    client = MockSAPClient(scenario=SAPMockScenario.SUCCESS)
    response = client.odata_get("API_EQUIPMENT", "Equipment('10000001')")

    # Override scenario per call:
    response = client.bapi_call(
        "BAPI_ALM_NOTIF_CREATE",
        params={},
        _scenario=SAPMockScenario.BAPI_ERROR,
    )
"""

from __future__ import annotations

import logging
from enum import StrEnum
from typing import Any

from infrastructure.sap.client.base import ISAPClient, SAPClientError
from infrastructure.sap.client.mock import scenarios as sc

logger = logging.getLogger(__name__)


class SAPMockScenario(StrEnum):
    """Configures which simulation scenario the MockSAPClient applies.

    Attributes:
        SUCCESS: Normal happy-path responses for all SAP operations.
        BAPI_ERROR: SAP returns a business error in the RETURN table.
        TRANSPORT_ERROR: Communication failure before SAP processes the request.
        DUPLICATE: SAP rejects the request as a duplicate document.
    """

    SUCCESS = "SUCCESS"
    BAPI_ERROR = "BAPI_ERROR"
    TRANSPORT_ERROR = "TRANSPORT_ERROR"
    DUPLICATE = "DUPLICATE"


# ---------------------------------------------------------------------------
# OData response routing — maps (service, entity_prefix) → canned response
# ---------------------------------------------------------------------------

_ODATA_GET_ROUTES: dict[tuple[str, str], dict] = {
    ("API_EQUIPMENT", "Equipment("): sc.ODATA_EQUIPMENT_SINGLE,
    ("API_EQUIPMENT", "EquipmentSet"): sc.ODATA_EQUIPMENT_LIST,
    ("API_DEFECTCODE_SRV", "DefectCode("): sc.ODATA_DEFECT_CODE_SINGLE,
    ("API_DEFECTCODE_SRV", "DefectCodeSet"): sc.ODATA_DEFECT_CODE_LIST,
    ("OBJECT_PART_CATALOG", "CatalogSet"): sc.ODATA_OBJECT_PART_LIST,
    ("OBJECT_PART_CATALOG", "CatalogEntry("): sc.ODATA_OBJECT_PART_SINGLE,
    ("API_PRODUCT_SRV", "A_Product("): sc.ODATA_MATERIAL_SINGLE,
    ("API_PRODUCT_SRV", "A_ProductPlant"): sc.ODATA_MATERIAL_LIST,
    ("API_MATERIAL_STOCK_SRV", "MatlStkInAcctMod("): sc.ODATA_STOCK_SINGLE,
    ("API_MATERIAL_STOCK_SRV", "MatlStkInAcctMod"): sc.ODATA_STOCK_LIST,
}

# BAPI response routing — maps function_module → (success, error, duplicate)
_BAPI_ROUTES: dict[str, tuple[dict, dict, dict]] = {
    "BAPI_ALM_NOTIF_CREATE": (
        sc.BAPI_PM_NOTIFICATION_CREATE_SUCCESS,
        sc.BAPI_PM_NOTIFICATION_ERROR,
        sc.BAPI_PM_NOTIFICATION_DUPLICATE,
    ),
    "BAPI_ALM_NOTIF_CLOSE": (
        sc.BAPI_PM_NOTIFICATION_CLOSE_SUCCESS,
        sc.BAPI_PM_NOTIFICATION_ERROR,
        sc.BAPI_PM_NOTIFICATION_ERROR,
    ),
    "BAPI_ALM_ORDER_MAINTAIN": (
        sc.BAPI_PM_ORDER_CREATE_SUCCESS,
        sc.BAPI_PM_ORDER_ERROR,
        sc.BAPI_PM_ORDER_ERROR,
    ),
    "BAPI_ALM_ORDER_COMPLETE": (
        sc.BAPI_PM_ORDER_COMPLETE_SUCCESS,
        sc.BAPI_PM_ORDER_ERROR,
        sc.BAPI_PM_ORDER_ERROR,
    ),
    "BAPI_ALM_ORDER_READ": (
        sc.BAPI_PM_ORDER_GET_SUCCESS,
        sc.BAPI_PM_ORDER_ERROR,
        sc.BAPI_PM_ORDER_ERROR,
    ),
    "BAPI_PR_CREATE": (
        sc.BAPI_PR_CREATE_SUCCESS,
        sc.BAPI_PR_CREATE_ERROR,
        sc.BAPI_PR_CREATE_DUPLICATE,
    ),
    "BAPI_PO_CREATE1": (
        sc.BAPI_PO_CREATE_SUCCESS,
        sc.BAPI_PO_CREATE_ERROR,
        sc.BAPI_PO_CREATE_ERROR,
    ),
    "BAPI_PO_APPROVE": (
        sc.BAPI_PO_APPROVE_SUCCESS,
        sc.BAPI_PO_CREATE_ERROR,
        sc.BAPI_PO_CREATE_ERROR,
    ),
    "BAPI_PO_GET_DETAIL": (
        sc.BAPI_PO_GET_SUCCESS,
        sc.BAPI_PO_CREATE_ERROR,
        sc.BAPI_PO_CREATE_ERROR,
    ),
    "BAPI_GOODSMVT_CREATE_GR": (
        sc.BAPI_GR_POST_SUCCESS,
        sc.BAPI_GR_POST_ERROR,
        sc.BAPI_GR_POST_ERROR,
    ),
    "BAPI_GOODSMVT_CANCEL_GR": (
        sc.BAPI_GR_REVERSE_SUCCESS,
        sc.BAPI_GR_POST_ERROR,
        sc.BAPI_GR_POST_ERROR,
    ),
    "BAPI_GOODSMVT_CREATE_GI": (
        sc.BAPI_GI_POST_SUCCESS,
        sc.BAPI_GI_POST_ERROR,
        sc.BAPI_GI_POST_ERROR,
    ),
    "BAPI_GOODSMVT_CANCEL_GI": (
        sc.BAPI_GI_REVERSE_SUCCESS,
        sc.BAPI_GI_POST_ERROR,
        sc.BAPI_GI_POST_ERROR,
    ),
    "BAPI_SERVICE_PO_CREATE": (
        sc.BAPI_SERVICE_PO_CREATE_SUCCESS,
        sc.BAPI_SERVICE_PO_CREATE_ERROR,
        sc.BAPI_SERVICE_PO_CREATE_ERROR,
    ),
    "BAPI_SERVICE_PO_CONFIRM": (
        sc.BAPI_SERVICE_PO_CONFIRM_SUCCESS,
        sc.BAPI_SERVICE_PO_CREATE_ERROR,
        sc.BAPI_SERVICE_PO_CREATE_ERROR,
    ),
    "BAPI_SERVICE_PO_GET": (
        sc.BAPI_SERVICE_PO_GET_SUCCESS,
        sc.BAPI_SERVICE_PO_CREATE_ERROR,
        sc.BAPI_SERVICE_PO_CREATE_ERROR,
    ),
}


class MockSAPClient(ISAPClient):
    """Simulated SAP client for development and testing.

    Provides canned responses that mirror real SAP OData/BAPI response shapes
    without requiring a live SAP system. Used in all non-production environments
    (``SAP_USE_MOCK=True``).

    Args:
        scenario: The default scenario applied to all calls.
            Can be overridden per-call via the ``_scenario`` kwarg
            accepted by all methods.

    Example::

        client = MockSAPClient(scenario=SAPMockScenario.SUCCESS)
        result = client.odata_get("API_EQUIPMENT", "EquipmentSet")
        assert "d" in result
    """

    def __init__(self, scenario: SAPMockScenario = SAPMockScenario.SUCCESS) -> None:
        self._scenario = scenario

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_scenario(self, override: SAPMockScenario | None) -> SAPMockScenario:
        return override if override is not None else self._scenario

    @staticmethod
    def _route_odata(service: str, entity: str) -> dict[str, Any]:
        """Find the canned OData response for a (service, entity) pair."""
        for (svc, entity_prefix), response in _ODATA_GET_ROUTES.items():
            if svc == service and entity.startswith(entity_prefix):
                return response
        # Fall back to equipment list as a safe default for unknown entities
        logger.warning(
            "MockSAPClient: no route for OData GET",
            extra={"service": service, "entity": entity},
        )
        return {"d": {"results": []}}

    @staticmethod
    def _route_bapi(function_module: str, scenario: SAPMockScenario) -> dict[str, Any]:
        """Find and select the canned BAPI response for a function module."""
        routes = _BAPI_ROUTES.get(function_module)
        if routes is None:
            logger.warning(
                "MockSAPClient: no route for BAPI call",
                extra={"function_module": function_module},
            )
            routes = (
                {"RETURN": sc._SAP_SUCCESS_RETURN},
                {"RETURN": sc._SAP_ERROR_RETURN},
                {"RETURN": sc._SAP_DUPLICATE_RETURN},
            )
        success_resp, error_resp, duplicate_resp = routes
        if scenario == SAPMockScenario.SUCCESS:
            return success_resp
        if scenario == SAPMockScenario.DUPLICATE:
            return duplicate_resp
        return error_resp  # BAPI_ERROR

    # ------------------------------------------------------------------
    # ISAPClient implementation
    # ------------------------------------------------------------------

    def odata_get(
        self,
        service: str,
        entity: str,
        params: dict[str, Any] | None = None,
        _scenario: SAPMockScenario | None = None,
    ) -> dict[str, Any]:
        """Simulate an OData GET request.

        Args:
            service: OData service name.
            entity: Entity set or key expression.
            params: Ignored in mock.
            _scenario: Optional per-call scenario override.

        Returns:
            Canned OData response matching real SAP response shape.

        Raises:
            SAPClientError: If scenario is ``TRANSPORT_ERROR``.
        """
        scenario = self._resolve_scenario(_scenario)
        logger.debug(
            "MockSAPClient.odata_get",
            extra={"service": service, "entity": entity, "scenario": scenario},
        )
        if scenario == SAPMockScenario.TRANSPORT_ERROR:
            raise SAPClientError(
                f"[MOCK] Transport error calling OData GET {service}/{entity}"
            )
        return self._route_odata(service, entity)

    def odata_post(
        self,
        service: str,
        entity: str,
        payload: dict[str, Any],
        _scenario: SAPMockScenario | None = None,
    ) -> dict[str, Any]:
        """Simulate an OData POST request.

        Args:
            service: OData service name.
            entity: Entity set.
            payload: Request body (ignored in mock).
            _scenario: Optional per-call scenario override.

        Returns:
            Canned OData response.

        Raises:
            SAPClientError: If scenario is ``TRANSPORT_ERROR``.
        """
        scenario = self._resolve_scenario(_scenario)
        logger.debug(
            "MockSAPClient.odata_post",
            extra={"service": service, "entity": entity, "scenario": scenario},
        )
        if scenario == SAPMockScenario.TRANSPORT_ERROR:
            raise SAPClientError(
                f"[MOCK] Transport error calling OData POST {service}/{entity}"
            )
        return self._route_odata(service, entity)

    def bapi_call(
        self,
        function_module: str,
        params: dict[str, Any],
        _scenario: SAPMockScenario | None = None,
    ) -> dict[str, Any]:
        """Simulate a BAPI/RFC function module call.

        Args:
            function_module: BAPI/RFC function module name.
            params: Function parameters (ignored in mock).
            _scenario: Optional per-call scenario override.

        Returns:
            Canned BAPI response with ``RETURN`` table.

        Raises:
            SAPClientError: If scenario is ``TRANSPORT_ERROR``.
        """
        scenario = self._resolve_scenario(_scenario)
        logger.debug(
            "MockSAPClient.bapi_call",
            extra={"function_module": function_module, "scenario": scenario},
        )
        if scenario == SAPMockScenario.TRANSPORT_ERROR:
            raise SAPClientError(
                f"[MOCK] Transport error calling BAPI {function_module}"
            )
        return self._route_bapi(function_module, scenario)
