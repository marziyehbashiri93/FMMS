"""Shared helpers for API integration tests."""

from __future__ import annotations

from typing import Any

from rest_framework.test import APIClient


def create_vehicle(
    client: APIClient,
    *,
    plate: str = "12API001",
    vin: str = "1HGCM82633A004352",
    sap_equipment_number: str | None = None,
) -> dict[str, Any]:
    """Create a vehicle via the API and return the response payload."""
    payload: dict[str, Any] = {
        "plate_number": plate,
        "vin": vin,
        "make": "Toyota",
        "model": "Hilux",
        "year": 2022,
        "category": "LIGHT",
    }
    if sap_equipment_number is not None:
        payload["sap_equipment_number"] = sap_equipment_number
    response = client.post("/api/v1/vehicles/", payload, format="json")
    assert response.status_code == 201, response.data
    return response.data
