"""API integration tests for one-open-fault/repair-flow-per-vehicle rule."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from rest_framework.test import APIClient

from core.workflow import VEHICLE_OPEN_FLOW_ERROR_CODE, VEHICLE_OPEN_FLOW_MESSAGE
from tests.integration.api.conftest import create_vehicle

pytestmark = pytest.mark.django_db


def _create_inspection_with_fail_items(
    client: APIClient,
    vehicle_id: str,
    *,
    fail_count: int = 2,
) -> str:
    """Create a draft inspection with multiple FAIL checklist items."""
    created = client.post(
        "/api/v1/inspections/",
        {
            "vehicle_id": vehicle_id,
            "inspection_type": "PRE_TRIP",
            "odometer_value": 15000,
            "odometer_unit": "KM",
            "inspected_at": datetime.now(tz=UTC).isoformat(),
            "items": [
                {
                    "category": "Brakes",
                    "description": "Brake pad thickness",
                    "result": "FAIL",
                    "notes": "Below minimum",
                    "severity": "HIGH",
                },
                {
                    "category": "Lights",
                    "description": "Left headlight",
                    "result": "FAIL",
                    "notes": "Broken lens",
                    "severity": "MEDIUM",
                },
                {
                    "category": "Tires",
                    "description": "Tire pressure",
                    "result": "PASS",
                },
            ][: fail_count + 1],
        },
        format="json",
    )
    assert created.status_code == 201, created.data
    return created.data["id"]


def _open_fault_and_repair(client: APIClient, vehicle_id: str) -> tuple[dict, dict]:
    fault = client.post(
        "/api/v1/faults/",
        {
            "vehicle_id": vehicle_id,
            "code": "WF-OPEN",
            "description": "Existing open fault",
            "severity": "MEDIUM",
        },
        format="json",
    )
    assert fault.status_code == 201, fault.data
    order = client.post(
        "/api/v1/repair-orders/",
        {"vehicle_id": vehicle_id, "fault_id": fault.data["id"]},
        format="json",
    )
    assert order.status_code == 201, order.data
    return fault.data, order.data


class TestVehicleOpenWorkflowAPI:
    """Enforce a single open fault/repair flow per vehicle."""

    def test_failed_inspection_creates_one_fault_with_multiple_items(
        self, authenticated_client: APIClient
    ) -> None:
        vehicle = create_vehicle(
            authenticated_client, plate="12WF001", vin="1HGCM82633A004501"
        )
        inspection_id = _create_inspection_with_fail_items(
            authenticated_client, vehicle["id"]
        )

        submitted = authenticated_client.post(
            f"/api/v1/inspections/{inspection_id}/submit/",
            {},
            format="json",
        )
        assert submitted.status_code == 200, submitted.data

        faults = authenticated_client.get(f"/api/v1/faults/?vehicle_id={vehicle['id']}")
        assert faults.status_code == 200
        assert faults.data["count"] == 1
        fault = faults.data["results"][0]
        assert len(fault["items"]) == 2

        orders = authenticated_client.get(
            f"/api/v1/repair-orders/?vehicle_id={vehicle['id']}"
        )
        assert orders.status_code == 200
        assert orders.data["count"] == 1

    def test_submit_failed_inspection_rejected_when_open_fault_exists(
        self, authenticated_client: APIClient
    ) -> None:
        vehicle = create_vehicle(
            authenticated_client, plate="12WF002", vin="1HGCM82633A004502"
        )
        _open_fault_and_repair(authenticated_client, vehicle["id"])
        inspection_id = _create_inspection_with_fail_items(
            authenticated_client, vehicle["id"], fail_count=1
        )

        response = authenticated_client.post(
            f"/api/v1/inspections/{inspection_id}/submit/",
            {},
            format="json",
        )

        assert response.status_code == 422, response.data
        assert response.data["error_code"] == VEHICLE_OPEN_FLOW_ERROR_CODE
        assert response.data["message"] == VEHICLE_OPEN_FLOW_MESSAGE

    def test_submit_failed_inspection_rejected_when_open_repair_exists(
        self, authenticated_client: APIClient
    ) -> None:
        vehicle = create_vehicle(
            authenticated_client, plate="12WF003", vin="1HGCM82633A004503"
        )
        _, order = _open_fault_and_repair(authenticated_client, vehicle["id"])
        authenticated_client.post(
            f"/api/v1/faults/{order['fault_id']}/close/",
            {},
            format="json",
        )
        inspection_id = _create_inspection_with_fail_items(
            authenticated_client, vehicle["id"], fail_count=1
        )

        response = authenticated_client.post(
            f"/api/v1/inspections/{inspection_id}/submit/",
            {},
            format="json",
        )

        assert response.status_code == 422, response.data
        assert response.data["error_code"] == VEHICLE_OPEN_FLOW_ERROR_CODE

    def test_report_fault_rejected_when_open_fault_exists(
        self, authenticated_client: APIClient
    ) -> None:
        vehicle = create_vehicle(
            authenticated_client, plate="12WF004", vin="1HGCM82633A004504"
        )
        _open_fault_and_repair(authenticated_client, vehicle["id"])

        response = authenticated_client.post(
            "/api/v1/faults/",
            {
                "vehicle_id": vehicle["id"],
                "code": "DUP-01",
                "description": "Duplicate fault attempt",
                "severity": "LOW",
            },
            format="json",
        )

        assert response.status_code == 422, response.data
        assert response.data["error_code"] == VEHICLE_OPEN_FLOW_ERROR_CODE

    def test_report_fault_rejected_when_open_repair_exists(
        self, authenticated_client: APIClient
    ) -> None:
        vehicle = create_vehicle(
            authenticated_client, plate="12WF005", vin="1HGCM82633A004505"
        )
        fault, _ = _open_fault_and_repair(authenticated_client, vehicle["id"])
        authenticated_client.post(
            f"/api/v1/faults/{fault['id']}/close/",
            {},
            format="json",
        )

        response = authenticated_client.post(
            "/api/v1/faults/",
            {
                "vehicle_id": vehicle["id"],
                "code": "DUP-02",
                "description": "Blocked by open repair",
                "severity": "LOW",
            },
            format="json",
        )

        assert response.status_code == 422, response.data
        assert response.data["error_code"] == VEHICLE_OPEN_FLOW_ERROR_CODE

    def test_new_fault_allowed_after_workflow_closed(
        self, authenticated_client: APIClient
    ) -> None:
        vehicle = create_vehicle(
            authenticated_client, plate="12WF006", vin="1HGCM82633A004506"
        )
        fault, order = _open_fault_and_repair(authenticated_client, vehicle["id"])

        authenticated_client.post(
            f"/api/v1/repair-orders/{order['id']}/approve/", {}, format="json"
        )
        authenticated_client.post(
            f"/api/v1/repair-orders/{order['id']}/assign-workshop/",
            {"workshop_type": "INTERNAL"},
            format="json",
        )
        authenticated_client.post(
            f"/api/v1/repair-orders/{order['id']}/start/", {}, format="json"
        )
        authenticated_client.post(
            f"/api/v1/repair-orders/{order['id']}/complete/",
            {"completed_at": datetime.now(tz=UTC).isoformat()},
            format="json",
        )
        handovers = authenticated_client.get("/api/v1/vehicle-handovers/")
        target = next(
            item for item in handovers.data if item["repair_order_id"] == order["id"]
        )
        confirmed = authenticated_client.post(
            f"/api/v1/vehicle-handovers/{target['id']}/confirm/",
            {"accepted": True, "comment": "ok"},
            format="json",
        )
        assert confirmed.status_code == 200, confirmed.data
        authenticated_client.post(
            f"/api/v1/faults/{fault['id']}/close/", {}, format="json"
        )

        response = authenticated_client.post(
            "/api/v1/faults/",
            {
                "vehicle_id": vehicle["id"],
                "code": "NEW-01",
                "description": "Fresh fault after closure",
                "severity": "MEDIUM",
            },
            format="json",
        )

        assert response.status_code == 201, response.data
        assert response.data["status"] == "OPEN"
