"""Application services for material requests."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from apps.material.application.dto.material_request_dto import (
    CreateMaterialRequestDTO,
    MaterialRequestDecisionDTO,
    MaterialRequestItemResponseDTO,
    MaterialRequestResponseDTO,
)
from apps.material.domain.entities import (
    MaterialRequest,
    MaterialRequestItem,
    MaterialRequestStatus,
)
from apps.material.domain.interfaces.inventory_availability_port import (
    IInventoryAvailabilityPort,
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
from apps.repair.domain.interfaces.repair_repository import IRepairOrderRepository
from core.exceptions.translation import load_or_not_found


def _to_dto(material_request: MaterialRequest) -> MaterialRequestResponseDTO:
    """Map aggregate to response DTO."""
    return MaterialRequestResponseDTO(
        id=material_request.id,
        repair_order_id=material_request.repair_order_id,
        status=material_request.status,
        created_by_id=material_request.created_by_id,
        created_at=material_request.created_at,
        updated_at=material_request.updated_at,
        items=[
            MaterialRequestItemResponseDTO(
                id=item.id,
                material_number=item.material_number,
                quantity=item.quantity,
                unit_of_measure=item.unit_of_measure,
            )
            for item in material_request.items
        ],
    )


class CreateMaterialRequestService:
    """Create material request linked to a repair order."""

    def __init__(
        self,
        material_request_repository: IMaterialRequestRepository,
        repair_order_repository: IRepairOrderRepository,
        event_recorder: RecordRepairOrderEventService | None = None,
    ) -> None:
        self._repo = material_request_repository
        self._repair_repo = repair_order_repository
        self._event_recorder = event_recorder

    def execute(self, dto: CreateMaterialRequestDTO) -> MaterialRequestResponseDTO:
        """Create material request in REQUESTED status."""
        load_or_not_found(
            lambda: self._repair_repo.get_by_id(dto.repair_order_id),
            message=f"Repair order '{dto.repair_order_id}' not found.",
            details={"repair_order_id": str(dto.repair_order_id)},
        )
        now = datetime.now(tz=UTC)
        material_request = MaterialRequest(
            id=uuid.uuid4(),
            repair_order_id=dto.repair_order_id,
            status=MaterialRequestStatus.REQUESTED,
            created_by_id=dto.requested_by,
            created_at=now,
            updated_at=now,
            items=[
                MaterialRequestItem(
                    id=uuid.uuid4(),
                    material_number=item.material_number,
                    quantity=item.quantity,
                    unit_of_measure=item.unit_of_measure,
                )
                for item in dto.items
            ],
        )
        saved = self._repo.save(material_request)
        record_repair_timeline_event(
            self._event_recorder,
            saved.repair_order_id,
            RepairOrderEventType.MATERIAL_REQUESTED,
            "درخواست قطعه ثبت شد.",
            created_by_id=dto.requested_by,
            request_id=dto.request_id,
        )
        return _to_dto(saved)


class ListMaterialRequestsService:
    """List material requests."""

    def __init__(self, material_request_repository: IMaterialRequestRepository) -> None:
        self._repo = material_request_repository

    def execute(
        self, status: MaterialRequestStatus | None = None
    ) -> list[MaterialRequestResponseDTO]:
        """List material requests optionally by status."""
        return [_to_dto(item) for item in self._repo.list_all(status=status)]


class ApproveMaterialRequestService:
    """Approve material request and route inventory/procurement flow."""

    def __init__(
        self,
        material_request_repository: IMaterialRequestRepository,
        inventory_availability_port: IInventoryAvailabilityPort,
        inventory_transaction_repository: IInventoryTransactionRepository,
        create_purchase_requisition_service: CreatePurchaseRequisitionService,
        add_pr_line_item_service: AddPRLineItemService,
        event_recorder: RecordRepairOrderEventService | None = None,
    ) -> None:
        self._repo = material_request_repository
        self._inventory = inventory_availability_port
        self._inventory_tx = inventory_transaction_repository
        self._create_pr = create_purchase_requisition_service
        self._add_pr_line_item = add_pr_line_item_service
        self._event_recorder = event_recorder

    def execute(self, dto: MaterialRequestDecisionDTO) -> MaterialRequestResponseDTO:
        """Approve a material request and apply stock routing logic."""
        material_request = load_or_not_found(
            lambda: self._repo.get_by_id(dto.material_request_id),
            message=f"Material request '{dto.material_request_id}' not found.",
            details={"material_request_id": str(dto.material_request_id)},
        )
        material_request.approve()
        material_request.updated_at = datetime.now(tz=UTC)
        saved = self._repo.save(material_request)
        record_repair_timeline_event(
            self._event_recorder,
            saved.repair_order_id,
            RepairOrderEventType.MATERIAL_APPROVED,
            "درخواست قطعه تایید شد.",
            created_by_id=dto.decided_by,
            request_id=dto.request_id,
        )

        available = all(self._inventory.is_available(item) for item in saved.items)
        if available:
            saved.transition_to(MaterialRequestStatus.STOCK_ISSUED)
            saved.updated_at = datetime.now(tz=UTC)
            saved = self._repo.save(saved)
            self._inventory_tx.create_issue_for_material_request(saved.id)
            record_repair_timeline_event(
                self._event_recorder,
                saved.repair_order_id,
                RepairOrderEventType.STOCK_ISSUED,
                "قطعات از انبار صادر شد.",
                created_by_id=dto.decided_by,
                request_id=dto.request_id,
            )
            return _to_dto(saved)

        saved.transition_to(MaterialRequestStatus.PURCHASE_REQUIRED)
        saved.updated_at = datetime.now(tz=UTC)
        saved = self._repo.save(saved)
        record_repair_timeline_event(
            self._event_recorder,
            saved.repair_order_id,
            RepairOrderEventType.PURCHASE_REQUIRED,
            "نیاز به خرید قطعات ثبت شد.",
            created_by_id=dto.decided_by,
            request_id=dto.request_id,
        )
        requisition = self._create_pr.execute(
            CreatePurchaseRequisitionDTO(
                repair_order_id=saved.repair_order_id,
                request_id=dto.request_id,
                requested_by=dto.decided_by,
                material_request_id=saved.id,
            )
        )
        for item in saved.items:
            self._add_pr_line_item.execute(
                AddPRLineItemDTO(
                    pr_id=requisition.id,
                    material_number=item.material_number,
                    quantity=item.quantity,
                    unit_of_measure=item.unit_of_measure,
                    description="Material request auto-generated line item.",
                    request_id=dto.request_id,
                )
            )
        return _to_dto(saved)


class RejectMaterialRequestService:
    """Reject material request."""

    def __init__(
        self,
        material_request_repository: IMaterialRequestRepository,
        event_recorder: RecordRepairOrderEventService | None = None,
    ) -> None:
        self._repo = material_request_repository
        self._event_recorder = event_recorder

    def execute(self, dto: MaterialRequestDecisionDTO) -> MaterialRequestResponseDTO:
        """Reject material request."""
        material_request = load_or_not_found(
            lambda: self._repo.get_by_id(dto.material_request_id),
            message=f"Material request '{dto.material_request_id}' not found.",
            details={"material_request_id": str(dto.material_request_id)},
        )
        material_request.reject()
        material_request.updated_at = datetime.now(tz=UTC)
        saved = self._repo.save(material_request)
        record_repair_timeline_event(
            self._event_recorder,
            saved.repair_order_id,
            RepairOrderEventType.MATERIAL_REJECTED,
            "درخواست قطعه رد شد.",
            created_by_id=dto.decided_by,
            request_id=dto.request_id,
        )
        return _to_dto(saved)
