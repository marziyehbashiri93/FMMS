"""SAP Inventory Port — abstract contract for stock level access.

FMMS queries SAP for current material stock levels to support procurement
decisions and availability checks before raising purchase requisitions.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from core.sap.dtos.inventory import SAPStockDTO


class ISAPInventoryPort(ABC):
    """Business contract for reading inventory stock data from SAP.

    All transport and protocol details are the responsibility of the adapter.
    """

    @abstractmethod
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
            SAPIntegrationError: If SAP returns an error or no stock record exists.
        """

    @abstractmethod
    def get_stock_by_plant(self, plant: str) -> list[SAPStockDTO]:
        """Retrieve stock levels for all materials at a given plant.

        Args:
            plant: The SAP plant code.

        Returns:
            A list of ``SAPStockDTO`` objects for the plant. May be empty.

        Raises:
            SAPIntegrationError: If SAP returns an error response.
        """
