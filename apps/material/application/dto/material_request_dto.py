"""Application DTOs for material requests."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from apps.material.domain.entities import MaterialRequestStatus


@dataclass(frozen=True)
class CreateMaterialRequestItemDTO:
    """Material request item input DTO."""

    material_number: str
    quantity: Decimal
    unit_of_measure: str


@dataclass(frozen=True)
class CreateMaterialRequestDTO:
    """Create material request input DTO."""

    repair_order_id: uuid.UUID
    items: tuple[CreateMaterialRequestItemDTO, ...]
    request_id: str
    requested_by: uuid.UUID


@dataclass(frozen=True)
class MaterialRequestDecisionDTO:
    """Approve/reject material request input DTO."""

    material_request_id: uuid.UUID
    request_id: str
    decided_by: uuid.UUID


@dataclass(frozen=True)
class MaterialRequestItemResponseDTO:
    """Material request item output DTO."""

    id: uuid.UUID
    material_number: str
    quantity: Decimal
    unit_of_measure: str


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
