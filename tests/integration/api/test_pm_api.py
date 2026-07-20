"""API integration tests for preventive maintenance endpoints."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from rest_framework.test import APIClient

from tests.integration.api.conftest import create_vehicle

pytestmark = pytest.mark.django_db


class TestPMAPI:
    """Cover PM plan trigger and work-order completion."""

    def test_create_plan_trigger_complete(
        self, authenticated_client: APIClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Create a PM plan, trigger a work order, and complete it."""
        monkeypatch.setenv("SAP_USE_MOCK", "True")

        vehicle = create_vehicle(
            authenticated_client, plate="12PM0001", vin="1HGCM82633A004357"
        )
        plan = authenticated_client.post(
            "/api/v1/pm-plans/",
            {
                "vehicle_id": vehicle["id"],
                "name": "Oil Change",
                "description": "Periodic oil change",
                "interval_value": 90,
                "interval_unit": "DAYS",
                "trigger_type": "TIME_BASED",
                "trigger_threshold": 90,
            },
            format="json",
        )
        assert plan.status_code == 201, plan.data
        plan_id = plan.data["id"]

        triggered = authenticated_client.post(
            f"/api/v1/pm-plans/{plan_id}/trigger/",
            {
                "scheduled_date": (
                    datetime.now(tz=UTC) + timedelta(days=1)
                ).isoformat(),
                "create_sap_notification": False,
            },
            format="json",
        )
        assert triggered.status_code == 201, triggered.data
        work_order_id = triggered.data["id"]

        listed = authenticated_client.get(f"/api/v1/pm-work-orders/?plan_id={plan_id}")
        assert listed.status_code == 200
        assert listed.data["count"] >= 1

        completed = authenticated_client.post(
            f"/api/v1/pm-work-orders/{work_order_id}/complete/",
            {
                "completed_at": datetime.now(tz=UTC).isoformat(),
                "notes": "Completed on schedule",
            },
            format="json",
        )
        assert completed.status_code == 200, completed.data
        assert completed.data["status"] == "COMPLETED"
