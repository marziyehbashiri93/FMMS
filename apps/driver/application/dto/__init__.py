"""Driver application DTOs — pure Python, no ORM, no Django objects."""

from apps.driver.application.dto.driver_dto import (
    AssignDriverToVehicleDTO,
    DriverResponseDTO,
    RegisterDriverDTO,
    SuspendDriverDTO,
)

__all__ = [
    "RegisterDriverDTO",
    "AssignDriverToVehicleDTO",
    "SuspendDriverDTO",
    "DriverResponseDTO",
]
