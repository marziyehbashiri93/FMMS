"""Shared helpers for API integration tests."""

from __future__ import annotations

from typing import Any

from rest_framework.test import APIClient

from apps.vehicle.domain.entities import VEHICLE_STATUS_LABELS, VehicleStatus
from apps.vehicle.infrastructure.models import VehicleModel


def create_vehicle(
    client: APIClient,
    *,
    plate: str = "12API001",
    vin: str | None = None,
    vehicle_number: str | None = None,
) -> dict[str, Any]:
    """Create a vehicle fixture directly; production create is SAP-only."""
    del client, vin
    vehicle_number = vehicle_number or str(abs(hash(plate)) % 10**12)
    obj = VehicleModel.objects.create(
        vehicle_number=vehicle_number,
        license_plate=plate,
        status=VehicleStatus.ACTIVE.value,
    )
    return {
        "id": str(obj.id),
        "vehicle_number": obj.vehicle_number,
        "license_plate": obj.license_plate,
        "status": obj.status,
        "status_label": VEHICLE_STATUS_LABELS[VehicleStatus(obj.status)],
        "commissioning_date": obj.commissioning_date or None,
    }


def create_repair_order_via_distribution(
    client: APIClient,
    *,
    plate: str,
    vin: str | None = None,
    code: str = "BRK-01",
    description: str = "Brake issue",
    severity: str = "HIGH",
) -> dict[str, Any]:
    """Create vehicle + open fault + distribution-unusable → CREATED repair order."""
    vehicle = create_vehicle(client, plate=plate, vin=vin)
    fault = client.post(
        "/api/v1/faults/",
        {
            "vehicle_id": vehicle["id"],
            "code": code,
            "description": description,
            "severity": severity,
        },
        format="json",
    )
    assert fault.status_code == 201, fault.data
    unusable = client.post(
        f"/api/v1/faults/{fault.data['id']}/distribution-unusable/",
        {"note": "needs repair"},
        format="json",
    )
    assert unusable.status_code == 200, unusable.data
    assert unusable.data["status"] == "AWAITING_TRANSPORT"

    orders = client.get(f"/api/v1/repair-orders/?vehicle_id={vehicle['id']}")
    assert orders.status_code == 200, orders.data
    assert orders.data["count"] >= 1, orders.data
    order = orders.data["results"][0]
    order["fault"] = unusable.data
    order["vehicle"] = vehicle
    return order
