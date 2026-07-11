"""Service that creates a DRAFT purchase requisition.

Cross-domain check: repair order must exist (IRepairOrderRepository).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from apps.procurement.application.dto.procurement_dto import (
    CreatePurchaseRequisitionDTO,
    PRLineItemResponseDTO,
    PurchaseRequisitionResponseDTO,
)
from apps.procurement.domain.entities import PRStatus, PurchaseRequisition
from apps.procurement.domain.interfaces.procurement_repository import (
    IPurchaseRequisitionRepository,
)
from apps.repair.domain.interfaces.repair_repository import IRepairOrderRepository
from core.exceptions.translation import load_or_not_found
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger("procurement", __name__)


def _pr_to_response_dto(
    pr: PurchaseRequisition,
    *,
    sap_transaction_id: uuid.UUID | None = None,
    sap_transaction_status: str | None = None,
) -> PurchaseRequisitionResponseDTO:
    """Map ``PurchaseRequisition`` → response DTO."""
    return PurchaseRequisitionResponseDTO(
        id=pr.id,
        repair_order_id=pr.repair_order_id,
        status=pr.status,
        requested_by_id=pr.requested_by_id,
        created_at=pr.created_at,
        updated_at=pr.updated_at,
        sap_pr_number=pr.sap_pr_number.value if pr.sap_pr_number else None,
        approved_by_id=pr.approved_by_id,
        material_request_id=pr.material_request_id,
        sap_transaction_id=sap_transaction_id,
        sap_transaction_status=sap_transaction_status,
        line_items=[
            PRLineItemResponseDTO(
                id=item.id,
                material_number=item.material_number.value,
                quantity=item.quantity.value,
                unit_of_measure=item.quantity.unit_of_measure,
                description=item.description,
                estimated_amount=(
                    item.estimated_price.amount if item.estimated_price else None
                ),
                currency=(
                    item.estimated_price.currency if item.estimated_price else None
                ),
            )
            for item in pr.line_items
        ],
    )


class CreatePurchaseRequisitionService:
    """Orchestrates creation of a DRAFT purchase requisition.

    Args:
        pr_repository: Concrete ``IPurchaseRequisitionRepository``.
        repair_order_repository: Concrete ``IRepairOrderRepository``.
    """

    def __init__(
        self,
        pr_repository: IPurchaseRequisitionRepository,
        repair_order_repository: IRepairOrderRepository,
    ) -> None:
        self._pr_repo = pr_repository
        self._repair_repo = repair_order_repository

    def execute(
        self, dto: CreatePurchaseRequisitionDTO
    ) -> PurchaseRequisitionResponseDTO:
        """Create and persist a DRAFT PR linked to a repair order.

        Args:
            dto: Creation request.

        Returns:
            ``PurchaseRequisitionResponseDTO`` in DRAFT status.

        Raises:
            FMMSNotFoundError: If the repair order does not exist.
        """
        logger.info(
            "Creating purchase requisition",
            extra={
                "domain": "procurement",
                "service": "CreatePurchaseRequisitionService",
                "operation": "execute",
                "request_id": dto.request_id,
                "repair_order_id": str(dto.repair_order_id),
            },
        )

        load_or_not_found(
            lambda: self._repair_repo.get_by_id(dto.repair_order_id),
            message=f"Repair order '{dto.repair_order_id}' not found.",
            details={"repair_order_id": str(dto.repair_order_id)},
        )

        now = datetime.now(tz=UTC)
        pr = PurchaseRequisition(
            id=uuid.uuid4(),
            repair_order_id=dto.repair_order_id,
            status=PRStatus.DRAFT,
            requested_by_id=dto.requested_by,
            material_request_id=dto.material_request_id,
            created_at=now,
            updated_at=now,
        )
        saved = self._pr_repo.save(pr)

        logger.info(
            "Purchase requisition created",
            extra={
                "domain": "procurement",
                "service": "CreatePurchaseRequisitionService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(saved.id),
                "result": "success",
            },
        )
        return _pr_to_response_dto(saved)
