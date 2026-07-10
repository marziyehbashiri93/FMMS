"""Services for transport-supervisor repair approval and workshop selection."""

from __future__ import annotations

from datetime import UTC, datetime

from apps.repair.application.dto.repair_dto import (
    ApproveRepairOrderDTO,
    AssignWorkshopDTO,
    RepairDecisionResponseDTO,
)
from apps.repair.domain.interfaces.repair_repository import IRepairOrderRepository
from core.exceptions.translation import load_or_not_found
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger("repair", __name__)

_APPROVE_MESSAGE = "دستور تعمیر توسط واحد ترابری تأیید شد."
_WORKSHOP_MESSAGE = "نوع تعمیرگاه با موفقیت انتخاب شد."


class ApproveRepairOrderService:
    """Approve a CREATED repair order (transport supervisor decision).

    Args:
        repair_order_repository: Concrete ``IRepairOrderRepository``.
    """

    def __init__(self, repair_order_repository: IRepairOrderRepository) -> None:
        self._repo = repair_order_repository

    def execute(self, dto: ApproveRepairOrderDTO) -> RepairDecisionResponseDTO:
        """Transition a repair order from CREATED to APPROVED.

        Args:
            dto: Approval request.

        Returns:
            Compact decision response with Persian confirmation message.

        Raises:
            FMMSNotFoundError: If the repair order does not exist.
            RepairOrderInvalidStateTransitionError: If not in CREATED status.
        """
        logger.info(
            "Approving repair order",
            extra={
                "domain": "repair",
                "service": "ApproveRepairOrderService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(dto.repair_order_id),
                "approved_by": str(dto.approved_by),
            },
        )

        order = load_or_not_found(
            lambda: self._repo.get_by_id(dto.repair_order_id),
            message=f"Repair order '{dto.repair_order_id}' not found.",
            details={"repair_order_id": str(dto.repair_order_id)},
        )
        order.approve()
        order.updated_at = datetime.now(tz=UTC)
        saved = self._repo.save(order)

        logger.info(
            "Repair order approved",
            extra={
                "domain": "repair",
                "service": "ApproveRepairOrderService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(saved.id),
                "result": "success",
            },
        )
        return RepairDecisionResponseDTO(
            id=saved.id,
            status=saved.status,
            message=_APPROVE_MESSAGE,
            workshop_type=saved.workshop_type,
        )


class AssignWorkshopService:
    """Assign INTERNAL/EXTERNAL workshop after transport approval.

    Args:
        repair_order_repository: Concrete ``IRepairOrderRepository``.
    """

    def __init__(self, repair_order_repository: IRepairOrderRepository) -> None:
        self._repo = repair_order_repository

    def execute(self, dto: AssignWorkshopDTO) -> RepairDecisionResponseDTO:
        """Transition APPROVED → WORKSHOP_ASSIGNED and store workshop type.

        Args:
            dto: Workshop assignment request.

        Returns:
            Compact decision response with Persian confirmation message.

        Raises:
            FMMSNotFoundError: If the repair order does not exist.
            RepairOrderInvalidStateTransitionError: If not in APPROVED status.
        """
        logger.info(
            "Assigning workshop to repair order",
            extra={
                "domain": "repair",
                "service": "AssignWorkshopService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(dto.repair_order_id),
                "workshop_type": dto.workshop_type.value,
                "assigned_by": str(dto.assigned_by),
            },
        )

        order = load_or_not_found(
            lambda: self._repo.get_by_id(dto.repair_order_id),
            message=f"Repair order '{dto.repair_order_id}' not found.",
            details={"repair_order_id": str(dto.repair_order_id)},
        )
        order.assign_workshop(dto.workshop_type)
        order.updated_at = datetime.now(tz=UTC)
        saved = self._repo.save(order)

        logger.info(
            "Workshop assigned to repair order",
            extra={
                "domain": "repair",
                "service": "AssignWorkshopService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(saved.id),
                "result": "success",
                "workshop_type": (
                    saved.workshop_type.value if saved.workshop_type else None
                ),
            },
        )
        return RepairDecisionResponseDTO(
            id=saved.id,
            status=saved.status,
            message=_WORKSHOP_MESSAGE,
            workshop_type=saved.workshop_type,
        )
