"""API integration tests for driver endpoints."""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from tests.integration.api.conftest import create_vehicle

pytestmark = pytest.mark.django_db


class TestDriverAPI:
    """Cover driver register, assign, and suspend flows."""

    def test_register_assign_suspend(self, authenticated_client: APIClient) -> None:
        """Register a driver, assign a vehicle, then suspend."""
        vehicle = create_vehicle(
            authenticated_client, plate="12DRV001", vin="1HGCM82633A004353"
        )
        created = authenticated_client.post(
            "/api/v1/drivers/",
            {
                "full_name": "Ali Ahmadi",
                "license_number": "LIC12345",
                "license_class": "B",
                "phone": "+989123456789",
                "email": "ali@fmms.test",
            },
            format="json",
        )
        assert created.status_code == 201, created.data
        driver_id = created.data["id"]

        listed = authenticated_client.get("/api/v1/drivers/")
        assert listed.status_code == 200
        assert listed.data["count"] >= 1

        retrieved = authenticated_client.get(f"/api/v1/drivers/{driver_id}/")
        assert retrieved.status_code == 200
        assert retrieved.data["license_number"] == "LIC12345"

        assigned = authenticated_client.post(
            f"/api/v1/drivers/{driver_id}/assign/",
            {"vehicle_id": vehicle["id"]},
            format="json",
        )
        assert assigned.status_code == 200, assigned.data
        assert assigned.data["assigned_vehicle_id"] == vehicle["id"]

        suspended = authenticated_client.post(
            f"/api/v1/drivers/{driver_id}/suspend/",
            {},
            format="json",
        )
        assert suspended.status_code == 200, suspended.data
        assert suspended.data["status"] == "SUSPENDED"
