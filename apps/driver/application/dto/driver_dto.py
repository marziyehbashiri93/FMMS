"""Application-layer DTOs for the Driver domain.

Rules:
- No ORM models, no Django objects, no database objects.
- All fields are primitive Python types or domain enums.
- Mapping DTO <-> Domain Entity happens explicitly inside each service.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from apps.driver.domain.entities import DriverStatus
from apps.driver.domain.value_objects import LicenseClass


@dataclass(frozen=True)
class RegisterDriverDTO:
    """Input DTO for registering a new driver.

    Attributes:
        full_name: Driver's full legal name.
        license_number: Raw license number string; validated by ``LicenseNumber`` VO.
        license_class: Classification of the driver's license.
        phone: Contact phone number.
        request_id: Correlation ID for tracing.
        created_by: UUID of the authenticated user performing the action.
        email: Optional contact email address.
    """

    full_name: str
    license_number: str
    license_class: LicenseClass
    phone: str
    request_id: str
    created_by: uuid.UUID
    email: str | None = field(default=None)


@dataclass(frozen=True)
class AssignDriverToVehicleDTO:
    """Input DTO for assigning a driver to a specific vehicle.

    The Application Service enforces the cross-domain invariants:
    - Driver must be ACTIVE and unassigned.
    - Vehicle must be ACTIVE and available.

    Attributes:
        driver_id: UUID of the driver to assign.
        vehicle_id: UUID of the target vehicle.
        request_id: Correlation ID for tracing.
        assigned_by: UUID of the user performing the assignment.
    """

    driver_id: uuid.UUID
    vehicle_id: uuid.UUID
    request_id: str
    assigned_by: uuid.UUID


@dataclass(frozen=True)
class SuspendDriverDTO:
    """Input DTO for suspending a driver.

    Attributes:
        driver_id: UUID of the driver to suspend.
        request_id: Correlation ID for tracing.
        requested_by: UUID of the user requesting suspension.
    """

    driver_id: uuid.UUID
    request_id: str
    requested_by: uuid.UUID


@dataclass(frozen=True)
class DriverResponseDTO:
    """Output DTO returned by all driver read and write operations.

    Contains only primitive types safe to serialise directly to JSON.

    Attributes:
        id: Driver UUID.
        full_name: Driver's full legal name.
        license_number: Normalised license number string.
        license_class: License classification.
        status: Current lifecycle status.
        phone: Contact phone number.
        created_at: UTC timestamp of record creation.
        updated_at: UTC timestamp of last modification.
        email: Optional contact email.
        assigned_vehicle_id: UUID of currently assigned vehicle, or ``None``.
    """

    id: uuid.UUID
    full_name: str
    license_number: str
    license_class: LicenseClass
    status: DriverStatus
    phone: str
    created_at: datetime
    updated_at: datetime
    email: str | None = field(default=None)
    assigned_vehicle_id: uuid.UUID | None = field(default=None)
