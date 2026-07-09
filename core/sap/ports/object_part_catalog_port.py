"""SAP Object Part Catalog Port — abstract contract for object part access.

SAP maintains a catalog of object parts (vehicle components) used during
inspection item categorization and fault reporting.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from core.sap.dtos.object_part_catalog import SAPObjectPartDTO


class ISAPObjectPartCatalogPort(ABC):
    """Business contract for reading object part catalog data from SAP.

    Implementations handle all transport, encoding, and SAP-specific details.
    """

    @abstractmethod
    def get_catalog(self, catalog_type: str) -> list[SAPObjectPartDTO]:
        """Retrieve all object parts for a given catalog type.

        Args:
            catalog_type: SAP catalog type identifier (e.g. "B" for object parts).

        Returns:
            A list of ``SAPObjectPartDTO`` objects for the specified catalog type.

        Raises:
            SAPIntegrationError: If SAP returns an error response.
        """

    @abstractmethod
    def get_part_by_code(
        self,
        code: str,
        code_group: str,
        catalog_type: str,
    ) -> SAPObjectPartDTO:
        """Retrieve a specific object part by its code and group.

        Args:
            code: The object part code.
            code_group: The code group within the catalog.
            catalog_type: The SAP catalog type identifier.

        Returns:
            A populated ``SAPObjectPartDTO``.

        Raises:
            SAPIntegrationError: If SAP returns an error or the part is not found.
        """
