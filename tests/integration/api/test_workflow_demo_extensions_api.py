"""API integration tests for demo manager workflow extensions."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from rest_framework.test import APIClient

from apps.driver.domain.entities import DriverStatus
from apps.driver.infrastructure.models import DriverModel
from apps.vehicle.domain.entities import VehicleStatus
from tests.integration.api.conftest import (
    create_repair_order_via_distribution,
    create_vehicle,
)

pytestmark = pytest.mark.django_db


def _create_fault_and_repair(
    client: APIClient, plate: str, vin: str
) -> tuple[dict, dict]:
    """Create vehicle, fault, and repair order via distribution-unusable."""
    order = create_repair_order_via_distribution(
        client, plate=plate, vin=vin, code="WF-01", description="Workflow fault"
    )
    return order["vehicle"], order


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


class TestVehicleStatusAPI:
    """Cover POST /api/v1/vehicles/{id}/status/."""

    def test_supervisor_can_activate_after_maintenance(
        self, authenticated_client: APIClient, supervisor_client: APIClient
    ) -> None:
        vehicle = create_vehicle(
            authenticated_client, plate="12ACT001", vin="1HGCM82633A004401"
        )
        deactivated = authenticated_client.post(
            f"/api/v1/vehicles/{vehicle['id']}/status/",
            {"status": VehicleStatus.INACTIVE.value},
            format="json",
        )
        assert deactivated.status_code == 200
        assert deactivated.data["status"] == VehicleStatus.INACTIVE.value

        activated = supervisor_client.post(
            f"/api/v1/vehicles/{vehicle['id']}/status/",
            {"status": VehicleStatus.ACTIVE.value},
            format="json",
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
            f"/api/v1/vehicles/{vehicle['id']}/status/",
            {"status": VehicleStatus.INACTIVE.value},
            format="json",
        )
        assert deactivated.status_code == 200

        response = authenticated_client.post(
            f"/api/v1/vehicles/{vehicle['id']}/status/",
            {"status": VehicleStatus.ACTIVE.value},
            format="json",
        )
        assert response.status_code == 409

    def test_viewer_cannot_activate_vehicle(
        self, authenticated_client: APIClient, viewer_client: APIClient
    ) -> None:
        vehicle = create_vehicle(
            authenticated_client, plate="12ACT003", vin="1HGCM82633A004403"
        )
        authenticated_client.post(
            f"/api/v1/vehicles/{vehicle['id']}/status/",
            {"status": VehicleStatus.INACTIVE.value},
            format="json",
        )
        response = viewer_client.post(
            f"/api/v1/vehicles/{vehicle['id']}/status/",
            {"status": VehicleStatus.ACTIVE.value},
            format="json",
        )
        assert response.status_code == 403

    def test_activate_closes_fault_after_completed_repair(
        self, authenticated_client: APIClient, supervisor_client: APIClient
    ) -> None:
        """Completed repair + vehicle activation should close the linked fault."""
        vehicle, order = _create_fault_and_repair(
            authenticated_client, "12ACT004", "1HGCM82633A004404"
        )
        order_id = order["id"]
        fault_id = order["fault_id"]

        approved = authenticated_client.post(
            f"/api/v1/repair-orders/{order_id}/approve/", {}, format="json"
        )
        assert approved.status_code == 200, approved.data
        assigned = authenticated_client.post(
            f"/api/v1/repair-orders/{order_id}/assign-workshop/",
            {"workshop_type": "INTERNAL"},
            format="json",
        )
        assert assigned.status_code == 200, assigned.data
        started = authenticated_client.post(
            f"/api/v1/repair-orders/{order_id}/start/", {}, format="json"
        )
        assert started.status_code == 200, started.data
        completed = authenticated_client.post(
            f"/api/v1/repair-orders/{order_id}/complete/",
            {"completed_at": datetime.now(tz=UTC).isoformat()},
            format="json",
        )
        assert completed.status_code == 200, completed.data
        assert completed.data["status"] == "WAITING_DRIVER_CONFIRMATION"

        handovers = authenticated_client.get("/api/v1/vehicle-handovers/")
        target = next(
            item for item in handovers.data if item["repair_order_id"] == order_id
        )
        confirmed = authenticated_client.post(
            f"/api/v1/vehicle-handovers/{target['id']}/confirm/",
            {"accepted": True, "comment": "ok"},
            format="json",
        )
        assert confirmed.status_code == 200, confirmed.data

        open_fault = authenticated_client.get(f"/api/v1/faults/{fault_id}/")
        assert open_fault.status_code == 200
        assert open_fault.data["status"] == "CLOSED"

        activated = authenticated_client.get(f"/api/v1/vehicles/{vehicle['id']}/")
        assert activated.status_code == 200, activated.data
        assert activated.data["status"] == VehicleStatus.ACTIVE.value

        closed_fault = authenticated_client.get(f"/api/v1/faults/{fault_id}/")
        assert closed_fault.status_code == 200
        assert closed_fault.data["status"] == "CLOSED"


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
        driver = DriverModel.objects.create(
            customer_number="6000008888",
            name="History Driver",
            mobile="09120000001",
            status=DriverStatus.ACTIVE.value,
        )

        for idx, result in enumerate(("PASS", "FAIL")):
            created = authenticated_client.post(
                "/api/v1/inspections/",
                {
                    "vehicle_id": vehicle["id"],
                    "inspection_type": "PRE_TRIP",
                    "odometer_value": 1000 + idx,
                    "odometer_unit": "KM",
                    "inspected_at": datetime.now(tz=UTC).isoformat(),
                    "driver_id": str(driver.id),
                    "items": [
                        {
                            "category": "SAFETY",
                            "description": "Seat belt",
                            "result": result,
                            "notes": "Broken" if result == "FAIL" else "",
                            **({"severity": "MEDIUM"} if result == "FAIL" else {}),
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
            if result == "FAIL":
                reported = authenticated_client.post(
                    f"/api/v1/inspections/{created.data['id']}/report-fault/",
                    {},
                    format="json",
                )
                assert reported.status_code == 201, reported.data

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
        assert "DISTRIBUTION_APPROVED" in events
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
