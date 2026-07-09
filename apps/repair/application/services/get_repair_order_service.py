"""Read-only services for retrieving repair order data."""

from __future__ import annotations

import uuid

from apps.repair.application.dto.repair_dto import RepairOrderResponseDTO
from apps.repair.application.services.create_repair_order_service import (
    _to_response_dto,
)
from apps.repair.domain.entities import RepairOrderStatus
from apps.repair.domain.interfaces.repair_repository import IRepairOrderRepository
from core.exceptions.translation import load_or_not_found
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger("repair", __name__)


class GetRepairOrderService:
    """Fetch a single repair order by its UUID.

    Args:
        repair_order_repository: Concrete ``IRepairOrderRepository``.
    """

    def __init__(self, repair_order_repository: IRepairOrderRepository) -> None:
        self._repo = repair_order_repository

    def execute(
        self, repair_order_id: uuid.UUID, request_id: str = ""
    ) -> RepairOrderResponseDTO:
        """Return the repair order identified by ``repair_order_id``.

        Args:
            repair_order_id: Target repair order UUID.
            request_id: Optional correlation ID for structured logging.

        Returns:
            ``RepairOrderResponseDTO`` for the requested order.

        Raises:
            FMMSNotFoundError: If no order with ``repair_order_id`` exists.
        """
        logger.info(
            "Fetching repair order",
            extra={
                "domain": "repair",
                "service": "GetRepairOrderService",
                "operation": "execute",
                "request_id": request_id,
                "entity_id": str(repair_order_id),
            },
        )

        order = load_or_not_found(
            lambda: self._repo.get_by_id(repair_order_id),
            message=f"Repair order '{repair_order_id}' not found.",
            details={"repair_order_id": str(repair_order_id)},
        )

        logger.info(
            "Repair order fetched",
            extra={
                "domain": "repair",
                "service": "GetRepairOrderService",
                "operation": "execute",
                "request_id": request_id,
                "entity_id": str(repair_order_id),
                "result": "success",
            },
        )

        return _to_response_dto(order)


class ListRepairOrdersService:
    """Fetch repair orders for a vehicle, optionally filtered by status.

    Args:
        repair_order_repository: Concrete ``IRepairOrderRepository``.
    """

    def __init__(self, repair_order_repository: IRepairOrderRepository) -> None:
        self._repo = repair_order_repository

    def execute(
        self,
        vehicle_id: uuid.UUID,
        status: RepairOrderStatus | None = None,
        request_id: str = "",
    ) -> list[RepairOrderResponseDTO]:
        """Return repair orders for ``vehicle_id``, with optional status filter.

        Args:
            vehicle_id: Target vehicle UUID.
            status: Optional status filter.
            request_id: Optional correlation ID for structured logging.

        Returns:
            Ordered list of ``RepairOrderResponseDTO`` objects.
        """
        logger.info(
            "Listing repair orders",
            extra={
                "domain": "repair",
                "service": "ListRepairOrdersService",
                "operation": "execute",
                "request_id": request_id,
                "vehicle_id": str(vehicle_id),
                "status_filter": status.value if status else None,
            },
        )

        orders = self._repo.list_by_vehicle(vehicle_id=vehicle_id, status=status)

        logger.info(
            "Repair orders listed",
            extra={
                "domain": "repair",
                "service": "ListRepairOrdersService",
                "operation": "execute",
                "request_id": request_id,
                "result": "success",
                "count": len(orders),
            },
        )

        return [_to_response_dto(o) for o in orders]
