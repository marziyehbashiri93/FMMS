"""Service that orchestrates fault assignment to a technician.

The domain entity's ``assign()`` enforces the state-machine rule
(only OPEN faults may be assigned). This service loads, delegates,
persists, and logs.
"""

from __future__ import annotations

from datetime import UTC, datetime

from apps.fault.application.dto.fault_dto import AssignFaultDTO, FaultResponseDTO
from apps.fault.application.services.report_fault_service import _to_response_dto
from apps.fault.domain.interfaces.fault_repository import IFaultRepository
from core.exceptions.translation import load_or_not_found
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger("fault", __name__)


class AssignFaultService:
    """Orchestrates assignment of a fault to a technician.

    Args:
        fault_repository: Concrete ``IFaultRepository``.
    """

    def __init__(self, fault_repository: IFaultRepository) -> None:
        self._repo = fault_repository

    def execute(self, dto: AssignFaultDTO) -> FaultResponseDTO:
        """Assign the fault to the specified technician.

        Delegates state-machine validation to ``Fault.assign()``.

        Args:
            dto: Assignment request.

        Returns:
            ``FaultResponseDTO`` with ``status == ASSIGNED``.

        Raises:
            FMMSNotFoundError: If no fault with ``dto.fault_id`` exists.
            FaultInvalidStateTransitionError: If the fault is not in OPEN status
                (raised by the domain entity).
            FaultAlreadyClosedError: If the fault is already CLOSED
                (raised by the domain entity).
        """
        logger.info(
            "Assigning fault",
            extra={
                "domain": "fault",
                "service": "AssignFaultService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(dto.fault_id),
                "technician_id": str(dto.technician_id),
            },
        )

        fault = load_or_not_found(
            lambda: self._repo.get_by_id(dto.fault_id),
            message=f"Fault '{dto.fault_id}' not found.",
            details={"fault_id": str(dto.fault_id)},
        )

        fault.assign(dto.technician_id)
        fault.updated_at = datetime.now(tz=UTC)

        saved = self._repo.save(fault)

        logger.info(
            "Fault assigned successfully",
            extra={
                "domain": "fault",
                "service": "AssignFaultService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(saved.id),
                "result": "success",
            },
        )

        return _to_response_dto(saved)
