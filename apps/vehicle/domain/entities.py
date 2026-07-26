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
from apps.vehicle.domain.value_objects import PlateNumber, SAPVehicleNumber


class VehicleStatus(StrEnum):
    """Lifecycle states of a vehicle in the fleet.

    Attributes:
        ACTIVE: Vehicle is operational and available for assignment.
        INACTIVE: Vehicle has been decommissioned or removed from service.
        UNDER_REPAIR: Vehicle is currently being repaired and unavailable.
        UNDER_EXTERNAL_REPAIR: Vehicle is at an external workshop and unavailable.
        EXITED_CENTER: Vehicle has left the fleet center after daily checklist.
        SUSPENDED: Vehicle is temporarily suspended (e.g. pending inspection).
        OUT_OF_SERVICE: Vehicle failed inspection and is not operational.
    """

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    UNDER_REPAIR = "UNDER_REPAIR"
    UNDER_EXTERNAL_REPAIR = "UNDER_EXTERNAL_REPAIR"
    WAITING_DRIVER_CONFIRMATION = "WAITING_DRIVER_CONFIRMATION"
    EXITED_CENTER = "EXITED_CENTER"
    SUSPENDED = "SUSPENDED"
    OUT_OF_SERVICE = "OUT_OF_SERVICE"
    DECOMMISSIONED = "DECOMMISSIONED"


VEHICLE_STATUS_LABELS: dict[VehicleStatus, str] = {
    VehicleStatus.ACTIVE: "عملیاتی",
    VehicleStatus.INACTIVE: "غیرفعال",
    VehicleStatus.UNDER_REPAIR: "در تعمیر",
    VehicleStatus.UNDER_EXTERNAL_REPAIR: "در تعمیرگاه بیرونی",
    VehicleStatus.WAITING_DRIVER_CONFIRMATION: "منتظر تایید راننده",
    VehicleStatus.EXITED_CENTER: "خروج از مرکز",
    VehicleStatus.SUSPENDED: "تعلیق‌شده",
    VehicleStatus.OUT_OF_SERVICE: "خارج از سرویس",
    VehicleStatus.DECOMMISSIONED: "از رده خارج",
}


# Permitted status transitions for the Vehicle aggregate.
_ALLOWED_TRANSITIONS: dict[VehicleStatus, frozenset[VehicleStatus]] = {
    VehicleStatus.ACTIVE: frozenset(
        {
            VehicleStatus.INACTIVE,
            VehicleStatus.UNDER_REPAIR,
            VehicleStatus.UNDER_EXTERNAL_REPAIR,
            VehicleStatus.WAITING_DRIVER_CONFIRMATION,
            VehicleStatus.EXITED_CENTER,
            VehicleStatus.SUSPENDED,
            VehicleStatus.OUT_OF_SERVICE,
            VehicleStatus.DECOMMISSIONED,
        }
    ),
    VehicleStatus.UNDER_REPAIR: frozenset(
        {
            VehicleStatus.ACTIVE,
            VehicleStatus.INACTIVE,
            VehicleStatus.UNDER_EXTERNAL_REPAIR,
            VehicleStatus.WAITING_DRIVER_CONFIRMATION,
            VehicleStatus.SUSPENDED,
            VehicleStatus.OUT_OF_SERVICE,
            VehicleStatus.DECOMMISSIONED,
        }
    ),
    VehicleStatus.WAITING_DRIVER_CONFIRMATION: frozenset(
        {
            VehicleStatus.ACTIVE,
            VehicleStatus.UNDER_REPAIR,
            VehicleStatus.UNDER_EXTERNAL_REPAIR,
            VehicleStatus.OUT_OF_SERVICE,
            VehicleStatus.SUSPENDED,
            VehicleStatus.INACTIVE,
            VehicleStatus.DECOMMISSIONED,
        }
    ),
    VehicleStatus.SUSPENDED: frozenset(
        {
            VehicleStatus.ACTIVE,
            VehicleStatus.INACTIVE,
            VehicleStatus.UNDER_REPAIR,
            VehicleStatus.UNDER_EXTERNAL_REPAIR,
            VehicleStatus.WAITING_DRIVER_CONFIRMATION,
            VehicleStatus.OUT_OF_SERVICE,
            VehicleStatus.DECOMMISSIONED,
        }
    ),
    VehicleStatus.EXITED_CENTER: frozenset(
        {
            VehicleStatus.ACTIVE,
            VehicleStatus.INACTIVE,
            VehicleStatus.UNDER_REPAIR,
            VehicleStatus.UNDER_EXTERNAL_REPAIR,
            VehicleStatus.WAITING_DRIVER_CONFIRMATION,
            VehicleStatus.SUSPENDED,
            VehicleStatus.OUT_OF_SERVICE,
            VehicleStatus.DECOMMISSIONED,
        }
    ),
    VehicleStatus.OUT_OF_SERVICE: frozenset(
        {
            VehicleStatus.ACTIVE,
            VehicleStatus.UNDER_REPAIR,
            VehicleStatus.UNDER_EXTERNAL_REPAIR,
            VehicleStatus.WAITING_DRIVER_CONFIRMATION,
            VehicleStatus.INACTIVE,
            VehicleStatus.SUSPENDED,
            VehicleStatus.DECOMMISSIONED,
        }
    ),
    VehicleStatus.INACTIVE: frozenset(
        {
            VehicleStatus.ACTIVE,
            VehicleStatus.UNDER_REPAIR,
            VehicleStatus.UNDER_EXTERNAL_REPAIR,
            VehicleStatus.DECOMMISSIONED,
        }
    ),
    VehicleStatus.UNDER_EXTERNAL_REPAIR: frozenset(
        {
            VehicleStatus.ACTIVE,
            VehicleStatus.UNDER_REPAIR,
            VehicleStatus.WAITING_DRIVER_CONFIRMATION,
            VehicleStatus.OUT_OF_SERVICE,
            VehicleStatus.SUSPENDED,
            VehicleStatus.INACTIVE,
            VehicleStatus.DECOMMISSIONED,
        }
    ),
    VehicleStatus.DECOMMISSIONED: frozenset(),
}


@dataclass(init=False)
class Vehicle:
    """Aggregate root for the Vehicle bounded context.

    Represents a physical fleet vehicle tracked by FMMS. All status transitions
    are guarded by the entity itself. Cross-domain invariants (e.g. preventing
    deactivation when an active repair order exists) are enforced by the
    Application Service before invoking transition methods.

    Attributes:
        id: Universally unique identifier for this vehicle.
        vehicle_number: SAP ``VehicleNumber`` and unique vehicle identifier.
        license_plate: SAP ``LicensePlate``.
        commissioning_date: SAP ``CommissioningDate`` in source format.
        driver1_customer_number: SAP ``Driver1CustomerNo`` for main driver.
        driver2_customer_number: SAP ``Driver2CustomerNo`` for assistant driver.
        status: Current lifecycle status.
        created_at: UTC timestamp when the record was created.
        updated_at: UTC timestamp of the last update.
    """

    id: uuid.UUID
    vehicle_number: SAPVehicleNumber
    license_plate: PlateNumber
    status: VehicleStatus
    created_at: datetime
    updated_at: datetime
    commissioning_date: str | None = field(default=None)
    driver1_customer_number: str | None = field(default=None)
    driver2_customer_number: str | None = field(default=None)

    def __init__(
        self,
        *,
        id: uuid.UUID,
        status: VehicleStatus,
        created_at: datetime,
        updated_at: datetime,
        vehicle_number: SAPVehicleNumber | None = None,
        license_plate: PlateNumber | None = None,
        commissioning_date: str | None = None,
        driver1_customer_number: str | None = None,
        driver2_customer_number: str | None = None,
    ) -> None:
        self.id = id
        if vehicle_number is None:
            raise ValueError("vehicle_number is required.")
        if license_plate is None:
            raise ValueError("license_plate is required.")
        self.vehicle_number = vehicle_number
        self.license_plate = license_plate
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at
        self.commissioning_date = _validated_commissioning_date(commissioning_date)
        self.driver1_customer_number = driver1_customer_number
        self.driver2_customer_number = driver2_customer_number

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

    def mark_under_external_repair(self) -> None:
        """Transition vehicle to UNDER_EXTERNAL_REPAIR after external delivery."""
        self.transition_to(VehicleStatus.UNDER_EXTERNAL_REPAIR)

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

    def decommission(self) -> None:
        """Mark the vehicle as removed from SAP fleet master data."""
        self.transition_to(VehicleStatus.DECOMMISSIONED)

    @property
    def is_available(self) -> bool:
        """Return True if the vehicle is ACTIVE and available for assignment."""
        return self.status == VehicleStatus.ACTIVE


def _validated_commissioning_date(value: str | None) -> str | None:
    """Return a validated SAP YYYYMMDD commissioning date."""
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    if len(stripped) != 8 or not stripped.isdigit():
        raise ValueError("commissioning_date must be an 8-digit SAP YYYYMMDD value.")
    return stripped
