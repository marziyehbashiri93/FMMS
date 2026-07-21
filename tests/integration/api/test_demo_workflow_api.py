"""API integration tests for demo workflow backend contracts."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from rest_framework.test import APIClient

from apps.fault.infrastructure.models import FaultItemModel, FaultModel
from apps.repair.infrastructure.models import RepairOrderModel
from apps.vehicle.domain.entities import VehicleStatus
from apps.vehicle.infrastructure.models import VehicleModel
from tests.integration.api.conftest import create_vehicle

pytestmark = pytest.mark.django_db


class TestVehicleSAPBulkSyncAPI:
    """Vehicle SAP sync is scheduled/operational, not a phase-1 public API."""

    def test_vehicle_sync_api_is_not_available_in_phase_1(
        self, authenticated_client: APIClient
    ) -> None:
        response = authenticated_client.post(
            "/api/v1/vehicles/sync-sap/", {}, format="json"
        )

        assert response.status_code == 405


class TestInspectionTemplateSAPSyncAPI:
    """Cover inspection-template sync and list APIs."""

    def test_sync_and_list_templates(
        self, authenticated_client: APIClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SAP_USE_MOCK", "True")

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
        assert "ترمز جلو" in descriptions
        assert "چراغ جلو" in descriptions
        assert "موتور اصلی" in descriptions
        assert "باتری/دینام" in descriptions

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
                        "severity": "MEDIUM",
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
        assert orm.status == VehicleStatus.ACTIVE.value

    def test_distribution_supervisor_can_deactivate_after_failed_inspection(
        self, authenticated_client: APIClient
    ) -> None:
        vehicle = create_vehicle(
            authenticated_client, plate="12DIST01", vin="1HGCM82633A004364"
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
                        "severity": "MEDIUM",
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

        detail = authenticated_client.get(f"/api/v1/vehicles/{vehicle['id']}/")
        assert detail.data["status"] == VehicleStatus.ACTIVE.value

        deactivated = authenticated_client.post(
            f"/api/v1/vehicles/{vehicle['id']}/status/",
            {"status": VehicleStatus.INACTIVE.value},
            format="json",
        )
        assert deactivated.status_code == 200, deactivated.data
        assert deactivated.data["status"] == VehicleStatus.INACTIVE.value

    def test_submit_multiple_failures_create_one_fault_with_items(
        self, authenticated_client: APIClient
    ) -> None:
        vehicle = create_vehicle(
            authenticated_client, plate="12FAIL02", vin="1HGCM82633A004363"
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
                        "severity": "MEDIUM",
                    },
                    {
                        "category": "COOLING",
                        "description": "Refrigerator",
                        "result": "FAIL",
                        "notes": "Cooling failure",
                        "severity": "HIGH",
                    },
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

        faults = FaultModel.objects.filter(
            vehicle_id=vehicle["id"], inspection_id=created.data["id"]
        )
        assert faults.count() == 1
        fault = faults.first()
        assert fault is not None
        assert fault.description == "Multiple inspection failures"
        assert FaultItemModel.objects.filter(fault_id=fault.id).count() == 2
        assert RepairOrderModel.objects.filter(vehicle_id=vehicle["id"]).count() == 1

        retrieved = authenticated_client.get(f"/api/v1/faults/{fault.id}/")
        assert retrieved.status_code == 200
        assert len(retrieved.data["items"]) == 2
        components = {item["component"] for item in retrieved.data["items"]}
        assert components == {"Front light", "Refrigerator"}


class TestDistributionUsableWorkflowAPI:
    """Distribution usable closes fault and cancels early repair orders."""

    def test_distribution_usable_allows_next_driver_inspection(
        self, authenticated_client: APIClient
    ) -> None:
        vehicle = create_vehicle(
            authenticated_client, plate="12USE001", vin="1HGCM82633A004371"
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
                        "severity": "MEDIUM",
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

        faults = authenticated_client.get(f"/api/v1/faults/?vehicle_id={vehicle['id']}")
        assert faults.status_code == 200
        assert faults.data["count"] == 1
        fault = faults.data["results"][0]
        assert fault["status"] == "OPEN"

        orders = authenticated_client.get(
            f"/api/v1/repair-orders/?vehicle_id={vehicle['id']}"
        )
        assert orders.status_code == 200
        assert orders.data["count"] == 1
        order = orders.data["results"][0]
        assert order["status"] == "CREATED"

        vehicle_detail = authenticated_client.get(f"/api/v1/vehicles/{vehicle['id']}/")
        assert vehicle_detail.data["status"] == VehicleStatus.ACTIVE.value

        closed = authenticated_client.post(
            f"/api/v1/faults/{fault['id']}/close/", {}, format="json"
        )
        assert closed.status_code == 200, closed.data
        assert closed.data["status"] == "CLOSED"

        cancelled = authenticated_client.get(f"/api/v1/repair-orders/{order['id']}/")
        assert cancelled.status_code == 200
        assert cancelled.data["status"] == "CANCELLED"

        timeline = authenticated_client.get(
            f"/api/v1/repair-orders/{order['id']}/timeline/"
        )
        assert timeline.status_code == 200, timeline.data
        events = {item["event"] for item in timeline.data}
        assert "DISTRIBUTION_APPROVED_USABLE" in events

        vehicle_after = authenticated_client.get(f"/api/v1/vehicles/{vehicle['id']}/")
        assert vehicle_after.data["status"] == VehicleStatus.ACTIVE.value

        next_inspection = authenticated_client.post(
            "/api/v1/inspections/",
            {
                "vehicle_id": vehicle["id"],
                "inspection_type": "PRE_TRIP",
                "odometer_value": 1100,
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
        assert next_inspection.status_code == 201, next_inspection.data

        next_submitted = authenticated_client.post(
            f"/api/v1/inspections/{next_inspection.data['id']}/submit/",
            {},
            format="json",
        )
        assert next_submitted.status_code == 200, next_submitted.data
        assert next_submitted.data["status"] == "SUBMITTED"
        assert next_submitted.data["has_failures"] is False
