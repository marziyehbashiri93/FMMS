"""Inventory OData Adapter — implements ISAPInventoryPort.

Reads stock data from SAP using the API_MATERIAL_STOCK_SRV OData service.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from apps.integration.domain.exceptions import SAPIntegrationError
from core.sap.dtos.inventory import SAPStockDTO
from core.sap.ports.inventory_port import ISAPInventoryPort
from infrastructure.sap.client.base import ISAPClient, SAPClientError

logger = logging.getLogger(__name__)

_SERVICE = "API_MATERIAL_STOCK_SRV"


class InventoryODataAdapter(ISAPInventoryPort):
    """Reads SAP material stock data via the API_MATERIAL_STOCK_SRV OData service.

    Args:
        client: An ``ISAPClient`` instance.
    """

    def __init__(self, client: ISAPClient) -> None:
        self._client = client

    def get_stock_by_material(
        self,
        material_number: str,
        plant: str,
    ) -> SAPStockDTO:
        """Retrieve current stock for a specific material at a plant.

        Args:
            material_number: The SAP material number.
            plant: The SAP plant code.

        Returns:
            A ``SAPStockDTO`` with unrestricted stock quantity.

        Raises:
            SAPIntegrationError: On SAP error or transport failure.
        """
        logger.info(
            "Fetching SAP stock",
            extra={
                "material_number": material_number,
                "plant": plant,
                "domain": "integration",
            },
        )
        try:
            response = self._client.odata_get(
                service=_SERVICE,
                entity=f"MatlStkInAcctMod(Material='{material_number}',Plant='{plant}')",
            )
        except SAPClientError as exc:
            raise SAPIntegrationError(
                f"Failed to fetch stock for {material_number!r} at {plant!r}: {exc}"
            ) from exc

        return self._map_single(response.get("d", response))

    def get_stock_by_plant(self, plant: str) -> list[SAPStockDTO]:
        """Retrieve stock levels for all materials at a given plant.

        Args:
            plant: The SAP plant code.

        Returns:
            A list of ``SAPStockDTO`` objects.

        Raises:
            SAPIntegrationError: On SAP error or transport failure.
        """
        logger.info(
            "Listing SAP stock by plant",
            extra={"plant": plant, "domain": "integration"},
        )
        try:
            response = self._client.odata_get(
                service=_SERVICE,
                entity="MatlStkInAcctMod",
                params={"$filter": f"Plant eq '{plant}'"},
            )
        except SAPClientError as exc:
            raise SAPIntegrationError(
                f"Failed to list stock for plant {plant!r}: {exc}"
            ) from exc

        results: list[dict[str, Any]] = response.get("d", {}).get("results", [])
        return [self._map_single(item) for item in results]

    @staticmethod
    def _map_single(data: dict[str, Any]) -> SAPStockDTO:
        """Map a raw SAP stock record to ``SAPStockDTO``."""
        qty_raw = data.get("MatlStkQtyInMatlBaseUnit", "0")
        return SAPStockDTO(
            material_number=data.get("Material", ""),
            plant=data.get("Plant", ""),
            unrestricted_qty=Decimal(qty_raw),
            unit=data.get("MaterialBaseUnit", ""),
            storage_location=data.get("StorageLocation") or None,
        )
