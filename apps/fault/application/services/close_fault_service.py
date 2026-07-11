"""Service that orchestrates closing of a fault.

When distribution marks a vehicle as usable, closing the fault also cancels
early-stage repair orders linked to that fault so a new inspection can start.

The domain entity's ``close()`` enforces the terminal-state rule.
This service loads, delegates, persists, and logs.
"""

from __future__ import annotations

from datetime import UTC, datetime

from apps.fault.application.dto.fault_dto import CloseFaultDTO, FaultResponseDTO
from apps.fault.application.services.report_fault_service import _to_response_dto
from apps.fault.domain.interfaces.fault_repository import IFaultRepository
from apps.repair.application.services._timeline_helper import record_repair_timeline_event
from apps.repair.application.services.repair_order_timeline_service import (
    RecordRepairOrderEventService,
)
from apps.repair.domain.entities import RepairOrderEventType, RepairOrderStatus
from apps.repair.domain.interfaces.repair_repository import IRepairOrderRepository
from core.exceptions.translation import load_or_not_found
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger("fault", __name__)

_DISTRIBUTION_USABLE_CANCEL_STATUSES: frozenset[RepairOrderStatus] = frozenset(
    {
        RepairOrderStatus.CREATED,
        RepairOrderStatus.APPROVED,
    }
)
_DISTRIBUTION_USABLE_EVENT_DESCRIPTION = (
    "توزیع: خودرو قابل استفاده — دستور تعمیر لغو شد."
)


class CloseFaultService:
    """Orchestrates closing of a fault record.

    When linked repair orders are still in ``CREATED`` or ``APPROVED`` status,
    they are cancelled as part of the distribution-usable decision so the
    vehicle can accept a new inspection flow.

    Args:
        fault_repository: Concrete ``IFaultRepository``.
        repair_order_repository: Concrete ``IRepairOrderRepository``.
        event_recorder: Optional timeline recorder for repair-order events.
    """

    def __init__(
        self,
        fault_repository: IFaultRepository,
        repair_order_repository: IRepairOrderRepository,
        event_recorder: RecordRepairOrderEventService | None = None,
    ) -> None:
        self._fault_repo = fault_repository
        self._repair_repo = repair_order_repository
        self._event_recorder = event_recorder

    def execute(self, dto: CloseFaultDTO) -> FaultResponseDTO:
        """Close the fault identified by ``dto.fault_id``.

        Delegates state-machine validation to ``Fault.close()``. Cancels related
        repair orders that have not yet entered active repair work.

        Args:
            dto: Close request.

        Returns:
            ``FaultResponseDTO`` with ``status == CLOSED``.

        Raises:
            FMMSNotFoundError: If no fault with ``dto.fault_id`` exists.
            FaultAlreadyClosedError: If already CLOSED (raised by the entity).
            FaultInvalidStateTransitionError: If transition is not permitted
                (raised by the entity).
            RepairOrderInvalidStateTransitionError: If a linked repair order
                cannot be cancelled (raised by the entity).
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

        fault = load_or_not_found(
            lambda: self._fault_repo.get_by_id(dto.fault_id),
            message=f"Fault '{dto.fault_id}' not found.",
            details={"fault_id": str(dto.fault_id)},
        )

        fault.close()
        fault.updated_at = datetime.now(tz=UTC)
        saved = self._fault_repo.save(fault)

        cancelled_count = self._cancel_distribution_usable_repair_orders(dto)

        logger.info(
            "Fault closed successfully",
            extra={
                "domain": "fault",
                "service": "CloseFaultService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(saved.id),
                "result": "success",
                "repairs_cancelled": cancelled_count,
            },
        )

        return _to_response_dto(saved)

    def _cancel_distribution_usable_repair_orders(self, dto: CloseFaultDTO) -> int:
        """Cancel early-stage repair orders after a distribution-usable decision."""
        cancelled_count = 0
        now = datetime.now(tz=UTC)

        for order in self._repair_repo.list_by_fault(dto.fault_id):
            if order.status not in _DISTRIBUTION_USABLE_CANCEL_STATUSES:
                continue

            order.cancel()
            order.updated_at = now
            self._repair_repo.save(order)
            record_repair_timeline_event(
                self._event_recorder,
                order.id,
                RepairOrderEventType.DISTRIBUTION_APPROVED_USABLE,
                _DISTRIBUTION_USABLE_EVENT_DESCRIPTION,
                created_by_id=dto.closed_by,
                request_id=dto.request_id,
            )
            cancelled_count += 1

        return cancelled_count
