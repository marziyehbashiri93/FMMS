"""API integration tests for driver endpoints."""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.driver.domain.entities import DriverStatus
from apps.driver.infrastructure.models import DriverModel

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
