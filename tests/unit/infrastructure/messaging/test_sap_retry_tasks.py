"""Unit tests for SAP retry Celery task (thin orchestrator)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from infrastructure.messaging.tasks.sap_retry_tasks import retry_failed_sap_transactions


@pytest.mark.unit
def test_retry_failed_sap_transactions_calls_application_service() -> None:
    """Task resolves deps and calls the retry application service."""
    service = MagicMock()
    with patch(
        "interfaces.api.v1.deps.get_retry_failed_sap_transactions_service",
        return_value=service,
    ):
        result = retry_failed_sap_transactions.run(correlation_id="corr-retry-1")

    service.execute.assert_called_once_with(request_id="corr-retry-1")
    assert result["status"] == "ok"
    assert result["task_name"] == "retry_failed_sap_transactions"


@pytest.mark.unit
def test_retry_failed_sap_transactions_reraises_on_failure() -> None:
    """Task logs and re-raises service failures (no silent swallow)."""
    service = MagicMock()
    service.execute.side_effect = RuntimeError("SAP down")
    with (
        patch(
            "interfaces.api.v1.deps.get_retry_failed_sap_transactions_service",
            return_value=service,
        ),
        pytest.raises(RuntimeError, match="SAP down"),
    ):
        retry_failed_sap_transactions.run(correlation_id="corr-fail")
