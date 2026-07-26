"""Vehicle application DTOs — pure Python, no ORM, no Django objects."""

from apps.vehicle.application.dto.vehicle_dto import (
    RecordVehicleOdometerDTO,
    VehicleDriverAssignmentHistoryResponseDTO,
    VehicleOdometerResponseDTO,
    VehicleResponseDTO,
)

__all__ = [
    "RecordVehicleOdometerDTO",
    "VehicleDriverAssignmentHistoryResponseDTO",
    "VehicleOdometerResponseDTO",
    "VehicleResponseDTO",
]
