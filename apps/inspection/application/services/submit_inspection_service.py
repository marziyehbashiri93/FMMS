"""Service that orchestrates inspection submission and automatic fault creation.

Multi-step workflow (designed for future transaction boundary addition):
  Step 1: Load and validate the inspection (must be DRAFT with ≥1 item).
  Step 2: Call ``inspection.submit()`` — transitions DRAFT → SUBMITTED.
  Step 3: If any FAIL items exist, create one ``Fault`` with ``FaultItem`` children
          and one ``RepairOrder``.
  Step 4: Save the updated inspection.

Vehicle operational availability is NOT decided at submit time.
Distribution supervisors close faults or deactivate vehicles separately.

Cross-domain:
    Fault/repair side-effects are workflow policy owned by this service,
    not by Inspection, Fault, or Repair entities alone.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from apps.fault.domain.entities import Fault, FaultItem, FaultStatus
from apps.fault.domain.interfaces.fault_repository import IFaultRepository
from apps.fault.domain.value_objects import FaultCode, FaultDescription, FaultSeverity
from apps.inspection.application.dto.inspection_dto import (
    InspectionResponseDTO,
    SubmitInspectionDTO,
)
from apps.inspection.application.services.create_inspection_service import (
    _to_response_dto,
)
from apps.inspection.domain.entities import InspectionItem
from apps.inspection.domain.interfaces.inspection_repository import (
    IInspectionRepository,
)
from apps.repair.domain.entities import RepairOrder, RepairOrderStatus
from apps.repair.domain.interfaces.repair_repository import IRepairOrderRepository
from core.exceptions.translation import load_or_not_found
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger("inspection", __name__)

_DEFAULT_FAULT_CODE = "INSP-FAIL"
_DEFAULT_FAULT_SEVERITY = FaultSeverity.MEDIUM
_MULTI_FAILURE_DESCRIPTION = "Multiple inspection failures"
_SEVERITY_RANK: dict[FaultSeverity, int] = {
    FaultSeverity.LOW: 0,
    FaultSeverity.MEDIUM: 1,
    FaultSeverity.HIGH: 2,
    FaultSeverity.CRITICAL: 3,
}


def _item_fault_severity(item: InspectionItem) -> FaultSeverity:
    """Map a failed inspection item to fault severity."""
    if item.severity is None:
        return _DEFAULT_FAULT_SEVERITY
    return FaultSeverity(item.severity.value)


def _max_fault_severity(severities: list[FaultSeverity]) -> FaultSeverity:
    """Return the highest severity from a non-empty list."""
    return max(severities, key=lambda level: _SEVERITY_RANK[level])


class SubmitInspectionService:
    """Orchestrates inspection submission and automatic fault/repair generation.

    When an inspection is submitted, failed checklist items are aggregated into
    a single operational fault with child fault items and one repair order.
    The vehicle status remains unchanged so distribution can decide usability.

    Args:
        inspection_repository: Concrete ``IInspectionRepository``.
        fault_repository: Concrete ``IFaultRepository`` for auto-fault creation.
        repair_order_repository: Concrete ``IRepairOrderRepository``.
    """

    def __init__(
        self,
        inspection_repository: IInspectionRepository,
        fault_repository: IFaultRepository,
        repair_order_repository: IRepairOrderRepository,
    ) -> None:
        self._inspection_repo = inspection_repository
        self._fault_repo = fault_repository
        self._repair_repo = repair_order_repository

    def execute(self, dto: SubmitInspectionDTO) -> InspectionResponseDTO:
        """Submit a DRAFT inspection and apply FAIL-side workflow effects.

        Args:
            dto: Submission request.

        Returns:
            ``InspectionResponseDTO`` with ``status == SUBMITTED``.

        Raises:
            FMMSNotFoundError: If inspection does not exist.
            InspectionItemRequiredError: If the inspection has no items.
            InspectionInvalidStateTransitionError: If not in DRAFT status.
        """
        logger.info(
            "Submitting inspection",
            extra={
                "domain": "inspection",
                "service": "SubmitInspectionService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(dto.inspection_id),
            },
        )

        inspection = load_or_not_found(
            lambda: self._inspection_repo.get_by_id(dto.inspection_id),
            message=f"Inspection '{dto.inspection_id}' not found.",
            details={"inspection_id": str(dto.inspection_id)},
        )

        inspection.submit()
        now = datetime.now(tz=UTC)
        inspection.updated_at = now

        failed_items = inspection.failed_items()
        faults_created = 0
        fault_items_created = 0
        repairs_created = 0

        if failed_items:
            fault = _build_fault_from_failed_items(
                inspection_id=inspection.id,
                vehicle_id=inspection.vehicle_id,
                failed_items=failed_items,
                reported_by_id=dto.submitted_by,
                now=now,
            )
            fault_items_created = len(fault.items)
            self._fault_repo.save(fault)
            faults_created = 1

            repair = RepairOrder(
                id=uuid.uuid4(),
                vehicle_id=inspection.vehicle_id,
                fault_id=fault.id,
                status=RepairOrderStatus.CREATED,
                created_by_id=dto.submitted_by,
                created_at=now,
                updated_at=now,
            )
            self._repair_repo.save(repair)
            repairs_created = 1

        saved = self._inspection_repo.save(inspection)

        logger.info(
            "Inspection submitted successfully",
            extra={
                "domain": "inspection",
                "service": "SubmitInspectionService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(saved.id),
                "result": "success",
                "faults_created": faults_created,
                "fault_items_created": fault_items_created,
                "repairs_created": repairs_created,
            },
        )

        return _to_response_dto(saved)


def _build_fault_from_failed_items(
    inspection_id: uuid.UUID,
    vehicle_id: uuid.UUID,
    failed_items: list[InspectionItem],
    reported_by_id: uuid.UUID,
    now: datetime,
) -> Fault:
    """Construct one fault aggregate from failed inspection checklist items."""
    fault_id = uuid.uuid4()
    if len(failed_items) == 1:
        item = failed_items[0]
        summary = f"[{item.category}] {item.description}"[:500]
    else:
        summary = _MULTI_FAILURE_DESCRIPTION

    item_severities = [_item_fault_severity(item) for item in failed_items]
    overall_severity = _max_fault_severity(item_severities)

    fault = Fault(
        id=fault_id,
        vehicle_id=vehicle_id,
        code=FaultCode(_DEFAULT_FAULT_CODE),
        description=FaultDescription(summary),
        severity=overall_severity,
        status=FaultStatus.OPEN,
        reported_by_id=reported_by_id,
        reported_at=now,
        inspection_id=inspection_id,
        created_at=now,
        updated_at=now,
        items=[
            _build_fault_item(
                fault_id=fault_id,
                item=item,
                now=now,
            )
            for item in failed_items
        ],
    )
    return fault


def _build_fault_item(
    fault_id: uuid.UUID,
    item: InspectionItem,
    now: datetime,
) -> FaultItem:
    """Construct a ``FaultItem`` from a failed inspection checklist item."""
    detail = (item.notes or item.description or "").strip() or item.description
    return FaultItem(
        id=uuid.uuid4(),
        fault_id=fault_id,
        inspection_item_id=item.id,
        component=item.description,
        description=detail[:500],
        severity=_item_fault_severity(item),
        created_at=now,
        updated_at=now,
    )
