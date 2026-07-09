"""Service that triggers PM work orders for overdue active plans.

Selects ACTIVE plans whose ``next_due_at`` is due, then delegates each
trigger to ``TriggerPMWorkOrderService``. Contains no Celery or ORM usage.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from apps.preventive_maintenance.application.dto.pm_dto import (
    PMWorkOrderResponseDTO,
    TriggerPMWorkOrderDTO,
)
from apps.preventive_maintenance.application.services.trigger_pm_work_order_service import (
    TriggerPMWorkOrderService,
)
from apps.preventive_maintenance.domain.interfaces.pm_repository import (
    IPMPlanRepository,
)
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger("preventive_maintenance", __name__)

#: Stable system actor used when background jobs trigger PM work orders.
SYSTEM_ACTOR_ID = uuid.UUID("00000000-0000-4000-8000-000000000001")


class TriggerOverduePMWorkOrdersService:
    """Trigger work orders for ACTIVE plans that are past ``next_due_at``.

    Args:
        pm_plan_repository: Plan repository (port).
        trigger_pm_work_order_service: Existing single-plan trigger service.
    """

    def __init__(
        self,
        pm_plan_repository: IPMPlanRepository,
        trigger_pm_work_order_service: TriggerPMWorkOrderService,
    ) -> None:
        self._plan_repo = pm_plan_repository
        self._trigger = trigger_pm_work_order_service

    def execute(
        self,
        *,
        request_id: str = "",
        triggered_by: uuid.UUID | None = None,
        create_sap_notification: bool = False,
    ) -> list[PMWorkOrderResponseDTO]:
        """Trigger overdue plans and return created work orders.

        Args:
            request_id: Correlation id for structured logging.
            triggered_by: Actor UUID; defaults to the system actor.
            create_sap_notification: Whether to create SAP notifications.

        Returns:
            List of triggered work-order response DTOs.
        """
        now = datetime.now(tz=UTC)
        actor = triggered_by or SYSTEM_ACTOR_ID
        logger.info(
            "Triggering overdue PM work orders",
            extra={
                "domain": "preventive_maintenance",
                "service": "TriggerOverduePMWorkOrdersService",
                "operation": "execute",
                "request_id": request_id,
            },
        )

        results: list[PMWorkOrderResponseDTO] = []
        for plan in self._plan_repo.list_active():
            if plan.next_due_at is None or plan.next_due_at > now:
                continue
            try:
                result = self._trigger.execute(
                    TriggerPMWorkOrderDTO(
                        plan_id=plan.id,
                        scheduled_date=plan.next_due_at,
                        request_id=request_id,
                        triggered_by=actor,
                        create_sap_notification=create_sap_notification,
                    )
                )
            except Exception as exc:
                logger.exception(
                    "Failed to trigger overdue PM plan; continuing sweep",
                    extra={
                        "domain": "preventive_maintenance",
                        "service": "TriggerOverduePMWorkOrdersService",
                        "operation": "execute",
                        "request_id": request_id,
                        "entity_id": str(plan.id),
                        "error": str(exc),
                    },
                )
                continue
            results.append(result)

        logger.info(
            "Overdue PM trigger sweep completed",
            extra={
                "domain": "preventive_maintenance",
                "service": "TriggerOverduePMWorkOrdersService",
                "operation": "execute",
                "request_id": request_id,
                "result": "success",
                "count": len(results),
            },
        )
        return results
