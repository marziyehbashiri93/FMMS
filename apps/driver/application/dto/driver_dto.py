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


@dataclass(frozen=True)
class DriverExitCenterDTO:
    """Input DTO for a driver requesting vehicle exit from the fleet center.

    Attributes:
        driver_id: Driver requesting the exit workflow.
        vehicle_id: Assigned vehicle that should leave the fleet center.
        inspection_id: Submitted daily checklist required for exit.
        request_id: Correlation ID for structured logs.
        requested_by_user_id: Authenticated FMMS user recorded in logs only.
    """

    driver_id: uuid.UUID
    vehicle_id: uuid.UUID
    inspection_id: uuid.UUID
    request_id: str
    requested_by_user_id: uuid.UUID


@dataclass(frozen=True)
class DriverAssignedVehicleDTO:
    """Vehicle details displayed inside driver responses.

    Attributes:
        id: Vehicle UUID.
        vehicle_number: SAP ``VehicleNumber``.
        license_plate: SAP ``LicensePlate``.
    """

    id: uuid.UUID
    vehicle_number: str
    license_plate: str


@dataclass(frozen=True)
class DriverResponseDTO:
    """Output DTO returned by all driver read and write operations.

    Contains only primitive types safe to serialise directly to JSON.

    Attributes:
        id: Driver UUID.
        customer_number: SAP ``CustomerNumber``.
        name: SAP driver name.
        mobile: SAP driver mobile/phone.
        personnel_number: SAP personnel number.
        gender: SAP gender text.
        nilofar_code: SAP Nilofar code.
        status: Current lifecycle status.
        created_at: UTC timestamp of record creation.
        updated_at: UTC timestamp of last modification.
        current_vehicle_as_driver: Vehicle where this driver is main driver.
        current_vehicle_as_assistant: Vehicle where this driver is assistant.
    """

    id: uuid.UUID
    customer_number: str
    name: str
    status: DriverStatus
    created_at: datetime
    updated_at: datetime
    mobile: str | None = field(default=None)
    personnel_number: str | None = field(default=None)
    gender: str | None = field(default=None)
    nilofar_code: str | None = field(default=None)
    current_vehicle_as_driver: DriverAssignedVehicleDTO | None = field(default=None)
    current_vehicle_as_assistant: DriverAssignedVehicleDTO | None = field(default=None)


@dataclass(frozen=True)
class DriverSummaryDTO:
    """Output DTO for driver dashboard summary cards.

    Attributes:
        active_count: Number of active (non-deleted) drivers.
        decommissioned_count: Number of decommissioned (non-deleted) drivers.
        with_vehicle_count: Active drivers currently assigned to a vehicle.
        last_sap_sync_at: Finished timestamp of the latest successful vehicles
            SAP sync run item, if any.
    """

    active_count: int
    decommissioned_count: int
    with_vehicle_count: int
    last_sap_sync_at: datetime | None
