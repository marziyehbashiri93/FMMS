"""Domain entities for inspection checklist templates synced from SAP."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass
class InspectionTemplate:
    """Local cache of an SAP object-part catalog entry used as a checklist item.

    Attributes:
        id: Universally unique identifier for this template row.
        sap_code: SAP object-part code (sync match key with code_group).
        code_group: SAP code group within the catalog.
        category: Display category for the driver checklist (from code_group).
        description: Human-readable checklist item text.
        catalog_type: SAP catalog type (e.g. ``B``).
        is_active: Whether the template is offered to drivers.
        created_at: UTC timestamp when the local row was created.
        updated_at: UTC timestamp of the last sync update.
    """

    id: uuid.UUID
    sap_code: str
    code_group: str
    category: str
    description: str
    catalog_type: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
