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
    """

    code_group: str
    code: str
    group_text: str
    code_text: str
