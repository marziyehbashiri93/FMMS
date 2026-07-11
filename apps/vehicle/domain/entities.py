"""Domain entities for the Vehicle bounded context.

Entities are mutable objects with identity defined by their unique ID.
All business rules that belong solely to the Vehicle aggregate are encoded here.
Cross-domain rules (e.g. checking for active repair orders before deactivation)
are the responsibility of the Application Service layer.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from apps.vehicle.domain.exceptions import VehicleInvalidStateTransitionError
from apps.vehicle.domain.value_objects import (
    VIN,
    ChassisNumber,
    PlateNumber,
    SAPEquipmentNumber,
)


class VehicleStatus(StrEnum):
    """Lifecycle states of a vehicle in the fleet.

    Attributes:
        ACTIVE: Vehicle is operational and available for assignment.
        INACTIVE: Vehicle has been decommissioned or removed from service.
        UNDER_REPAIR: Vehicle is currently being repaired and unavailable.
        SUSPENDED: Vehicle is temporarily suspended (e.g. pending inspection).
        OUT_OF_SERVICE: Vehicle failed inspection and is not operational.
    """

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    UNDER_REPAIR = "UNDER_REPAIR"
    WAITING_DRIVER_CONFIRMATION = "WAITING_DRIVER_CONFIRMATION"
    SUSPENDED = "SUSPENDED"
    OUT_OF_SERVICE = "OUT_OF_SERVICE"


class VehicleCategory(StrEnum):
    """Operational category of a vehicle.

    Attributes:
        LIGHT: Passenger cars and light vans.
        HEAVY: Trucks, buses, and heavy machinery.
        MOTORCYCLE: Motorcycles and scooters.
        SPECIAL: Special-purpose equipment (e.g. cranes, forklifts).
    """

    LIGHT = "LIGHT"
    HEAVY = "HEAVY"
    MOTORCYCLE = "MOTORCYCLE"
    SPECIAL = "SPECIAL"


# Permitted status transitions for the Vehicle aggregate.
_ALLOWED_TRANSITIONS: dict[VehicleStatus, frozenset[VehicleStatus]] = {
    VehicleStatus.ACTIVE: frozenset(
        {
            VehicleStatus.INACTIVE,
            VehicleStatus.UNDER_REPAIR,
            VehicleStatus.WAITING_DRIVER_CONFIRMATION,
            VehicleStatus.SUSPENDED,
            VehicleStatus.OUT_OF_SERVICE,
        }
    ),
    VehicleStatus.UNDER_REPAIR: frozenset(
        {
            VehicleStatus.ACTIVE,
            VehicleStatus.INACTIVE,
            VehicleStatus.WAITING_DRIVER_CONFIRMATION,
            VehicleStatus.SUSPENDED,
            VehicleStatus.OUT_OF_SERVICE,
        }
    ),
    VehicleStatus.WAITING_DRIVER_CONFIRMATION: frozenset(
        {
            VehicleStatus.ACTIVE,
            VehicleStatus.OUT_OF_SERVICE,
            VehicleStatus.SUSPENDED,
            VehicleStatus.INACTIVE,
        }
    ),
    VehicleStatus.SUSPENDED: frozenset(
        {
            VehicleStatus.ACTIVE,
            VehicleStatus.INACTIVE,
            VehicleStatus.UNDER_REPAIR,
            VehicleStatus.WAITING_DRIVER_CONFIRMATION,
            VehicleStatus.OUT_OF_SERVICE,
        }
    ),
    VehicleStatus.OUT_OF_SERVICE: frozenset(
        {
            VehicleStatus.ACTIVE,
            VehicleStatus.UNDER_REPAIR,
            VehicleStatus.WAITING_DRIVER_CONFIRMATION,
            VehicleStatus.INACTIVE,
            VehicleStatus.SUSPENDED,
        }
    ),
    VehicleStatus.INACTIVE: frozenset({VehicleStatus.ACTIVE}),
}


@dataclass
class Vehicle:
    """Aggregate root for the Vehicle bounded context.

    Represents a physical fleet vehicle tracked by FMMS. All status transitions
    are guarded by the entity itself. Cross-domain invariants (e.g. preventing
    deactivation when an active repair order exists) are enforced by the
    Application Service before invoking transition methods.

    Attributes:
        id: Universally unique identifier for this vehicle.
        plate_number: Validated, unique plate number.
        vin: 17-character Vehicle Identification Number.
        chassis_number: Optional chassis number.
        sap_equipment_number: Optional SAP plant-maintenance equipment number.
        make: Manufacturer name (e.g. "Toyota").
        model: Model name (e.g. "Hilux").
        year: Manufacturing year.
        category: Operational category of the vehicle.
        status: Current lifecycle status.
        created_at: UTC timestamp when the record was created.
        updated_at: UTC timestamp of the last update.
    """

    id: uuid.UUID
    plate_number: PlateNumber
    vin: VIN
    make: str
    model: str
    year: int
    category: VehicleCategory
    status: VehicleStatus
    created_at: datetime
    updated_at: datetime
    chassis_number: ChassisNumber | None = field(default=None)
    sap_equipment_number: SAPEquipmentNumber | None = field(default=None)

    def transition_to(self, target: VehicleStatus) -> None:
        """Transition the vehicle to a new status if the transition is permitted.

        Args:
            target: The desired new status.

        Raises:
            VehicleInvalidStateTransitionError: If the transition from the
                current status to ``target`` is not allowed.
        """
        allowed = _ALLOWED_TRANSITIONS.get(self.status, frozenset())
        if target not in allowed:
            raise VehicleInvalidStateTransitionError(
                current_status=self.status.value,
                target_status=target.value,
            )
        self.status = target

    def mark_under_repair(self) -> None:
        """Transition the vehicle to UNDER_REPAIR status.

        Raises:
            VehicleInvalidStateTransitionError: If not permitted from the
                current status.
        """
        self.transition_to(VehicleStatus.UNDER_REPAIR)

    def mark_out_of_service(self) -> None:
        """Transition the vehicle to OUT_OF_SERVICE after a failed inspection.

        Raises:
            VehicleInvalidStateTransitionError: If not permitted from the
                current status.
        """
        self.transition_to(VehicleStatus.OUT_OF_SERVICE)

    def complete_repair(self) -> None:
        """Transition the vehicle back to ACTIVE after repair completion.

        Raises:
            VehicleInvalidStateTransitionError: If not permitted from the
                current status.
        """
        self.transition_to(VehicleStatus.ACTIVE)

    def mark_waiting_driver_confirmation(self) -> None:
        """Transition vehicle to WAITING_DRIVER_CONFIRMATION after repair."""
        self.transition_to(VehicleStatus.WAITING_DRIVER_CONFIRMATION)

    def activate(self) -> None:
        """Return the vehicle to ACTIVE when maintenance clearance allows it.

        Raises:
            VehicleInvalidStateTransitionError: If not permitted from the
                current status.
        """
        self.transition_to(VehicleStatus.ACTIVE)

    def suspend(self) -> None:
        """Suspend the vehicle pending an inspection or administrative action.

        Raises:
            VehicleInvalidStateTransitionError: If not permitted from the
                current status.
        """
        self.transition_to(VehicleStatus.SUSPENDED)

    def deactivate(self) -> None:
        """Permanently deactivate the vehicle.

        Note:
            The Application Service layer is responsible for verifying that
            no active repair orders exist for this vehicle before calling
            this method.

        Raises:
            VehicleInvalidStateTransitionError: If the vehicle is already
                INACTIVE or the transition is otherwise not permitted.
        """
        self.transition_to(VehicleStatus.INACTIVE)

    @property
    def is_available(self) -> bool:
        """Return True if the vehicle is ACTIVE and available for assignment."""
        return self.status == VehicleStatus.ACTIVE
