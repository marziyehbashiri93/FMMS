"""P0 — API error-handling scenarios through the FMMS exception handler.

Known production defects discovered during M9 (awaiting approval before any
production code change):

DEFECT-M9-01
  Symptom: ``GET /api/v1/vehicles/{missing}/`` returns HTTP 500.
  Cause: ``DjangoVehicleRepository.get_by_id`` raises ``VehicleNotFoundError``
  (plain domain exception). ``GetVehicleService`` documents ``None`` →
  ``FMMSNotFoundError``, but the repository never returns ``None``, so the
  service never raises ``FMMSNotFoundError``. The DRF handler only maps
  ``FMMS*`` types, so the response is an unhandled 500.
  Proposed fix (needs approval):
    A) Repository returns ``None`` / optional and services raise
       ``FMMSNotFoundError`` (match interface intent), OR
    B) Map ``VehicleNotFoundError`` (and peer *NotFound domain exceptions) in
       ``fmms_exception_handler`` to HTTP 404, OR
    C) Services catch domain not-found and re-raise ``FMMSNotFoundError``.

DEFECT-M9-02
  Symptom: Illegal repair transitions (e.g. start from CREATED) return HTTP 500.
  Cause: ``RepairOrderInvalidStateTransitionError`` /
  ``RepairOrderInvalidStateError`` are not ``FMMSBaseException`` subclasses and
  are not wrapped by application services before reaching the API.
  Proposed fix (needs approval):
    A) Application services catch repair state errors and raise
       ``FMMSStateError``, OR
    B) Map those domain exceptions in ``fmms_exception_handler`` to HTTP 422.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch
from uuid import uuid4

import pytest
from rest_framework.test import APIClient

from core.exceptions.base_exception import FMMSIntegrationError, FMMSNotFoundError
from tests.integration.api.conftest import create_vehicle

pytestmark = pytest.mark.django_db


class TestAPIErrorMapping:
    """Domain/application errors must map to the standard FMMS error body."""

    def test_missing_vehicle_currently_returns_500_defect_m9_01(
        self, authenticated_client: APIClient
    ) -> None:
        """DEFECT-M9-01: missing vehicle currently surfaces as unhandled 500."""
        authenticated_client.raise_request_exception = False
        missing = uuid4()
        response = authenticated_client.get(f"/api/v1/vehicles/{missing}/")
        assert response.status_code == 500

    def test_illegal_repair_start_currently_returns_500_defect_m9_02(
        self, authenticated_client: APIClient
    ) -> None:
        """DEFECT-M9-02: invalid repair transition currently surfaces as 500."""
        authenticated_client.raise_request_exception = False
        vehicle = create_vehicle(
            authenticated_client, plate="12ERR001", vin="1HGCM82633A004394"
        )
        fault = authenticated_client.post(
            "/api/v1/faults/",
            {
                "vehicle_id": vehicle["id"],
                "code": "ENG-02",
                "description": "Knock",
                "severity": "HIGH",
            },
            format="json",
        )
        assert fault.status_code == 201, fault.data
        created = authenticated_client.post(
            "/api/v1/repair-orders/",
            {"vehicle_id": vehicle["id"], "fault_id": fault.data["id"]},
            format="json",
        )
        assert created.status_code == 201, created.data

        response = authenticated_client.post(
            f"/api/v1/repair-orders/{created.data['id']}/start/",
            {},
            format="json",
        )
        assert response.status_code == 500

    def test_validation_error_maps_to_400(
        self, authenticated_client: APIClient
    ) -> None:
        """Serializer validation failures return VALIDATION_ERROR."""
        response = authenticated_client.post(
            "/api/v1/vehicles/",
            {"plate_number": "BAD"},
            format="json",
        )
        assert response.status_code == 400
        assert response.data["error_code"] == "VALIDATION_ERROR"

    def test_fmms_not_found_from_service_maps_to_404(
        self, authenticated_client: APIClient
    ) -> None:
        """When an application service raises FMMSNotFoundError, API returns 404."""
        missing = uuid4()
        with patch("interfaces.api.v1.deps.get_get_vehicle_service") as factory:
            factory.return_value.execute.side_effect = FMMSNotFoundError(
                message=f"Vehicle '{missing}' not found.",
                details={"vehicle_id": str(missing)},
            )
            response = authenticated_client.get(f"/api/v1/vehicles/{missing}/")

        assert response.status_code == 404
        assert response.data["error_code"] == "NOT_FOUND"
        assert "request_id" in response.data

    def test_sap_integration_error_maps_to_502(
        self, authenticated_client: APIClient
    ) -> None:
        """SAP write failures surface as INTEGRATION / 502 through the API."""
        vehicle = create_vehicle(
            authenticated_client,
            plate="12ERR002",
            vin="1HGCM82633A004393",
            sap_equipment_number="100099",
        )
        fault = authenticated_client.post(
            "/api/v1/faults/",
            {
                "vehicle_id": vehicle["id"],
                "code": "ENG-03",
                "description": "Oil leak",
                "severity": "HIGH",
            },
            format="json",
        )
        assert fault.status_code == 201, fault.data
        created = authenticated_client.post(
            "/api/v1/repair-orders/",
            {"vehicle_id": vehicle["id"], "fault_id": fault.data["id"]},
            format="json",
        )
        assert created.status_code == 201, created.data

        with patch("interfaces.api.v1.deps.get_sync_repair_to_sap_service") as factory:
            service = factory.return_value
            service.execute.side_effect = FMMSIntegrationError(
                message="SAP unavailable",
                details={"repair_order_id": created.data["id"]},
            )
            response = authenticated_client.post(
                f"/api/v1/repair-orders/{created.data['id']}/sync-sap/",
                {
                    "order_type": "PM01",
                    "description": "Corrective",
                    "planned_start": datetime.now(tz=UTC).isoformat(),
                },
                format="json",
            )

        assert response.status_code == 502
        assert response.data["error_code"] == "INTEGRATION_ERROR"
