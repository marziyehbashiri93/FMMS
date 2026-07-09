"""Read-only services for retrieving procurement documents."""

from __future__ import annotations

import uuid

from apps.procurement.application.dto.procurement_dto import (
    PurchaseOrderResponseDTO,
    PurchaseRequisitionResponseDTO,
)
from apps.procurement.application.services.create_purchase_requisition_service import (
    _pr_to_response_dto,
)
from apps.procurement.application.services.receive_po_from_sap_service import (
    _po_to_response_dto,
)
from apps.procurement.domain.entities import PRStatus
from apps.procurement.domain.interfaces.procurement_repository import (
    IPurchaseOrderRepository,
    IPurchaseRequisitionRepository,
)
from core.exceptions.translation import load_or_not_found
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger("procurement", __name__)


class GetPurchaseRequisitionService:
    """Fetch a single purchase requisition by UUID."""

    def __init__(self, pr_repository: IPurchaseRequisitionRepository) -> None:
        self._repo = pr_repository

    def execute(
        self, pr_id: uuid.UUID, request_id: str = ""
    ) -> PurchaseRequisitionResponseDTO:
        """Return the PR identified by ``pr_id``.

        Raises:
            FMMSNotFoundError: If the PR does not exist.
        """
        logger.info(
            "Fetching purchase requisition",
            extra={
                "domain": "procurement",
                "service": "GetPurchaseRequisitionService",
                "operation": "execute",
                "request_id": request_id,
                "entity_id": str(pr_id),
            },
        )
        pr = load_or_not_found(
            lambda: self._repo.get_by_id(pr_id),
            message=f"Purchase requisition '{pr_id}' not found.",
            details={"pr_id": str(pr_id)},
        )
        return _pr_to_response_dto(pr)


class ListPurchaseRequisitionsService:
    """List PRs by repair order or status."""

    def __init__(self, pr_repository: IPurchaseRequisitionRepository) -> None:
        self._repo = pr_repository

    def execute(
        self,
        *,
        repair_order_id: uuid.UUID | None = None,
        status: PRStatus | None = None,
        request_id: str = "",
    ) -> list[PurchaseRequisitionResponseDTO]:
        """Return PRs filtered by repair order or status.

        When ``repair_order_id`` is provided it takes precedence.
        When neither filter is provided, returns an empty list.
        """
        logger.info(
            "Listing purchase requisitions",
            extra={
                "domain": "procurement",
                "service": "ListPurchaseRequisitionsService",
                "operation": "execute",
                "request_id": request_id,
                "repair_order_id": str(repair_order_id) if repair_order_id else None,
                "status_filter": status.value if status else None,
            },
        )
        if repair_order_id is not None:
            prs = self._repo.list_by_repair_order(repair_order_id)
        elif status is not None:
            prs = self._repo.list_by_status(status)
        else:
            prs = []
        return [_pr_to_response_dto(pr) for pr in prs]


class GetPurchaseOrderService:
    """Fetch a single purchase order by UUID."""

    def __init__(self, po_repository: IPurchaseOrderRepository) -> None:
        self._repo = po_repository

    def execute(
        self, po_id: uuid.UUID, request_id: str = ""
    ) -> PurchaseOrderResponseDTO:
        """Return the PO identified by ``po_id``.

        Raises:
            FMMSNotFoundError: If the PO does not exist.
        """
        logger.info(
            "Fetching purchase order",
            extra={
                "domain": "procurement",
                "service": "GetPurchaseOrderService",
                "operation": "execute",
                "request_id": request_id,
                "entity_id": str(po_id),
            },
        )
        po = load_or_not_found(
            lambda: self._repo.get_by_id(po_id),
            message=f"Purchase order '{po_id}' not found.",
            details={"po_id": str(po_id)},
        )
        return _po_to_response_dto(po)
