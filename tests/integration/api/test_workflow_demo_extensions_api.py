"""API integration tests for demo manager workflow extensions."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from rest_framework.test import APIClient

from apps.vehicle.domain.entities import VehicleStatus
from tests.integration.api.conftest import create_vehicle

pytestmark = pytest.mark.django_db


def _create_fault_and_repair(
    client: APIClient, plate: str, vin: str
) -> tuple[dict, dict]:
    """Create vehicle, fault, and repair order."""
    vehicle = create_vehicle(client, plate=plate, vin=vin)
    fault = client.post(
        "/api/v1/faults/",
        {
            "vehicle_id": vehicle["id"],
            "code": "WF-01",
            "description": "Workflow fault",
            "severity": "HIGH",
        },
        format="json",
    )
    assert fault.status_code == 201, fault.data
    order = client.post(
        "/api/v1/repair-orders/",
        {"vehicle_id": vehicle["id"], "fault_id": fault.data["id"]},
        format="json",
    )
    assert order.status_code == 201, order.data
    return vehicle, order.data


def _workshop_assigned_order(client: APIClient, plate: str, vin: str) -> dict:
    """Return a repair order in WORKSHOP_ASSIGNED status."""
    _, order = _create_fault_and_repair(client, plate, vin)
    approved = client.post(
        f"/api/v1/repair-orders/{order['id']}/approve/", {}, format="json"
    )
    assert approved.status_code == 200, approved.data
    assigned = client.post(
        f"/api/v1/repair-orders/{order['id']}/assign-workshop/",
        {"workshop_type": "INTERNAL"},
        format="json",
    )
    assert assigned.status_code == 200, assigned.data
    assert assigned.data["status"] == "WORKSHOP_ASSIGNED"
    return assigned.data


class TestVehicleActivateAPI:
    """Cover POST /api/v1/vehicles/{id}/activate/."""

    def test_supervisor_can_activate_after_maintenance(
        self, authenticated_client: APIClient, supervisor_client: APIClient
    ) -> None:
        vehicle = create_vehicle(
            authenticated_client, plate="12ACT001", vin="1HGCM82633A004401"
        )
        deactivated = authenticated_client.post(
            f"/api/v1/vehicles/{vehicle['id']}/deactivate/", {}, format="json"
        )
        assert deactivated.status_code == 200
        assert deactivated.data["status"] == VehicleStatus.INACTIVE.value

        activated = supervisor_client.post(
            f"/api/v1/vehicles/{vehicle['id']}/activate/", {}, format="json"
        )
        assert activated.status_code == 200, activated.data
        assert activated.data["status"] == VehicleStatus.ACTIVE.value
        assert activated.data["id"] == vehicle["id"]

    def test_activate_blocked_when_open_repair_exists(
        self, authenticated_client: APIClient
    ) -> None:
        vehicle, _order = _create_fault_and_repair(
            authenticated_client, "12ACT002", "1HGCM82633A004402"
        )
        deactivated = authenticated_client.post(
            f"/api/v1/vehicles/{vehicle['id']}/deactivate/", {}, format="json"
        )
        assert deactivated.status_code == 200

        response = authenticated_client.post(
            f"/api/v1/vehicles/{vehicle['id']}/activate/", {}, format="json"
        )
        assert response.status_code == 409

    def test_viewer_cannot_activate_vehicle(
        self, authenticated_client: APIClient, viewer_client: APIClient
    ) -> None:
        vehicle = create_vehicle(
            authenticated_client, plate="12ACT003", vin="1HGCM82633A004403"
        )
        authenticated_client.post(
            f"/api/v1/vehicles/{vehicle['id']}/deactivate/", {}, format="json"
        )
        response = viewer_client.post(
            f"/api/v1/vehicles/{vehicle['id']}/activate/", {}, format="json"
        )
        assert response.status_code == 403


class TestFaultCreatedByAPI:
    """Cover created_by enrichment on fault responses."""

    def test_fault_response_includes_created_by(
        self, authenticated_client: APIClient, admin_user
    ) -> None:
        vehicle = create_vehicle(
            authenticated_client, plate="12CBY001", vin="1HGCM82633A004411"
        )
        created = authenticated_client.post(
            "/api/v1/faults/",
            {
                "vehicle_id": vehicle["id"],
                "code": "CBY-01",
                "description": "Created by audit test",
                "severity": "MEDIUM",
            },
            format="json",
        )
        assert created.status_code == 201, created.data
        assert created.data["created_by"] is not None
        assert created.data["created_by"]["id"] == str(admin_user.id)
        assert created.data["created_by"]["role"] == "ADMIN"
        assert created.data["created_by"]["name"]

        retrieved = authenticated_client.get(f"/api/v1/faults/{created.data['id']}/")
        assert retrieved.status_code == 200
        assert retrieved.data["created_by"]["id"] == str(admin_user.id)


class TestInspectionHistoryAPI:
    """Cover enriched GET /api/v1/inspections/?vehicle_id=."""

    def test_list_inspection_history_for_vehicle(
        self, authenticated_client: APIClient
    ) -> None:
        vehicle = create_vehicle(
            authenticated_client, plate="12HIS001", vin="1HGCM82633A004421"
        )
        driver = authenticated_client.post(
            "/api/v1/drivers/",
            {
                "full_name": "History Driver",
                "license_number": "LICHIS01",
                "license_class": "B",
                "phone": "+989120000001",
                "email": "history@fmms.test",
            },
            format="json",
        )
        assert driver.status_code == 201, driver.data

        for idx, result in enumerate(("PASS", "FAIL")):
            created = authenticated_client.post(
                "/api/v1/inspections/",
                {
                    "vehicle_id": vehicle["id"],
                    "inspection_type": "PRE_TRIP",
                    "odometer_value": 1000 + idx,
                    "odometer_unit": "KM",
                    "inspected_at": datetime.now(tz=UTC).isoformat(),
                    "driver_id": driver.data["id"],
                    "items": [
                        {
                            "category": "SAFETY",
                            "description": "Seat belt",
                            "result": result,
                            "notes": "Broken" if result == "FAIL" else "",
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

        listed = authenticated_client.get(
            f"/api/v1/inspections/?vehicle_id={vehicle['id']}"
        )
        assert listed.status_code == 200
        results = listed.data["results"] if "results" in listed.data else listed.data
        assert len(results) >= 2

        by_result = {item["overall_result"]: item for item in results}
        assert by_result["PASS"]["driver"]["name"] == "History Driver"
        assert by_result["PASS"]["overall_result"] == "PASS"
        assert by_result["FAIL"]["overall_result"] == "FAIL"
        assert len(by_result["FAIL"]["related_fault_ids"]) >= 1


class TestRepairStartFromWorkshopAssignedAPI:
    """Cover POST /api/v1/repair-orders/{id}/start/ from WORKSHOP_ASSIGNED."""

    def test_start_from_workshop_assigned(
        self, authenticated_client: APIClient
    ) -> None:
        order = _workshop_assigned_order(
            authenticated_client, "12STR001", "1HGCM82633A004431"
        )
        started = authenticated_client.post(
            f"/api/v1/repair-orders/{order['id']}/start/", {}, format="json"
        )
        assert started.status_code == 200, started.data
        assert started.data["status"] == "IN_PROGRESS"

    def test_start_from_created_returns_422(
        self, authenticated_client: APIClient
    ) -> None:
        _, order = _create_fault_and_repair(
            authenticated_client, "12STR002", "1HGCM82633A004432"
        )
        response = authenticated_client.post(
            f"/api/v1/repair-orders/{order['id']}/start/", {}, format="json"
        )
        assert response.status_code == 422

    def test_viewer_cannot_start_repair(
        self, authenticated_client: APIClient, viewer_client: APIClient
    ) -> None:
        order = _workshop_assigned_order(
            authenticated_client, "12STR003", "1HGCM82633A004433"
        )
        response = viewer_client.post(
            f"/api/v1/repair-orders/{order['id']}/start/", {}, format="json"
        )
        assert response.status_code == 403


class TestRepairTimelineAPI:
    """Cover GET /api/v1/repair-orders/{id}/timeline/."""

    def test_timeline_records_workflow_events(
        self, authenticated_client: APIClient
    ) -> None:
        order = _workshop_assigned_order(
            authenticated_client, "12TL001", "1HGCM82633A004441"
        )
        started = authenticated_client.post(
            f"/api/v1/repair-orders/{order['id']}/start/", {}, format="json"
        )
        assert started.status_code == 200
        completed = authenticated_client.post(
            f"/api/v1/repair-orders/{order['id']}/complete/",
            {"completed_at": datetime.now(tz=UTC).isoformat()},
            format="json",
        )
        assert completed.status_code == 200

        timeline = authenticated_client.get(
            f"/api/v1/repair-orders/{order['id']}/timeline/"
        )
        assert timeline.status_code == 200, timeline.data
        events = {item["event"] for item in timeline.data}
        assert "FAULT_CREATED" in events
        assert "TRANSPORT_APPROVED" in events
        assert "WORKSHOP_ASSIGNED" in events
        assert "REPAIR_STARTED" in events
        assert "REPAIR_COMPLETED" in events


class TestRepairPartsAPI:
    """Cover POST /api/v1/repair-orders/{id}/parts/ validation rules."""

    def test_add_part_while_in_progress(self, authenticated_client: APIClient) -> None:
        order = _workshop_assigned_order(
            authenticated_client, "12PRT001", "1HGCM82633A004451"
        )
        started = authenticated_client.post(
            f"/api/v1/repair-orders/{order['id']}/start/", {}, format="json"
        )
        assert started.status_code == 200

        with_part = authenticated_client.post(
            f"/api/v1/repair-orders/{order['id']}/parts/",
            {
                "material_number": "MAT-001",
                "quantity": 1,
                "unit_of_measure": "EA",
            },
            format="json",
        )
        assert with_part.status_code == 200, with_part.data
        assert len(with_part.data["parts"]) == 1
        assert with_part.data["parts"][0]["material_number"] == "MAT-001"

    def test_invalid_quantity_returns_400(
        self, authenticated_client: APIClient
    ) -> None:
        order = _workshop_assigned_order(
            authenticated_client, "12PRT002", "1HGCM82633A004452"
        )
        started = authenticated_client.post(
            f"/api/v1/repair-orders/{order['id']}/start/", {}, format="json"
        )
        assert started.status_code == 200

        response = authenticated_client.post(
            f"/api/v1/repair-orders/{order['id']}/parts/",
            {
                "material_number": "MAT-002",
                "quantity": 0,
                "unit_of_measure": "EA",
            },
            format="json",
        )
        assert response.status_code == 400

    def test_add_part_to_completed_order_returns_422(
        self, authenticated_client: APIClient
    ) -> None:
        order = _workshop_assigned_order(
            authenticated_client, "12PRT003", "1HGCM82633A004453"
        )
        technician_id = str(uuid4())
        authenticated_client.post(
            f"/api/v1/repair-orders/{order['id']}/assign/",
            {"technician_id": technician_id},
            format="json",
        )
        authenticated_client.post(
            f"/api/v1/repair-orders/{order['id']}/start/", {}, format="json"
        )
        completed = authenticated_client.post(
            f"/api/v1/repair-orders/{order['id']}/complete/",
            {"completed_at": datetime.now(tz=UTC).isoformat()},
            format="json",
        )
        assert completed.status_code == 200

        response = authenticated_client.post(
            f"/api/v1/repair-orders/{order['id']}/parts/",
            {
                "material_number": "MAT-003",
                "quantity": 1,
                "unit_of_measure": "EA",
            },
            format="json",
        )
        assert response.status_code == 422
