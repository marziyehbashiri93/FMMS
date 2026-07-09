"""Read-only services for retrieving PM plan and work order data."""

from __future__ import annotations

import uuid

from apps.preventive_maintenance.application.dto.pm_dto import (
    PMPlanResponseDTO,
    PMWorkOrderResponseDTO,
)
from apps.preventive_maintenance.application.services.create_pm_plan_service import (
    _plan_to_response_dto,
)
from apps.preventive_maintenance.application.services.trigger_pm_work_order_service import (
    _work_order_to_response_dto,
)
from apps.preventive_maintenance.domain.entities import PMPlanStatus, PMWorkOrderStatus
from apps.preventive_maintenance.domain.interfaces.pm_repository import (
    IPMPlanRepository,
    IPMWorkOrderRepository,
)
from core.exceptions.translation import load_or_not_found
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger("preventive_maintenance", __name__)


class GetPMPlanService:
    """Fetch a single PM plan by UUID.

    Args:
        pm_plan_repository: Concrete ``IPMPlanRepository``.
    """

    def __init__(self, pm_plan_repository: IPMPlanRepository) -> None:
        self._repo = pm_plan_repository

    def execute(self, plan_id: uuid.UUID, request_id: str = "") -> PMPlanResponseDTO:
        """Return the PM plan identified by ``plan_id``.

        Args:
            plan_id: Target plan UUID.
            request_id: Optional correlation ID.

        Returns:
            ``PMPlanResponseDTO``.

        Raises:
            FMMSNotFoundError: If the plan does not exist.
        """
        logger.info(
            "Fetching PM plan",
            extra={
                "domain": "preventive_maintenance",
                "service": "GetPMPlanService",
                "operation": "execute",
                "request_id": request_id,
                "entity_id": str(plan_id),
            },
        )

        plan = load_or_not_found(
            lambda: self._repo.get_by_id(plan_id),
            message=f"PM plan '{plan_id}' not found.",
            details={"plan_id": str(plan_id)},
        )

        logger.info(
            "PM plan fetched",
            extra={
                "domain": "preventive_maintenance",
                "service": "GetPMPlanService",
                "operation": "execute",
                "request_id": request_id,
                "entity_id": str(plan_id),
                "result": "success",
            },
        )

        return _plan_to_response_dto(plan)


class ListPMPlansService:
    """List PM plans for a vehicle, optionally filtered by status.

    Args:
        pm_plan_repository: Concrete ``IPMPlanRepository``.
    """

    def __init__(self, pm_plan_repository: IPMPlanRepository) -> None:
        self._repo = pm_plan_repository

    def execute(
        self,
        vehicle_id: uuid.UUID,
        status: PMPlanStatus | None = None,
        request_id: str = "",
    ) -> list[PMPlanResponseDTO]:
        """Return plans for ``vehicle_id``.

        Args:
            vehicle_id: Target vehicle UUID.
            status: Optional status filter.
            request_id: Optional correlation ID.

        Returns:
            List of ``PMPlanResponseDTO``.
        """
        logger.info(
            "Listing PM plans",
            extra={
                "domain": "preventive_maintenance",
                "service": "ListPMPlansService",
                "operation": "execute",
                "request_id": request_id,
                "vehicle_id": str(vehicle_id),
                "status_filter": status.value if status else None,
            },
        )

        plans = self._repo.list_by_vehicle(vehicle_id=vehicle_id, status=status)

        logger.info(
            "PM plans listed",
            extra={
                "domain": "preventive_maintenance",
                "service": "ListPMPlansService",
                "operation": "execute",
                "request_id": request_id,
                "result": "success",
                "count": len(plans),
            },
        )

        return [_plan_to_response_dto(p) for p in plans]


class ListPMWorkOrdersService:
    """List PM work orders for a plan, optionally filtered by status.

    Args:
        pm_work_order_repository: Concrete ``IPMWorkOrderRepository``.
    """

    def __init__(self, pm_work_order_repository: IPMWorkOrderRepository) -> None:
        self._repo = pm_work_order_repository

    def execute(
        self,
        plan_id: uuid.UUID,
        status: PMWorkOrderStatus | None = None,
        request_id: str = "",
    ) -> list[PMWorkOrderResponseDTO]:
        """Return work orders for ``plan_id``.

        Args:
            plan_id: Parent plan UUID.
            status: Optional status filter.
            request_id: Optional correlation ID.

        Returns:
            List of ``PMWorkOrderResponseDTO``.
        """
        logger.info(
            "Listing PM work orders",
            extra={
                "domain": "preventive_maintenance",
                "service": "ListPMWorkOrdersService",
                "operation": "execute",
                "request_id": request_id,
                "plan_id": str(plan_id),
                "status_filter": status.value if status else None,
            },
        )

        work_orders = self._repo.list_by_plan(plan_id=plan_id, status=status)

        logger.info(
            "PM work orders listed",
            extra={
                "domain": "preventive_maintenance",
                "service": "ListPMWorkOrdersService",
                "operation": "execute",
                "request_id": request_id,
                "result": "success",
                "count": len(work_orders),
            },
        )

        return [_work_order_to_response_dto(wo) for wo in work_orders]
