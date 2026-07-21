"""API integration tests for vehicle endpoints."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from rest_framework.test import APIClient

from apps.driver.domain.entities import DriverStatus
from apps.driver.infrastructure.models import DriverModel
from apps.fault.domain.entities import FaultStatus
from apps.fault.domain.value_objects import FaultSeverity
from apps.fault.infrastructure.models import FaultModel
from apps.integration.infrastructure.models import SAPSyncRunItemModel, SAPSyncRunModel
from apps.vehicle.domain.entities import VehicleStatus
from apps.vehicle.infrastructure.models import (
    VehicleDriverAssignmentHistoryModel,
    VehicleModel,
    VehicleOdometerReadingModel,
)
from tests.integration.api.conftest import create_vehicle

pytestmark = pytest.mark.django_db


class TestVehicleAPI:
    """Cover vehicle read, workflow, odometer, and auth endpoints."""

    def test_auth_required(self, api_client: APIClient) -> None:
        """Unauthenticated clients receive 401."""
        response = api_client.get("/api/v1/vehicles/")
        assert response.status_code == 401

    def test_manual_create_is_not_available(
        self, authenticated_client: APIClient
    ) -> None:
        """Vehicle master data must enter FMMS through SAP sync, not API create."""
        response = authenticated_client.post(
            "/api/v1/vehicles/",
            {
                "plate_number": "12VEH001",
                "vin": "1HGCM82633A004352",
                "make": "Toyota",
                "model": "Hilux",
                "year": 2022,
                "category": "LIGHT",
            },
            format="json",
        )
        assert response.status_code == 405

    def test_list_retrieve_no_manual_patch_and_deactivate(
        self, authenticated_client: APIClient
    ) -> None:
        """Vehicle master data has no generic manual update endpoint."""
        created = create_vehicle(
            authenticated_client,
            plate="12VEH001",
            vin="1HGCM82633A004352",
        )
        vehicle_id = created["id"]
        assert created["status"] == "ACTIVE"
        DriverModel.objects.create(
            customer_number="6000000001",
            name="راننده اصلی",
            status=DriverStatus.ACTIVE.value,
        )
        DriverModel.objects.create(
            customer_number="6000000002",
            name="کمک راننده",
            status=DriverStatus.ACTIVE.value,
        )
        VehicleModel.objects.filter(id=vehicle_id).update(
            driver1_customer_number="6000000001",
            driver2_customer_number="6000000002",
        )

        listed = authenticated_client.get("/api/v1/vehicles/")
        assert listed.status_code == 200
        assert listed.data["count"] >= 1

        retrieved = authenticated_client.get(f"/api/v1/vehicles/{vehicle_id}/")
        assert retrieved.status_code == 200
        assert retrieved.data["license_plate"] == "12VEH001"
        assert retrieved.data["status_label"] == "عملیاتی"
        assert "driver1_customer_number" not in retrieved.data
        assert "driver2_customer_number" not in retrieved.data
        assert retrieved.data["driver1"] == {
            "customer_number": "6000000001",
            "name": "راننده اصلی",
        }
        assert retrieved.data["driver2"] == {
            "customer_number": "6000000002",
            "name": "کمک راننده",
        }

        patched = authenticated_client.patch(
            f"/api/v1/vehicles/{vehicle_id}/",
            {"status": "SUSPENDED"},
            format="json",
        )
        assert patched.status_code == 405

        deactivated = authenticated_client.post(
            f"/api/v1/vehicles/{vehicle_id}/status/",
            {"status": "INACTIVE"},
            format="json",
        )
        assert deactivated.status_code == 200
        assert deactivated.data["status"] == "INACTIVE"

    def test_list_supports_ordering(self, authenticated_client: APIClient) -> None:
        first = create_vehicle(
            authenticated_client,
            plate="B-002",
            vin="1HGCM82633A004352",
        )
        second = create_vehicle(
            authenticated_client,
            plate="A-001",
            vin="1HGCM82633A004353",
        )
        DriverModel.objects.create(
            customer_number="6000000101",
            name="راننده لیست",
            status=DriverStatus.ACTIVE.value,
        )
        DriverModel.objects.create(
            customer_number="6000000102",
            name="کمک راننده لیست",
            status=DriverStatus.ACTIVE.value,
        )
        VehicleModel.objects.filter(id=first["id"]).update(
            driver1_customer_number="6000000101"
        )
        VehicleModel.objects.filter(id=second["id"]).update(
            driver2_customer_number="6000000102"
        )

        response = authenticated_client.get("/api/v1/vehicles/?ordering=license_plate")

        assert response.status_code == 200
        assert [item["license_plate"] for item in response.data["results"]] == [
            "A-001",
            "B-002",
        ]
        assert response.data["results"][0]["driver1"] is None
        assert response.data["results"][0]["driver2"] == {
            "customer_number": "6000000102",
            "name": "کمک راننده لیست",
        }
        assert response.data["results"][1]["driver1"] == {
            "customer_number": "6000000101",
            "name": "راننده لیست",
        }
        assert response.data["results"][1]["driver2"] is None

    def test_summary_returns_vehicle_dashboard_counts(
        self, authenticated_client: APIClient, admin_user: Any
    ) -> None:
        """Vehicle summary endpoint returns dashboard card values."""
        operational = create_vehicle(authenticated_client, plate="KPI-001")
        with_open_fault = create_vehicle(authenticated_client, plate="KPI-002")
        under_repair = create_vehicle(authenticated_client, plate="KPI-003")
        unusable = create_vehicle(authenticated_client, plate="KPI-004")
        decommissioned = create_vehicle(authenticated_client, plate="KPI-005")
        VehicleModel.objects.filter(id=under_repair["id"]).update(
            status=VehicleStatus.UNDER_REPAIR.value
        )
        VehicleModel.objects.filter(id=unusable["id"]).update(
            status=VehicleStatus.OUT_OF_SERVICE.value
        )
        VehicleModel.objects.filter(id=decommissioned["id"]).update(
            status=VehicleStatus.DECOMMISSIONED.value
        )
        now = datetime.now(tz=UTC)
        FaultModel.objects.create(
            vehicle_id=with_open_fault["id"],
            code="ENG-01",
            description="Engine fault",
            reported_at=now,
            severity=FaultSeverity.HIGH.value,
            status=FaultStatus.OPEN.value,
            reported_by_id=admin_user.id,
        )
        VehicleOdometerReadingModel.objects.create(
            vehicle_id=operational["id"],
            reading_date="2026-07-20",
            odometer_km=100,
            recorded_by_id=admin_user.id,
            recorded_at=now,
        )
        VehicleOdometerReadingModel.objects.create(
            vehicle_id=with_open_fault["id"],
            reading_date="2026-07-20",
            odometer_km=300,
            recorded_by_id=admin_user.id,
            recorded_at=now,
        )
        sync_run = SAPSyncRunModel.objects.create(
            trigger_source="API",
            status="SUCCESS",
            request_id="kpi-sync",
            started_at=now,
            finished_at=now,
        )
        SAPSyncRunItemModel.objects.create(
            sync_run=sync_run,
            name="vehicles",
            status="SUCCESS",
            started_at=now,
            finished_at=now,
            summary={"total_received": 5},
        )

        response = authenticated_client.get("/api/v1/vehicles/summary/")

        assert response.status_code == 200, response.data
        assert response.data["active_fleet_count"] == 4
        assert response.data["operational_fleet_count"] == 1
        assert response.data["under_repair_fleet_count"] == 1
        assert response.data["unusable_fleet_count"] == 1
        assert response.data["last_sap_sync_at"] is not None
        assert response.data["average_odometer_km"] == 200
        assert response.data["average_faults_last_30_days"] == 0.25

    def test_change_status_endpoint_updates_vehicle_status(
        self, authenticated_client: APIClient
    ) -> None:
        vehicle = create_vehicle(authenticated_client)

        response = authenticated_client.post(
            f"/api/v1/vehicles/{vehicle['id']}/status/",
            {"status": "UNDER_REPAIR"},
            format="json",
        )

        assert response.status_code == 200, response.data
        assert response.data["status"] == "UNDER_REPAIR"
        assert response.data["status_label"] == "در تعمیر"

    def test_change_status_to_active_rejects_open_fault(
        self, authenticated_client: APIClient
    ) -> None:
        vehicle = create_vehicle(authenticated_client, plate="12OPN001")
        created_fault = authenticated_client.post(
            "/api/v1/faults/",
            {
                "vehicle_id": vehicle["id"],
                "code": "ENG-01",
                "description": "Engine failure",
                "severity": "HIGH",
            },
            format="json",
        )
        assert created_fault.status_code == 201, created_fault.data

        response = authenticated_client.post(
            f"/api/v1/vehicles/{vehicle['id']}/status/",
            {"status": "ACTIVE"},
            format="json",
        )

        assert response.status_code == 409
        assert response.data["error_code"] == "VEHICLE_HAS_OPEN_FAULTS"

    def test_record_odometer_upserts_daily_reading(
        self, authenticated_client: APIClient
    ) -> None:
        vehicle = create_vehicle(authenticated_client)
        url = f"/api/v1/vehicles/{vehicle['id']}/odometer/"

        first = authenticated_client.post(
            url,
            {"reading_date": "2026-07-15", "odometer_km": 1000},
            format="json",
        )
        assert first.status_code == 200, first.data
        assert first.data["odometer_km"] == 1000

        updated = authenticated_client.post(
            url,
            {"reading_date": "2026-07-15", "odometer_km": 1015},
            format="json",
        )
        assert updated.status_code == 200, updated.data
        assert updated.data["id"] == first.data["id"]
        assert updated.data["odometer_km"] == 1015

        current = authenticated_client.get(url)
        assert current.status_code == 200
        assert current.data["id"] == first.data["id"]
        assert current.data["odometer_km"] == 1015

    def test_odometer_history_supports_date_filter(
        self, authenticated_client: APIClient
    ) -> None:
        vehicle = create_vehicle(authenticated_client)
        url = f"/api/v1/vehicles/{vehicle['id']}/odometer/"
        history_url = f"/api/v1/vehicles/{vehicle['id']}/odometer-history/"
        authenticated_client.post(
            url,
            {"reading_date": "2026-07-15", "odometer_km": 1000},
            format="json",
        )
        authenticated_client.post(
            url,
            {"reading_date": "2026-07-16", "odometer_km": 1015},
            format="json",
        )

        history = authenticated_client.get(f"{history_url}?from_date=2026-07-16")

        assert history.status_code == 200
        assert [item["reading_date"] for item in history.data] == ["2026-07-16"]

    def test_get_odometer_without_reading_returns_not_found(
        self, authenticated_client: APIClient
    ) -> None:
        vehicle = create_vehicle(authenticated_client)

        response = authenticated_client.get(
            f"/api/v1/vehicles/{vehicle['id']}/odometer/"
        )

        assert response.status_code == 404

    def test_vehicle_driver_assignment_history_supports_date_filter(
        self, authenticated_client: APIClient
    ) -> None:
        vehicle = create_vehicle(authenticated_client, vehicle_number="203200001")
        vehicle_id = vehicle["id"]
        DriverModel.objects.create(
            customer_number="6000000001",
            name="راننده قدیمی",
            status=DriverStatus.ACTIVE.value,
        )
        DriverModel.objects.create(
            customer_number="6000000002",
            name="راننده اصلی",
            status=DriverStatus.ACTIVE.value,
        )
        DriverModel.objects.create(
            customer_number="6000000003",
            name="کمک راننده",
            status=DriverStatus.ACTIVE.value,
        )
        VehicleDriverAssignmentHistoryModel.objects.create(
            sync_run_id=uuid.uuid4(),
            request_id="old-sync",
            synced_at=datetime(2026, 7, 14, 8, 0, tzinfo=UTC),
            vehicle_id=vehicle_id,
            vehicle_number=vehicle["vehicle_number"],
            license_plate=vehicle["license_plate"],
            driver_role=VehicleDriverAssignmentHistoryModel.DriverRole.DRIVER,
            driver_customer_number="6000000001",
        )
        new_sync_run_id = uuid.uuid4()
        VehicleDriverAssignmentHistoryModel.objects.create(
            sync_run_id=new_sync_run_id,
            request_id="new-sync",
            synced_at=datetime(2026, 7, 16, 8, 0, tzinfo=UTC),
            vehicle_id=vehicle_id,
            vehicle_number=vehicle["vehicle_number"],
            license_plate=vehicle["license_plate"],
            driver_role=VehicleDriverAssignmentHistoryModel.DriverRole.DRIVER,
            driver_customer_number="6000000002",
        )
        VehicleDriverAssignmentHistoryModel.objects.create(
            sync_run_id=new_sync_run_id,
            request_id="new-sync",
            synced_at=datetime(2026, 7, 16, 8, 0, tzinfo=UTC),
            vehicle_id=vehicle_id,
            vehicle_number=vehicle["vehicle_number"],
            license_plate=vehicle["license_plate"],
            driver_role=VehicleDriverAssignmentHistoryModel.DriverRole.ASSISTANT,
            driver_customer_number="6000000003",
        )

        response = authenticated_client.get(
            f"/api/v1/vehicles/{vehicle_id}/driver-assignment-history/"
            "?from_date=2026-07-16"
        )

        assert response.status_code == 200, response.data
        assert len(response.data) == 1
        assert response.data[0]["assigned_at"].startswith("2026-07-16T08:00:00")
        assert response.data[0]["driver1"] == {
            "customer_number": "6000000002",
            "name": "راننده اصلی",
        }
        assert response.data[0]["driver2"] == {
            "customer_number": "6000000003",
            "name": "کمک راننده",
        }
        assert "driver" not in response.data[0]
        assert "assistant" not in response.data[0]
        assert "vehicle_id" not in response.data[0]
        assert "request_id" not in response.data[0]
        assert "sync_run_id" not in response.data[0]
        assert "vehicle_number" not in response.data[0]

    def test_odometer_must_increase_by_at_least_10_km(
        self, authenticated_client: APIClient
    ) -> None:
        vehicle = create_vehicle(authenticated_client)
        url = f"/api/v1/vehicles/{vehicle['id']}/odometer/"
        authenticated_client.post(
            url,
            {"reading_date": "2026-07-15", "odometer_km": 1000},
            format="json",
        )

        invalid = authenticated_client.post(
            url,
            {"reading_date": "2026-07-16", "odometer_km": 1005},
            format="json",
        )

        assert invalid.status_code == 422
