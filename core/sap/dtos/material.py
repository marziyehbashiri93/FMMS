"""SAP Material Master DTOs.

Represents data received from SAP's material master.
Materials are spare parts and consumables used in repair activities.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SAPMaterialDTO:
    """A single material record from the SAP material master.

    Attributes:
        material_number: The SAP material number (unique identifier).
        description: Human-readable material description.
        base_unit: The base unit of measure (e.g. "EA", "KG", "L").
        material_type: SAP material type code (e.g. "ERSA" for spare parts).
        plant: Optional plant code; present when plant-specific data is included.
        material_group: Optional SAP material group classification.
    """

    material_number: str
    description: str
    base_unit: str
    material_type: str
    plant: str | None = None
    material_group: str | None = None
