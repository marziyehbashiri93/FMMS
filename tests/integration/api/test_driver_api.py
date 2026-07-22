"""API integration tests for driver endpoints."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from rest_framework.test import APIClient

from apps.driver.domain.entities import DriverStatus
from apps.driver.infrastructure.models import DriverModel
from apps.integration.infrastructure.models import (
    SAPSyncRunItemModel,
    SAPSyncRunModel,
)
from apps.vehicle.domain.entities import VehicleStatus
from apps.vehicle.infrastructure.models import (
    VehicleDriverAssignmentHistoryModel,
    VehicleModel,
)

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
        assert retrieved.data["current_vehicle_as_driver"] is None
        assert retrieved.data["current_vehicle_as_assistant"] is None

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

    def test_retrieve_includes_current_vehicles_when_assigned(
        self,
        authenticated_client: APIClient,
    ) -> None:
        """Retrieve enriches driver with current vehicle as driver and assistant."""
        driver = DriverModel.objects.create(
            customer_number="6000006234",
            name="Assigned Driver",
            status=DriverStatus.ACTIVE.value,
        )
        as_driver = VehicleModel.objects.create(
            vehicle_number="203200101",
            license_plate="11الف101",
            status=VehicleStatus.ACTIVE.value,
            driver1_customer_number=driver.customer_number,
        )
        as_assistant = VehicleModel.objects.create(
            vehicle_number="203200102",
            license_plate="22ب102",
            status=VehicleStatus.ACTIVE.value,
            driver2_customer_number=driver.customer_number,
        )

        response = authenticated_client.get(f"/api/v1/drivers/{driver.id}/")

        assert response.status_code == 200, response.data
        assert response.data["current_vehicle_as_driver"] == {
            "id": str(as_driver.id),
            "vehicle_number": "203200101",
            "license_plate": "11الف101",
        }
        assert response.data["current_vehicle_as_assistant"] == {
            "id": str(as_assistant.id),
            "vehicle_number": "203200102",
            "license_plate": "22ب102",
        }

    def test_summary_returns_driver_dashboard_counts(
        self,
        authenticated_client: APIClient,
    ) -> None:
        """Driver summary endpoint returns dashboard card values."""
        with_vehicle = DriverModel.objects.create(
            customer_number="6000007234",
            name="With Vehicle",
            status=DriverStatus.ACTIVE.value,
        )
        DriverModel.objects.create(
            customer_number="6000007235",
            name="Active Without Vehicle",
            status=DriverStatus.ACTIVE.value,
        )
        DriverModel.objects.create(
            customer_number="6000007236",
            name="Decommissioned Driver",
            status=DriverStatus.DECOMMISSIONED.value,
        )
        VehicleModel.objects.create(
            vehicle_number="203200201",
            license_plate="33ج201",
            status=VehicleStatus.ACTIVE.value,
            driver1_customer_number=with_vehicle.customer_number,
        )
        now = datetime.now(tz=UTC)
        sync_run = SAPSyncRunModel.objects.create(
            trigger_source="API",
            status="SUCCESS",
            request_id="driver-kpi-sync",
            started_at=now,
            finished_at=now,
        )
        SAPSyncRunItemModel.objects.create(
            sync_run=sync_run,
            name="vehicles",
            status="SUCCESS",
            started_at=now,
            finished_at=now,
            summary={"total_received": 1},
        )

        response = authenticated_client.get("/api/v1/drivers/summary/")

        assert response.status_code == 200, response.data
        assert response.data["active_count"] >= 2
        assert response.data["decommissioned_count"] >= 1
        assert response.data["with_vehicle_count"] >= 1
        assert response.data["last_sap_sync_at"] is not None

    def test_list_supports_search_filter(
        self,
        authenticated_client: APIClient,
    ) -> None:
        """List search filters by name, customer_number, or personnel_number."""
        DriverModel.objects.create(
            customer_number="6000008234",
            name="Searchable Ali",
            personnel_number="PN-SEARCH-01",
            status=DriverStatus.ACTIVE.value,
        )
        DriverModel.objects.create(
            customer_number="6000008235",
            name="Other Driver",
            personnel_number="PN-OTHER",
            status=DriverStatus.ACTIVE.value,
        )

        by_name = authenticated_client.get("/api/v1/drivers/?search=searchable")
        assert by_name.status_code == 200
        assert {item["customer_number"] for item in by_name.data["results"]} == {
            "6000008234"
        }

        by_personnel = authenticated_client.get(
            "/api/v1/drivers/?search=pn-search-01"
        )
        assert by_personnel.status_code == 200
        assert {item["customer_number"] for item in by_personnel.data["results"]} == {
            "6000008234"
        }

    def test_list_supports_current_assignment_role_filter(
        self,
        authenticated_client: APIClient,
    ) -> None:
        """List role filter matches current main-driver or assistant assignment."""
        main_driver = DriverModel.objects.create(
            customer_number="6000009234",
            name="Main Driver",
            status=DriverStatus.ACTIVE.value,
        )
        assistant = DriverModel.objects.create(
            customer_number="6000009235",
            name="Assistant Driver",
            status=DriverStatus.ACTIVE.value,
        )
        DriverModel.objects.create(
            customer_number="6000009236",
            name="Unassigned Driver",
            status=DriverStatus.ACTIVE.value,
        )
        VehicleModel.objects.create(
            vehicle_number="203200301",
            license_plate="44د301",
            status=VehicleStatus.ACTIVE.value,
            driver1_customer_number=main_driver.customer_number,
            driver2_customer_number=assistant.customer_number,
        )

        as_driver = authenticated_client.get("/api/v1/drivers/?role=DRIVER")
        assert as_driver.status_code == 200
        assert {item["customer_number"] for item in as_driver.data["results"]} == {
            main_driver.customer_number
        }

        as_assistant = authenticated_client.get("/api/v1/drivers/?role=ASSISTANT")
        assert as_assistant.status_code == 200
        assert {
            item["customer_number"] for item in as_assistant.data["results"]
        } == {assistant.customer_number}

        invalid = authenticated_client.get("/api/v1/drivers/?role=UNKNOWN")
        assert invalid.status_code == 400

    def test_driver_can_mark_assigned_vehicle_exited_center_after_checklist(
        self,
        authenticated_client: APIClient,
    ) -> None:
        """Assigned driver can exit center after submitting a passing checklist."""
        driver = DriverModel.objects.create(
            customer_number="6000009334",
            name="Exit Driver",
            status=DriverStatus.ACTIVE.value,
        )
        vehicle = VehicleModel.objects.create(
            vehicle_number="203200401",
            license_plate="55ه401",
            status=VehicleStatus.ACTIVE.value,
            driver1_customer_number=driver.customer_number,
        )
        created = authenticated_client.post(
            "/api/v1/inspections/",
            {
                "vehicle_id": str(vehicle.id),
                "driver_id": str(driver.id),
                "inspection_type": "PRE_TRIP",
                "odometer_value": 12000,
                "odometer_unit": "KM",
                "inspected_at": datetime(2026, 7, 22, 8, 0, tzinfo=UTC).isoformat(),
                "items": [
                    {
                        "category": "ایمنی",
                        "description": "کمربند ایمنی",
                        "result": "PASS",
                    }
                ],
            },
            format="json",
        )
        assert created.status_code == 201, created.data
        submitted = authenticated_client.post(
            f"/api/v1/inspections/{created.data['id']}/submit/",
            {},
            format="json",
        )
        assert submitted.status_code == 200, submitted.data

        response = authenticated_client.post(
            f"/api/v1/drivers/{driver.id}/exit-center/",
            {
                "vehicle_id": str(vehicle.id),
                "inspection_id": created.data["id"],
            },
            format="json",
        )

        assert response.status_code == 200, response.data
        assert response.data["status"] == "EXITED_CENTER"
        assert response.data["status_label"] == "خروج از مرکز"

    def test_driver_exit_center_rejects_failed_checklist(
        self,
        authenticated_client: APIClient,
    ) -> None:
        """Vehicles with failed checklist items cannot exit the center."""
        driver = DriverModel.objects.create(
            customer_number="6000009335",
            name="Failed Exit Driver",
            status=DriverStatus.ACTIVE.value,
        )
        vehicle = VehicleModel.objects.create(
            vehicle_number="203200402",
            license_plate="66و402",
            status=VehicleStatus.ACTIVE.value,
            driver1_customer_number=driver.customer_number,
        )
        created = authenticated_client.post(
            "/api/v1/inspections/",
            {
                "vehicle_id": str(vehicle.id),
                "driver_id": str(driver.id),
                "inspection_type": "PRE_TRIP",
                "odometer_value": 12000,
                "odometer_unit": "KM",
                "inspected_at": datetime(2026, 7, 22, 8, 0, tzinfo=UTC).isoformat(),
                "items": [
                    {
                        "category": "ترمز",
                        "description": "لنت ترمز",
                        "result": "FAIL",
                        "notes": "نیازمند بررسی",
                        "severity": "HIGH",
                    }
                ],
            },
            format="json",
        )
        assert created.status_code == 201, created.data
        submitted = authenticated_client.post(
            f"/api/v1/inspections/{created.data['id']}/submit/",
            {},
            format="json",
        )
        assert submitted.status_code == 200, submitted.data

        response = authenticated_client.post(
            f"/api/v1/drivers/{driver.id}/exit-center/",
            {
                "vehicle_id": str(vehicle.id),
                "inspection_id": created.data["id"],
            },
            format="json",
        )

        assert response.status_code == 409
        assert response.data["error_code"] == "CHECKLIST_HAS_FAILURES"

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
