"""Fault Catalog OData Adapter — implements ISAPFaultCatalogPort.

Reads defect codes from SAP using the API_DEFECTCODE_SRV OData service.
"""

from __future__ import annotations

import logging
from typing import Any

from apps.integration.domain.exceptions import SAPIntegrationError
from core.sap.dtos.fault_catalog import SAPDefectCodeDTO
from core.sap.ports.fault_catalog_port import ISAPFaultCatalogPort
from infrastructure.sap.client.base import ISAPClient, SAPClientError

logger = logging.getLogger(__name__)

_SERVICE = "API_DEFECTCODE_SRV"


class FaultCatalogODataAdapter(ISAPFaultCatalogPort):
    """Reads SAP defect codes via the API_DEFECTCODE_SRV OData service.

    Args:
        client: An ``ISAPClient`` instance.
    """

    def __init__(self, client: ISAPClient) -> None:
        self._client = client

    def list_defect_codes(
        self,
        catalog_profile: str | None = None,
    ) -> list[SAPDefectCodeDTO]:
        """Retrieve defect codes, optionally filtered by catalog profile.

        Args:
            catalog_profile: Optional SAP catalog profile identifier.

        Returns:
            A list of ``SAPDefectCodeDTO`` objects.

        Raises:
            SAPIntegrationError: On SAP error or transport failure.
        """
        params: dict[str, Any] = {}
        if catalog_profile:
            params["$filter"] = f"CatalogProfile eq '{catalog_profile}'"

        logger.info(
            "Listing SAP defect codes",
            extra={"catalog_profile": catalog_profile, "domain": "integration"},
        )
        try:
            response = self._client.odata_get(
                service=_SERVICE,
                entity="DefectCodeSet",
                params=params,
            )
        except SAPClientError as exc:
            raise SAPIntegrationError(
                f"Failed to list defect codes (profile={catalog_profile!r}): {exc}"
            ) from exc

        results: list[dict[str, Any]] = response.get("d", {}).get("results", [])
        return [self._map_single(item) for item in results]

    def get_defect_code(
        self,
        code: str,
        catalog_profile: str,
    ) -> SAPDefectCodeDTO:
        """Retrieve a single defect code from the SAP catalog.

        Args:
            code: The defect code identifier.
            catalog_profile: The SAP catalog profile.

        Returns:
            A populated ``SAPDefectCodeDTO``.

        Raises:
            SAPIntegrationError: On SAP error or transport failure.
        """
        logger.info(
            "Fetching SAP defect code",
            extra={
                "code": code,
                "catalog_profile": catalog_profile,
                "domain": "integration",
            },
        )
        try:
            response = self._client.odata_get(
                service=_SERVICE,
                entity=f"DefectCode('{code}')",
            )
        except SAPClientError as exc:
            raise SAPIntegrationError(
                f"Failed to fetch defect code {code!r}: {exc}"
            ) from exc

        return self._map_single(response.get("d", response))

    @staticmethod
    def _map_single(data: dict[str, Any]) -> SAPDefectCodeDTO:
        """Map a raw SAP defect code record to ``SAPDefectCodeDTO``."""
        return SAPDefectCodeDTO(
            code=data.get("DefectCode", ""),
            text=data.get("DefectCodeText", ""),
            catalog_profile=data.get("CatalogProfile", ""),
            code_group=data.get("CodeGroup") or None,
        )
