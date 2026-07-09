"""Domain entities for the Preventive Maintenance bounded context.

Vehicle is referenced by UUID only — no cross-domain imports.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from apps.preventive_maintenance.domain.exceptions import (
    PMInvalidStateTransitionError,
)
from apps.preventive_maintenance.domain.value_objects import (
    MaintenanceInterval,
    TriggerCondition,
)


class PMPlanStatus(StrEnum):
    """Lifecycle states of a preventive maintenance plan.

    Attributes:
        ACTIVE: Plan is enabled and will trigger work orders automatically.
        INACTIVE: Plan is disabled; no work orders will be generated.
        SUSPENDED: Plan is temporarily paused.
    """

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"


class PMWorkOrderStatus(StrEnum):
    """Lifecycle states of a PM work order.

    Attributes:
        SCHEDULED: Work order has been created and is awaiting execution.
        TRIGGERED: Work order has been triggered and is pending assignment.
        IN_PROGRESS: Work is actively being carried out.
        COMPLETED: All PM tasks have been completed.
        OVERDUE: Work order has passed its due date without completion.
        CANCELLED: Work order was cancelled.
    """

    SCHEDULED = "SCHEDULED"
    TRIGGERED = "TRIGGERED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"


_WO_ALLOWED_TRANSITIONS: dict[PMWorkOrderStatus, frozenset[PMWorkOrderStatus]] = {
    PMWorkOrderStatus.SCHEDULED: frozenset(
        {
            PMWorkOrderStatus.TRIGGERED,
            PMWorkOrderStatus.CANCELLED,
            PMWorkOrderStatus.OVERDUE,
        }
    ),
    PMWorkOrderStatus.TRIGGERED: frozenset(
        {
            PMWorkOrderStatus.IN_PROGRESS,
            PMWorkOrderStatus.CANCELLED,
            PMWorkOrderStatus.OVERDUE,
        }
    ),
    PMWorkOrderStatus.IN_PROGRESS: frozenset(
        {PMWorkOrderStatus.COMPLETED, PMWorkOrderStatus.CANCELLED}
    ),
    PMWorkOrderStatus.OVERDUE: frozenset(
        {PMWorkOrderStatus.IN_PROGRESS, PMWorkOrderStatus.CANCELLED}
    ),
    PMWorkOrderStatus.COMPLETED: frozenset(),
    PMWorkOrderStatus.CANCELLED: frozenset(),
}


@dataclass
class PMWorkOrder:
    """A preventive maintenance work order generated from a PM plan.

    Attributes:
        id: Unique identifier for this work order.
        plan_id: UUID of the parent PM plan.
        vehicle_id: UUID of the target vehicle (cross-domain link by ID).
        status: Current lifecycle status.
        scheduled_date: The date by which this work must be completed.
        triggered_at: UTC timestamp when the work order was triggered (optional).
        completed_at: UTC timestamp of completion (optional).
        notes: Optional technician notes.
        sap_order_number: SAP PM order number after SAP sync (optional).
        created_at: UTC timestamp of creation.
        updated_at: UTC timestamp of last update.
    """

    id: uuid.UUID
    plan_id: uuid.UUID
    vehicle_id: uuid.UUID
    status: PMWorkOrderStatus
    scheduled_date: datetime
    created_at: datetime
    updated_at: datetime
    triggered_at: datetime | None = field(default=None)
    completed_at: datetime | None = field(default=None)
    notes: str | None = field(default=None)
    sap_order_number: str | None = field(default=None)

    def transition_to(self, target: PMWorkOrderStatus) -> None:
        """Guard and apply a status transition.

        Args:
            target: The desired new status.

        Raises:
            PMInvalidStateTransitionError: If the transition is not allowed.
        """
        allowed = _WO_ALLOWED_TRANSITIONS.get(self.status, frozenset())
        if target not in allowed:
            raise PMInvalidStateTransitionError(
                current_status=self.status.value,
                target_status=target.value,
            )
        self.status = target

    def trigger(self, triggered_at: datetime) -> None:
        """Trigger the work order for execution.

        Args:
            triggered_at: UTC timestamp of the trigger event.

        Raises:
            PMInvalidStateTransitionError: If not in SCHEDULED status.
        """
        self.transition_to(PMWorkOrderStatus.TRIGGERED)
        self.triggered_at = triggered_at

    def start(self) -> None:
        """Mark the work order as in progress.

        Raises:
            PMInvalidStateTransitionError: If not TRIGGERED or OVERDUE.
        """
        self.transition_to(PMWorkOrderStatus.IN_PROGRESS)

    def complete(self, completed_at: datetime) -> None:
        """Mark the work order as completed.

        Args:
            completed_at: UTC timestamp of completion.

        Raises:
            PMInvalidStateTransitionError: If not IN_PROGRESS.
        """
        self.transition_to(PMWorkOrderStatus.COMPLETED)
        self.completed_at = completed_at

    def mark_overdue(self) -> None:
        """Mark the work order as overdue.

        Raises:
            PMInvalidStateTransitionError: If not SCHEDULED or TRIGGERED.
        """
        self.transition_to(PMWorkOrderStatus.OVERDUE)

    def cancel(self) -> None:
        """Cancel the work order.

        Raises:
            PMInvalidStateTransitionError: If already COMPLETED or CANCELLED.
        """
        self.transition_to(PMWorkOrderStatus.CANCELLED)

    @property
    def is_terminal(self) -> bool:
        """Return True if the work order has reached a terminal state."""
        return self.status in {PMWorkOrderStatus.COMPLETED, PMWorkOrderStatus.CANCELLED}


@dataclass
class PMPlan:
    """A preventive maintenance plan for a specific vehicle.

    A plan defines the scheduled maintenance interval and trigger condition.
    When the condition is met, the Application Service generates a ``PMWorkOrder``.
    The entity enforces that only one work order is active at a time.

    Attributes:
        id: Unique identifier for this plan.
        vehicle_id: UUID of the target vehicle (cross-domain link by ID).
        name: Human-readable name of the maintenance plan.
        description: Detailed description of the maintenance activities.
        interval: The maintenance schedule interval.
        trigger_condition: The condition that triggers a work order.
        status: Current plan status.
        last_triggered_at: UTC timestamp of the last trigger event (optional).
        next_due_at: Computed next-due date (optional).
        created_by_id: UUID of the user who created this plan.
        created_at: UTC timestamp of creation.
        updated_at: UTC timestamp of last update.
    """

    id: uuid.UUID
    vehicle_id: uuid.UUID
    name: str
    description: str
    interval: MaintenanceInterval
    trigger_condition: TriggerCondition
    status: PMPlanStatus
    created_by_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    last_triggered_at: datetime | None = field(default=None)
    next_due_at: datetime | None = field(default=None)

    def activate(self) -> None:
        """Activate the maintenance plan."""
        self.status = PMPlanStatus.ACTIVE

    def suspend(self) -> None:
        """Temporarily suspend the maintenance plan."""
        self.status = PMPlanStatus.SUSPENDED

    def deactivate(self) -> None:
        """Permanently deactivate the maintenance plan."""
        self.status = PMPlanStatus.INACTIVE

    def record_trigger(self, triggered_at: datetime) -> None:
        """Record that a work order has been triggered from this plan.

        Args:
            triggered_at: UTC timestamp of the trigger event.

        Raises:
            PMAlreadyTriggeredError: Enforced at the Application Service level
                by checking for active work orders before calling this method.
        """
        self.last_triggered_at = triggered_at

    @property
    def is_active(self) -> bool:
        """Return True if the plan is currently active."""
        return self.status == PMPlanStatus.ACTIVE
