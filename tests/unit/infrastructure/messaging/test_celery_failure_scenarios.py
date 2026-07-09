"""P0 — Celery task failure and observability scenarios."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from apps.preventive_maintenance.application.dto.pm_dto import PMWorkOrderResponseDTO
from apps.preventive_maintenance.application.services.trigger_overdue_pm_work_orders_service import (
    TriggerOverduePMWorkOrdersService,
)
from apps.preventive_maintenance.domain.entities import (
    PMPlan,
    PMPlanStatus,
    PMWorkOrderStatus,
)
from apps.preventive_maintenance.domain.exceptions import PMAlreadyTriggeredError
from apps.preventive_maintenance.domain.value_objects import (
    IntervalUnit,
    MaintenanceInterval,
    TriggerCondition,
    TriggerType,
)
from core.exceptions.base_exception import FMMSNotFoundError
from infrastructure.messaging.tasks.maintenance_tasks import (
    trigger_overdue_pm_work_orders,
)
from infrastructure.messaging.tasks.sap_retry_tasks import retry_failed_sap_transactions
from infrastructure.messaging.tasks.sap_sync_tasks import sync_equipment_from_sap


def _plan(next_due_at: datetime) -> PMPlan:
    now = datetime.now(tz=UTC)
    return PMPlan(
        id=uuid.uuid4(),
        vehicle_id=uuid.uuid4(),
        name="Service",
        description="Due",
        interval=MaintenanceInterval(value=30, unit=IntervalUnit.DAYS),
        trigger_condition=TriggerCondition(
            trigger_type=TriggerType.TIME_BASED, threshold=30
        ),
        status=PMPlanStatus.ACTIVE,
        created_by_id=uuid.uuid4(),
        created_at=now,
        updated_at=now,
        next_due_at=next_due_at,
    )


@pytest.mark.unit
class TestCeleryFailureScenarios:
    """Tasks re-raise failures and emit required structured log fields."""

    def test_retry_task_log_includes_required_fields(self) -> None:
        """Successful retry task logs domain/task_name/correlation_id."""
        service = MagicMock()
        captured: list[logging.LogRecord] = []

        class _ListHandler(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                captured.append(record)

        handler = _ListHandler(level=logging.INFO)
        root = logging.getLogger("fmms.integration")
        root.addHandler(handler)
        try:
            with patch(
                "interfaces.api.v1.deps.get_retry_failed_sap_transactions_service",
                return_value=service,
            ):
                retry_failed_sap_transactions.run(correlation_id="corr-log-1")
        finally:
            root.removeHandler(handler)

        assert any("SAP retry task" in r.getMessage() for r in captured)
        assert any(
            r.__dict__.get("task_name") == "retry_failed_sap_transactions"
            for r in captured
        )
        assert any(r.__dict__.get("correlation_id") == "corr-log-1" for r in captured)
        assert any("task_id" in r.__dict__ for r in captured)
        assert any(r.__dict__.get("domain") == "integration" for r in captured)
        service.execute.assert_called_once_with(request_id="corr-log-1")

    def test_sync_task_reraises_not_found(self) -> None:
        """Single-equipment sync propagates FMMSNotFoundError."""
        service = MagicMock()
        service.execute.side_effect = FMMSNotFoundError(
            message="No vehicle linked",
            details={"sap_equipment_number": "999"},
        )
        with (
            patch(
                "interfaces.api.v1.deps.get_sync_sap_equipment_service",
                return_value=service,
            ),
            pytest.raises(FMMSNotFoundError),
        ):
            sync_equipment_from_sap.run("999", correlation_id="corr-sync-nf")

    def test_overdue_task_reraises_service_failure(self) -> None:
        """Overdue PM task does not swallow top-level service failures."""
        service = MagicMock()
        service.execute.side_effect = RuntimeError("sweep boom")
        with (
            patch(
                "interfaces.api.v1.deps.get_trigger_overdue_pm_work_orders_service",
                return_value=service,
            ),
            pytest.raises(RuntimeError, match="sweep boom"),
        ):
            trigger_overdue_pm_work_orders.run(correlation_id="corr-pm-fail")

    def test_overdue_service_continues_after_one_plan_failure(self) -> None:
        """One plan conflict does not abort the remainder of the sweep."""
        due_a = _plan(datetime.now(tz=UTC) - timedelta(days=2))
        due_b = _plan(datetime.now(tz=UTC) - timedelta(days=1))
        plan_repo = MagicMock()
        plan_repo.list_active.return_value = [due_a, due_b]
        trigger = MagicMock()
        trigger.execute.side_effect = [
            PMAlreadyTriggeredError(due_a.id),
            PMWorkOrderResponseDTO(
                id=uuid.uuid4(),
                plan_id=due_b.id,
                vehicle_id=due_b.vehicle_id,
                status=PMWorkOrderStatus.TRIGGERED,
                scheduled_date=due_b.next_due_at or datetime.now(tz=UTC),
                created_at=datetime.now(tz=UTC),
                updated_at=datetime.now(tz=UTC),
            ),
        ]
        results = TriggerOverduePMWorkOrdersService(plan_repo, trigger).execute(
            request_id="corr-partial"
        )
        assert len(results) == 1
        assert trigger.execute.call_count == 2
