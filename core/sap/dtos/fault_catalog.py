"""SAP Fault / Defect Catalog DTOs.

Represents data received from SAP's defect code catalog.
SAP maintains the authoritative list of fault codes used during inspections.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SAPDefectCodeDTO:
    """A single defect code entry from the SAP fault catalog.

    Attributes:
        code: The defect code identifier (unique within a catalog profile).
        text: Human-readable description of the defect.
        catalog_profile: The SAP catalog profile this code belongs to.
        code_group: Optional grouping code within the catalog.
    """

    code: str
    text: str
    catalog_profile: str
    code_group: str | None = None
