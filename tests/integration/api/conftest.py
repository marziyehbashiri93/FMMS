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
