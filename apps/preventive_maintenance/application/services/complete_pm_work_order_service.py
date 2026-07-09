"""Service that completes a PM work order.

State transitions remain inside ``PMWorkOrder`` entity methods.
This service only orchestrates: load → start if needed → complete → save.
"""

from __future__ import annotations

from datetime import UTC, datetime

from apps.preventive_maintenance.application.dto.pm_dto import (
    CompletePMWorkOrderDTO,
    PMWorkOrderResponseDTO,
)
from apps.preventive_maintenance.application.services.trigger_pm_work_order_service import (
    _work_order_to_response_dto,
)
from apps.preventive_maintenance.domain.entities import PMWorkOrderStatus
from apps.preventive_maintenance.domain.interfaces.pm_repository import (
    IPMWorkOrderRepository,
)
from core.exceptions.base_exception import FMMSNotFoundError
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger("preventive_maintenance", __name__)


class CompletePMWorkOrderService:
    """Orchestrates completion of a PM work order.

    If the work order is TRIGGERED or OVERDUE, ``start()`` is called first so
    ``complete()`` can run — both are domain entity methods.

    Args:
        pm_work_order_repository: Concrete ``IPMWorkOrderRepository``.
    """

    def __init__(self, pm_work_order_repository: IPMWorkOrderRepository) -> None:
        self._wo_repo = pm_work_order_repository

    def execute(self, dto: CompletePMWorkOrderDTO) -> PMWorkOrderResponseDTO:
        """Complete the work order identified by ``dto.work_order_id``.

        Args:
            dto: Completion request.

        Returns:
            ``PMWorkOrderResponseDTO`` with ``status == COMPLETED``.

        Raises:
            FMMSNotFoundError: If the work order does not exist.
            PMInvalidStateTransitionError: If the entity rejects the transition.
        """
        logger.info(
            "Completing PM work order",
            extra={
                "domain": "preventive_maintenance",
                "service": "CompletePMWorkOrderService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(dto.work_order_id),
            },
        )

        work_order = self._wo_repo.get_by_id(dto.work_order_id)
        if work_order is None:
            raise FMMSNotFoundError(
                message=f"PM work order '{dto.work_order_id}' not found.",
                details={"work_order_id": str(dto.work_order_id)},
            )

        if work_order.status in {
            PMWorkOrderStatus.TRIGGERED,
            PMWorkOrderStatus.OVERDUE,
        }:
            work_order.start()

        work_order.complete(completed_at=dto.completed_at)
        if dto.notes is not None:
            work_order.notes = dto.notes
        work_order.updated_at = datetime.now(tz=UTC)

        saved = self._wo_repo.save(work_order)

        logger.info(
            "PM work order completed",
            extra={
                "domain": "preventive_maintenance",
                "service": "CompletePMWorkOrderService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(saved.id),
                "result": "success",
            },
        )

        return _work_order_to_response_dto(saved)
