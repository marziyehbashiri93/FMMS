"""API integration tests for vehicle endpoints."""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from tests.integration.api.conftest import create_vehicle

pytestmark = pytest.mark.django_db


class TestVehicleAPI:
    """Cover vehicle create/list/get/patch/deactivate and auth."""

    def test_auth_required(self, api_client: APIClient) -> None:
        """Unauthenticated clients receive 401."""
        response = api_client.get("/api/v1/vehicles/")
        assert response.status_code == 401

    def test_create_list_retrieve_patch_deactivate(
        self, authenticated_client: APIClient
    ) -> None:
        """Exercise the main vehicle lifecycle endpoints."""
        created = create_vehicle(
            authenticated_client,
            plate="12VEH001",
            vin="1HGCM82633A004352",
        )
        vehicle_id = created["id"]
        assert created["status"] == "ACTIVE"

        listed = authenticated_client.get("/api/v1/vehicles/")
        assert listed.status_code == 200
        assert listed.data["count"] >= 1

        retrieved = authenticated_client.get(f"/api/v1/vehicles/{vehicle_id}/")
        assert retrieved.status_code == 200
        assert retrieved.data["plate_number"] == "12VEH001"

        patched = authenticated_client.patch(
            f"/api/v1/vehicles/{vehicle_id}/",
            {"model": "Land Cruiser"},
            format="json",
        )
        assert patched.status_code == 200
        assert patched.data["model"] == "Land Cruiser"

        deactivated = authenticated_client.post(
            f"/api/v1/vehicles/{vehicle_id}/deactivate/",
            {},
            format="json",
        )
        assert deactivated.status_code == 200
        assert deactivated.data["status"] == "INACTIVE"
