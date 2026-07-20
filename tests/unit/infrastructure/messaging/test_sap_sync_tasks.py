"""Unit tests for single-equipment SAP sync Celery task."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from infrastructure.messaging.tasks.sap_sync_tasks import sync_equipment_from_sap


@pytest.mark.unit
def test_sync_equipment_from_sap_calls_application_service() -> None:
    """Task forwards a single equipment number to SyncSAPEquipmentService."""
    service = MagicMock()
    with patch(
        "interfaces.api.v1.deps.get_sync_sap_equipment_service", return_value=service
    ):
        result = sync_equipment_from_sap.run(
            "10000123",
            correlation_id="corr-sync-1",
        )

    service.execute.assert_called_once_with("10000123", request_id="corr-sync-1")
    assert result["status"] == "ok"
    assert result["vehicle_number"] == "10000123"


@pytest.mark.unit
def test_sync_equipment_from_sap_reraises_on_failure() -> None:
    """Task does not swallow application failures."""
    service = MagicMock()
    service.execute.side_effect = RuntimeError("equipment missing")
    with (
        patch(
            "interfaces.api.v1.deps.get_sync_sap_equipment_service",
            return_value=service,
        ),
        pytest.raises(RuntimeError, match="equipment missing"),
    ):
        sync_equipment_from_sap.run("999", correlation_id="corr-sync-fail")
