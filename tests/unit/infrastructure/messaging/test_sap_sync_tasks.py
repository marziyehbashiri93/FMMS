"""Unit tests for bulk vehicle SAP sync Celery task."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from apps.vehicle.application.dto.vehicle_dto import VehicleSAPSyncResultDTO
from infrastructure.messaging.tasks.sap_sync_tasks import sync_vehicles_from_sap


@pytest.mark.unit
def test_sync_vehicles_from_sap_calls_application_service() -> None:
    """Task forwards to the bulk vehicle SAP sync service."""
    service = MagicMock()
    service.execute.return_value = VehicleSAPSyncResultDTO(
        total_received=2,
        created=1,
        updated=1,
        decommissioned=0,
        failed=0,
    )
    with patch(
        "interfaces.api.v1.deps.get_sync_vehicles_from_sap_service",
        return_value=service,
    ):
        result = sync_vehicles_from_sap.run(correlation_id="corr-sync-1")

    service.execute.assert_called_once_with(request_id="corr-sync-1")
    assert result["status"] == "ok"
    assert result["task_name"] == "sync_vehicles_from_sap"
    assert result["total_received"] == 2


@pytest.mark.unit
def test_sync_vehicles_from_sap_reraises_on_failure() -> None:
    """Task does not swallow bulk sync failures."""
    service = MagicMock()
    service.execute.side_effect = RuntimeError("SAP unavailable")
    with (
        patch(
            "interfaces.api.v1.deps.get_sync_vehicles_from_sap_service",
            return_value=service,
        ),
        pytest.raises(RuntimeError, match="SAP unavailable"),
    ):
        sync_vehicles_from_sap.run(correlation_id="corr-sync-fail")
