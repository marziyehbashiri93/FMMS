"""API integration tests for fault endpoints."""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.vehicle.infrastructure.models import VehicleModel
from tests.integration.api.conftest import create_vehicle

pytestmark = pytest.mark.django_db


class TestFaultAPI:
    """Cover fault report and close flow."""

    def test_report_and_close(self, authenticated_client: APIClient) -> None:
        """Report a fault and close it from OPEN."""
        vehicle = create_vehicle(
            authenticated_client, plate="12FLT001", vin="1HGCM82633A004355"
        )
        created = authenticated_client.post(
            "/api/v1/faults/",
            {
                "vehicle_id": vehicle["id"],
                "code": "BRK-01",
                "description": "Brake pad wear",
                "severity": "MEDIUM",
            },
            format="json",
        )
        assert created.status_code == 201, created.data
        fault_id = created.data["id"]
        assert created.data["status"] == "OPEN"

        listed = authenticated_client.get(f"/api/v1/faults/?vehicle_id={vehicle['id']}")
        assert listed.status_code == 200
        assert listed.data["count"] >= 1

        retrieved = authenticated_client.get(f"/api/v1/faults/{fault_id}/")
        assert retrieved.status_code == 200
        assert retrieved.data["code"] == "BRK-01"
        assert retrieved.data["items"] == []

        closed = authenticated_client.post(
            f"/api/v1/faults/{fault_id}/close/",
            {},
            format="json",
        )
        assert closed.status_code == 200, closed.data
        assert closed.data["status"] == "CLOSED"

    def test_report_multiple_items_as_one_fault(
        self, authenticated_client: APIClient
    ) -> None:
        """Several catalog defects can be reported as one open fault."""
        vehicle = create_vehicle(
            authenticated_client, plate="12FLT003", vin="1HGCM82633A004357"
        )
        created = authenticated_client.post(
            "/api/v1/faults/",
            {
                "vehicle_id": vehicle["id"],
                "code": "MULTI",
                "description": "ثبت همزمان چند خرابی",
                "severity": "MEDIUM",
                "items": [
                    {
                        "code": "BRK-01",
                        "description": "لنت ترمز",
                        "severity": "MEDIUM",
                        "component": "ترمز",
                    },
                    {
                        "code": "LGT-01",
                        "description": "چراغ جلو",
                        "severity": "HIGH",
                        "component": "چراغ",
                    },
                ],
            },
            format="json",
        )
        assert created.status_code == 201, created.data
        assert created.data["severity"] == "HIGH"
        assert len(created.data["items"]) == 2

    def test_report_fault_keeps_active_vehicle_until_distribution_decision(
        self, authenticated_client: APIClient
    ) -> None:
        """Reporting a fault must not move the vehicle to UNDER_REPAIR yet."""
        vehicle = create_vehicle(
            authenticated_client, plate="12FLT002", vin="1HGCM82633A004356"
        )

        created = authenticated_client.post(
            "/api/v1/faults/",
            {
                "vehicle_id": vehicle["id"],
                "code": "ENG-01",
                "description": "Engine failure",
                "severity": "HIGH",
            },
            format="json",
        )

        assert created.status_code == 201, created.data
        assert VehicleModel.objects.get(id=vehicle["id"]).status == "ACTIVE"

    def test_list_all_faults_for_distribution_queue(
        self, authenticated_client: APIClient
    ) -> None:
        vehicle = create_vehicle(
            authenticated_client, plate="12FLT004", vin="1HGCM82633A004358"
        )
        created = authenticated_client.post(
            "/api/v1/faults/",
            {
                "vehicle_id": vehicle["id"],
                "code": "BRK-02",
                "description": "Brake vibration",
                "severity": "MEDIUM",
            },
            format="json",
        )
        assert created.status_code == 201, created.data

        listed = authenticated_client.get("/api/v1/faults/")

        assert listed.status_code == 200
        assert listed.data["count"] >= 1
        assert created.data["id"] in {item["id"] for item in listed.data["results"]}

    def test_distribution_marks_fault_vehicle_usable(
        self, authenticated_client: APIClient
    ) -> None:
        vehicle = create_vehicle(
            authenticated_client, plate="12FLT005", vin="1HGCM82633A004359"
        )
        created = authenticated_client.post(
            "/api/v1/faults/",
            {
                "vehicle_id": vehicle["id"],
                "code": "LGT-02",
                "description": "چراغ سالم است",
                "severity": "LOW",
            },
            format="json",
        )
        assert created.status_code == 201, created.data

        decision = authenticated_client.post(
            f"/api/v1/faults/{created.data['id']}/distribution-usable/",
            {"note": "خودرو قابل استفاده است"},
            format="json",
        )

        assert decision.status_code == 200, decision.data
        assert decision.data["status"] == "CLOSED"
        assert VehicleModel.objects.get(id=vehicle["id"]).status == "ACTIVE"

    def test_distribution_marks_fault_vehicle_unusable(
        self, authenticated_client: APIClient
    ) -> None:
        vehicle = create_vehicle(
            authenticated_client, plate="12FLT006", vin="1HGCM82633A004360"
        )
        VehicleModel.objects.filter(id=vehicle["id"]).update(
            driver1_customer_number="6000001001"
        )
        created = authenticated_client.post(
            "/api/v1/faults/",
            {
                "vehicle_id": vehicle["id"],
                "code": "ENG-02",
                "description": "خودرو قابل استفاده نیست",
                "severity": "HIGH",
            },
            format="json",
        )
        assert created.status_code == 201, created.data

        decision = authenticated_client.post(
            f"/api/v1/faults/{created.data['id']}/distribution-unusable/",
            {"note": "نیازمند خودرو جایگزین"},
            format="json",
        )

        assert decision.status_code == 200, decision.data
        assert decision.data["status"] == "AWAITING_TRANSPORT"
        assert VehicleModel.objects.get(id=vehicle["id"]).status == "OUT_OF_SERVICE"
