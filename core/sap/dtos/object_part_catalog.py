"""SAP Object Part Catalog DTOs.

Represents data received from SAP's object part catalog.
Used during inspection item categorization and fault reporting.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SAPObjectPartDTO:
    """A single object part entry from the SAP catalog.

    Attributes:
        code: The object part code identifier.
        code_group: The grouping code within the catalog.
        description: Human-readable description of the part/component.
        catalog_type: The SAP catalog type (e.g. "B" for object parts).
    """

    code: str
    code_group: str
    description: str
    catalog_type: str
