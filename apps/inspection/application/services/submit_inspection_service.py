"""Service that orchestrates inspection submission and automatic fault creation.

Multi-step workflow (designed for future transaction boundary addition):
  Step 1: Load and validate the inspection (must be DRAFT with ≥1 item).
  Step 2: Call ``inspection.submit()`` — transitions DRAFT → SUBMITTED.
  Step 3: For each FAIL checklist item, create a ``Fault`` and ``RepairOrder``.
  Step 4: If any FAIL items exist, mark the vehicle OUT_OF_SERVICE.
  Step 5: Save the updated inspection.

Cross-domain:
    Fault/repair/vehicle side-effects are workflow policy owned by this
    service, not by Inspection, Fault, Repair, or Vehicle entities alone.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from apps.fault.domain.entities import Fault, FaultStatus
from apps.fault.domain.interfaces.fault_repository import IFaultRepository
from apps.fault.domain.value_objects import FaultCode, FaultDescription, FaultSeverity
from apps.inspection.application.dto.inspection_dto import (
    InspectionResponseDTO,
    SubmitInspectionDTO,
)
from apps.inspection.application.services.create_inspection_service import (
    _to_response_dto,
)
from apps.inspection.domain.interfaces.inspection_repository import (
    IInspectionRepository,
)
from apps.inspection.domain.value_objects import ChecklistResult
from apps.repair.domain.entities import RepairOrder, RepairOrderStatus
from apps.repair.domain.interfaces.repair_repository import IRepairOrderRepository
from apps.vehicle.domain.interfaces.vehicle_repository import IVehicleRepository
from core.exceptions.translation import load_or_not_found
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger("inspection", __name__)

_DEFAULT_FAULT_CODE = "INSP-FAIL"
_DEFAULT_FAULT_SEVERITY = FaultSeverity.MEDIUM


class SubmitInspectionService:
    """Orchestrates inspection submission and automatic fault/repair generation.

    When an inspection is submitted, any checklist items with a FAIL result
    automatically produce:
      - a new ``Fault`` in OPEN status
      - a new ``RepairOrder`` in CREATED status
    and the vehicle is transitioned to ``OUT_OF_SERVICE``.

    Args:
        inspection_repository: Concrete ``IInspectionRepository``.
        fault_repository: Concrete ``IFaultRepository`` for auto-fault creation.
        repair_order_repository: Concrete ``IRepairOrderRepository``.
        vehicle_repository: Concrete ``IVehicleRepository``.
    """

    def __init__(
        self,
        inspection_repository: IInspectionRepository,
        fault_repository: IFaultRepository,
        repair_order_repository: IRepairOrderRepository,
        vehicle_repository: IVehicleRepository,
    ) -> None:
        self._inspection_repo = inspection_repository
        self._fault_repo = fault_repository
        self._repair_repo = repair_order_repository
        self._vehicle_repo = vehicle_repository

    def execute(self, dto: SubmitInspectionDTO) -> InspectionResponseDTO:
        """Submit a DRAFT inspection and apply FAIL-side workflow effects.

        Args:
            dto: Submission request.

        Returns:
            ``InspectionResponseDTO`` with ``status == SUBMITTED``.

        Raises:
            FMMSNotFoundError: If inspection or vehicle does not exist.
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

        faults_created = 0
        repairs_created = 0
        for item in inspection.items:
            if item.result != ChecklistResult.FAIL:
                continue
            fault = _build_fault_from_item(
                inspection_id=inspection.id,
                vehicle_id=inspection.vehicle_id,
                item_category=item.category,
                item_description=item.description,
                reported_by_id=dto.submitted_by,
                now=now,
            )
            self._fault_repo.save(fault)
            faults_created += 1

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
            repairs_created += 1

        if faults_created > 0:
            vehicle = load_or_not_found(
                lambda: self._vehicle_repo.get_by_id(inspection.vehicle_id),
                message=f"Vehicle '{inspection.vehicle_id}' not found.",
                details={"vehicle_id": str(inspection.vehicle_id)},
            )
            vehicle.mark_out_of_service()
            vehicle.updated_at = now
            self._vehicle_repo.save(vehicle)

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
                "repairs_created": repairs_created,
                "vehicle_out_of_service": faults_created > 0,
            },
        )

        return _to_response_dto(saved)


def _build_fault_from_item(
    inspection_id: uuid.UUID,
    vehicle_id: uuid.UUID,
    item_category: str,
    item_description: str,
    reported_by_id: uuid.UUID,
    now: datetime,
) -> Fault:
    """Construct a ``Fault`` entity from a failed inspection checklist item.

    Args:
        inspection_id: UUID of the originating inspection.
        vehicle_id: UUID of the vehicle being inspected.
        item_category: Category of the failed checklist item.
        item_description: Description of the failed item.
        reported_by_id: UUID of the user who submitted the inspection.
        now: Current UTC datetime for timestamps.

    Returns:
        A new ``Fault`` entity in OPEN status.
    """
    description_text = f"[{item_category}] {item_description}"[:500]
    return Fault(
        id=uuid.uuid4(),
        vehicle_id=vehicle_id,
        code=FaultCode(_DEFAULT_FAULT_CODE),
        description=FaultDescription(description_text),
        severity=_DEFAULT_FAULT_SEVERITY,
        status=FaultStatus.OPEN,
        reported_by_id=reported_by_id,
        reported_at=now,
        inspection_id=inspection_id,
        created_at=now,
        updated_at=now,
    )
