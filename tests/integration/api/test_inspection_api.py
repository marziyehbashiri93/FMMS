"""API integration tests for inspection endpoints."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from rest_framework.test import APIClient

from apps.fault.infrastructure.models import FaultModel
from apps.repair.infrastructure.models import RepairOrderModel
from tests.integration.api.conftest import create_vehicle

pytestmark = pytest.mark.django_db


class TestInspectionAPI:
    """Cover inspection create, item add, and submit flows."""

    def test_create_add_item_submit(self, authenticated_client: APIClient) -> None:
        """Create an inspection, add an item, and submit it."""
        vehicle = create_vehicle(
            authenticated_client, plate="12INSP01", vin="1HGCM82633A004354"
        )
        created = authenticated_client.post(
            "/api/v1/inspections/",
            {
                "vehicle_id": vehicle["id"],
                "inspection_type": "PRE_TRIP",
                "odometer_value": 12000,
                "odometer_unit": "KM",
                "inspected_at": datetime.now(tz=UTC).isoformat(),
            },
            format="json",
        )
        assert created.status_code == 201, created.data
        inspection_id = created.data["id"]
        assert created.data["status"] == "DRAFT"

        with_item = authenticated_client.post(
            f"/api/v1/inspections/{inspection_id}/items/",
            {
                "category": "Brakes",
                "description": "Pad thickness",
                "result": "PASS",
            },
            format="json",
        )
        assert with_item.status_code == 200, with_item.data
        assert len(with_item.data["items"]) == 1

        submitted = authenticated_client.post(
            f"/api/v1/inspections/{inspection_id}/submit/",
            {},
            format="json",
        )
        assert submitted.status_code == 200, submitted.data
        assert submitted.data["status"] != "DRAFT"

        listed = authenticated_client.get(
            f"/api/v1/inspections/?vehicle_id={vehicle['id']}"
        )
        assert listed.status_code == 200
        assert listed.data["count"] >= 1

        inspected_at = submitted.data["inspected_at"][:10]
        ranged = authenticated_client.get(
            f"/api/v1/inspections/?vehicle_id={vehicle['id']}"
            f"&from_date={inspected_at}&to_date={inspected_at}"
        )
        assert ranged.status_code == 200, ranged.data
        assert ranged.data["count"] >= 1

        invalid = authenticated_client.get(
            f"/api/v1/inspections/?vehicle_id={vehicle['id']}"
            "&from_date=2026-07-20&to_date=2026-07-10"
        )
        assert invalid.status_code == 400
        assert "to_date" in invalid.data.get("details", invalid.data)

    def test_failed_checklist_requires_explicit_fault_report(
        self, authenticated_client: APIClient
    ) -> None:
        """Submitting a failed checklist does not create a fault until requested."""
        vehicle = create_vehicle(
            authenticated_client,
            plate="12FAIL01",
            vin="1HGCM82633A004355",
        )
        created = authenticated_client.post(
            "/api/v1/inspections/",
            {
                "vehicle_id": vehicle["id"],
                "inspection_type": "PRE_TRIP",
                "odometer_value": 12000,
                "odometer_unit": "KM",
                "inspected_at": datetime.now(tz=UTC).isoformat(),
                "items": [
                    {
                        "category": "Brakes",
                        "description": "Pad thickness",
                        "result": "FAIL",
                        "notes": "Pad worn",
                        "severity": "HIGH",
                    }
                ],
            },
            format="json",
        )
        assert created.status_code == 201, created.data
        inspection_id = created.data["id"]

        submitted = authenticated_client.post(
            f"/api/v1/inspections/{inspection_id}/submit/",
            {},
            format="json",
        )
        assert submitted.status_code == 200, submitted.data
        assert submitted.data["has_failures"] is True
        assert FaultModel.objects.filter(inspection_id=inspection_id).count() == 0

        reported = authenticated_client.post(
            f"/api/v1/inspections/{inspection_id}/report-fault/",
            {},
            format="json",
        )

        assert reported.status_code == 201, reported.data
        assert reported.data["inspection_id"] == inspection_id
        assert len(reported.data["items"]) == 1
        assert FaultModel.objects.filter(inspection_id=inspection_id).count() == 1
        assert (
            RepairOrderModel.objects.filter(fault_id=reported.data["id"]).count() == 0
        )
