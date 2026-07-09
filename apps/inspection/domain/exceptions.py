"""Domain exceptions for the Inspection bounded context."""

from __future__ import annotations


class InspectionDomainError(Exception):
    """Base class for all Inspection domain exceptions."""


class InspectionNotFoundError(InspectionDomainError):
    """Raised when an inspection cannot be located by its identifier.

    Args:
        inspection_id: The identifier that was searched for.
    """

    def __init__(self, inspection_id: object) -> None:
        super().__init__(f"Inspection not found: '{inspection_id}'.")
        self.inspection_id = inspection_id


class InspectionAlreadySubmittedError(InspectionDomainError):
    """Raised when attempting to modify or re-submit an already-submitted inspection.

    Args:
        inspection_id: The ID of the already-submitted inspection.
    """

    def __init__(self, inspection_id: object) -> None:
        super().__init__(f"Inspection '{inspection_id}' has already been submitted.")
        self.inspection_id = inspection_id


class InspectionItemRequiredError(InspectionDomainError):
    """Raised when attempting to submit an inspection that has no checklist items."""

    def __init__(self) -> None:
        super().__init__(
            "An inspection must have at least one checklist item before submission."
        )


class InspectionInvalidStateTransitionError(InspectionDomainError):
    """Raised when an inspection status transition is not permitted.

    Args:
        current_status: The current inspection status.
        target_status: The attempted target status.
    """

    def __init__(self, current_status: str, target_status: str) -> None:
        super().__init__(
            f"Cannot transition inspection from '{current_status}' to '{target_status}'."
        )
        self.current_status = current_status
        self.target_status = target_status
