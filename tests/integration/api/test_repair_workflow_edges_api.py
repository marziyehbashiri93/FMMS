"""P1 — Repair workflow edge cases through the API (and defect locks)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from rest_framework.test import APIClient

from tests.integration.api.conftest import create_vehicle

pytestmark = pytest.mark.django_db


def _create_order(client: APIClient, *, plate: str, vin: str) -> tuple[dict, str]:
    """Create a vehicle+fault+repair order; return (vehicle, order_id)."""
    vehicle = create_vehicle(client, plate=plate, vin=vin, vehicle_number="100010")
    fault = client.post(
        "/api/v1/faults/",
        {
            "vehicle_id": vehicle["id"],
            "code": "WF-01",
            "description": "Workflow edge",
            "severity": "MEDIUM",
        },
        format="json",
    )
    assert fault.status_code == 201, fault.data
    created = client.post(
        "/api/v1/repair-orders/",
        {"vehicle_id": vehicle["id"], "fault_id": fault.data["id"]},
        format="json",
    )
    assert created.status_code == 201, created.data
    return vehicle, created.data["id"]


class TestRepairWorkflowEdges:
    """Cancel and illegal-transition edges after DEFECT-M9-02 fix."""

    def test_cancel_from_created(self, authenticated_client: APIClient) -> None:
        """CREATED orders may be cancelled."""
        _, order_id = _create_order(
            authenticated_client, plate="12WF0001", vin="1HGCM82633A004380"
        )
        cancelled = authenticated_client.post(
            f"/api/v1/repair-orders/{order_id}/cancel/",
            {},
            format="json",
        )
        assert cancelled.status_code == 200, cancelled.data
        assert cancelled.data["status"] == "CANCELLED"

    def test_cancel_from_assigned(self, authenticated_client: APIClient) -> None:
        """ASSIGNED orders may be cancelled."""
        _, order_id = _create_order(
            authenticated_client, plate="12WF0002", vin="1HGCM82633A004381"
        )
        assigned = authenticated_client.post(
            f"/api/v1/repair-orders/{order_id}/assign/",
            {"technician_id": str(uuid4())},
            format="json",
        )
        assert assigned.status_code == 200, assigned.data
        cancelled = authenticated_client.post(
            f"/api/v1/repair-orders/{order_id}/cancel/",
            {},
            format="json",
        )
        assert cancelled.status_code == 200, cancelled.data
        assert cancelled.data["status"] == "CANCELLED"

    def test_complete_from_created_maps_to_422(
        self, authenticated_client: APIClient
    ) -> None:
        """Illegal complete from CREATED returns DomainStateError → 422."""
        _, order_id = _create_order(
            authenticated_client, plate="12WF0003", vin="1HGCM82633A004382"
        )
        response = authenticated_client.post(
            f"/api/v1/repair-orders/{order_id}/complete/",
            {"completed_at": datetime.now(tz=UTC).isoformat()},
            format="json",
        )
        assert response.status_code == 422
        assert response.data["error_code"] == "INVALID_STATE_TRANSITION"

    def test_assign_then_start_happy_path(
        self, authenticated_client: APIClient
    ) -> None:
        """ASSIGNED → IN_PROGRESS remains the valid start path."""
        _, order_id = _create_order(
            authenticated_client, plate="12WF0004", vin="1HGCM82633A004383"
        )
        assigned = authenticated_client.post(
            f"/api/v1/repair-orders/{order_id}/assign/",
            {"technician_id": str(uuid4())},
            format="json",
        )
        assert assigned.status_code == 200
        started = authenticated_client.post(
            f"/api/v1/repair-orders/{order_id}/start/",
            {},
            format="json",
        )
        assert started.status_code == 200
        assert started.data["status"] == "IN_PROGRESS"
