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
        code_group: SAP ``CodeGroup``.
        code: SAP ``Code``.
        group_text: SAP ``GroupText``.
        code_text: SAP ``CodeText``.
        defect_class: SAP ``DefectClass``.
        defect_class_text: SAP ``DefectClassText``.
        catalog_type: The SAP catalog type (e.g. "B").
    """

    code_group: str
    code: str
    group_text: str
    code_text: str
    defect_class: str
    defect_class_text: str
    catalog_type: str
