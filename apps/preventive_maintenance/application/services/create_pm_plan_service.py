"""Service that orchestrates creation of a preventive maintenance plan.

Cross-domain check: vehicle must exist (IVehicleRepository).
Interval and trigger validation belong to domain value objects.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from apps.preventive_maintenance.application.dto.pm_dto import (
    CreatePMPlanDTO,
    PMPlanResponseDTO,
)
from apps.preventive_maintenance.domain.entities import PMPlan, PMPlanStatus
from apps.preventive_maintenance.domain.interfaces.pm_repository import (
    IPMPlanRepository,
)
from apps.preventive_maintenance.domain.value_objects import (
    MaintenanceInterval,
    TriggerCondition,
)
from apps.vehicle.domain.interfaces.vehicle_repository import IVehicleRepository
from core.exceptions.translation import load_or_not_found
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger("preventive_maintenance", __name__)


def _plan_to_response_dto(plan: PMPlan) -> PMPlanResponseDTO:
    """Map ``PMPlan`` domain entity → ``PMPlanResponseDTO``."""
    return PMPlanResponseDTO(
        id=plan.id,
        vehicle_id=plan.vehicle_id,
        name=plan.name,
        description=plan.description,
        interval_value=plan.interval.value,
        interval_unit=plan.interval.unit,
        trigger_type=plan.trigger_condition.trigger_type,
        trigger_threshold=plan.trigger_condition.threshold,
        status=plan.status,
        created_by_id=plan.created_by_id,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
        last_triggered_at=plan.last_triggered_at,
        next_due_at=plan.next_due_at,
    )


class CreatePMPlanService:
    """Orchestrates creation of a new ACTIVE PM plan.

    Args:
        pm_plan_repository: Concrete ``IPMPlanRepository``.
        vehicle_repository: Concrete ``IVehicleRepository`` for existence check.
    """

    def __init__(
        self,
        pm_plan_repository: IPMPlanRepository,
        vehicle_repository: IVehicleRepository,
    ) -> None:
        self._plan_repo = pm_plan_repository
        self._vehicle_repo = vehicle_repository

    def execute(self, dto: CreatePMPlanDTO) -> PMPlanResponseDTO:
        """Create and persist a new ACTIVE PM plan.

        Args:
            dto: Input data for the plan.

        Returns:
            ``PMPlanResponseDTO`` in ACTIVE status.

        Raises:
            FMMSNotFoundError: If no vehicle with ``dto.vehicle_id`` exists.
            ValueError: If interval or trigger value objects reject the input.
        """
        logger.info(
            "Creating PM plan",
            extra={
                "domain": "preventive_maintenance",
                "service": "CreatePMPlanService",
                "operation": "execute",
                "request_id": dto.request_id,
                "vehicle_id": str(dto.vehicle_id),
            },
        )

        load_or_not_found(
            lambda: self._vehicle_repo.get_by_id(dto.vehicle_id),
            message=f"Vehicle '{dto.vehicle_id}' not found.",
            details={"vehicle_id": str(dto.vehicle_id)},
        )

        now = datetime.now(tz=UTC)
        plan = PMPlan(
            id=uuid.uuid4(),
            vehicle_id=dto.vehicle_id,
            name=dto.name,
            description=dto.description,
            interval=MaintenanceInterval(
                value=dto.interval_value, unit=dto.interval_unit
            ),
            trigger_condition=TriggerCondition(
                trigger_type=dto.trigger_type, threshold=dto.trigger_threshold
            ),
            status=PMPlanStatus.ACTIVE,
            created_by_id=dto.created_by,
            created_at=now,
            updated_at=now,
        )

        saved = self._plan_repo.save(plan)

        logger.info(
            "PM plan created successfully",
            extra={
                "domain": "preventive_maintenance",
                "service": "CreatePMPlanService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(saved.id),
                "result": "success",
            },
        )

        return _plan_to_response_dto(saved)
