"""SAP Material Port — abstract contract for material master data access.

SAP owns material master data. FMMS reads materials to support spare part
selection during repair order creation and purchase requisition preparation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from core.sap.dtos.material import SAPMaterialDTO


class ISAPMaterialPort(ABC):
    """Business contract for reading material master data from SAP.

    All transport and protocol details are the responsibility of the adapter.
    """

    @abstractmethod
    def get_material(self, material_number: str) -> SAPMaterialDTO:
        """Retrieve a single material record from SAP.

        Args:
            material_number: The SAP material number.

        Returns:
            A populated ``SAPMaterialDTO``.

        Raises:
            SAPIntegrationError: If SAP returns an error or the material is not found.
        """

    @abstractmethod
    def list_materials(
        self,
        plant: str | None = None,
        material_type: str | None = None,
    ) -> list[SAPMaterialDTO]:
        """Retrieve material records, optionally filtered by plant or type.

        Args:
            plant: Optional SAP plant code to filter by plant-specific data.
            material_type: Optional SAP material type code (e.g. "ERSA" for spares).

        Returns:
            A list of ``SAPMaterialDTO`` objects. May be empty.

        Raises:
            SAPIntegrationError: If SAP returns an error response.
        """
