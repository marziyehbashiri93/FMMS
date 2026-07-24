"""Domain entities for SAP-synced fault catalog rows."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass
class FaultCatalog:
    """Local cache of one SAP defect catalog row."""

    id: uuid.UUID
    code_group: str
    code: str
    group_text: str
    code_text: str
    defect_class: str
    defect_class_text: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
