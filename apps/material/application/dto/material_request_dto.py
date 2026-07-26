"""Application DTOs for material requests."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from apps.material.domain.entities import (
    MaterialItemDecision,
    MaterialItemStatus,
    MaterialRequestStatus,
)

DEFAULT_MATERIAL_UOM = "-"


@dataclass(frozen=True)
class CreateMaterialRequestItemDTO:
    """Material request item input DTO."""

    material_number: str
    quantity: Decimal
    unit_of_measure: str = DEFAULT_MATERIAL_UOM
    from_catalog: bool = True


@dataclass(frozen=True)
class CreateMaterialRequestDTO:
    """Create material request input DTO."""

    repair_order_id: uuid.UUID
    items: tuple[CreateMaterialRequestItemDTO, ...]
    request_id: str
    requested_by: uuid.UUID


@dataclass(frozen=True)
class MaterialRequestDecisionDTO:
    """Approve/receive material request input DTO."""

    material_request_id: uuid.UUID
    request_id: str
    decided_by: uuid.UUID


@dataclass(frozen=True)
class PartsItemDecisionDTO:
    """One per-item transport availability decision."""

    item_id: uuid.UUID
    decision: MaterialItemDecision


@dataclass(frozen=True)
class PartsAvailabilityDecisionDTO:
    """Transport decides stock vs purchase for each requested item."""

    material_request_id: uuid.UUID
    items: tuple[PartsItemDecisionDTO, ...]
    request_id: str
    decided_by: uuid.UUID
    note: str = ""
    enforce_stock_check: bool = True


@dataclass(frozen=True)
class MaterialRequestItemResponseDTO:
    """Material request item output DTO with live stock enrichment."""

    id: uuid.UUID
    material_number: str
    quantity: Decimal
    unit_of_measure: str
    from_catalog: bool = True
    decision: MaterialItemDecision = MaterialItemDecision.PENDING
    item_status: MaterialItemStatus = MaterialItemStatus.PENDING
    material_name: str = ""
    available_quantity: Decimal = Decimal("0")
    in_catalog: bool = False
    available_quantity_snapshot: Decimal | None = None


@dataclass(frozen=True)
class MaterialRequestResponseDTO:
    """Material request output DTO."""

    id: uuid.UUID
    repair_order_id: uuid.UUID
    status: MaterialRequestStatus
    created_by_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    items: list[MaterialRequestItemResponseDTO] = field(default_factory=list)
