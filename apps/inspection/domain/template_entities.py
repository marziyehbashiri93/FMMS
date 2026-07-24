"""Domain entities for inspection checklist templates synced from SAP."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass
class InspectionTemplate:
    """Local cache of one SAP inspection-template catalog row.

    Attributes:
        id: Universally unique identifier for this template row.
        code_group: SAP ``CodeGroup``.
        code: SAP ``Code``.
        group_text: SAP ``GroupText`` displayed as checklist category.
        code_text: SAP ``CodeText`` displayed as checklist item text.
        is_active: Whether the template is offered to drivers.
        created_at: UTC timestamp when the local row was created.
        updated_at: UTC timestamp of the last sync update.
    """

    id: uuid.UUID
    code_group: str
    code: str
    group_text: str
    code_text: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
