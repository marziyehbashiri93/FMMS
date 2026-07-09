"""API error-handling scenarios through the FMMS exception handler.

DEFECT-M9-01 and DEFECT-M9-02 production fixes are verified here:
- Domain not-found exceptions are translated by application services to
  ``FMMSNotFoundError`` → HTTP 404.
- Domain state violations (``DomainStateError``) map to HTTP 422.
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

    def test_missing_vehicle_maps_to_404(self, authenticated_client: APIClient) -> None:
        """DEFECT-M9-01 Option C: repo not-found → FMMSNotFoundError → 404."""
        missing = uuid4()
        response = authenticated_client.get(f"/api/v1/vehicles/{missing}/")
        assert response.status_code == 404
        assert response.data["error_code"] == "NOT_FOUND"
        assert "request_id" in response.data

    def test_illegal_repair_start_maps_to_422(
        self, authenticated_client: APIClient
    ) -> None:
        """DEFECT-M9-02: DomainStateError from repair transitions → 422."""
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
        assert response.status_code == 422
        assert response.data["error_code"] == "INVALID_STATE_TRANSITION"
        assert "request_id" in response.data

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
