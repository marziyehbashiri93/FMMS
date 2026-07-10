"""API integration tests for demo workflow backend contracts."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from rest_framework.test import APIClient

from apps.fault.infrastructure.models import FaultModel
from apps.repair.infrastructure.models import RepairOrderModel
from apps.vehicle.domain.entities import VehicleStatus
from apps.vehicle.infrastructure.models import VehicleModel
from tests.integration.api.conftest import create_vehicle

pytestmark = pytest.mark.django_db


class TestVehicleSAPBulkSyncAPI:
    """Cover POST /api/v1/vehicles/sync-sap/ bulk import."""

    def test_sync_creates_vehicles_from_mock_sap(
        self, authenticated_client: APIClient
    ) -> None:
        response = authenticated_client.post(
            "/api/v1/vehicles/sync-sap/", {}, format="json"
        )

        assert response.status_code == 200, response.data
        assert response.data["total_received"] >= 1
        assert response.data["created"] >= 1
        assert response.data["failed"] == 0

        listed = authenticated_client.get("/api/v1/vehicles/")
        assert listed.status_code == 200
        assert listed.data["count"] >= response.data["created"]

    def test_sync_updates_existing_and_is_idempotent(
        self, authenticated_client: APIClient
    ) -> None:
        first = authenticated_client.post(
            "/api/v1/vehicles/sync-sap/", {}, format="json"
        )
        assert first.status_code == 200
        second = authenticated_client.post(
            "/api/v1/vehicles/sync-sap/", {}, format="json"
        )
        assert second.status_code == 200

        assert second.data["created"] == 0
        assert second.data["updated"] == first.data["created"] + first.data["updated"]
        assert second.data["failed"] == 0


class TestInspectionTemplateSAPSyncAPI:
    """Cover inspection-template sync and list APIs."""

    def test_sync_and_list_templates(self, authenticated_client: APIClient) -> None:
        synced = authenticated_client.post(
            "/api/v1/inspection-templates/sync-sap/", {}, format="json"
        )
        assert synced.status_code == 200, synced.data
        assert synced.data["total_received"] >= 4
        assert synced.data["created"] >= 4
        assert synced.data["failed"] == 0

        listed = authenticated_client.get("/api/v1/inspection-templates/")
        assert listed.status_code == 200
        results = listed.data["results"] if "results" in listed.data else listed.data
        descriptions = {item["description"] for item in results}
        assert "Seat belt" in descriptions
        assert "Front light" in descriptions
        assert "Refrigerator" in descriptions
        assert "Safety equipment" in descriptions

        again = authenticated_client.post(
            "/api/v1/inspection-templates/sync-sap/", {}, format="json"
        )
        assert again.status_code == 200
        assert again.data["created"] == 0
        assert again.data["updated"] >= 4


class TestDriverInspectionWorkflowAPI:
    """Cover PASS vs FAIL inspection submit side-effects."""

    def test_submit_all_pass_keeps_vehicle_active(
        self, authenticated_client: APIClient
    ) -> None:
        vehicle = create_vehicle(
            authenticated_client, plate="12PASS01", vin="1HGCM82633A004361"
        )
        created = authenticated_client.post(
            "/api/v1/inspections/",
            {
                "vehicle_id": vehicle["id"],
                "inspection_type": "PRE_TRIP",
                "odometer_value": 1000,
                "odometer_unit": "KM",
                "inspected_at": datetime.now(tz=UTC).isoformat(),
                "items": [
                    {
                        "category": "SAFETY",
                        "description": "Seat belt",
                        "result": "PASS",
                    }
                ],
            },
            format="json",
        )
        assert created.status_code == 201, created.data

        submitted = authenticated_client.post(
            f"/api/v1/inspections/{created.data['id']}/submit/", {}, format="json"
        )
        assert submitted.status_code == 200, submitted.data
        assert submitted.data["status"] == "SUBMITTED"
        assert submitted.data["has_failures"] is False

        detail = authenticated_client.get(f"/api/v1/vehicles/{vehicle['id']}/")
        assert detail.data["status"] == VehicleStatus.ACTIVE.value
        assert FaultModel.objects.filter(vehicle_id=vehicle["id"]).count() == 0
        assert RepairOrderModel.objects.filter(vehicle_id=vehicle["id"]).count() == 0

    def test_submit_fail_creates_fault_repair_and_out_of_service(
        self, authenticated_client: APIClient
    ) -> None:
        vehicle = create_vehicle(
            authenticated_client, plate="12FAIL01", vin="1HGCM82633A004362"
        )
        created = authenticated_client.post(
            "/api/v1/inspections/",
            {
                "vehicle_id": vehicle["id"],
                "inspection_type": "PRE_TRIP",
                "odometer_value": 1000,
                "odometer_unit": "KM",
                "inspected_at": datetime.now(tz=UTC).isoformat(),
                "items": [
                    {
                        "category": "LIGHTS",
                        "description": "Front light",
                        "result": "FAIL",
                        "notes": "Broken",
                    }
                ],
            },
            format="json",
        )
        assert created.status_code == 201, created.data

        submitted = authenticated_client.post(
            f"/api/v1/inspections/{created.data['id']}/submit/", {}, format="json"
        )
        assert submitted.status_code == 200, submitted.data
        assert submitted.data["has_failures"] is True

        assert (
            FaultModel.objects.filter(
                vehicle_id=vehicle["id"], inspection_id=created.data["id"]
            ).count()
            == 1
        )
        assert RepairOrderModel.objects.filter(vehicle_id=vehicle["id"]).count() == 1

        orm = VehicleModel.objects.get(id=vehicle["id"])
        assert orm.status == VehicleStatus.OUT_OF_SERVICE.value
