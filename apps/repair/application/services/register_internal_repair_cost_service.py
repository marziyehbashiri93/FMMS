"""Register internal workshop financial documents."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from apps.repair.domain.entities import WorkshopType
from apps.repair.domain.interfaces.internal_cost_repository import (
    IInternalRepairCostRepository,
)
from apps.repair.domain.interfaces.repair_repository import IRepairOrderRepository
from apps.repair.domain.internal_cost_entities import (
    InternalRepairCost,
    InternalRepairCostStatus,
)
from core.exceptions.base_exception import FMMSConflictError, FMMSValidationError
from core.exceptions.translation import load_or_not_found
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger("repair", __name__)


@dataclass(frozen=True)
class RegisterInternalRepairCostDTO:
    """Input for registering INTERNAL repair costs."""

    repair_order_id: uuid.UUID
    invoice_number: str
    labor_cost: Decimal
    parts_cost: Decimal
    service_cost: Decimal
    currency: str
    notes: str
    request_id: str
    registered_by: uuid.UUID


@dataclass(frozen=True)
class InternalRepairCostResponseDTO:
    """Output DTO for an internal repair cost document."""

    id: uuid.UUID
    repair_order_id: uuid.UUID
    invoice_number: str
    labor_cost: Decimal
    parts_cost: Decimal
    service_cost: Decimal
    total_cost: Decimal
    currency: str
    status: str
    notes: str
    registered_by_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class RegisterInternalRepairCostService:
    """Create/register the financial document for an INTERNAL repair."""

    def __init__(
        self,
        cost_repository: IInternalRepairCostRepository,
        repair_order_repository: IRepairOrderRepository,
    ) -> None:
        self._cost_repo = cost_repository
        self._repair_repo = repair_order_repository

    def execute(self, dto: RegisterInternalRepairCostDTO) -> InternalRepairCostResponseDTO:
        """Register costs for an INTERNAL repair order."""
        order = load_or_not_found(
            lambda: self._repair_repo.get_by_id(dto.repair_order_id),
            message=f"Repair order '{dto.repair_order_id}' not found.",
            details={"repair_order_id": str(dto.repair_order_id)},
        )
        if order.workshop_type != WorkshopType.INTERNAL:
            raise FMMSValidationError(
                message="Internal cost registration applies only to INTERNAL workshop repairs.",
                error_code="INTERNAL_COST_REQUIRES_INTERNAL_WORKSHOP",
                details={"repair_order_id": str(order.id)},
            )
        existing = self._cost_repo.get_by_repair_order(order.id)
        if existing is not None and existing.status == InternalRepairCostStatus.REGISTERED:
            raise FMMSConflictError(
                message="Internal repair cost is already registered for this order.",
                error_code="INTERNAL_COST_ALREADY_REGISTERED",
                details={"repair_order_id": str(order.id)},
            )

        now = datetime.now(tz=UTC)
        cost = existing or InternalRepairCost(
            id=uuid.uuid4(),
            repair_order_id=order.id,
            invoice_number=dto.invoice_number,
            labor_cost=dto.labor_cost,
            parts_cost=dto.parts_cost,
            service_cost=dto.service_cost,
            currency=dto.currency or "IRR",
            status=InternalRepairCostStatus.DRAFT,
            notes=dto.notes,
            registered_by_id=dto.registered_by,
            created_at=now,
            updated_at=now,
        )
        cost.invoice_number = dto.invoice_number
        cost.labor_cost = dto.labor_cost
        cost.parts_cost = dto.parts_cost
        cost.service_cost = dto.service_cost
        cost.currency = dto.currency or "IRR"
        cost.notes = dto.notes
        cost.registered_by_id = dto.registered_by
        cost.updated_at = now
        cost.register()
        saved = self._cost_repo.save(cost)
        logger.info(
            "Internal repair cost registered",
            extra={
                "domain": "repair",
                "service": "RegisterInternalRepairCostService",
                "repair_order_id": str(order.id),
                "request_id": dto.request_id,
            },
        )
        return InternalRepairCostResponseDTO(
            id=saved.id,
            repair_order_id=saved.repair_order_id,
            invoice_number=saved.invoice_number,
            labor_cost=saved.labor_cost,
            parts_cost=saved.parts_cost,
            service_cost=saved.service_cost,
            total_cost=saved.total_cost,
            currency=saved.currency,
            status=saved.status.value,
            notes=saved.notes,
            registered_by_id=saved.registered_by_id,
            created_at=saved.created_at,
            updated_at=saved.updated_at,
        )
