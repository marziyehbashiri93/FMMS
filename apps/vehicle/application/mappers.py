"""Application-layer mappers for vehicle DTOs."""

from __future__ import annotations

from apps.vehicle.application.dto.vehicle_dto import (
    VehicleAssignedDriverDTO,
    VehicleResponseDTO,
)
from apps.vehicle.domain.entities import VEHICLE_STATUS_LABELS, Vehicle


def vehicle_to_response_dto(
    vehicle: Vehicle,
    *,
    driver1: VehicleAssignedDriverDTO | None = None,
    driver2: VehicleAssignedDriverDTO | None = None,
) -> VehicleResponseDTO:
    """Map a vehicle domain entity to a response DTO."""
    return VehicleResponseDTO(
        id=vehicle.id,
        vehicle_number=vehicle.vehicle_number.value,
        license_plate=vehicle.license_plate.value,
        status=vehicle.status,
        status_label=VEHICLE_STATUS_LABELS[vehicle.status],
        created_at=vehicle.created_at,
        updated_at=vehicle.updated_at,
        commissioning_date=vehicle.commissioning_date,
        driver1=driver1,
        driver2=driver2,
    )
