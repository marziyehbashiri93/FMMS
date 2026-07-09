"""Service that orchestrates technician assignment to a repair order.

The domain entity's ``assign_technician()`` enforces:
- Order must be in a mutable state.
- State transitions: CREATED → ASSIGNED.

This service only loads, delegates, persists, and logs.
"""

from __future__ import annotations

from datetime import UTC, datetime

from apps.repair.application.dto.repair_dto import (
    AssignRepairOrderDTO,
    RepairOrderResponseDTO,
)
from apps.repair.application.services.create_repair_order_service import (
    _to_response_dto,
)
from apps.repair.domain.interfaces.repair_repository import IRepairOrderRepository
from apps.repair.domain.value_objects import TechnicianAssignment
from core.exceptions.translation import load_or_not_found
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger("repair", __name__)


class AssignRepairOrderService:
    """Orchestrates assignment of a technician to a repair order.

    Args:
        repair_order_repository: Concrete ``IRepairOrderRepository``.
    """

    def __init__(self, repair_order_repository: IRepairOrderRepository) -> None:
        self._repo = repair_order_repository

    def execute(self, dto: AssignRepairOrderDTO) -> RepairOrderResponseDTO:
        """Assign a technician to the repair order.

        Delegates all state-machine validation to ``RepairOrder.assign_technician()``.

        Args:
            dto: Assignment request.

        Returns:
            ``RepairOrderResponseDTO`` with ``status == ASSIGNED``.

        Raises:
            FMMSNotFoundError: If no repair order with ``dto.repair_order_id`` exists.
            RepairOrderInvalidStateTransitionError: If not in CREATED status
                (raised by the domain entity).
        """
        logger.info(
            "Assigning technician to repair order",
            extra={
                "domain": "repair",
                "service": "AssignRepairOrderService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(dto.repair_order_id),
                "technician_id": str(dto.technician_id),
            },
        )

        order = load_or_not_found(
            lambda: self._repo.get_by_id(dto.repair_order_id),
            message=f"Repair order '{dto.repair_order_id}' not found.",
            details={"repair_order_id": str(dto.repair_order_id)},
        )

        now = datetime.now(tz=UTC)
        assignment = TechnicianAssignment(
            technician_id=dto.technician_id,
            assigned_at=now,
        )
        order.assign_technician(assignment)
        order.updated_at = now

        saved = self._repo.save(order)

        logger.info(
            "Repair order assigned successfully",
            extra={
                "domain": "repair",
                "service": "AssignRepairOrderService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(saved.id),
                "result": "success",
            },
        )

        return _to_response_dto(saved)
