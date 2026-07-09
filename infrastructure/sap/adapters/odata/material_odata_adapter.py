"""Material OData Adapter — implements ISAPMaterialPort.

Reads material master data from SAP using the API_PRODUCT_SRV OData service.
"""

from __future__ import annotations

import logging
from typing import Any

from apps.integration.domain.exceptions import SAPIntegrationError
from core.sap.dtos.material import SAPMaterialDTO
from core.sap.ports.material_port import ISAPMaterialPort
from infrastructure.sap.client.base import ISAPClient, SAPClientError

logger = logging.getLogger(__name__)

_SERVICE = "API_PRODUCT_SRV"


class MaterialODataAdapter(ISAPMaterialPort):
    """Reads SAP material master data via the API_PRODUCT_SRV OData service.

    Args:
        client: An ``ISAPClient`` instance.
    """

    def __init__(self, client: ISAPClient) -> None:
        self._client = client

    def get_material(self, material_number: str) -> SAPMaterialDTO:
        """Retrieve a single material record from SAP.

        Args:
            material_number: The SAP material number.

        Returns:
            A populated ``SAPMaterialDTO``.

        Raises:
            SAPIntegrationError: On SAP error or transport failure.
        """
        logger.info(
            "Fetching SAP material",
            extra={"material_number": material_number, "domain": "integration"},
        )
        try:
            response = self._client.odata_get(
                service=_SERVICE,
                entity=f"A_Product('{material_number}')",
            )
        except SAPClientError as exc:
            raise SAPIntegrationError(
                f"Failed to fetch material {material_number!r}: {exc}"
            ) from exc

        return self._map_single(response.get("d", response))

    def list_materials(
        self,
        plant: str | None = None,
        material_type: str | None = None,
    ) -> list[SAPMaterialDTO]:
        """Retrieve material records, optionally filtered by plant or type.

        Args:
            plant: Optional SAP plant code.
            material_type: Optional SAP material type code.

        Returns:
            A list of ``SAPMaterialDTO`` objects.

        Raises:
            SAPIntegrationError: On SAP error or transport failure.
        """
        params: dict[str, Any] = {}
        filters: list[str] = []
        if plant:
            filters.append(f"Plant eq '{plant}'")
        if material_type:
            filters.append(f"ProductType eq '{material_type}'")
        if filters:
            params["$filter"] = " and ".join(filters)

        entity = "A_ProductPlant" if plant else "A_ProductPlant"

        logger.info(
            "Listing SAP materials",
            extra={
                "plant": plant,
                "material_type": material_type,
                "domain": "integration",
            },
        )
        try:
            response = self._client.odata_get(
                service=_SERVICE,
                entity=entity,
                params=params,
            )
        except SAPClientError as exc:
            raise SAPIntegrationError(f"Failed to list materials: {exc}") from exc

        results: list[dict[str, Any]] = response.get("d", {}).get("results", [])
        return [self._map_single(item) for item in results]

    @staticmethod
    def _map_single(data: dict[str, Any]) -> SAPMaterialDTO:
        """Map a raw SAP product record to ``SAPMaterialDTO``."""
        return SAPMaterialDTO(
            material_number=data.get("Product", ""),
            description=data.get("ProductDesc", ""),
            base_unit=data.get("BaseUnit", ""),
            material_type=data.get("ProductType", ""),
            plant=data.get("Plant") or None,
            material_group=data.get("MaterialGroup") or None,
        )
