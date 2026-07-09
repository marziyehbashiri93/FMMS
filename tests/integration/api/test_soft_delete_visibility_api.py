"""P1 — Soft-delete visibility through repositories and API list endpoints."""

from __future__ import annotations

from uuid import UUID

import pytest
from rest_framework.test import APIClient

from apps.vehicle.infrastructure.models import VehicleModel
from apps.vehicle.infrastructure.repositories import DjangoVehicleRepository
from tests.integration.api.conftest import create_vehicle

pytestmark = pytest.mark.django_db


class TestSoftDeleteVisibility:
    """Soft-deleted vehicles must disappear from active reads and list APIs."""

    def test_repository_soft_delete_hides_from_list_and_get(
        self, authenticated_client: APIClient
    ) -> None:
        """Repository soft-delete excludes the record from get/list."""
        vehicle = create_vehicle(
            authenticated_client, plate="12SOFT01", vin="1HGCM82633A004370"
        )
        vehicle_id = UUID(vehicle["id"])
        repo = DjangoVehicleRepository()
        repo.delete(vehicle_id)

        orm = VehicleModel.objects.get(id=vehicle_id)
        assert orm.is_deleted is True

        listed = authenticated_client.get("/api/v1/vehicles/")
        assert listed.status_code == 200
        ids = {row["id"] for row in listed.data["results"]}
        assert vehicle["id"] not in ids

        detail = authenticated_client.get(f"/api/v1/vehicles/{vehicle['id']}/")
        assert detail.status_code == 404
        assert detail.data["error_code"] == "NOT_FOUND"

    def test_deactivate_does_not_soft_delete(
        self, authenticated_client: APIClient
    ) -> None:
        """Status deactivate keeps the record visible (INACTIVE, not soft-deleted)."""
        vehicle = create_vehicle(
            authenticated_client, plate="12SOFT02", vin="1HGCM82633A004371"
        )
        deactivated = authenticated_client.post(
            f"/api/v1/vehicles/{vehicle['id']}/deactivate/",
            {},
            format="json",
        )
        assert deactivated.status_code == 200
        assert deactivated.data["status"] == "INACTIVE"

        orm = VehicleModel.objects.get(id=vehicle["id"])
        assert orm.is_deleted is False

        detail = authenticated_client.get(f"/api/v1/vehicles/{vehicle['id']}/")
        assert detail.status_code == 200
        assert detail.data["status"] == "INACTIVE"
