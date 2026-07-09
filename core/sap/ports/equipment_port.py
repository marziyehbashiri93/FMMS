"""SAP Equipment Port — abstract contract for equipment master data access.

SAP is the system of record for fleet equipment. FMMS reads equipment data
from SAP to synchronise vehicle master records.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from core.sap.dtos.equipment import SAPEquipmentDTO


class ISAPEquipmentPort(ABC):
    """Business contract for reading equipment master data from SAP.

    Implementations must not leak transport details into this interface.
    All exceptions must be translated to ``SAPIntegrationError`` or its subclasses
    before crossing this boundary.
    """

    @abstractmethod
    def get_equipment(self, equipment_number: str) -> SAPEquipmentDTO:
        """Retrieve a single equipment record from SAP by its number.

        Args:
            equipment_number: The SAP equipment identifier.

        Returns:
            A populated ``SAPEquipmentDTO`` for the given equipment.

        Raises:
            SAPIntegrationError: If SAP returns an error or the equipment is not found.
        """

    @abstractmethod
    def list_equipment(self, plant: str | None = None) -> list[SAPEquipmentDTO]:
        """Retrieve all equipment records, optionally filtered by plant.

        Args:
            plant: Optional SAP plant code to filter results. When ``None``,
                all accessible equipment records are returned.

        Returns:
            A list of ``SAPEquipmentDTO`` objects. May be empty.

        Raises:
            SAPIntegrationError: If SAP returns an error response.
        """
