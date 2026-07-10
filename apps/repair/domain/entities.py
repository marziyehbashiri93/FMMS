"""Domain entities for the Repair bounded context.

Vehicle and Fault are referenced by UUID only — no cross-domain imports.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from apps.repair.domain.exceptions import (
    RepairOrderInvalidStateError,
    RepairOrderInvalidStateTransitionError,
)
from apps.repair.domain.value_objects import (
    LaborHours,
    PartQuantity,
    TechnicianAssignment,
)


class RepairOrderStatus(StrEnum):
    """Lifecycle states of a repair order.

    Attributes:
        CREATED: Order has been created and awaits transport approval or assignment.
        APPROVED: Transport supervisor approved continuing the repair process.
        WORKSHOP_ASSIGNED: Workshop type (internal/external) has been selected.
        ASSIGNED: A technician has been assigned.
        IN_PROGRESS: Active repair work is underway.
        COMPLETED: All repair activities are done; order is closed successfully.
        CANCELLED: Order was cancelled before completion.
    """

    CREATED = "CREATED"
    APPROVED = "APPROVED"
    WORKSHOP_ASSIGNED = "WORKSHOP_ASSIGNED"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class WorkshopType(StrEnum):
    """Where the repair work will be performed.

    Attributes:
        INTERNAL: Repair handled by the fleet's own workshop.
        EXTERNAL: Repair outsourced to an external workshop.
    """

    INTERNAL = "INTERNAL"
    EXTERNAL = "EXTERNAL"


_ALLOWED_TRANSITIONS: dict[RepairOrderStatus, frozenset[RepairOrderStatus]] = {
    RepairOrderStatus.CREATED: frozenset(
        {
            RepairOrderStatus.APPROVED,
            RepairOrderStatus.ASSIGNED,
            RepairOrderStatus.CANCELLED,
        }
    ),
    RepairOrderStatus.APPROVED: frozenset(
        {RepairOrderStatus.WORKSHOP_ASSIGNED, RepairOrderStatus.CANCELLED}
    ),
    RepairOrderStatus.WORKSHOP_ASSIGNED: frozenset(
        {
            RepairOrderStatus.ASSIGNED,
            RepairOrderStatus.IN_PROGRESS,
            RepairOrderStatus.CANCELLED,
        }
    ),
    RepairOrderStatus.ASSIGNED: frozenset(
        {
            RepairOrderStatus.IN_PROGRESS,
            RepairOrderStatus.CREATED,
            RepairOrderStatus.CANCELLED,
        }
    ),
    RepairOrderStatus.IN_PROGRESS: frozenset(
        {RepairOrderStatus.COMPLETED, RepairOrderStatus.CANCELLED}
    ),
    RepairOrderStatus.COMPLETED: frozenset(),
    RepairOrderStatus.CANCELLED: frozenset(),
}

_MUTABLE_STATUSES: frozenset[RepairOrderStatus] = frozenset(
    {
        RepairOrderStatus.CREATED,
        RepairOrderStatus.APPROVED,
        RepairOrderStatus.WORKSHOP_ASSIGNED,
        RepairOrderStatus.ASSIGNED,
        RepairOrderStatus.IN_PROGRESS,
    }
)


@dataclass
class RepairActivity:
    """A single work activity performed during a repair order.

    Attributes:
        id: Unique identifier for this activity.
        description: Description of the work performed.
        labor_hours: Hours spent on this activity.
        performed_by_id: UUID of the technician who performed the activity.
        performed_at: UTC timestamp when the activity was completed.
        notes: Optional additional notes.
    """

    id: uuid.UUID
    description: str
    labor_hours: LaborHours
    performed_by_id: uuid.UUID
    performed_at: datetime
    notes: str | None = field(default=None)


@dataclass
class RepairPart:
    """A spare part consumed during a repair order.

    Attributes:
        id: Unique identifier for this part record.
        part_quantity: Material number, quantity, and unit of measure.
        goods_issue_id: UUID of the associated goods issue document, if posted.
        posted_at: UTC timestamp when the goods issue was posted (optional).
    """

    id: uuid.UUID
    part_quantity: PartQuantity
    goods_issue_id: uuid.UUID | None = field(default=None)
    posted_at: datetime | None = field(default=None)


@dataclass
class RepairOrder:
    """Aggregate root for the Repair bounded context.

    A repair order manages the lifecycle of repair work on a vehicle fault.
    Parts and activities can only be added while the order is in a mutable state.

    Attributes:
        id: Unique identifier for this repair order.
        vehicle_id: UUID of the vehicle being repaired (cross-domain by ID).
        fault_id: UUID of the originating fault (cross-domain by ID).
        status: Current lifecycle status.
        assignment: Current technician assignment, if any.
        activities: List of repair activities performed.
        parts: List of spare parts consumed.
        sap_order_number: SAP PM order number after SAP sync (optional).
        workshop_type: Internal or external workshop selection (optional).
        created_by_id: UUID of the user who created this order.
        created_at: UTC timestamp of creation.
        updated_at: UTC timestamp of the last update.
        completed_at: UTC timestamp of completion (optional).
    """

    id: uuid.UUID
    vehicle_id: uuid.UUID
    fault_id: uuid.UUID
    status: RepairOrderStatus
    created_by_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    assignment: TechnicianAssignment | None = field(default=None)
    activities: list[RepairActivity] = field(default_factory=list)
    parts: list[RepairPart] = field(default_factory=list)
    sap_order_number: str | None = field(default=None)
    workshop_type: WorkshopType | None = field(default=None)
    completed_at: datetime | None = field(default=None)

    def _assert_mutable(self, operation: str) -> None:
        """Assert that the order is in a mutable state.

        Args:
            operation: Name of the operation being attempted (for error messages).

        Raises:
            RepairOrderInvalidStateError: If the order is COMPLETED or CANCELLED.
        """
        if self.status not in _MUTABLE_STATUSES:
            raise RepairOrderInvalidStateError(
                order_id=self.id,
                current_status=self.status.value,
                operation=operation,
            )

    def transition_to(self, target: RepairOrderStatus) -> None:
        """Guard and apply a status transition.

        Args:
            target: The desired new status.

        Raises:
            RepairOrderInvalidStateTransitionError: If the transition is not allowed.
        """
        allowed = _ALLOWED_TRANSITIONS.get(self.status, frozenset())
        if target not in allowed:
            raise RepairOrderInvalidStateTransitionError(
                current_status=self.status.value,
                target_status=target.value,
            )
        self.status = target

    def assign_technician(self, assignment: TechnicianAssignment) -> None:
        """Assign a technician to this repair order.

        Allowed from ``CREATED`` (legacy path) or ``WORKSHOP_ASSIGNED``
        (transport-approved demo path).

        Args:
            assignment: The ``TechnicianAssignment`` value object.

        Raises:
            RepairOrderInvalidStateError: If the order is not in a mutable state.
            RepairOrderInvalidStateTransitionError: If transition is not allowed.
        """
        self._assert_mutable("assign_technician")
        self.transition_to(RepairOrderStatus.ASSIGNED)
        self.assignment = assignment

    def approve(self) -> None:
        """Approve the repair order for continuation (transport supervisor).

        Raises:
            RepairOrderInvalidStateTransitionError: If not in CREATED status.
        """
        self.transition_to(RepairOrderStatus.APPROVED)

    def assign_workshop(self, workshop_type: WorkshopType) -> None:
        """Select internal or external workshop after transport approval.

        Args:
            workshop_type: ``INTERNAL`` or ``EXTERNAL``.

        Raises:
            RepairOrderInvalidStateTransitionError: If not in APPROVED status.
        """
        self.transition_to(RepairOrderStatus.WORKSHOP_ASSIGNED)
        self.workshop_type = workshop_type

    def start_work(self) -> None:
        """Mark the repair order as actively in progress.

        Allowed from ``ASSIGNED`` (technician assigned) or ``WORKSHOP_ASSIGNED``
        (simplified demo path without explicit technician assignment).

        Raises:
            RepairOrderInvalidStateTransitionError: If not in a startable state.
        """
        if self.status not in (
            RepairOrderStatus.ASSIGNED,
            RepairOrderStatus.WORKSHOP_ASSIGNED,
        ):
            raise RepairOrderInvalidStateTransitionError(
                current_status=self.status.value,
                target_status=RepairOrderStatus.IN_PROGRESS.value,
            )
        self.transition_to(RepairOrderStatus.IN_PROGRESS)

    def complete(self, completed_at: datetime) -> None:
        """Mark the repair order as completed.

        Args:
            completed_at: UTC timestamp of completion.

        Raises:
            RepairOrderInvalidStateTransitionError: If not IN_PROGRESS.
        """
        self.transition_to(RepairOrderStatus.COMPLETED)
        self.completed_at = completed_at

    def cancel(self) -> None:
        """Cancel the repair order.

        Raises:
            RepairOrderInvalidStateTransitionError: If already COMPLETED or CANCELLED.
        """
        self.transition_to(RepairOrderStatus.CANCELLED)

    def add_activity(self, activity: RepairActivity) -> None:
        """Add a repair activity to this order.

        Args:
            activity: The ``RepairActivity`` to add.

        Raises:
            RepairOrderInvalidStateError: If the order is not in a mutable state.
        """
        self._assert_mutable("add_activity")
        self.activities.append(activity)

    def add_part(self, part: RepairPart) -> None:
        """Add a spare part consumption record to this order.

        Args:
            part: The ``RepairPart`` to add.

        Raises:
            RepairOrderInvalidStateError: If the order is not in a mutable state.
        """
        self._assert_mutable("add_part")
        self.parts.append(part)

    def link_sap_order(self, sap_order_number: str) -> None:
        """Record the SAP PM order number after successful SAP sync.

        Args:
            sap_order_number: The SAP-assigned order number.
        """
        self.sap_order_number = sap_order_number

    @property
    def total_labor_hours(self) -> Decimal:
        """Sum of all labor hours across repair activities."""
        return sum((a.labor_hours.hours for a in self.activities), Decimal("0"))

    @property
    def is_active(self) -> bool:
        """Return True if the repair order is in a mutable (active) state."""
        return self.status in _MUTABLE_STATUSES


class RepairOrderEventType(StrEnum):
    """Canonical repair-order lifecycle events recorded for audit/timeline."""

    FAULT_CREATED = "FAULT_CREATED"
    DISTRIBUTION_APPROVED = "DISTRIBUTION_APPROVED"
    TRANSPORT_APPROVED = "TRANSPORT_APPROVED"
    WORKSHOP_ASSIGNED = "WORKSHOP_ASSIGNED"
    REPAIR_STARTED = "REPAIR_STARTED"
    REPAIR_COMPLETED = "REPAIR_COMPLETED"


@dataclass(frozen=True)
class RepairOrderEvent:
    """Immutable repair-order lifecycle event.

    Attributes:
        id: Event UUID.
        repair_order_id: Parent repair order.
        event_type: Canonical event code.
        description: Human-readable Persian/English description.
        created_at: UTC timestamp when the event occurred.
        created_by_id: Optional actor UUID.
    """

    id: uuid.UUID
    repair_order_id: uuid.UUID
    event_type: RepairOrderEventType
    description: str
    created_at: datetime
    created_by_id: uuid.UUID | None = None
