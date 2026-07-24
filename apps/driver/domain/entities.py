"""Domain entities for SAP-sourced fleet drivers."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from apps.driver.domain.exceptions import DriverInvalidStateTransitionError
from apps.driver.domain.value_objects import CustomerNumber


class DriverStatus(StrEnum):
    """Lifecycle states of a SAP-sourced driver record."""

    ACTIVE = "ACTIVE"
    DECOMMISSIONED = "DECOMMISSIONED"


_ALLOWED_TRANSITIONS: dict[DriverStatus, frozenset[DriverStatus]] = {
    DriverStatus.ACTIVE: frozenset({DriverStatus.DECOMMISSIONED}),
    DriverStatus.DECOMMISSIONED: frozenset({DriverStatus.ACTIVE}),
}


@dataclass(init=False)
class Driver:
    """Aggregate root for the Driver bounded context.

    Attributes:
        id: Universally unique identifier for this driver.
        customer_number: SAP ``CustomerNumber`` and unique driver identifier.
        name: SAP driver name.
        mobile: SAP driver mobile/phone.
        personnel_number: SAP personnel number.
        gender: SAP gender text.
        nilofar_code: SAP Nilofar code.
        status: Current lifecycle status.
        created_at: UTC timestamp when the record was created.
        updated_at: UTC timestamp of the last update.
    """

    id: uuid.UUID
    customer_number: CustomerNumber
    name: str
    status: DriverStatus
    created_at: datetime
    updated_at: datetime
    mobile: str | None = field(default=None)
    personnel_number: str | None = field(default=None)
    gender: str | None = field(default=None)
    nilofar_code: str | None = field(default=None)

    def __init__(
        self,
        *,
        id: uuid.UUID,
        status: DriverStatus,
        created_at: datetime,
        updated_at: datetime,
        customer_number: CustomerNumber | None = None,
        name: str | None = None,
        mobile: str | None = None,
        personnel_number: str | None = None,
        gender: str | None = None,
        nilofar_code: str | None = None,
    ) -> None:
        self.id = id
        if customer_number is None:
            raise ValueError("customer_number is required.")
        self.customer_number = customer_number
        self.name = name or self.customer_number.value
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at
        self.mobile = mobile
        self.personnel_number = personnel_number
        self.gender = gender
        self.nilofar_code = nilofar_code

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

    def reactivate(self) -> None:
        """Mark the driver ACTIVE when returned by SAP again.

        Raises:
            DriverInvalidStateTransitionError: If not permitted.
        """
        self.transition_to(DriverStatus.ACTIVE)

    def decommission(self) -> None:
        """Mark the driver decommissioned when absent from SAP sync.

        Raises:
            DriverInvalidStateTransitionError: If not permitted.
        """
        self.transition_to(DriverStatus.DECOMMISSIONED)
