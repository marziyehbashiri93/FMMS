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
        code_group: SAP ``CodeGroup``.
        code: SAP ``Code``.
        group_text: SAP ``GroupText``.
        code_text: SAP ``CodeText``.
        defect_class: SAP ``DefectClass``.
        defect_class_text: SAP ``DefectClassText``.
    """

    code_group: str
    code: str
    group_text: str
    code_text: str
    defect_class: str
    defect_class_text: str
