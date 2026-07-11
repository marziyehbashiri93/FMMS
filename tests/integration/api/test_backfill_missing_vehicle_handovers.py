"""Integration tests for backfill_missing_vehicle_handovers management command."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.handover.infrastructure.models import VehicleHandoverModel
from apps.repair.infrastructure.models import RepairOrderModel
from apps.vehicle.domain.entities import VehicleStatus
from apps.vehicle.infrastructure.models import VehicleModel
from tests.integration.api.conftest import create_vehicle

pytestmark = pytest.mark.django_db


class TestBackfillMissingVehicleHandoversCommand:
    """Repair orphaned WAITING_DRIVER_CONFIRMATION rows without handovers."""

    def test_backfill_creates_handover_for_orphaned_repair_order(
        self, technician_client: APIClient, authenticated_client: APIClient
    ) -> None:
        vehicle = create_vehicle(
            authenticated_client, plate="12BFLL01", vin="1HGCM82633A004501"
        )
        inspection = authenticated_client.post(
            "/api/v1/inspections/",
            {
                "vehicle_id": vehicle["id"],
                "inspection_type": "PRE_TRIP",
                "odometer_value": 900,
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

        deactivated = authenticated_client.post(
            f"/api/v1/vehicles/{vehicle['id']}/deactivate/", {}, format="json"
        )
        assert deactivated.status_code == 200, deactivated.data

        orders = authenticated_client.get(
            f"/api/v1/repair-orders/?vehicle_id={vehicle['id']}"
        )
        order = orders.data["results"][0]
        order_id = order["id"]

        for step in (
            lambda: authenticated_client.post(
                f"/api/v1/repair-orders/{order_id}/approve/", {}, format="json"
            ),
            lambda: authenticated_client.post(
                f"/api/v1/repair-orders/{order_id}/assign-workshop/",
                {"workshop_type": "INTERNAL", "workshop_id": "WS-001"},
                format="json",
            ),
            lambda: technician_client.post(
                f"/api/v1/repair-orders/{order_id}/accept/", {}, format="json"
            ),
            lambda: technician_client.post(
                f"/api/v1/repair-orders/{order_id}/start/", {}, format="json"
            ),
        ):
            response = step()
            assert response.status_code == 200, response.data

        ro = RepairOrderModel.objects.get(id=order_id)
        ro.status = VehicleStatus.WAITING_DRIVER_CONFIRMATION.value
        ro.completed_at = datetime.now(tz=UTC)
        ro.save(update_fields=["status", "completed_at", "updated_at"])
        VehicleHandoverModel.objects.filter(repair_order_id=order_id).delete()

        assert (
            VehicleHandoverModel.objects.filter(repair_order_id=order_id).count() == 0
        )

        call_command("backfill_missing_vehicle_handovers")

        assert (
            VehicleHandoverModel.objects.filter(repair_order_id=order_id).count() == 1
        )
        handover = VehicleHandoverModel.objects.get(repair_order_id=order_id)
        assert handover.status == VehicleStatus.WAITING_DRIVER_CONFIRMATION.value

        vehicle_orm = VehicleModel.objects.get(id=vehicle["id"])
        assert vehicle_orm.status == VehicleStatus.WAITING_DRIVER_CONFIRMATION.value

        call_command("backfill_missing_vehicle_handovers")
        assert (
            VehicleHandoverModel.objects.filter(repair_order_id=order_id).count() == 1
        )
