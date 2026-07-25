"""Integration tests for maintenance workflow v2 APIs."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from rest_framework.test import APIClient

from tests.integration.api.conftest import (
    create_repair_order_via_distribution,
    create_vehicle,
)

pytestmark = pytest.mark.django_db


def _create_order(client: APIClient, plate: str, vin: str) -> dict:
    """Create repair order with prerequisite vehicle and fault."""
    return create_repair_order_via_distribution(
        client,
        plate=plate,
        vin=vin,
        code="MWF2",
        description="Maintenance workflow v2 fault",
    )


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


def _move_to_accepted_by_driver(
    client: APIClient, technician_client: APIClient, order: dict
) -> dict:
    """Run internal repair through driver acceptance and final transport wait."""
    del technician_client
    _move_to_workshop_assigned(client, order["id"])
    accepted = client.post(
        f"/api/v1/repair-orders/{order['id']}/accept/", {}, format="json"
    )
    assert accepted.status_code == 200, accepted.data
    assert accepted.data["status"] == "IN_PROGRESS"
    completed = client.post(
        f"/api/v1/repair-orders/{order['id']}/complete/",
        {"completed_at": datetime.now(tz=UTC).isoformat()},
        format="json",
    )
    assert completed.status_code == 200, completed.data
    handovers = client.get("/api/v1/vehicle-handovers/")
    target = next(
        item for item in handovers.data if item["repair_order_id"] == order["id"]
    )
    confirmed = client.post(
        f"/api/v1/vehicle-handovers/{target['id']}/confirm/",
        {"accepted": True, "comment": "ok"},
        format="json",
    )
    assert confirmed.status_code == 200, confirmed.data
    return order


def _confirm_driver_handover(
    client: APIClient,
    order_id: str,
    *,
    invoice: dict | None = None,
) -> dict:
    """Confirm the handover for a repair order."""
    handovers = client.get("/api/v1/vehicle-handovers/")
    assert handovers.status_code == 200, handovers.data
    target = next(
        item for item in handovers.data if item["repair_order_id"] == order_id
    )
    payload: dict = {"accepted": True, "comment": "ok"}
    if invoice:
        payload.update(invoice)
    confirmed = client.post(
        f"/api/v1/vehicle-handovers/{target['id']}/confirm/",
        payload,
        format="json",
    )
    assert confirmed.status_code == 200, confirmed.data
    return confirmed.data


class TestMaintenanceWorkflowV2API:
    """Maintenance workflow v2 end-to-end scenarios."""

    def test_internal_workshop_accept_and_start(
        self,
        workshop_supervisor_client: APIClient,
        authenticated_client: APIClient,
    ) -> None:
        order = _create_order(authenticated_client, "12MWF201", "1HGCM82633A008201")
        _move_to_workshop_assigned(authenticated_client, order["id"])

        accepted = workshop_supervisor_client.post(
            f"/api/v1/repair-orders/{order['id']}/accept/", {}, format="json"
        )
        assert accepted.status_code == 200, accepted.data
        assert accepted.data["status"] == "IN_PROGRESS"

        retrieved = authenticated_client.get(f"/api/v1/repair-orders/{order['id']}/")
        assert retrieved.status_code == 200
        assert retrieved.data["sap_order_number"]

    def test_internal_workshop_reject_cancels_order(
        self,
        workshop_supervisor_client: APIClient,
        authenticated_client: APIClient,
    ) -> None:
        order = _create_order(authenticated_client, "12MWF202", "1HGCM82633A008202")
        _move_to_workshop_assigned(authenticated_client, order["id"])
        rejected = workshop_supervisor_client.post(
            f"/api/v1/repair-orders/{order['id']}/reject/", {}, format="json"
        )
        assert rejected.status_code == 200, rejected.data
        assert rejected.data["status"] == "NO_REPAIR_NEEDED"

    def test_create_and_list_material_requests(
        self, technician_client: APIClient, authenticated_client: APIClient
    ) -> None:
        order = _create_order(authenticated_client, "12MWF203", "1HGCM82633A008203")
        _move_to_workshop_assigned(authenticated_client, order["id"])
        accepted = authenticated_client.post(
            f"/api/v1/repair-orders/{order['id']}/accept/", {}, format="json"
        )
        assert accepted.status_code == 200, accepted.data
        created = authenticated_client.post(
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
        _move_to_workshop_assigned(authenticated_client, order["id"])
        accepted = authenticated_client.post(
            f"/api/v1/repair-orders/{order['id']}/accept/", {}, format="json"
        )
        assert accepted.status_code == 200, accepted.data
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

    def test_per_item_availability_decision_purchase(
        self, supervisor_client: APIClient, authenticated_client: APIClient
    ) -> None:
        order = _create_order(authenticated_client, "12MWF205", "1HGCM82633A008205")
        _move_to_workshop_assigned(authenticated_client, order["id"])
        accepted = authenticated_client.post(
            f"/api/v1/repair-orders/{order['id']}/accept/", {}, format="json"
        )
        assert accepted.status_code == 200, accepted.data
        created = authenticated_client.post(
            f"/api/v1/repair-orders/{order['id']}/material-requests/",
            {
                "items": [
                    {
                        "material_number": "252800000000000003",
                        "quantity": "2",
                        "from_catalog": False,
                    }
                ]
            },
            format="json",
        )
        assert created.status_code == 201, created.data
        item_id = created.data["items"][0]["id"]
        decided = supervisor_client.post(
            f"/api/v1/material-requests/{created.data['id']}/availability-decision/",
            {
                "note": "not in warehouse",
                "items": [{"item_id": item_id, "decision": "PURCHASE"}],
            },
            format="json",
        )
        assert decided.status_code == 200, decided.data
        assert decided.data["status"] == "PURCHASE_REQUIRED"
        assert decided.data["items"][0]["decision"] == "PURCHASE"
        assert decided.data["items"][0]["item_status"] == "PURCHASE_REQUIRED"

        missing = supervisor_client.post(
            f"/api/v1/material-requests/{created.data['id']}/reject/", {}, format="json"
        )
        assert missing.status_code == 404

    def test_complete_creates_handover_waiting_driver_confirmation(
        self, technician_client: APIClient, authenticated_client: APIClient
    ) -> None:
        order = _create_order(authenticated_client, "12MWF206", "1HGCM82633A008206")
        _move_to_workshop_assigned(authenticated_client, order["id"])
        authenticated_client.post(
            f"/api/v1/repair-orders/{order['id']}/accept/", {}, format="json"
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
        authenticated_client.post(
            f"/api/v1/repair-orders/{order['id']}/accept/", {}, format="json"
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
        assert repair.data["status"] == "WAITING_TRANSPORT_FINAL_APPROVAL"

        vehicle = technician_client.get(f"/api/v1/vehicles/{order['vehicle_id']}/")
        assert vehicle.status_code == 200
        assert vehicle.data["status"] == "WAITING_DRIVER_CONFIRMATION"

    def test_transport_handover_approve_completes_repair_and_closes_fault(
        self,
        supervisor_client: APIClient,
        technician_client: APIClient,
        authenticated_client: APIClient,
    ) -> None:
        order = _create_order(authenticated_client, "12MWF214", "1HGCM82633A008214")
        _move_to_accepted_by_driver(authenticated_client, technician_client, order)

        approved = supervisor_client.post(
            f"/api/v1/repair-orders/{order['id']}/transport-handover-approve/",
            {},
            format="json",
        )
        assert approved.status_code == 200, approved.data
        assert approved.data["status"] == "COMPLETED"

        repair = authenticated_client.get(f"/api/v1/repair-orders/{order['id']}/")
        assert repair.data["status"] == "COMPLETED"

        fault = authenticated_client.get(f"/api/v1/faults/{order['fault_id']}/")
        assert fault.status_code == 200
        assert fault.data["status"] == "CLOSED"

        vehicle = authenticated_client.get(f"/api/v1/vehicles/{order['vehicle_id']}/")
        assert vehicle.status_code == 200
        assert vehicle.data["status"] == "ACTIVE"

    def test_transport_handover_reject_creates_follow_up_repair(
        self,
        supervisor_client: APIClient,
        technician_client: APIClient,
        authenticated_client: APIClient,
    ) -> None:
        order = _create_order(authenticated_client, "12MWF215", "1HGCM82633A008215")
        vehicle_id = order["vehicle_id"]
        _move_to_accepted_by_driver(authenticated_client, technician_client, order)

        rejected = supervisor_client.post(
            f"/api/v1/repair-orders/{order['id']}/transport-handover-reject/",
            {"comment": "not fixed properly"},
            format="json",
        )
        assert rejected.status_code == 200, rejected.data
        assert rejected.data["status"] == "COMPLETED"

        vehicle = authenticated_client.get(f"/api/v1/vehicles/{vehicle_id}/")
        assert vehicle.data["status"] == "UNDER_REPAIR"

        listed = authenticated_client.get(
            f"/api/v1/repair-orders/?vehicle_id={vehicle_id}"
        )
        results = listed.data["results"] if "results" in listed.data else listed.data
        follow_ups = [
            item
            for item in results
            if item["status"] == "CREATED" and item["id"] != order["id"]
        ]
        assert len(follow_ups) == 1
        assert follow_ups[0]["fault_id"] == order["fault_id"]

    def test_viewer_cannot_approve_transport_handover(
        self,
        viewer_client: APIClient,
        technician_client: APIClient,
        authenticated_client: APIClient,
    ) -> None:
        order = _create_order(authenticated_client, "12MWF216", "1HGCM82633A008216")
        _move_to_accepted_by_driver(authenticated_client, technician_client, order)
        response = viewer_client.post(
            f"/api/v1/repair-orders/{order['id']}/transport-handover-approve/",
            {},
            format="json",
        )
        assert response.status_code == 403

    def test_external_workshop_assignment_creates_referral_request(
        self,
        supervisor_client: APIClient,
        authenticated_client: APIClient,
    ) -> None:
        order = _create_order(authenticated_client, "12MWF208", "1HGCM82633A008208")
        approved = authenticated_client.post(
            f"/api/v1/repair-orders/{order['id']}/approve/", {}, format="json"
        )
        assert approved.status_code == 200, approved.data

        assigned = authenticated_client.post(
            f"/api/v1/repair-orders/{order['id']}/assign-workshop/",
            {
                "workshop_type": "EXTERNAL",
                "workshop_id": "EXT-001",
                "reason": "Central workshop unavailable",
            },
            format="json",
        )
        assert assigned.status_code == 200, assigned.data
        assert assigned.data["workshop_type"] == "EXTERNAL"
        assert assigned.data["status"] == "WAITING_EXTERNAL_REFERRAL_APPROVAL"
        assert assigned.data["external_referral_request_id"]

        repair_after_assign = authenticated_client.get(
            f"/api/v1/repair-orders/{order['id']}/"
        )
        assert (
            repair_after_assign.data["status"] == "WAITING_EXTERNAL_REFERRAL_APPROVAL"
        )

        vehicle_after_assign = authenticated_client.get(
            f"/api/v1/vehicles/{order['vehicle_id']}/"
        )
        # Distribution-unusable parks the vehicle OUT_OF_SERVICE until later stages.
        assert vehicle_after_assign.data["status"] == "OUT_OF_SERVICE"

        listed = supervisor_client.get("/api/v1/external-workshop-referrals/")
        assert listed.status_code == 200, listed.data
        referral_results = (
            listed.data["results"] if "results" in listed.data else listed.data
        )
        referral = next(
            item for item in referral_results if item["repair_order_id"] == order["id"]
        )
        assert referral["status"] == "REQUESTED"
        assert referral["workshop_id"] == "EXT-001"

    def test_approve_material_unavailable_creates_pr(
        self,
        supervisor_client: APIClient,
        authenticated_client: APIClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("FMMS_INVENTORY_AVAILABLE_DEFAULT", "false")
        order = _create_order(authenticated_client, "12MWF209", "1HGCM82633A008209")
        _move_to_workshop_assigned(authenticated_client, order["id"])
        accepted = authenticated_client.post(
            f"/api/v1/repair-orders/{order['id']}/accept/", {}, format="json"
        )
        assert accepted.status_code == 200, accepted.data
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
        authenticated_client.post(
            f"/api/v1/repair-orders/{order['id']}/accept/", {}, format="json"
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
            authenticated_client.post(
                f"/api/v1/repair-orders/{order['id']}/accept/", {}, format="json"
            ).status_code
            == 200
        )
        vehicle_under_repair = authenticated_client.get(
            f"/api/v1/vehicles/{vehicle_id}/"
        )
        assert vehicle_under_repair.data["status"] == "UNDER_REPAIR"

        material = authenticated_client.post(
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
        received = authenticated_client.post(
            f"/api/v1/material-requests/{material.data['id']}/receive/",
            {},
            format="json",
        )
        assert received.status_code == 200, received.data
        assert received.data["status"] == "RECEIVED"

        completed = authenticated_client.post(
            f"/api/v1/repair-orders/{order['id']}/complete/",
            {
                "completed_at": datetime.now(tz=UTC).isoformat(),
                "no_parts_consumed": True,
            },
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
        assert repair.data["status"] == "WAITING_TRANSPORT_FINAL_APPROVAL"
        vehicle = authenticated_client.get(f"/api/v1/vehicles/{vehicle_id}/")
        assert vehicle.data["status"] == "WAITING_DRIVER_CONFIRMATION"

        final_approved = authenticated_client.post(
            f"/api/v1/repair-orders/{order['id']}/transport-handover-approve/",
            {},
            format="json",
        )
        assert final_approved.status_code == 200, final_approved.data
        vehicle = authenticated_client.get(f"/api/v1/vehicles/{vehicle_id}/")
        assert vehicle.data["status"] == "ACTIVE"

    def test_inactive_vehicle_full_workflow_creates_handover(
        self, technician_client: APIClient, authenticated_client: APIClient
    ) -> None:
        """Failed inspection → deactivate → repair → complete must create handover."""
        vehicle = create_vehicle(
            authenticated_client, plate="12MWF301", vin="1HGCM82633A008301"
        )
        inspection = authenticated_client.post(
            "/api/v1/inspections/",
            {
                "vehicle_id": vehicle["id"],
                "inspection_type": "PRE_TRIP",
                "odometer_value": 1200,
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
        assert inspection.status_code == 201, inspection.data

        submitted = authenticated_client.post(
            f"/api/v1/inspections/{inspection.data['id']}/submit/", {}, format="json"
        )
        assert submitted.status_code == 200, submitted.data
        assert submitted.data["has_failures"] is True

        reported = authenticated_client.post(
            f"/api/v1/inspections/{inspection.data['id']}/report-fault/",
            {},
            format="json",
        )
        assert reported.status_code == 201, reported.data

        unusable = authenticated_client.post(
            f"/api/v1/faults/{reported.data['id']}/distribution-unusable/",
            {"note": "needs repair"},
            format="json",
        )
        assert unusable.status_code == 200, unusable.data

        deactivated = authenticated_client.post(
            f"/api/v1/vehicles/{vehicle['id']}/status/",
            {"status": "INACTIVE"},
            format="json",
        )
        assert deactivated.status_code == 200, deactivated.data
        assert deactivated.data["status"] == "INACTIVE"

        orders = authenticated_client.get(
            f"/api/v1/repair-orders/?vehicle_id={vehicle['id']}"
        )
        assert orders.status_code == 200, orders.data
        assert orders.data["count"] == 1
        order = orders.data["results"][0]

        approved = authenticated_client.post(
            f"/api/v1/repair-orders/{order['id']}/approve/", {}, format="json"
        )
        assert approved.status_code == 200, approved.data

        assigned = authenticated_client.post(
            f"/api/v1/repair-orders/{order['id']}/assign-workshop/",
            {"workshop_type": "INTERNAL", "workshop_id": "WS-001"},
            format="json",
        )
        assert assigned.status_code == 200, assigned.data

        accepted = authenticated_client.post(
            f"/api/v1/repair-orders/{order['id']}/accept/", {}, format="json"
        )
        assert accepted.status_code == 200, accepted.data
        assert accepted.data["status"] == "IN_PROGRESS"

        vehicle_after_start = authenticated_client.get(
            f"/api/v1/vehicles/{vehicle['id']}/"
        )
        assert vehicle_after_start.data["status"] == "UNDER_REPAIR"

        completed = technician_client.post(
            f"/api/v1/repair-orders/{order['id']}/complete/",
            {"completed_at": datetime.now(tz=UTC).isoformat()},
            format="json",
        )
        assert completed.status_code == 200, completed.data
        assert completed.data["status"] == "WAITING_DRIVER_CONFIRMATION"

        vehicle_after_complete = authenticated_client.get(
            f"/api/v1/vehicles/{vehicle['id']}/"
        )
        assert vehicle_after_complete.data["status"] == "WAITING_DRIVER_CONFIRMATION"

        handovers = technician_client.get("/api/v1/vehicle-handovers/")
        assert handovers.status_code == 200, handovers.data
        target = next(
            item for item in handovers.data if item["repair_order_id"] == order["id"]
        )
        assert target["status"] == "WAITING_DRIVER_CONFIRMATION"

        timeline = technician_client.get(
            f"/api/v1/repair-orders/{order['id']}/timeline/"
        )
        assert timeline.status_code == 200, timeline.data
        event_types = {item["event"] for item in timeline.data}
        assert "REPAIR_STARTED" in event_types
        assert "REPAIR_COMPLETED" in event_types
        assert "WAITING_DRIVER_CONFIRMATION" in event_types
