"""Unit tests for RetryFailedSAPTransactionsService."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from apps.integration.application.services.retry_failed_sap_transactions_service import (
    RetryFailedSAPTransactionsService,
)
from apps.integration.domain.entities import SAPObjectType


@pytest.mark.unit
def test_retry_service_delegates_to_manager_with_adapter_map() -> None:
    """Service builds an adapter map and calls retry_all_pending."""
    manager = MagicMock()
    pr_port = MagicMock()
    order_port = MagicMock()
    notif_port = MagicMock()
    measurement_port = MagicMock()
    vehicle_assignment_port = MagicMock()

    RetryFailedSAPTransactionsService(
        manager,
        pr_port,
        order_port,
        notif_port,
        measurement_port,
        vehicle_assignment_port,
    ).execute(request_id="corr-1")

    manager.retry_all_pending.assert_called_once()
    adapter_map = manager.retry_all_pending.call_args.args[0]
    assert SAPObjectType.PURCHASE_REQUISITION in adapter_map
    assert SAPObjectType.REPAIR_ORDER in adapter_map
    assert SAPObjectType.PM_WORK_ORDER in adapter_map
    assert SAPObjectType.FAULT in adapter_map
    assert SAPObjectType.MEASUREMENT_DOCUMENT in adapter_map
    assert SAPObjectType.VEHICLE_ASSIGNMENT in adapter_map
