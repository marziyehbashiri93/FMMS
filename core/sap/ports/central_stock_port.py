"""SAP Central Stock Port — contract for KH08 warehouse stock reads."""

from __future__ import annotations

from abc import ABC, abstractmethod

from core.sap.dtos.central_stock import SAPCentralStockDTO


class ISAPCentralStockPort(ABC):
    """Business contract for reading central spare-parts warehouse stock.

    Source CDS: ``ZI_STOCK_KH08_CDS``.
    """

    @abstractmethod
    def list_stock(self) -> list[SAPCentralStockDTO]:
        """Retrieve all central warehouse stock rows.

        Returns:
            A list of ``SAPCentralStockDTO`` objects. May be empty.

        Raises:
            SAPIntegrationError: If SAP returns an error or transport fails.
        """
