"""API integration tests for repair order endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from rest_framework.test import APIClient

from tests.integration.api.conftest import create_vehicle

pytestmark = pytest.mark.django_db


class TestRepairAPI:
    """Cover repair order lifecycle endpoints."""

    def test_repair_lifecycle(self, authenticated_client: APIClient) -> None:
        """Create, assign, start, and complete a repair order."""
        vehicle = create_vehicle(
            authenticated_client,
            plate="12REP001",
            vin="1HGCM82633A004356",
            sap_equipment_number="100001",
        )
        fault = authenticated_client.post(
            "/api/v1/faults/",
            {
                "vehicle_id": vehicle["id"],
                "code": "ENG-01",
                "description": "Engine noise",
                "severity": "HIGH",
            },
            format="json",
        )
        assert fault.status_code == 201, fault.data

        created = authenticated_client.post(
            "/api/v1/repair-orders/",
            {"vehicle_id": vehicle["id"], "fault_id": fault.data["id"]},
            format="json",
        )
        assert created.status_code == 201, created.data
        order_id = created.data["id"]
        assert created.data["status"] == "CREATED"

        technician_id = str(uuid4())
        assigned = authenticated_client.post(
            f"/api/v1/repair-orders/{order_id}/assign/",
            {"technician_id": technician_id},
            format="json",
        )
        assert assigned.status_code == 200, assigned.data
        assert assigned.data["status"] == "ASSIGNED"

        started = authenticated_client.post(
            f"/api/v1/repair-orders/{order_id}/start/",
            {},
            format="json",
        )
        assert started.status_code == 200, started.data
        assert started.data["status"] == "IN_PROGRESS"

        with_activity = authenticated_client.post(
            f"/api/v1/repair-orders/{order_id}/activities/",
            {
                "description": "Inspected engine bay",
                "labor_hours": "1.50",
                "performed_by_id": technician_id,
                "performed_at": datetime.now(tz=UTC).isoformat(),
            },
            format="json",
        )
        assert with_activity.status_code == 200, with_activity.data
        assert len(with_activity.data["activities"]) == 1

        with_part = authenticated_client.post(
            f"/api/v1/repair-orders/{order_id}/parts/",
            {
                "material_number": "4000001",
                "quantity": 2,
                "unit_of_measure": "EA",
            },
            format="json",
        )
        assert with_part.status_code == 200, with_part.data
        assert len(with_part.data["parts"]) == 1

        completed = authenticated_client.post(
            f"/api/v1/repair-orders/{order_id}/complete/",
            {"completed_at": datetime.now(tz=UTC).isoformat()},
            format="json",
        )
        assert completed.status_code == 200, completed.data
        assert completed.data["status"] == "WAITING_DRIVER_CONFIRMATION"

        listed = authenticated_client.get(
            f"/api/v1/repair-orders/?vehicle_id={vehicle['id']}"
        )
        assert listed.status_code == 200
        assert listed.data["count"] >= 1
