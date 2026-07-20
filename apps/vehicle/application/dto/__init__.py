"""Vehicle application DTOs — pure Python, no ORM, no Django objects."""

from apps.vehicle.application.dto.vehicle_dto import (
    RecordVehicleOdometerDTO,
    UpdateVehicleDTO,
    VehicleOdometerResponseDTO,
    VehicleResponseDTO,
)

__all__ = [
    "RecordVehicleOdometerDTO",
    "UpdateVehicleDTO",
    "VehicleOdometerResponseDTO",
    "VehicleResponseDTO",
]
