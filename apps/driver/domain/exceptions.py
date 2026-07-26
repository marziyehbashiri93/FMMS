"""Domain exceptions for the Driver bounded context."""

from __future__ import annotations

from core.domain.exceptions import DomainError, DomainNotFoundError, DomainStateError


class DriverDomainError(DomainError):
    """Base class for all Driver domain exceptions."""


class DriverNotFoundError(DriverDomainError, DomainNotFoundError):
    """Raised when a driver cannot be located by its identifier.

    Args:
        driver_id: The identifier that was searched for.
    """

    def __init__(self, driver_id: object) -> None:
        super().__init__(f"Driver not found: '{driver_id}'.")
        self.driver_id = driver_id


class DriverInvalidStateTransitionError(DriverDomainError, DomainStateError):
    """Raised when a driver status transition is not permitted.

    Args:
        current_status: The current driver status.
        target_status: The attempted target status.
    """

    def __init__(self, current_status: str, target_status: str) -> None:
        super().__init__(
            f"Cannot transition driver from '{current_status}' to '{target_status}'."
        )
        self.current_status = current_status
        self.target_status = target_status
