"""API integration tests for fault endpoints."""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.vehicle.infrastructure.models import VehicleModel
from tests.integration.api.conftest import create_vehicle

pytestmark = pytest.mark.django_db


class TestFaultAPI:
    """Cover fault report and close flow."""

    def test_report_and_close(self, authenticated_client: APIClient) -> None:
        """Report a fault and close it from OPEN."""
        vehicle = create_vehicle(
            authenticated_client, plate="12FLT001", vin="1HGCM82633A004355"
        )
        created = authenticated_client.post(
            "/api/v1/faults/",
            {
                "vehicle_id": vehicle["id"],
                "code": "BRK-01",
                "description": "Brake pad wear",
                "severity": "MEDIUM",
            },
            format="json",
        )
        assert created.status_code == 201, created.data
        fault_id = created.data["id"]
        assert created.data["status"] == "OPEN"

        listed = authenticated_client.get(f"/api/v1/faults/?vehicle_id={vehicle['id']}")
        assert listed.status_code == 200
        assert listed.data["count"] >= 1

        retrieved = authenticated_client.get(f"/api/v1/faults/{fault_id}/")
        assert retrieved.status_code == 200
        assert retrieved.data["code"] == "BRK-01"
        assert retrieved.data["items"] == []

        closed = authenticated_client.post(
            f"/api/v1/faults/{fault_id}/close/",
            {},
            format="json",
        )
        assert closed.status_code == 200, closed.data
        assert closed.data["status"] == "CLOSED"

    def test_report_fault_marks_active_vehicle_under_repair(
        self, authenticated_client: APIClient
    ) -> None:
        """An open fault must be reflected in vehicle availability status."""
        vehicle = create_vehicle(
            authenticated_client, plate="12FLT002", vin="1HGCM82633A004356"
        )

        created = authenticated_client.post(
            "/api/v1/faults/",
            {
                "vehicle_id": vehicle["id"],
                "code": "ENG-01",
                "description": "Engine failure",
                "severity": "HIGH",
            },
            format="json",
        )

        assert created.status_code == 201, created.data
        assert VehicleModel.objects.get(id=vehicle["id"]).status == "UNDER_REPAIR"
