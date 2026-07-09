"""Domain exceptions for the Fault bounded context."""

from __future__ import annotations

from core.domain.exceptions import DomainError, DomainNotFoundError, DomainStateError


class FaultDomainError(DomainError):
    """Base class for all Fault domain exceptions."""


class FaultNotFoundError(FaultDomainError, DomainNotFoundError):
    """Raised when a fault cannot be located by its identifier.

    Args:
        fault_id: The identifier that was searched for.
    """

    def __init__(self, fault_id: object) -> None:
        super().__init__(f"Fault not found: '{fault_id}'.")
        self.fault_id = fault_id


class FaultAlreadyClosedError(FaultDomainError, DomainStateError):
    """Raised when attempting to transition a CLOSED fault to another status.

    Args:
        fault_id: The ID of the closed fault.
    """

    def __init__(self, fault_id: object) -> None:
        super().__init__(f"Fault '{fault_id}' is already closed and cannot be changed.")
        self.fault_id = fault_id


class FaultInvalidStateTransitionError(FaultDomainError, DomainStateError):
    """Raised when a fault status transition is not permitted.

    Args:
        current_status: The current fault status.
        target_status: The attempted target status.
    """

    def __init__(self, current_status: str, target_status: str) -> None:
        super().__init__(
            f"Cannot transition fault from '{current_status}' to '{target_status}'."
        )
        self.current_status = current_status
        self.target_status = target_status
