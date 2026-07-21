"""API integration tests for driver endpoints."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from rest_framework.test import APIClient

from apps.driver.domain.entities import DriverStatus
from apps.driver.infrastructure.models import DriverModel
from apps.vehicle.infrastructure.models import VehicleDriverAssignmentHistoryModel

pytestmark = pytest.mark.django_db


class TestDriverAPI:
    """Cover read-only driver API flows."""

    def test_manual_register_is_not_available(
        self,
        authenticated_client: APIClient,
    ) -> None:
        """Driver registration is SAP-sync driven, not a manual API action."""
        response = authenticated_client.post(
            "/api/v1/drivers/",
            {
                "customer_number": "6000001234",
                "name": "Ali Ahmadi",
                "mobile": "09123456789",
                "personnel_number": "21000001",
                "gender": "مذکر",
                "nilofar_code": "520000001",
            },
            format="json",
        )
        assert response.status_code == 405

    def test_read_driver_and_manual_actions_are_unavailable(
        self,
        authenticated_client: APIClient,
    ) -> None:
        """Driver records can be read, but manual mutation actions are unavailable."""
        driver = DriverModel.objects.create(
            customer_number="6000001234",
            name="Ali Ahmadi",
            mobile="09123456789",
            personnel_number="21000001",
            gender="مذکر",
            nilofar_code="520000001",
            status=DriverStatus.ACTIVE.value,
        )

        listed = authenticated_client.get("/api/v1/drivers/")
        assert listed.status_code == 200
        assert listed.data["count"] >= 1

        retrieved = authenticated_client.get(f"/api/v1/drivers/{driver.id}/")
        assert retrieved.status_code == 200
        assert retrieved.data["customer_number"] == "6000001234"

        assign = authenticated_client.post(
            f"/api/v1/drivers/{driver.id}/assign/",
            {"vehicle_id": "00000000-0000-0000-0000-000000000001"},
            format="json",
        )
        assert assign.status_code == 404

        suspended = authenticated_client.post(
            f"/api/v1/drivers/{driver.id}/suspend/",
            {},
            format="json",
        )
        assert suspended.status_code == 404

    def test_list_without_status_filter_returns_all_statuses(
        self,
        authenticated_client: APIClient,
    ) -> None:
        active = DriverModel.objects.create(
            customer_number="6000002234",
            name="Active Driver",
            status=DriverStatus.ACTIVE.value,
        )
        decommissioned = DriverModel.objects.create(
            customer_number="6000002235",
            name="Decommissioned Driver",
            status=DriverStatus.DECOMMISSIONED.value,
        )

        response = authenticated_client.get("/api/v1/drivers/")

        assert response.status_code == 200
        customer_numbers = {
            item["customer_number"] for item in response.data["results"]
        }
        assert active.customer_number in customer_numbers
        assert decommissioned.customer_number in customer_numbers

    def test_list_with_status_filter_returns_matching_status_only(
        self,
        authenticated_client: APIClient,
    ) -> None:
        DriverModel.objects.create(
            customer_number="6000003234",
            name="Active Driver",
            status=DriverStatus.ACTIVE.value,
        )
        decommissioned = DriverModel.objects.create(
            customer_number="6000003235",
            name="Decommissioned Driver",
            status=DriverStatus.DECOMMISSIONED.value,
        )

        response = authenticated_client.get(
            f"/api/v1/drivers/?status={DriverStatus.DECOMMISSIONED.value}"
        )

        assert response.status_code == 200
        customer_numbers = {
            item["customer_number"] for item in response.data["results"]
        }
        assert customer_numbers == {decommissioned.customer_number}

    def test_list_supports_ordering(
        self,
        authenticated_client: APIClient,
    ) -> None:
        DriverModel.objects.create(
            customer_number="6000004234",
            name="Ali Driver",
            status=DriverStatus.ACTIVE.value,
        )
        DriverModel.objects.create(
            customer_number="6000004235",
            name="Reza Driver",
            status=DriverStatus.ACTIVE.value,
        )

        response = authenticated_client.get("/api/v1/drivers/?ordering=-name")

        assert response.status_code == 200
        assert [item["name"] for item in response.data["results"]] == [
            "Reza Driver",
            "Ali Driver",
        ]

    def test_driver_vehicle_assignment_history_supports_date_filter(
        self,
        authenticated_client: APIClient,
    ) -> None:
        driver = DriverModel.objects.create(
            customer_number="6000005234",
            name="History Driver",
            status=DriverStatus.ACTIVE.value,
        )
        VehicleDriverAssignmentHistoryModel.objects.create(
            sync_run_id=uuid.uuid4(),
            request_id="old-sync",
            synced_at=datetime(2026, 7, 14, 8, 0, tzinfo=UTC),
            vehicle_id=uuid.uuid4(),
            vehicle_number="203200001",
            license_plate="11الف111",
            driver_role=VehicleDriverAssignmentHistoryModel.DriverRole.DRIVER,
            driver_customer_number=driver.customer_number,
        )
        VehicleDriverAssignmentHistoryModel.objects.create(
            sync_run_id=uuid.uuid4(),
            request_id="new-sync",
            synced_at=datetime(2026, 7, 16, 8, 0, tzinfo=UTC),
            vehicle_id=uuid.uuid4(),
            vehicle_number="203200002",
            license_plate="22ب222",
            driver_role=VehicleDriverAssignmentHistoryModel.DriverRole.ASSISTANT,
            driver_customer_number=driver.customer_number,
        )

        response = authenticated_client.get(
            f"/api/v1/drivers/{driver.id}/vehicle-assignment-history/"
            "?from_date=2026-07-16"
        )

        assert response.status_code == 200, response.data
        assert [item["vehicle_number"] for item in response.data] == ["203200002"]
