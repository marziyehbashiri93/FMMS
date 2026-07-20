"""API integration tests for procurement endpoints."""

from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest
from rest_framework.test import APIClient

from tests.integration.api.conftest import create_vehicle

pytestmark = pytest.mark.django_db


class TestProcurementAPI:
    """Cover PR create, line items, SAP submit, and PO receive."""

    def test_pr_submit_and_receive_po(
        self, authenticated_client: APIClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Create a PR, submit to SAP, and receive a PO."""
        monkeypatch.setenv("SAP_USE_MOCK", "True")

        vehicle = create_vehicle(
            authenticated_client,
            plate="12PRC001",
            vin="1HGCM82633A004358",
            vehicle_number="100002",
        )
        fault = authenticated_client.post(
            "/api/v1/faults/",
            {
                "vehicle_id": vehicle["id"],
                "code": "PRT-01",
                "description": "Part required",
                "severity": "MEDIUM",
            },
            format="json",
        )
        assert fault.status_code == 201, fault.data

        repair = authenticated_client.post(
            "/api/v1/repair-orders/",
            {"vehicle_id": vehicle["id"], "fault_id": fault.data["id"]},
            format="json",
        )
        assert repair.status_code == 201, repair.data

        pr = authenticated_client.post(
            "/api/v1/purchase-requisitions/",
            {"repair_order_id": repair.data["id"]},
            format="json",
        )
        assert pr.status_code == 201, pr.data
        pr_id = pr.data["id"]

        with_line = authenticated_client.post(
            f"/api/v1/purchase-requisitions/{pr_id}/line-items/",
            {
                "material_number": "4000001",
                "quantity": "2.000",
                "unit_of_measure": "EA",
                "description": "Brake pads",
                "estimated_amount": "150.00",
                "currency": "IRR",
            },
            format="json",
        )
        assert with_line.status_code == 200, with_line.data
        assert len(with_line.data["line_items"]) == 1

        submitted = authenticated_client.post(
            f"/api/v1/purchase-requisitions/{pr_id}/submit-sap/",
            {
                "document_type": "NB",
                "plant": "1000",
                "delivery_date": date(2026, 8, 1).isoformat(),
                "idempotency_key": f"pr-submit-{uuid4()}",
            },
            format="json",
        )
        assert submitted.status_code == 200, submitted.data
        assert submitted.data["sap_pr_number"]

        po = authenticated_client.post(
            "/api/v1/purchase-orders/",
            {
                "pr_id": pr_id,
                "sap_po_number": "4500000001",
                "vendor_number": "V1000",
                "line_items": [
                    {
                        "material_number": "4000001",
                        "quantity": "2.000",
                        "unit_of_measure": "EA",
                        "unit_price": "150.00",
                        "currency": "IRR",
                    }
                ],
            },
            format="json",
        )
        assert po.status_code == 201, po.data
        po_id = po.data["id"]

        retrieved = authenticated_client.get(f"/api/v1/purchase-orders/{po_id}/")
        assert retrieved.status_code == 200
        assert retrieved.data["sap_po_number"] == "4500000001"
