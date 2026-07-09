"""Service that adds a line item to a DRAFT purchase requisition."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from apps.procurement.application.dto.procurement_dto import (
    AddPRLineItemDTO,
    PurchaseRequisitionResponseDTO,
)
from apps.procurement.application.services.create_purchase_requisition_service import (
    _pr_to_response_dto,
)
from apps.procurement.domain.entities import PRLineItem
from apps.procurement.domain.interfaces.procurement_repository import (
    IPurchaseRequisitionRepository,
)
from apps.procurement.domain.value_objects import MaterialNumber, Money, Quantity
from core.exceptions.base_exception import FMMSValidationError
from core.exceptions.translation import load_or_not_found
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger("procurement", __name__)


class AddPRLineItemService:
    """Orchestrates addition of a line item to a DRAFT PR.

    Args:
        pr_repository: Concrete ``IPurchaseRequisitionRepository``.
    """

    def __init__(self, pr_repository: IPurchaseRequisitionRepository) -> None:
        self._pr_repo = pr_repository

    def execute(self, dto: AddPRLineItemDTO) -> PurchaseRequisitionResponseDTO:
        """Add a line item to a DRAFT purchase requisition.

        Args:
            dto: Line item details.

        Returns:
            Updated ``PurchaseRequisitionResponseDTO``.

        Raises:
            FMMSNotFoundError: If the PR does not exist.
            FMMSValidationError: If estimated price fields are incomplete.
            ProcurementInvalidStateTransitionError: If PR is not DRAFT (entity).
        """
        logger.info(
            "Adding PR line item",
            extra={
                "domain": "procurement",
                "service": "AddPRLineItemService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(dto.pr_id),
            },
        )

        pr = load_or_not_found(
            lambda: self._pr_repo.get_by_id(dto.pr_id),
            message=f"Purchase requisition '{dto.pr_id}' not found.",
            details={"pr_id": str(dto.pr_id)},
        )

        estimated_price: Money | None = None
        if dto.estimated_amount is not None or dto.currency is not None:
            if dto.estimated_amount is None or dto.currency is None:
                raise FMMSValidationError(
                    message="Both estimated_amount and currency are required together.",
                    details={
                        "estimated_amount": str(dto.estimated_amount),
                        "currency": dto.currency,
                    },
                )
            estimated_price = Money(
                amount=Decimal(dto.estimated_amount), currency=dto.currency
            )

        item = PRLineItem(
            id=uuid.uuid4(),
            material_number=MaterialNumber(dto.material_number),
            quantity=Quantity(
                value=Decimal(dto.quantity), unit_of_measure=dto.unit_of_measure
            ),
            description=dto.description,
            estimated_price=estimated_price,
        )
        pr.add_line_item(item)
        pr.updated_at = datetime.now(tz=UTC)
        saved = self._pr_repo.save(pr)

        logger.info(
            "PR line item added",
            extra={
                "domain": "procurement",
                "service": "AddPRLineItemService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(saved.id),
                "result": "success",
                "line_item_count": len(saved.line_items),
            },
        )
        return _pr_to_response_dto(saved)
