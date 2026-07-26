"""Unit tests for bulk vehicle SAP sync Celery task."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from apps.integration.application.services.run_sap_sync_service import (
    RunSAPSyncResultDTO,
    SAPSyncItemResultDTO,
)
from infrastructure.messaging.tasks.sap_sync_tasks import sync_vehicles_from_sap


@pytest.mark.unit
def test_sync_vehicles_from_sap_calls_application_service() -> None:
    """Task forwards to the global SAP read sync service."""
    service = MagicMock()
    now = datetime.now(tz=UTC)
    service.execute.return_value = RunSAPSyncResultDTO(
        id="sync-run-1",
        trigger_source="CELERY",
        status="SUCCESS",
        started_at=now,
        finished_at=now,
        items=[
            SAPSyncItemResultDTO(
                name="vehicles",
                status="SUCCESS",
                started_at=now,
                finished_at=now,
                summary={"total_received": 2},
            )
        ],
    )
    with patch(
        "interfaces.api.v1.deps.get_run_sap_sync_service",
        return_value=service,
    ):
        result = sync_vehicles_from_sap.run(correlation_id="corr-sync-1")

    service.execute.assert_called_once_with(
        request_id="corr-sync-1",
        trigger_source="CELERY",
    )
    assert result["status"] == "ok"
    assert result["task_name"] == "sync_vehicles_from_sap"
    assert result["sync_run_id"] == "sync-run-1"
    assert result["sync_status"] == "SUCCESS"
    assert result["items"] == ["vehicles"]


@pytest.mark.unit
def test_sync_vehicles_from_sap_reraises_on_failure() -> None:
    """Task does not swallow bulk sync failures."""
    service = MagicMock()
    service.execute.side_effect = RuntimeError("SAP unavailable")
    with (
        patch(
            "interfaces.api.v1.deps.get_run_sap_sync_service",
            return_value=service,
        ),
        pytest.raises(RuntimeError, match="SAP unavailable"),
    ):
        sync_vehicles_from_sap.run(correlation_id="corr-sync-fail")
