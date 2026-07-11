"""Integration tests for maintenance workflow v2 APIs."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from rest_framework.test import APIClient

from tests.integration.api.conftest import create_vehicle

pytestmark = pytest.mark.django_db


def _create_order(client: APIClient, plate: str, vin: str) -> dict:
    """Create repair order with prerequisite vehicle and fault."""
    vehicle = create_vehicle(client, plate=plate, vin=vin)
    fault = client.post(
        "/api/v1/faults/",
        {
            "vehicle_id": vehicle["id"],
            "code": "MWF2",
            "description": "Maintenance workflow v2 fault",
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
    return order.data


def _move_to_workshop_assigned(client: APIClient, order_id: str) -> dict:
    """Move order to WORKSHOP_ASSIGNED."""
    approved = client.post(
        f"/api/v1/repair-orders/{order_id}/approve/", {}, format="json"
    )
    assert approved.status_code == 200, approved.data
    assigned = client.post(
        f"/api/v1/repair-orders/{order_id}/assign-workshop/",
        {"workshop_type": "INTERNAL", "workshop_id": "WS-001"},
        format="json",
    )
    assert assigned.status_code == 200, assigned.data
    return assigned.data


class TestMaintenanceWorkflowV2API:
    """Maintenance workflow v2 end-to-end scenarios."""

    def test_internal_workshop_accept_and_start(
        self, technician_client: APIClient, authenticated_client: APIClient
    ) -> None:
        order = _create_order(authenticated_client, "12MWF201", "1HGCM82633A008201")
        _move_to_workshop_assigned(authenticated_client, order["id"])

        accepted = technician_client.post(
            f"/api/v1/repair-orders/{order['id']}/accept/", {}, format="json"
        )
        assert accepted.status_code == 200, accepted.data
        assert accepted.data["status"] == "WAITING_WORKSHOP_CONFIRMATION"

        started = technician_client.post(
            f"/api/v1/repair-orders/{order['id']}/start/", {}, format="json"
        )
        assert started.status_code == 200, started.data
        assert started.data["status"] == "IN_PROGRESS"

    def test_internal_workshop_reject_cancels_order(
        self, technician_client: APIClient, authenticated_client: APIClient
    ) -> None:
        order = _create_order(authenticated_client, "12MWF202", "1HGCM82633A008202")
        _move_to_workshop_assigned(authenticated_client, order["id"])
        rejected = technician_client.post(
            f"/api/v1/repair-orders/{order['id']}/reject/", {}, format="json"
        )
        assert rejected.status_code == 200, rejected.data
        assert rejected.data["status"] == "CANCELLED"

    def test_create_and_list_material_requests(
        self, technician_client: APIClient, authenticated_client: APIClient
    ) -> None:
        order = _create_order(authenticated_client, "12MWF203", "1HGCM82633A008203")
        created = technician_client.post(
            f"/api/v1/repair-orders/{order['id']}/material-requests/",
            {
                "items": [
                    {
                        "material_number": "MAT000000000000001",
                        "quantity": "1",
                        "unit_of_measure": "EA",
                    }
                ]
            },
            format="json",
        )
        assert created.status_code == 201, created.data
        assert created.data["status"] == "REQUESTED"

        listed = technician_client.get("/api/v1/material-requests/")
        assert listed.status_code == 200, listed.data
        assert len(listed.data) >= 1

    def test_approve_material_request_stock_issued(
        self, supervisor_client: APIClient, authenticated_client: APIClient
    ) -> None:
        order = _create_order(authenticated_client, "12MWF204", "1HGCM82633A008204")
        created = authenticated_client.post(
            f"/api/v1/repair-orders/{order['id']}/material-requests/",
            {
                "items": [
                    {
                        "material_number": "MAT000000000000002",
                        "quantity": "1",
                        "unit_of_measure": "EA",
                    }
                ]
            },
            format="json",
        )
        assert created.status_code == 201, created.data
        approved = supervisor_client.post(
            f"/api/v1/material-requests/{created.data['id']}/approve/",
            {},
            format="json",
        )
        assert approved.status_code == 200, approved.data
        assert approved.data["status"] == "STOCK_ISSUED"

    def test_reject_material_request(
        self, supervisor_client: APIClient, authenticated_client: APIClient
    ) -> None:
        order = _create_order(authenticated_client, "12MWF205", "1HGCM82633A008205")
        created = authenticated_client.post(
            f"/api/v1/repair-orders/{order['id']}/material-requests/",
            {
                "items": [
                    {
                        "material_number": "MAT000000000000003",
                        "quantity": "2",
                        "unit_of_measure": "EA",
                    }
                ]
            },
            format="json",
        )
        rejected = supervisor_client.post(
            f"/api/v1/material-requests/{created.data['id']}/reject/", {}, format="json"
        )
        assert rejected.status_code == 200, rejected.data
        assert rejected.data["status"] == "REJECTED"

    def test_complete_creates_handover_waiting_driver_confirmation(
        self, technician_client: APIClient, authenticated_client: APIClient
    ) -> None:
        order = _create_order(authenticated_client, "12MWF206", "1HGCM82633A008206")
        _move_to_workshop_assigned(authenticated_client, order["id"])
        technician_client.post(
            f"/api/v1/repair-orders/{order['id']}/accept/", {}, format="json"
        )
        technician_client.post(
            f"/api/v1/repair-orders/{order['id']}/start/", {}, format="json"
        )
        completed = technician_client.post(
            f"/api/v1/repair-orders/{order['id']}/complete/",
            {"completed_at": datetime.now(tz=UTC).isoformat()},
            format="json",
        )
        assert completed.status_code == 200, completed.data
        assert completed.data["status"] == "WAITING_DRIVER_CONFIRMATION"

        handovers = technician_client.get("/api/v1/vehicle-handovers/")
        assert handovers.status_code == 200
        assert any(item["repair_order_id"] == order["id"] for item in handovers.data)

    def test_driver_handover_accepts_repair(
        self, technician_client: APIClient, authenticated_client: APIClient
    ) -> None:
        order = _create_order(authenticated_client, "12MWF207", "1HGCM82633A008207")
        _move_to_workshop_assigned(authenticated_client, order["id"])
        technician_client.post(
            f"/api/v1/repair-orders/{order['id']}/accept/", {}, format="json"
        )
        technician_client.post(
            f"/api/v1/repair-orders/{order['id']}/start/", {}, format="json"
        )
        technician_client.post(
            f"/api/v1/repair-orders/{order['id']}/complete/",
            {"completed_at": datetime.now(tz=UTC).isoformat()},
            format="json",
        )
        handovers = technician_client.get("/api/v1/vehicle-handovers/")
        target = next(
            item for item in handovers.data if item["repair_order_id"] == order["id"]
        )
        confirmed = technician_client.post(
            f"/api/v1/vehicle-handovers/{target['id']}/confirm/",
            {"accepted": True, "comment": "ok"},
            format="json",
        )
        assert confirmed.status_code == 200, confirmed.data
        assert confirmed.data["status"] == "ACCEPTED"

        repair = technician_client.get(f"/api/v1/repair-orders/{order['id']}/")
        assert repair.status_code == 200
        assert repair.data["status"] == "ACCEPTED_BY_DRIVER"

    def test_external_invoice_upload_list_and_approve(
        self, supervisor_client: APIClient, authenticated_client: APIClient
    ) -> None:
        order = _create_order(authenticated_client, "12MWF208", "1HGCM82633A008208")
        uploaded = authenticated_client.post(
            f"/api/v1/repair-orders/{order['id']}/invoice/",
            {"amount": "500000.00", "currency": "IRR"},
            format="json",
        )
        assert uploaded.status_code == 201, uploaded.data
        assert uploaded.data["status"] == "UPLOADED"

        listed = authenticated_client.get("/api/v1/external-invoices/")
        assert listed.status_code == 200, listed.data
        assert any(item["id"] == uploaded.data["id"] for item in listed.data)

        approved = supervisor_client.post(
            f"/api/v1/external-invoices/{uploaded.data['id']}/approve/",
            {},
            format="json",
        )
        assert approved.status_code == 200, approved.data
        assert approved.data["status"] == "APPROVED"

    def test_approve_material_unavailable_creates_pr(
        self,
        supervisor_client: APIClient,
        authenticated_client: APIClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("FMMS_INVENTORY_AVAILABLE_DEFAULT", "false")
        order = _create_order(authenticated_client, "12MWF209", "1HGCM82633A008209")
        created = authenticated_client.post(
            f"/api/v1/repair-orders/{order['id']}/material-requests/",
            {
                "items": [
                    {
                        "material_number": "000000000000000009",
                        "quantity": "1",
                        "unit_of_measure": "EA",
                    }
                ]
            },
            format="json",
        )
        assert created.status_code == 201, created.data
        approved = supervisor_client.post(
            f"/api/v1/material-requests/{created.data['id']}/approve/",
            {},
            format="json",
        )
        assert approved.status_code == 200, approved.data
        assert approved.data["status"] == "PURCHASE_REQUIRED"

        prs = authenticated_client.get(
            f"/api/v1/purchase-requisitions/?repair_order_id={order['id']}"
        )
        assert prs.status_code == 200, prs.data
        results = prs.data["results"] if "results" in prs.data else prs.data
        assert len(results) >= 1
        assert any(
            str(item.get("material_request_id")) == str(created.data["id"])
            and str(item.get("repair_order_id")) == str(order["id"])
            for item in results
        )

    def test_driver_reject_creates_follow_up_repair(
        self, technician_client: APIClient, authenticated_client: APIClient
    ) -> None:
        order = _create_order(authenticated_client, "12MWF210", "1HGCM82633A008210")
        _move_to_workshop_assigned(authenticated_client, order["id"])
        technician_client.post(
            f"/api/v1/repair-orders/{order['id']}/accept/", {}, format="json"
        )
        technician_client.post(
            f"/api/v1/repair-orders/{order['id']}/start/", {}, format="json"
        )
        technician_client.post(
            f"/api/v1/repair-orders/{order['id']}/complete/",
            {"completed_at": datetime.now(tz=UTC).isoformat()},
            format="json",
        )
        handovers = technician_client.get("/api/v1/vehicle-handovers/")
        target = next(
            item for item in handovers.data if item["repair_order_id"] == order["id"]
        )
        rejected = technician_client.post(
            f"/api/v1/vehicle-handovers/{target['id']}/confirm/",
            {"accepted": False, "comment": "not fixed"},
            format="json",
        )
        assert rejected.status_code == 200, rejected.data
        assert rejected.data["status"] == "REJECTED"

        repair = technician_client.get(f"/api/v1/repair-orders/{order['id']}/")
        assert repair.status_code == 200
        assert repair.data["status"] == "REJECTED_BY_DRIVER"

        vehicle = technician_client.get(f"/api/v1/vehicles/{order['vehicle_id']}/")
        assert vehicle.status_code == 200
        assert vehicle.data["status"] == "WAITING_DRIVER_CONFIRMATION"

        listed = technician_client.get(
            f"/api/v1/repair-orders/?vehicle_id={order['vehicle_id']}"
        )
        assert listed.status_code == 200
        results = listed.data["results"] if "results" in listed.data else listed.data
        created_follow_ups = [
            item
            for item in results
            if item["status"] == "CREATED" and item["id"] != order["id"]
        ]
        assert len(created_follow_ups) == 1
        assert created_follow_ups[0]["fault_id"] == order["fault_id"]

        faults = technician_client.get(
            f"/api/v1/faults/?vehicle_id={order['vehicle_id']}"
        )
        assert faults.status_code == 200
        fault_results = (
            faults.data["results"] if "results" in faults.data else faults.data
        )
        assert len(fault_results) == 1

    def test_viewer_cannot_accept_repair(
        self, authenticated_client: APIClient, viewer_client: APIClient
    ) -> None:
        order = _create_order(authenticated_client, "12MWF211", "1HGCM82633A008211")
        _move_to_workshop_assigned(authenticated_client, order["id"])
        response = viewer_client.post(
            f"/api/v1/repair-orders/{order['id']}/accept/", {}, format="json"
        )
        assert response.status_code == 403

    def test_invalid_complete_before_start_returns_422(
        self, authenticated_client: APIClient
    ) -> None:
        order = _create_order(authenticated_client, "12MWF212", "1HGCM82633A008212")
        _move_to_workshop_assigned(authenticated_client, order["id"])
        response = authenticated_client.post(
            f"/api/v1/repair-orders/{order['id']}/complete/",
            {"completed_at": datetime.now(tz=UTC).isoformat()},
            format="json",
        )
        assert response.status_code == 422

    def test_internal_workshop_happy_path_to_active(
        self, technician_client: APIClient, authenticated_client: APIClient
    ) -> None:
        order = _create_order(authenticated_client, "12MWF213", "1HGCM82633A008213")
        vehicle_id = order["vehicle_id"]
        _move_to_workshop_assigned(authenticated_client, order["id"])
        assert (
            technician_client.post(
                f"/api/v1/repair-orders/{order['id']}/accept/", {}, format="json"
            ).status_code
            == 200
        )
        assert (
            technician_client.post(
                f"/api/v1/repair-orders/{order['id']}/start/", {}, format="json"
            ).status_code
            == 200
        )
        vehicle_under_repair = authenticated_client.get(
            f"/api/v1/vehicles/{vehicle_id}/"
        )
        assert vehicle_under_repair.data["status"] == "UNDER_REPAIR"

        material = technician_client.post(
            f"/api/v1/repair-orders/{order['id']}/material-requests/",
            {
                "items": [
                    {
                        "material_number": "MAT000000000000013",
                        "quantity": "1",
                        "unit_of_measure": "EA",
                    }
                ]
            },
            format="json",
        )
        assert material.status_code == 201, material.data
        approved = authenticated_client.post(
            f"/api/v1/material-requests/{material.data['id']}/approve/",
            {},
            format="json",
        )
        assert approved.status_code == 200, approved.data
        assert approved.data["status"] == "STOCK_ISSUED"

        completed = technician_client.post(
            f"/api/v1/repair-orders/{order['id']}/complete/",
            {"completed_at": datetime.now(tz=UTC).isoformat()},
            format="json",
        )
        assert completed.status_code == 200, completed.data
        assert completed.data["status"] == "WAITING_DRIVER_CONFIRMATION"

        handovers = technician_client.get("/api/v1/vehicle-handovers/")
        target = next(
            item for item in handovers.data if item["repair_order_id"] == order["id"]
        )
        confirmed = technician_client.post(
            f"/api/v1/vehicle-handovers/{target['id']}/confirm/",
            {"accepted": True, "comment": "ok"},
            format="json",
        )
        assert confirmed.status_code == 200, confirmed.data

        repair = technician_client.get(f"/api/v1/repair-orders/{order['id']}/")
        assert repair.data["status"] == "ACCEPTED_BY_DRIVER"
        vehicle = authenticated_client.get(f"/api/v1/vehicles/{vehicle_id}/")
        assert vehicle.data["status"] == "ACTIVE"
