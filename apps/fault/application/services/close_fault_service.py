"""Service that orchestrates closing of a fault.

The domain entity's ``close()`` enforces the terminal-state rule.
This service loads, delegates, persists, and logs.
"""

from __future__ import annotations

from datetime import UTC, datetime

from apps.fault.application.dto.fault_dto import CloseFaultDTO, FaultResponseDTO
from apps.fault.application.services.report_fault_service import _to_response_dto
from apps.fault.domain.interfaces.fault_repository import IFaultRepository
from core.exceptions.base_exception import FMMSNotFoundError
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger("fault", __name__)


class CloseFaultService:
    """Orchestrates closing of a fault record.

    Args:
        fault_repository: Concrete ``IFaultRepository``.
    """

    def __init__(self, fault_repository: IFaultRepository) -> None:
        self._repo = fault_repository

    def execute(self, dto: CloseFaultDTO) -> FaultResponseDTO:
        """Close the fault identified by ``dto.fault_id``.

        Delegates state-machine validation to ``Fault.close()``.

        Args:
            dto: Close request.

        Returns:
            ``FaultResponseDTO`` with ``status == CLOSED``.

        Raises:
            FMMSNotFoundError: If no fault with ``dto.fault_id`` exists.
            FaultAlreadyClosedError: If already CLOSED (raised by the entity).
            FaultInvalidStateTransitionError: If transition is not permitted
                (raised by the entity).
        """
        logger.info(
            "Closing fault",
            extra={
                "domain": "fault",
                "service": "CloseFaultService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(dto.fault_id),
            },
        )

        fault = self._repo.get_by_id(dto.fault_id)
        if fault is None:
            raise FMMSNotFoundError(
                message=f"Fault '{dto.fault_id}' not found.",
                details={"fault_id": str(dto.fault_id)},
            )

        fault.close()
        fault.updated_at = datetime.now(tz=UTC)

        saved = self._repo.save(fault)

        logger.info(
            "Fault closed successfully",
            extra={
                "domain": "fault",
                "service": "CloseFaultService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(saved.id),
                "result": "success",
            },
        )

        return _to_response_dto(saved)
