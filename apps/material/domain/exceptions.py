"""Domain exceptions for material requests."""

from core.domain.exceptions import DomainError, DomainNotFoundError, DomainStateError


class MaterialDomainError(DomainError):
    """Base material domain error."""


class MaterialRequestNotFoundError(MaterialDomainError, DomainNotFoundError):
    """Raised when a material request cannot be found."""

    def __init__(self, request_id: object) -> None:
        super().__init__(f"Material request not found: '{request_id}'.")
        self.request_id = request_id


class MaterialRequestInvalidStateError(MaterialDomainError, DomainStateError):
    """Raised when a material request transition is not allowed."""

    def __init__(self, current_status: str, target_status: str) -> None:
        super().__init__(
            f"Cannot transition material request from '{current_status}' to '{target_status}'."
        )
