"""API integration tests for vehicle endpoints."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from rest_framework.test import APIClient

from apps.vehicle.infrastructure.models import VehicleDriverAssignmentHistoryModel
from tests.integration.api.conftest import create_vehicle

pytestmark = pytest.mark.django_db


class TestVehicleAPI:
    """Cover vehicle read, workflow, odometer, and auth endpoints."""

    def test_auth_required(self, api_client: APIClient) -> None:
        """Unauthenticated clients receive 401."""
        response = api_client.get("/api/v1/vehicles/")
        assert response.status_code == 401

    def test_manual_create_is_not_available(
        self, authenticated_client: APIClient
    ) -> None:
        """Vehicle master data must enter FMMS through SAP sync, not API create."""
        response = authenticated_client.post(
            "/api/v1/vehicles/",
            {
                "plate_number": "12VEH001",
                "vin": "1HGCM82633A004352",
                "make": "Toyota",
                "model": "Hilux",
                "year": 2022,
                "category": "LIGHT",
            },
            format="json",
        )
        assert response.status_code == 405

    def test_list_retrieve_no_manual_patch_and_deactivate(
        self, authenticated_client: APIClient
    ) -> None:
        """Vehicle master data has no generic manual update endpoint."""
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
        assert retrieved.data["license_plate"] == "12VEH001"
        assert retrieved.data["status_label"] == "عملیاتی"

        patched = authenticated_client.patch(
            f"/api/v1/vehicles/{vehicle_id}/",
            {"status": "SUSPENDED"},
            format="json",
        )
        assert patched.status_code == 405

        deactivated = authenticated_client.post(
            f"/api/v1/vehicles/{vehicle_id}/status/",
            {"status": "INACTIVE"},
            format="json",
        )
        assert deactivated.status_code == 200
        assert deactivated.data["status"] == "INACTIVE"

    def test_list_supports_ordering(self, authenticated_client: APIClient) -> None:
        create_vehicle(authenticated_client, plate="B-002", vin="1HGCM82633A004352")
        create_vehicle(authenticated_client, plate="A-001", vin="1HGCM82633A004353")

        response = authenticated_client.get("/api/v1/vehicles/?ordering=license_plate")

        assert response.status_code == 200
        assert [item["license_plate"] for item in response.data["results"]] == [
            "A-001",
            "B-002",
        ]

    def test_change_status_endpoint_updates_vehicle_status(
        self, authenticated_client: APIClient
    ) -> None:
        vehicle = create_vehicle(authenticated_client)

        response = authenticated_client.post(
            f"/api/v1/vehicles/{vehicle['id']}/status/",
            {"status": "UNDER_REPAIR"},
            format="json",
        )

        assert response.status_code == 200, response.data
        assert response.data["status"] == "UNDER_REPAIR"
        assert response.data["status_label"] == "در تعمیر"

    def test_change_status_to_active_rejects_open_fault(
        self, authenticated_client: APIClient
    ) -> None:
        vehicle = create_vehicle(authenticated_client, plate="12OPN001")
        created_fault = authenticated_client.post(
            "/api/v1/faults/",
            {
                "vehicle_id": vehicle["id"],
                "code": "ENG-01",
                "description": "Engine failure",
                "severity": "HIGH",
            },
            format="json",
        )
        assert created_fault.status_code == 201, created_fault.data

        response = authenticated_client.post(
            f"/api/v1/vehicles/{vehicle['id']}/status/",
            {"status": "ACTIVE"},
            format="json",
        )

        assert response.status_code == 409
        assert response.data["error_code"] == "VEHICLE_HAS_OPEN_FAULTS"

    def test_record_odometer_upserts_daily_reading(
        self, authenticated_client: APIClient
    ) -> None:
        vehicle = create_vehicle(authenticated_client)
        url = f"/api/v1/vehicles/{vehicle['id']}/odometer/"

        first = authenticated_client.post(
            url,
            {"reading_date": "2026-07-15", "odometer_km": 1000},
            format="json",
        )
        assert first.status_code == 200, first.data
        assert first.data["odometer_km"] == 1000

        updated = authenticated_client.post(
            url,
            {"reading_date": "2026-07-15", "odometer_km": 1015},
            format="json",
        )
        assert updated.status_code == 200, updated.data
        assert updated.data["id"] == first.data["id"]
        assert updated.data["odometer_km"] == 1015

        current = authenticated_client.get(url)
        assert current.status_code == 200
        assert current.data["id"] == first.data["id"]
        assert current.data["odometer_km"] == 1015

    def test_odometer_history_supports_date_filter(
        self, authenticated_client: APIClient
    ) -> None:
        vehicle = create_vehicle(authenticated_client)
        url = f"/api/v1/vehicles/{vehicle['id']}/odometer/"
        history_url = f"/api/v1/vehicles/{vehicle['id']}/odometer-history/"
        authenticated_client.post(
            url,
            {"reading_date": "2026-07-15", "odometer_km": 1000},
            format="json",
        )
        authenticated_client.post(
            url,
            {"reading_date": "2026-07-16", "odometer_km": 1015},
            format="json",
        )

        history = authenticated_client.get(f"{history_url}?from_date=2026-07-16")

        assert history.status_code == 200
        assert [item["reading_date"] for item in history.data] == ["2026-07-16"]

    def test_get_odometer_without_reading_returns_not_found(
        self, authenticated_client: APIClient
    ) -> None:
        vehicle = create_vehicle(authenticated_client)

        response = authenticated_client.get(
            f"/api/v1/vehicles/{vehicle['id']}/odometer/"
        )

        assert response.status_code == 404

    def test_vehicle_driver_assignment_history_supports_date_filter(
        self, authenticated_client: APIClient
    ) -> None:
        vehicle = create_vehicle(authenticated_client, vehicle_number="203200001")
        vehicle_id = vehicle["id"]
        VehicleDriverAssignmentHistoryModel.objects.create(
            sync_run_id=uuid.uuid4(),
            request_id="old-sync",
            synced_at=datetime(2026, 7, 14, 8, 0, tzinfo=UTC),
            vehicle_id=vehicle_id,
            vehicle_number=vehicle["vehicle_number"],
            license_plate=vehicle["license_plate"],
            driver_role=VehicleDriverAssignmentHistoryModel.DriverRole.DRIVER,
            driver_customer_number="6000000001",
        )
        VehicleDriverAssignmentHistoryModel.objects.create(
            sync_run_id=uuid.uuid4(),
            request_id="new-sync",
            synced_at=datetime(2026, 7, 16, 8, 0, tzinfo=UTC),
            vehicle_id=vehicle_id,
            vehicle_number=vehicle["vehicle_number"],
            license_plate=vehicle["license_plate"],
            driver_role=VehicleDriverAssignmentHistoryModel.DriverRole.ASSISTANT,
            driver_customer_number="6000000002",
        )

        response = authenticated_client.get(
            f"/api/v1/vehicles/{vehicle_id}/driver-assignment-history/"
            "?from_date=2026-07-16"
        )

        assert response.status_code == 200, response.data
        assert [item["driver_customer_number"] for item in response.data] == [
            "6000000002"
        ]

    def test_odometer_must_increase_by_at_least_10_km(
        self, authenticated_client: APIClient
    ) -> None:
        vehicle = create_vehicle(authenticated_client)
        url = f"/api/v1/vehicles/{vehicle['id']}/odometer/"
        authenticated_client.post(
            url,
            {"reading_date": "2026-07-15", "odometer_km": 1000},
            format="json",
        )

        invalid = authenticated_client.post(
            url,
            {"reading_date": "2026-07-16", "odometer_km": 1005},
            format="json",
        )

        assert invalid.status_code == 422
