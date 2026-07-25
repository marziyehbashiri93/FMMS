"""Service that orchestrates inspection submission.

Submitting a checklist only finalizes the inspection. Fault creation from failed
checklist items is intentionally handled by a separate explicit endpoint.
"""

from __future__ import annotations

from datetime import UTC, datetime

from apps.fault.domain.interfaces.fault_repository import IFaultRepository
from apps.inspection.application.dto.inspection_dto import (
    InspectionResponseDTO,
    SubmitInspectionDTO,
)
from apps.inspection.application.services.create_inspection_service import (
    _to_response_dto,
    assert_vehicle_is_operational_for_checklist,
)
from apps.inspection.domain.interfaces.inspection_repository import (
    IInspectionRepository,
)
from apps.repair.domain.interfaces.repair_repository import IRepairOrderRepository
from apps.vehicle.domain.interfaces.vehicle_repository import IVehicleRepository
from core.exceptions.translation import load_or_not_found
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger("inspection", __name__)


class SubmitInspectionService:
    """Orchestrates inspection submission.

    Args:
        inspection_repository: Concrete ``IInspectionRepository``.
        fault_repository: Kept for constructor compatibility; unused by submit.
        repair_order_repository: Kept for constructor compatibility; unused by submit.
        vehicle_repository: Used to ensure the vehicle is still operational.
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
        """Submit a DRAFT inspection without creating faults.

        Args:
            dto: Submission request.

        Returns:
            ``InspectionResponseDTO`` with ``status == SUBMITTED``.

        Raises:
            FMMSNotFoundError: If inspection does not exist.
            FMMSConflictError: If the vehicle is not operational (ACTIVE).
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
        assert_vehicle_is_operational_for_checklist(
            vehicle_id=inspection.vehicle_id,
            vehicle_repository=self._vehicle_repo,
        )

        inspection.submit()
        now = datetime.now(tz=UTC)
        inspection.updated_at = now
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
            },
        )

        return _to_response_dto(saved)
