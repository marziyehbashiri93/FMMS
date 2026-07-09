"""
FMMS Domain Exception Hierarchy.

All FMMS business exceptions inherit from FMMSBaseException.
These are domain-level exceptions — they carry meaning about what
went wrong in the business domain, not how it maps to HTTP.

HTTP mapping is handled separately by the DRF exception handler.
"""

from typing import Any


class FMMSBaseException(Exception):
    """
    Base exception for all FMMS domain exceptions.

    Attributes:
        message: Human-readable error description.
        error_code: Machine-readable error code (e.g. 'VEHICLE_NOT_FOUND').
        details: Optional dict with additional context for debugging.
    """

    default_message: str = "An unexpected error occurred."
    default_error_code: str = "FMMS_ERROR"

    def __init__(
        self,
        message: str | None = None,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize the exception.

        Args:
            message: Override the default message.
            error_code: Override the default error code.
            details: Additional context dictionary.
        """
        self.message = message or self.default_message
        self.error_code = error_code or self.default_error_code
        self.details = details or {}
        super().__init__(self.message)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(error_code={self.error_code!r}, message={self.message!r})"


class FMMSNotFoundError(FMMSBaseException):
    """Raised when a requested resource does not exist or has been soft-deleted."""

    default_message = "The requested resource was not found."
    default_error_code = "NOT_FOUND"


class FMMSValidationError(FMMSBaseException):
    """Raised when input data fails domain-level validation rules."""

    default_message = "Validation failed."
    default_error_code = "VALIDATION_ERROR"


class FMMSPermissionError(FMMSBaseException):
    """Raised when the requesting user lacks permission to perform the action."""

    default_message = "You do not have permission to perform this action."
    default_error_code = "PERMISSION_DENIED"


class FMMSConflictError(FMMSBaseException):
    """Raised when an operation conflicts with the current state of a resource."""

    default_message = "The operation conflicts with the current resource state."
    default_error_code = "CONFLICT"


class FMMSStateError(FMMSBaseException):
    """Raised when a state machine transition is invalid for the current state."""

    default_message = "This operation is not allowed in the current state."
    default_error_code = "INVALID_STATE_TRANSITION"


class FMMSIntegrationError(FMMSBaseException):
    """Raised when an external integration (e.g. SAP) fails unexpectedly."""

    default_message = "An external integration error occurred."
    default_error_code = "INTEGRATION_ERROR"
