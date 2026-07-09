"""API integration tests for fault endpoints."""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient

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

        closed = authenticated_client.post(
            f"/api/v1/faults/{fault_id}/close/",
            {},
            format="json",
        )
        assert closed.status_code == 200, closed.data
        assert closed.data["status"] == "CLOSED"
