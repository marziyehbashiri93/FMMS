"""Service that orchestrates inspection submission and automatic fault creation.

Multi-step workflow (designed for future transaction boundary addition):
  Step 1: Load and validate the inspection (must be DRAFT with ≥1 item).
  Step 2: Call ``inspection.submit()`` — transitions DRAFT → SUBMITTED.
  Step 3: For each FAIL checklist item, create a ``Fault`` entity and persist it.
  Step 4: Save the updated inspection.

Transaction boundary note:
    Steps 2–4 are logically atomic. The service method is written so that
    wrapping the body in ``django.db.transaction.atomic()`` at a later stage
    requires no rewrite of business logic — only a decorator or context manager
    around the call to ``execute()``.

Cross-domain:
    Fault creation happens here because it is a workflow policy ("failed
    inspection items become faults"), not a rule owned by Inspection or Fault
    entities.  Both repository ports are injected as abstractions.
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
from core.exceptions.base_exception import FMMSNotFoundError
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger("inspection", __name__)

_DEFAULT_FAULT_CODE = "INSP-FAIL"
_DEFAULT_FAULT_SEVERITY = FaultSeverity.MEDIUM


class SubmitInspectionService:
    """Orchestrates inspection submission and automatic fault generation.

    When an inspection is submitted, any checklist items with a FAIL result
    automatically produce a new ``Fault`` entity in OPEN status.  This
    workflow policy is owned by this service, not by either domain entity.

    Args:
        inspection_repository: Concrete ``IInspectionRepository``.
        fault_repository: Concrete ``IFaultRepository`` for auto-fault creation.
    """

    def __init__(
        self,
        inspection_repository: IInspectionRepository,
        fault_repository: IFaultRepository,
    ) -> None:
        self._inspection_repo = inspection_repository
        self._fault_repo = fault_repository

    def execute(self, dto: SubmitInspectionDTO) -> InspectionResponseDTO:
        """Submit a DRAFT inspection and auto-create faults for FAIL items.

        All mutations (inspection status update + fault creation) are designed
        to be wrapped in a single database transaction without logic changes.

        Args:
            dto: Submission request.

        Returns:
            ``InspectionResponseDTO`` with ``status == SUBMITTED``.

        Raises:
            FMMSNotFoundError: If no inspection with ``dto.inspection_id`` exists.
            InspectionItemRequiredError: If the inspection has no items
                (raised by ``Inspection.submit()``).
            InspectionInvalidStateTransitionError: If not in DRAFT status
                (raised by ``Inspection.submit()``).
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

        inspection = self._inspection_repo.get_by_id(dto.inspection_id)
        if inspection is None:
            raise FMMSNotFoundError(
                message=f"Inspection '{dto.inspection_id}' not found.",
                details={"inspection_id": str(dto.inspection_id)},
            )

        inspection.submit()
        now = datetime.now(tz=UTC)
        inspection.updated_at = now

        faults_created = 0
        for item in inspection.items:
            if item.result == ChecklistResult.FAIL:
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
