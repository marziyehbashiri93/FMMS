"""Application DTOs for inspection checklist templates."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class InspectionTemplateResponseDTO:
    """Output DTO for a single inspection checklist template.

    Attributes:
        id: Template UUID.
        sap_code: SAP object-part code.
        code_group: SAP code group.
        category: Checklist category shown to the driver.
        description: Checklist item description.
        catalog_type: SAP catalog type.
        is_active: Whether the template is offered to drivers.
        created_at: Local creation timestamp.
        updated_at: Last sync/update timestamp.
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


@dataclass(frozen=True)
class InspectionTemplateSyncResultDTO:
    """Summary of a bulk SAP catalog → inspection template synchronisation.

    Attributes:
        total_received: Number of catalog entries returned by SAP.
        created: Number of new local templates created.
        updated: Number of existing templates updated.
        failed: Number of records that could not be synced.
    """

    total_received: int
    created: int
    updated: int
    failed: int
