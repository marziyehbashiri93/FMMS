"""Domain exceptions for the Vehicle bounded context."""

from __future__ import annotations

from core.domain.exceptions import DomainError, DomainNotFoundError, DomainStateError


class VehicleDomainError(DomainError):
    """Base class for all Vehicle domain exceptions."""


class VehicleNotFoundError(VehicleDomainError, DomainNotFoundError):
    """Raised when a vehicle cannot be located by its identifier.

    Args:
        vehicle_id: The identifier that was searched for.
    """

    def __init__(self, vehicle_id: object) -> None:
        super().__init__(f"Vehicle not found: '{vehicle_id}'.")
        self.vehicle_id = vehicle_id


class VehicleAlreadyExistsError(VehicleDomainError):
    """Raised when attempting to register a vehicle with a duplicate plate number.

    Args:
        plate_number: The conflicting plate number.
    """

    def __init__(self, plate_number: str) -> None:
        super().__init__(
            f"A vehicle with plate number '{plate_number}' already exists."
        )
        self.plate_number = plate_number


class VehicleInvalidStateTransitionError(VehicleDomainError, DomainStateError):
    """Raised when a vehicle status transition is not permitted.

    Args:
        current_status: The current vehicle status.
        target_status: The attempted target status.
    """

    def __init__(self, current_status: str, target_status: str) -> None:
        super().__init__(
            f"Cannot transition vehicle from '{current_status}' to '{target_status}'."
        )
        self.current_status = current_status
        self.target_status = target_status
