"""Domain entities for the Fault bounded context.

Vehicle and Inspection are referenced by UUID only — no cross-domain imports.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from apps.fault.domain.exceptions import (
    FaultAlreadyClosedError,
    FaultInvalidStateTransitionError,
)
from apps.fault.domain.value_objects import (
    FaultCode,
    FaultDescription,
    FaultSeverity,
    SAPDefectCode,
)


class FaultStatus(StrEnum):
    """Lifecycle states of a fault record.

    Attributes:
        OPEN: Fault has been reported and awaits distribution decision.
        AWAITING_TRANSPORT: Distribution marked unusable; in transport queue.
        ASSIGNED: Fault has been assigned to a technician.
        IN_REPAIR: Active repair work is being carried out.
        CLOSED: Fault has been resolved. Terminal state — no further transitions.
    """

    OPEN = "OPEN"
    AWAITING_TRANSPORT = "AWAITING_TRANSPORT"
    ASSIGNED = "ASSIGNED"
    IN_REPAIR = "IN_REPAIR"
    CLOSED = "CLOSED"


_ALLOWED_TRANSITIONS: dict[FaultStatus, frozenset[FaultStatus]] = {
    FaultStatus.OPEN: frozenset(
        {FaultStatus.AWAITING_TRANSPORT, FaultStatus.CLOSED}
    ),
    FaultStatus.AWAITING_TRANSPORT: frozenset(
        {
            FaultStatus.ASSIGNED,
            FaultStatus.OPEN,
            FaultStatus.IN_REPAIR,
            FaultStatus.CLOSED,
        }
    ),
    FaultStatus.ASSIGNED: frozenset({FaultStatus.IN_REPAIR, FaultStatus.OPEN}),
    FaultStatus.IN_REPAIR: frozenset({FaultStatus.CLOSED}),
    FaultStatus.CLOSED: frozenset(),
}


@dataclass
class FaultItem:
    """A single failed component within a fault incident.

    Attributes:
        id: Unique identifier for this fault item.
        fault_id: Parent fault aggregate identifier.
        inspection_item_id: Optional originating inspection checklist item ID.
        component: Component or checklist label (e.g. "Front light").
        description: Human-readable failure detail.
        severity: Severity assigned to this item.
        created_at: UTC timestamp when the record was created.
        updated_at: UTC timestamp of the last update.
    """

    id: uuid.UUID
    fault_id: uuid.UUID
    component: str
    description: str
    severity: FaultSeverity
    created_at: datetime
    updated_at: datetime
    inspection_item_id: uuid.UUID | None = field(default=None)


@dataclass
class Fault:
    """Aggregate root for the Fault bounded context.

    A fault represents a defect or issue reported for a vehicle.
    It may originate from an inspection or be reported directly.
    Once CLOSED it cannot transition to any other state.

    Attributes:
        id: Unique identifier for this fault.
        vehicle_id: UUID of the affected vehicle (cross-domain link by ID).
        code: Classified fault code.
        description: Human-readable fault description.
        severity: Severity level of this fault.
        status: Current lifecycle status.
        inspection_id: UUID of the originating inspection, if any.
        sap_defect_code: SAP PM defect code for SAP notification (optional).
        sap_notification_number: SAP PM notification number after SAP sync.
        assigned_to_id: UUID of the user/technician the fault is assigned to.
        reported_by_id: UUID of the user who reported the fault.
        reported_at: UTC timestamp when the fault was reported.
        created_at: UTC timestamp when the record was created.
        updated_at: UTC timestamp of the last update.
        items: Child fault items when the incident has multiple failed components.
    """

    id: uuid.UUID
    vehicle_id: uuid.UUID
    code: FaultCode
    description: FaultDescription
    severity: FaultSeverity
    status: FaultStatus
    reported_by_id: uuid.UUID
    reported_at: datetime
    created_at: datetime
    updated_at: datetime
    inspection_id: uuid.UUID | None = field(default=None)
    sap_defect_code: SAPDefectCode | None = field(default=None)
    sap_notification_number: str | None = field(default=None)
    assigned_to_id: uuid.UUID | None = field(default=None)
    items: list[FaultItem] = field(default_factory=list)

    def transition_to(self, target: FaultStatus) -> None:
        """Guard and apply a status transition.

        Args:
            target: The desired new status.

        Raises:
            FaultAlreadyClosedError: If the fault is already CLOSED.
            FaultInvalidStateTransitionError: If the transition is not permitted.
        """
        if self.status == FaultStatus.CLOSED:
            raise FaultAlreadyClosedError(self.id)
        allowed = _ALLOWED_TRANSITIONS.get(self.status, frozenset())
        if target not in allowed:
            raise FaultInvalidStateTransitionError(
                current_status=self.status.value,
                target_status=target.value,
            )
        self.status = target

    def mark_awaiting_transport(self) -> None:
        """Move the fault into the transport queue after distribution unusable.

        Raises:
            FaultAlreadyClosedError: If the fault is already CLOSED.
            FaultInvalidStateTransitionError: If not in OPEN status.
        """
        self.transition_to(FaultStatus.AWAITING_TRANSPORT)

    def assign(self, technician_id: uuid.UUID) -> None:
        """Assign the fault to a technician.

        Args:
            technician_id: UUID of the technician.

        Raises:
            FaultAlreadyClosedError: If the fault is already CLOSED.
            FaultInvalidStateTransitionError: If not awaiting transport.
        """
        self.transition_to(FaultStatus.ASSIGNED)
        self.assigned_to_id = technician_id

    def start_repair(self) -> None:
        """Mark the fault as actively being repaired.

        Raises:
            FaultAlreadyClosedError: If already CLOSED.
            FaultInvalidStateTransitionError: If not ASSIGNED or AWAITING_TRANSPORT.
        """
        self.transition_to(FaultStatus.IN_REPAIR)

    def close(self) -> None:
        """Close the fault. This is a terminal state.

        Raises:
            FaultAlreadyClosedError: If already CLOSED.
            FaultInvalidStateTransitionError: If in an invalid state.
        """
        self.transition_to(FaultStatus.CLOSED)

    def link_sap_notification(self, notification_number: str) -> None:
        """Record the SAP PM notification number after successful SAP sync.

        Args:
            notification_number: The SAP-assigned notification number.
        """
        self.sap_notification_number = notification_number

    @property
    def is_critical(self) -> bool:
        """Return True if this fault has CRITICAL severity."""
        return self.severity == FaultSeverity.CRITICAL

    @property
    def is_open(self) -> bool:
        """Return True if this fault is still active (not CLOSED)."""
        return self.status != FaultStatus.CLOSED
