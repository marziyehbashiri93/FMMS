"""Domain exceptions for the Preventive Maintenance bounded context."""

from __future__ import annotations

from core.domain.exceptions import DomainError, DomainNotFoundError, DomainStateError


class PMDomainError(DomainError):
    """Base class for all Preventive Maintenance domain exceptions."""


class PMPlanNotFoundError(PMDomainError, DomainNotFoundError):
    """Raised when a PM plan cannot be located by its identifier.

    Args:
        plan_id: The identifier that was searched for.
    """

    def __init__(self, plan_id: object) -> None:
        super().__init__(f"PM Plan not found: '{plan_id}'.")
        self.plan_id = plan_id


class PMWorkOrderNotFoundError(PMDomainError, DomainNotFoundError):
    """Raised when a PM work order cannot be located by its identifier.

    Args:
        work_order_id: The identifier that was searched for.
    """

    def __init__(self, work_order_id: object) -> None:
        super().__init__(f"PM Work Order not found: '{work_order_id}'.")
        self.work_order_id = work_order_id


class PMAlreadyTriggeredError(PMDomainError, DomainStateError):
    """Raised when a PM plan trigger is requested but a work order is already active.

    Args:
        plan_id: The ID of the PM plan.
    """

    def __init__(self, plan_id: object) -> None:
        super().__init__(
            f"PM Plan '{plan_id}' already has an active work order in progress."
        )
        self.plan_id = plan_id


class PMInvalidStateTransitionError(PMDomainError, DomainStateError):
    """Raised when a PM work order status transition is not permitted.

    Args:
        current_status: The current status.
        target_status: The attempted target status.
    """

    def __init__(self, current_status: str, target_status: str) -> None:
        super().__init__(
            f"Cannot transition PM Work Order from '{current_status}' to '{target_status}'."
        )
        self.current_status = current_status
        self.target_status = target_status
