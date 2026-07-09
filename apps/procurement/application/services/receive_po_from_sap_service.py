"""Service that records a Purchase Order received from SAP against a PR."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from apps.procurement.application.dto.procurement_dto import (
    PurchaseOrderResponseDTO,
    ReceivePOFromSAPDTO,
)
from apps.procurement.domain.entities import POLineItem, POStatus, PurchaseOrder
from apps.procurement.domain.interfaces.procurement_repository import (
    IPurchaseOrderRepository,
    IPurchaseRequisitionRepository,
)
from apps.procurement.domain.value_objects import (
    MaterialNumber,
    Money,
    Quantity,
    SAPDocumentNumber,
    VendorNumber,
)
from core.exceptions.base_exception import FMMSConflictError
from core.exceptions.translation import load_or_not_found
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger("procurement", __name__)


def _po_to_response_dto(po: PurchaseOrder) -> PurchaseOrderResponseDTO:
    """Map ``PurchaseOrder`` → response DTO."""
    return PurchaseOrderResponseDTO(
        id=po.id,
        pr_id=po.pr_id,
        vendor_number=po.vendor_number.value,
        status=po.status,
        created_by_id=po.created_by_id,
        created_at=po.created_at,
        updated_at=po.updated_at,
        sap_po_number=po.sap_po_number.value if po.sap_po_number else None,
        approved_by_id=po.approved_by_id,
    )


class ReceivePOFromSAPService:
    """Orchestrates creation of a local PO from SAP PO data.

    Args:
        pr_repository: Concrete ``IPurchaseRequisitionRepository``.
        po_repository: Concrete ``IPurchaseOrderRepository``.
    """

    def __init__(
        self,
        pr_repository: IPurchaseRequisitionRepository,
        po_repository: IPurchaseOrderRepository,
    ) -> None:
        self._pr_repo = pr_repository
        self._po_repo = po_repository

    def execute(self, dto: ReceivePOFromSAPDTO) -> PurchaseOrderResponseDTO:
        """Create a CREATED purchase order linked to an existing PR.

        Args:
            dto: SAP PO receipt payload.

        Returns:
            ``PurchaseOrderResponseDTO``.

        Raises:
            FMMSNotFoundError: If the PR does not exist.
            FMMSConflictError: If a PO for this PR already exists, or the PR
                has no SAP PR number yet.
            FMMSValidationError: If no line items are provided.
        """
        logger.info(
            "Receiving PO from SAP",
            extra={
                "domain": "procurement",
                "service": "ReceivePOFromSAPService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(dto.pr_id),
                "sap_po_number": dto.sap_po_number,
            },
        )

        pr = load_or_not_found(
            lambda: self._pr_repo.get_by_id(dto.pr_id),
            message=f"Purchase requisition '{dto.pr_id}' not found.",
            details={"pr_id": str(dto.pr_id)},
        )

        if pr.sap_pr_number is None:
            raise FMMSConflictError(
                message=(
                    f"PR '{dto.pr_id}' has no SAP PR number; "
                    "submit to SAP before receiving a PO."
                ),
                details={"pr_id": str(dto.pr_id)},
            )

        existing = self._po_repo.list_by_pr(dto.pr_id)
        if existing:
            raise FMMSConflictError(
                message=f"Purchase order already exists for PR '{dto.pr_id}'.",
                details={
                    "pr_id": str(dto.pr_id),
                    "existing_po_id": str(existing[0].id),
                },
            )

        if not dto.line_items:
            raise FMMSConflictError(
                message="Cannot create a PO with no line items.",
                details={"pr_id": str(dto.pr_id)},
            )

        now = datetime.now(tz=UTC)
        po = PurchaseOrder(
            id=uuid.uuid4(),
            pr_id=dto.pr_id,
            vendor_number=VendorNumber(dto.vendor_number),
            status=POStatus.CREATED,
            created_by_id=dto.created_by,
            created_at=now,
            updated_at=now,
            sap_po_number=SAPDocumentNumber(dto.sap_po_number),
            line_items=[
                POLineItem(
                    id=uuid.uuid4(),
                    material_number=MaterialNumber(item.material_number),
                    quantity=Quantity(
                        value=Decimal(item.quantity),
                        unit_of_measure=item.unit_of_measure,
                    ),
                    unit_price=Money(
                        amount=Decimal(item.unit_price), currency=item.currency
                    ),
                )
                for item in dto.line_items
            ],
        )
        saved = self._po_repo.save(po)

        logger.info(
            "PO received from SAP",
            extra={
                "domain": "procurement",
                "service": "ReceivePOFromSAPService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(saved.id),
                "result": "success",
                "sap_po_number": dto.sap_po_number,
            },
        )
        return _po_to_response_dto(saved)
