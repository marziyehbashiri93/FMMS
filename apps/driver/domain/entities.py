"""Domain entities for the Driver bounded context.

Cross-domain rules (e.g. verifying vehicle availability before assigning a
driver) are the responsibility of the Application Service layer.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from apps.driver.domain.exceptions import DriverInvalidStateTransitionError
from apps.driver.domain.value_objects import DriverContact, LicenseClass, LicenseNumber


class DriverStatus(StrEnum):
    """Lifecycle states of a driver record.

    Attributes:
        ACTIVE: Driver is available for vehicle assignment.
        SUSPENDED: Driver is temporarily suspended.
        INACTIVE: Driver record is decommissioned.
        ON_LEAVE: Driver is on authorised leave and temporarily unavailable.
    """

    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    INACTIVE = "INACTIVE"
    ON_LEAVE = "ON_LEAVE"


_ALLOWED_TRANSITIONS: dict[DriverStatus, frozenset[DriverStatus]] = {
    DriverStatus.ACTIVE: frozenset(
        {DriverStatus.SUSPENDED, DriverStatus.INACTIVE, DriverStatus.ON_LEAVE}
    ),
    DriverStatus.SUSPENDED: frozenset({DriverStatus.ACTIVE, DriverStatus.INACTIVE}),
    DriverStatus.ON_LEAVE: frozenset(
        {DriverStatus.ACTIVE, DriverStatus.SUSPENDED, DriverStatus.INACTIVE}
    ),
    DriverStatus.INACTIVE: frozenset(),
}


@dataclass
class Driver:
    """Aggregate root for the Driver bounded context.

    Attributes:
        id: Universally unique identifier for this driver.
        full_name: Driver's full legal name.
        license_number: Validated unique license number.
        license_class: Classification of the driver's license.
        contact: Contact details (phone, optional email).
        status: Current lifecycle status.
        assigned_vehicle_id: UUID of the currently assigned vehicle,
            or ``None`` if unassigned. Cross-domain link by ID only.
        created_at: UTC timestamp when the record was created.
        updated_at: UTC timestamp of the last update.
    """

    id: uuid.UUID
    full_name: str
    license_number: LicenseNumber
    license_class: LicenseClass
    contact: DriverContact
    status: DriverStatus
    created_at: datetime
    updated_at: datetime
    assigned_vehicle_id: uuid.UUID | None = field(default=None)

    def transition_to(self, target: DriverStatus) -> None:
        """Transition the driver to a new status if the transition is permitted.

        Args:
            target: The desired new status.

        Raises:
            DriverInvalidStateTransitionError: If the transition is not allowed.
        """
        allowed = _ALLOWED_TRANSITIONS.get(self.status, frozenset())
        if target not in allowed:
            raise DriverInvalidStateTransitionError(
                current_status=self.status.value,
                target_status=target.value,
            )
        self.status = target

    def suspend(self) -> None:
        """Suspend the driver.

        Raises:
            DriverInvalidStateTransitionError: If not permitted.
        """
        self.transition_to(DriverStatus.SUSPENDED)

    def reinstate(self) -> None:
        """Reinstate the driver to ACTIVE status.

        Raises:
            DriverInvalidStateTransitionError: If not permitted.
        """
        self.transition_to(DriverStatus.ACTIVE)

    def deactivate(self) -> None:
        """Permanently deactivate the driver record.

        Raises:
            DriverInvalidStateTransitionError: If already INACTIVE or
                transition not permitted.
        """
        self.transition_to(DriverStatus.INACTIVE)

    def assign_vehicle(self, vehicle_id: uuid.UUID) -> None:
        """Record an assignment of a vehicle to this driver.

        Note:
            Vehicle availability is verified at the Application Service level
            before invoking this method.

        Args:
            vehicle_id: UUID of the vehicle being assigned.
        """
        self.assigned_vehicle_id = vehicle_id

    def unassign_vehicle(self) -> None:
        """Remove the current vehicle assignment from this driver."""
        self.assigned_vehicle_id = None

    @property
    def is_available(self) -> bool:
        """Return True if the driver is ACTIVE and not currently assigned."""
        return self.status == DriverStatus.ACTIVE and self.assigned_vehicle_id is None
