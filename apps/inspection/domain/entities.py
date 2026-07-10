"""Domain entities for the Inspection bounded context.

Vehicle and Driver are referenced by UUID only — no cross-domain entity imports.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from apps.inspection.domain.exceptions import (
    InspectionAlreadySubmittedError,
    InspectionInvalidStateTransitionError,
    InspectionItemRequiredError,
)
from apps.inspection.domain.value_objects import (
    ChecklistResult,
    InspectionScore,
    OdometerReading,
)


class InspectionStatus(StrEnum):
    """Lifecycle states of an inspection.

    Attributes:
        DRAFT: Inspection is being created; items may be added or modified.
        SUBMITTED: Inspection has been finalized and submitted for review.
        APPROVED: Inspection has been reviewed and approved.
        REJECTED: Inspection has been rejected and requires re-submission.
    """

    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class InspectionType(StrEnum):
    """Type of vehicle inspection.

    Attributes:
        PRE_TRIP: Inspection conducted before a trip.
        POST_TRIP: Inspection conducted after a trip.
        PERIODIC: Scheduled periodic inspection.
        UNSCHEDULED: Ad-hoc inspection triggered by an event.
    """

    PRE_TRIP = "PRE_TRIP"
    POST_TRIP = "POST_TRIP"
    PERIODIC = "PERIODIC"
    UNSCHEDULED = "UNSCHEDULED"


_ALLOWED_TRANSITIONS: dict[InspectionStatus, frozenset[InspectionStatus]] = {
    InspectionStatus.DRAFT: frozenset({InspectionStatus.SUBMITTED}),
    InspectionStatus.SUBMITTED: frozenset(
        {InspectionStatus.APPROVED, InspectionStatus.REJECTED}
    ),
    InspectionStatus.REJECTED: frozenset({InspectionStatus.DRAFT}),
    InspectionStatus.APPROVED: frozenset(),
}


@dataclass
class InspectionItem:
    """A single checklist item within an inspection.

    Attributes:
        id: Unique identifier for this item.
        category: Category of the check (e.g. "Brakes", "Lights").
        description: Human-readable description of what is being checked.
        result: The outcome of the check.
        notes: Optional technician notes or observations.
    """

    id: uuid.UUID
    category: str
    description: str
    result: ChecklistResult
    notes: str | None = field(default=None)

    @property
    def passed(self) -> bool:
        """Return True if this checklist item passed."""
        return self.result == ChecklistResult.PASS

    @property
    def is_applicable(self) -> bool:
        """Return True if this checklist item is applicable."""
        return self.result != ChecklistResult.NOT_APPLICABLE


@dataclass
class Inspection:
    """Aggregate root for the Inspection bounded context.

    An inspection is tied to a specific vehicle and optionally a driver.
    Cross-domain references (vehicle, driver) are stored as UUIDs only.

    Attributes:
        id: Unique identifier for this inspection.
        vehicle_id: UUID of the vehicle being inspected.
        driver_id: UUID of the driver conducting the inspection (optional).
        inspection_type: The type of inspection.
        odometer_reading: Odometer reading recorded at inspection time.
        status: Current lifecycle status.
        items: Ordered list of checklist items.
        reviewed_by_id: UUID of the user who reviewed the inspection (optional).
        review_notes: Optional reviewer notes.
        inspected_at: UTC timestamp when the inspection was conducted.
        created_at: UTC timestamp when the record was created.
        updated_at: UTC timestamp of the last update.
    """

    id: uuid.UUID
    vehicle_id: uuid.UUID
    inspection_type: InspectionType
    odometer_reading: OdometerReading
    status: InspectionStatus
    inspected_at: datetime
    created_at: datetime
    updated_at: datetime
    driver_id: uuid.UUID | None = field(default=None)
    reviewed_by_id: uuid.UUID | None = field(default=None)
    review_notes: str | None = field(default=None)
    items: list[InspectionItem] = field(default_factory=list)

    def transition_to(self, target: InspectionStatus) -> None:
        """Guard and apply a status transition.

        Args:
            target: The desired new status.

        Raises:
            InspectionInvalidStateTransitionError: If the transition is not allowed.
        """
        allowed = _ALLOWED_TRANSITIONS.get(self.status, frozenset())
        if target not in allowed:
            raise InspectionInvalidStateTransitionError(
                current_status=self.status.value,
                target_status=target.value,
            )
        self.status = target

    def add_item(self, item: InspectionItem) -> None:
        """Append a checklist item to this inspection.

        Args:
            item: The ``InspectionItem`` to append.

        Raises:
            InspectionAlreadySubmittedError: If the inspection is no longer DRAFT.
        """
        if self.status != InspectionStatus.DRAFT:
            raise InspectionAlreadySubmittedError(self.id)
        self.items.append(item)

    def submit(self) -> None:
        """Submit the inspection for review.

        Raises:
            InspectionItemRequiredError: If no checklist items have been added.
            InspectionInvalidStateTransitionError: If not in DRAFT status.
        """
        if not self.items:
            raise InspectionItemRequiredError()
        self.transition_to(InspectionStatus.SUBMITTED)

    def approve(self, reviewed_by_id: uuid.UUID, notes: str | None = None) -> None:
        """Approve the submitted inspection.

        Args:
            reviewed_by_id: UUID of the reviewer.
            notes: Optional reviewer notes.

        Raises:
            InspectionInvalidStateTransitionError: If not SUBMITTED.
        """
        self.transition_to(InspectionStatus.APPROVED)
        self.reviewed_by_id = reviewed_by_id
        self.review_notes = notes

    def reject(self, reviewed_by_id: uuid.UUID, notes: str | None = None) -> None:
        """Reject the submitted inspection.

        Args:
            reviewed_by_id: UUID of the reviewer.
            notes: Optional explanation of the rejection.

        Raises:
            InspectionInvalidStateTransitionError: If not SUBMITTED.
        """
        self.transition_to(InspectionStatus.REJECTED)
        self.reviewed_by_id = reviewed_by_id
        self.review_notes = notes

    def reopen(self) -> None:
        """Reopen a REJECTED inspection for editing.

        Raises:
            InspectionInvalidStateTransitionError: If not REJECTED.
        """
        self.transition_to(InspectionStatus.DRAFT)
        self.reviewed_by_id = None
        self.review_notes = None

    @property
    def score(self) -> InspectionScore | None:
        """Compute and return the inspection score.

        Returns:
            An ``InspectionScore`` if there are applicable items, else ``None``.
        """
        applicable = [i for i in self.items if i.is_applicable]
        if not applicable:
            return None
        passed = sum(1 for i in applicable if i.passed)
        return InspectionScore.compute(passed=passed, total=len(applicable))

    @property
    def has_failures(self) -> bool:
        """Return True if any checklist item has a FAIL result."""
        return any(i.result == ChecklistResult.FAIL for i in self.items)

    def failed_items(self) -> list[InspectionItem]:
        """Return checklist items that failed inspection."""
        return [item for item in self.items if item.result == ChecklistResult.FAIL]
