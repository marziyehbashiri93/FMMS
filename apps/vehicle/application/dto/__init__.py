"""Vehicle application DTOs — pure Python, no ORM, no Django objects."""

from apps.vehicle.application.dto.vehicle_dto import (
    CreateVehicleDTO,
    UpdateVehicleDTO,
    VehicleResponseDTO,
)

__all__ = [
    "CreateVehicleDTO",
    "UpdateVehicleDTO",
    "VehicleResponseDTO",
]
