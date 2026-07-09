"""Object Part Catalog OData Adapter — implements ISAPObjectPartCatalogPort."""

from __future__ import annotations

import logging
from typing import Any

from apps.integration.domain.exceptions import SAPIntegrationError
from core.sap.dtos.object_part_catalog import SAPObjectPartDTO
from core.sap.ports.object_part_catalog_port import ISAPObjectPartCatalogPort
from infrastructure.sap.client.base import ISAPClient, SAPClientError

logger = logging.getLogger(__name__)

_SERVICE = "OBJECT_PART_CATALOG"


class ObjectPartCatalogODataAdapter(ISAPObjectPartCatalogPort):
    """Reads SAP object part catalog data via OData.

    Args:
        client: An ``ISAPClient`` instance.
    """

    def __init__(self, client: ISAPClient) -> None:
        self._client = client

    def get_catalog(self, catalog_type: str) -> list[SAPObjectPartDTO]:
        """Retrieve all object parts for a given catalog type.

        Args:
            catalog_type: SAP catalog type identifier.

        Returns:
            A list of ``SAPObjectPartDTO`` objects.

        Raises:
            SAPIntegrationError: On SAP error or transport failure.
        """
        logger.info(
            "Fetching SAP object part catalog",
            extra={"catalog_type": catalog_type, "domain": "integration"},
        )
        try:
            response = self._client.odata_get(
                service=_SERVICE,
                entity="CatalogSet",
                params={"$filter": f"CatalogType eq '{catalog_type}'"},
            )
        except SAPClientError as exc:
            raise SAPIntegrationError(
                f"Failed to fetch object part catalog (type={catalog_type!r}): {exc}"
            ) from exc

        results: list[dict[str, Any]] = response.get("d", {}).get("results", [])
        return [self._map_single(item) for item in results]

    def get_part_by_code(
        self,
        code: str,
        code_group: str,
        catalog_type: str,
    ) -> SAPObjectPartDTO:
        """Retrieve a specific object part by code and group.

        Args:
            code: The object part code.
            code_group: The code group.
            catalog_type: The SAP catalog type.

        Returns:
            A populated ``SAPObjectPartDTO``.

        Raises:
            SAPIntegrationError: On SAP error or transport failure.
        """
        logger.info(
            "Fetching SAP object part",
            extra={"code": code, "code_group": code_group, "domain": "integration"},
        )
        try:
            response = self._client.odata_get(
                service=_SERVICE,
                entity=f"CatalogEntry(Code='{code}',CodeGroup='{code_group}')",
            )
        except SAPClientError as exc:
            raise SAPIntegrationError(
                f"Failed to fetch object part {code!r}/{code_group!r}: {exc}"
            ) from exc

        return self._map_single(response.get("d", response))

    @staticmethod
    def _map_single(data: dict[str, Any]) -> SAPObjectPartDTO:
        """Map a raw SAP catalog record to ``SAPObjectPartDTO``."""
        return SAPObjectPartDTO(
            code=data.get("Code", ""),
            code_group=data.get("CodeGroup", ""),
            description=data.get("CodeText", ""),
            catalog_type=data.get("CatalogType", ""),
        )
