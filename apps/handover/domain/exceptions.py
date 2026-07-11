"""Domain exceptions for handover."""

from core.domain.exceptions import DomainError, DomainNotFoundError, DomainStateError


class HandoverDomainError(DomainError):
    """Base handover error."""


class VehicleHandoverNotFoundError(HandoverDomainError, DomainNotFoundError):
    """Raised when handover record is not found."""

    def __init__(self, handover_id: object) -> None:
        super().__init__(f"Vehicle handover not found: '{handover_id}'.")


class VehicleHandoverInvalidStateError(HandoverDomainError, DomainStateError):
    """Raised when handover state transition is invalid."""

    def __init__(self, current_status: str, target_status: str) -> None:
        super().__init__(
            f"Cannot transition handover from '{current_status}' to '{target_status}'."
        )
