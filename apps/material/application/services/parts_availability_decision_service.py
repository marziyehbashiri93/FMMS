"""Transport decides warehouse vs purchase fulfillment per material-request item."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from apps.material.application.dto.material_request_dto import (
    PartsAvailabilityDecisionDTO,
    PartsItemDecisionDTO,
)
from apps.material.application.services.material_request_mapper import (
    to_material_request_response,
)
from apps.material.domain.entities import (
    MaterialItemDecision,
    MaterialItemStatus,
    MaterialRequest,
    MaterialRequestItem,
    MaterialRequestStatus,
)
from apps.material.domain.interfaces.central_stock_repository import (
    ICentralStockRepository,
)
from apps.material.domain.interfaces.inventory_transaction_repository import (
    IInventoryTransactionRepository,
)
from apps.material.domain.interfaces.material_request_repository import (
    IMaterialRequestRepository,
)
from apps.procurement.application.dto.procurement_dto import (
    AddPRLineItemDTO,
    CreatePurchaseRequisitionDTO,
)
from apps.procurement.application.services.add_pr_line_item_service import (
    AddPRLineItemService,
)
from apps.procurement.application.services.create_purchase_requisition_service import (
    CreatePurchaseRequisitionService,
)
from apps.repair.application.services._timeline_helper import (
    record_repair_timeline_event,
)
from apps.repair.application.services.repair_order_timeline_service import (
    RecordRepairOrderEventService,
)
from apps.repair.domain.entities import RepairOrderEventType
from core.exceptions.base_exception import FMMSConflictError, FMMSValidationError
from core.exceptions.translation import load_or_not_found
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger("material", __name__)

# Draft PR placeholder when workshop stored a free-text name (not a SAP number).
_EXTERNAL_MATERIAL_PLACEHOLDER = "000000000000000000"


def _pr_line_fields(item: MaterialRequestItem) -> tuple[str, str, str]:
    """Map a material-request item to PR line material/uom/description.

    Workshop may store out-of-catalog free-text names in ``material_number``.
    SAP ``MaterialNumber`` only accepts digits, so free-text goes into
    description with a numeric placeholder.

    Args:
        item: Material request line being sent to purchase.

    Returns:
        Tuple of ``(material_number, unit_of_measure, description)``.
    """
    raw = (item.material_number or "").strip()
    uom = (item.unit_of_measure or "").strip()
    if not uom or uom == "-":
        uom = "EA"
    if raw.isdigit() and len(raw) <= 18:
        description = "Material request auto-generated line item."
        if not item.from_catalog:
            description = f"Out-of-catalog purchase: {raw}"
        return raw, uom, description
    return (
        _EXTERNAL_MATERIAL_PLACEHOLDER,
        uom,
        f"خرید خارج از کاتالوگ: {raw}",
    )


class DecidePartsAvailabilityService:
    """Transport supervisor decides stock vs purchase for each requested item.

    Header aggregation after per-item decisions:
        - all FROM_STOCK → STOCK_ISSUED
        - all PURCHASE → PURCHASE_REQUIRED
        - mixed → PARTIALLY_ISSUED until purchased items are issued
    """

    def __init__(
        self,
        material_request_repository: IMaterialRequestRepository,
        central_stock_repository: ICentralStockRepository,
        inventory_transaction_repository: IInventoryTransactionRepository,
        create_purchase_requisition_service: CreatePurchaseRequisitionService,
        add_pr_line_item_service: AddPRLineItemService,
        event_recorder: RecordRepairOrderEventService | None = None,
    ) -> None:
        self._repo = material_request_repository
        self._stock = central_stock_repository
        self._inventory_tx = inventory_transaction_repository
        self._create_pr = create_purchase_requisition_service
        self._add_pr_line_item = add_pr_line_item_service
        self._event_recorder = event_recorder

    def execute(self, dto: PartsAvailabilityDecisionDTO):
        """Apply per-item availability decisions and advance the workflow."""
        logger.info(
            "Deciding parts availability per item",
            extra={
                "domain": "material",
                "service": "DecidePartsAvailabilityService",
                "operation": "execute",
                "request_id": dto.request_id,
                "material_request_id": str(dto.material_request_id),
                "item_count": len(dto.items),
            },
        )
        material_request = load_or_not_found(
            lambda: self._repo.get_by_id(dto.material_request_id),
            message=f"Material request '{dto.material_request_id}' not found.",
            details={"material_request_id": str(dto.material_request_id)},
        )
        if material_request.status != MaterialRequestStatus.REQUESTED:
            raise FMMSConflictError(
                message="Availability can only be decided for REQUESTED material requests.",
                error_code="MATERIAL_REQUEST_INVALID_STATE",
                details={
                    "material_request_id": str(material_request.id),
                    "status": material_request.status.value,
                },
            )

        decisions_by_id = self._validate_item_decisions(material_request, dto.items)
        self._apply_item_decisions(material_request, decisions_by_id, dto)

        material_request.approve()
        header_status = self._aggregate_header_status(material_request)
        material_request.transition_to(header_status)
        material_request.updated_at = datetime.now(tz=UTC)
        saved = self._repo.save(material_request)

        if any(
            item.decision == MaterialItemDecision.FROM_STOCK for item in saved.items
        ):
            self._inventory_tx.create_issue_for_material_request(saved.id)

        purchase_items = [
            item
            for item in saved.items
            if item.decision == MaterialItemDecision.PURCHASE
        ]
        if purchase_items:
            self._create_purchase_lines(saved, purchase_items, dto)

        note_suffix = f" ({dto.note})" if dto.note.strip() else ""
        record_repair_timeline_event(
            self._event_recorder,
            saved.repair_order_id,
            RepairOrderEventType.MATERIAL_APPROVED,
            f"تصمیم ترابری برای اقلام درخواست قطعه ثبت شد.{note_suffix}",
            created_by_id=dto.decided_by,
            request_id=dto.request_id,
        )
        if saved.status == MaterialRequestStatus.STOCK_ISSUED:
            record_repair_timeline_event(
                self._event_recorder,
                saved.repair_order_id,
                RepairOrderEventType.STOCK_ISSUED,
                "همه قطعات از انبار مرکزی تخصیص و به تعمیرگاه ارسال شد.",
                created_by_id=dto.decided_by,
                request_id=dto.request_id,
            )
        elif saved.status == MaterialRequestStatus.PURCHASE_REQUIRED:
            record_repair_timeline_event(
                self._event_recorder,
                saved.repair_order_id,
                RepairOrderEventType.PURCHASE_REQUIRED,
                "همه قطعات برای خرید از بیرون ثبت شدند؛ سفارش خرید ایجاد شد.",
                created_by_id=dto.decided_by,
                request_id=dto.request_id,
            )
        elif saved.status == MaterialRequestStatus.PARTIALLY_ISSUED:
            record_repair_timeline_event(
                self._event_recorder,
                saved.repair_order_id,
                RepairOrderEventType.PURCHASE_REQUIRED,
                "برخی قطعات از انبار تخصیص شد و برخی برای خرید از بیرون ثبت شدند.",
                created_by_id=dto.decided_by,
                request_id=dto.request_id,
            )

        return to_material_request_response(saved, self._stock)

    def _validate_item_decisions(
        self,
        material_request: MaterialRequest,
        decisions: tuple[PartsItemDecisionDTO, ...],
    ) -> dict[uuid.UUID, MaterialItemDecision]:
        """Ensure every item has exactly one FROM_STOCK/PURCHASE decision."""
        expected_ids = {item.id for item in material_request.items}
        provided_ids = {item.item_id for item in decisions}
        if expected_ids != provided_ids:
            raise FMMSValidationError(
                message="A decision is required for every material request item.",
                error_code="MATERIAL_ITEM_DECISIONS_INCOMPLETE",
                details={
                    "expected_item_ids": [str(item_id) for item_id in sorted(expected_ids)],
                    "provided_item_ids": [str(item_id) for item_id in sorted(provided_ids)],
                },
            )
        result: dict[uuid.UUID, MaterialItemDecision] = {}
        for decision in decisions:
            if decision.decision not in {
                MaterialItemDecision.FROM_STOCK,
                MaterialItemDecision.PURCHASE,
            }:
                raise FMMSValidationError(
                    message="Item decision must be FROM_STOCK or PURCHASE.",
                    error_code="MATERIAL_ITEM_DECISION_INVALID",
                    details={
                        "item_id": str(decision.item_id),
                        "decision": decision.decision.value,
                    },
                )
            result[decision.item_id] = decision.decision
        return result

    def _apply_item_decisions(
        self,
        material_request: MaterialRequest,
        decisions_by_id: dict[uuid.UUID, MaterialItemDecision],
        dto: PartsAvailabilityDecisionDTO,
    ) -> None:
        """Mutate item decision/status fields and validate stock path."""
        for item in material_request.items:
            decision = decisions_by_id[item.id]
            available = self._stock.get_available_quantity(item.material_number)
            in_catalog = self._stock.material_exists(item.material_number)
            item.available_quantity_snapshot = available
            item.decision = decision

            if decision == MaterialItemDecision.FROM_STOCK:
                if dto.enforce_stock_check:
                    if not in_catalog or not item.from_catalog:
                        raise FMMSValidationError(
                            message=(
                                "Parts not in the central catalog cannot be "
                                "allocated from stock."
                            ),
                            error_code="MATERIAL_NOT_IN_CENTRAL_CATALOG",
                            details={
                                "item_id": str(item.id),
                                "material_number": item.material_number,
                                "in_catalog": in_catalog,
                                "from_catalog": item.from_catalog,
                            },
                        )
                    if available < item.quantity:
                        raise FMMSValidationError(
                            message=(
                                "Central warehouse stock is insufficient for "
                                "the requested part."
                            ),
                            error_code="INSUFFICIENT_CENTRAL_STOCK",
                            details={
                                "item_id": str(item.id),
                                "material_number": item.material_number,
                                "requested": str(item.quantity),
                                "available": str(available),
                            },
                        )
                item.item_status = MaterialItemStatus.READY
            else:
                item.item_status = MaterialItemStatus.PURCHASE_REQUIRED

    @staticmethod
    def _aggregate_header_status(
        material_request: MaterialRequest,
    ) -> MaterialRequestStatus:
        """Derive header status from per-item decisions/statuses."""
        decisions = {item.decision for item in material_request.items}
        if decisions == {MaterialItemDecision.FROM_STOCK}:
            return MaterialRequestStatus.STOCK_ISSUED
        if decisions == {MaterialItemDecision.PURCHASE}:
            return MaterialRequestStatus.PURCHASE_REQUIRED
        return MaterialRequestStatus.PARTIALLY_ISSUED

    def _create_purchase_lines(
        self,
        material_request: MaterialRequest,
        purchase_items: list,
        dto: PartsAvailabilityDecisionDTO,
    ) -> None:
        """Create a draft PR with only purchase-path items."""
        requisition = self._create_pr.execute(
            CreatePurchaseRequisitionDTO(
                repair_order_id=material_request.repair_order_id,
                request_id=dto.request_id,
                requested_by=dto.decided_by,
                material_request_id=material_request.id,
            )
        )
        for item in purchase_items:
            material_number, unit_of_measure, description = _pr_line_fields(item)
            try:
                self._add_pr_line_item.execute(
                    AddPRLineItemDTO(
                        pr_id=requisition.id,
                        material_number=material_number,
                        quantity=item.quantity,
                        unit_of_measure=unit_of_measure,
                        description=description,
                        request_id=dto.request_id,
                    )
                )
            except ValueError as exc:
                raise FMMSValidationError(
                    message=(
                        "Cannot create purchase requisition line for this "
                        "material request item."
                    ),
                    error_code="MATERIAL_PR_LINE_INVALID",
                    details={
                        "item_id": str(item.id),
                        "material_number": item.material_number,
                        "reason": str(exc),
                    },
                ) from exc


class IssuePurchasedPartsService:
    """After goods receipt, mark purchase items READY and advance header when complete."""

    def __init__(
        self,
        material_request_repository: IMaterialRequestRepository,
        inventory_transaction_repository: IInventoryTransactionRepository,
        central_stock_repository: ICentralStockRepository | None = None,
        event_recorder: RecordRepairOrderEventService | None = None,
    ) -> None:
        self._repo = material_request_repository
        self._inventory_tx = inventory_transaction_repository
        self._stock = central_stock_repository
        self._event_recorder = event_recorder

    def execute(
        self,
        *,
        material_request_id: uuid.UUID,
        request_id: str,
        decided_by: uuid.UUID,
    ):
        """Move purchase-pending items to READY; header becomes STOCK_ISSUED when all ready."""
        material_request = load_or_not_found(
            lambda: self._repo.get_by_id(material_request_id),
            message=f"Material request '{material_request_id}' not found.",
            details={"material_request_id": str(material_request_id)},
        )
        if material_request.status not in {
            MaterialRequestStatus.PURCHASE_REQUIRED,
            MaterialRequestStatus.WAITING_STOCK,
            MaterialRequestStatus.PARTIALLY_ISSUED,
        }:
            raise FMMSConflictError(
                message="Purchased parts can only be issued from purchase-pending states.",
                error_code="MATERIAL_REQUEST_INVALID_STATE",
                details={
                    "material_request_id": str(material_request.id),
                    "status": material_request.status.value,
                },
            )

        for item in material_request.items:
            if item.item_status == MaterialItemStatus.PURCHASE_REQUIRED:
                item.item_status = MaterialItemStatus.READY

        if not all(
            item.item_status == MaterialItemStatus.READY
            for item in material_request.items
        ):
            raise FMMSConflictError(
                message="Not all material request items are ready after purchase issue.",
                error_code="MATERIAL_ITEMS_NOT_READY",
                details={"material_request_id": str(material_request.id)},
            )

        if material_request.status != MaterialRequestStatus.STOCK_ISSUED:
            material_request.transition_to(MaterialRequestStatus.STOCK_ISSUED)
        material_request.updated_at = datetime.now(tz=UTC)
        saved = self._repo.save(material_request)
        self._inventory_tx.create_issue_for_material_request(saved.id)
        record_repair_timeline_event(
            self._event_recorder,
            saved.repair_order_id,
            RepairOrderEventType.STOCK_ISSUED,
            "قطعات خریداری‌شده پس از رسید کالا تخصیص و به تعمیرگاه ارسال شد.",
            created_by_id=decided_by,
            request_id=request_id,
        )
        return to_material_request_response(saved, self._stock)
