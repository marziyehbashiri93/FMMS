"""API integration tests for inspection endpoints."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from rest_framework.test import APIClient

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
