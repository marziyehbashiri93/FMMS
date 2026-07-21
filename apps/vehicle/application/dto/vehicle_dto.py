"""Application-layer DTOs for the Vehicle domain.

Rules enforced here:
- No ORM models, no Django serializers, no database objects.
- All fields are primitive Python types or enums from the domain layer.
- Mapping between DTO <-> Domain Entity happens explicitly inside each service.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime

from apps.vehicle.domain.entities import VehicleStatus


@dataclass(frozen=True)
class ChangeVehicleStatusDTO:
    """Input DTO for changing an FMMS-controlled vehicle status."""

    vehicle_id: uuid.UUID
    status: VehicleStatus
    request_id: str
    requested_by: uuid.UUID


@dataclass(frozen=True)
class VehicleAssignedDriverDTO:
    """Driver details displayed inside vehicle detail responses."""

    customer_number: str
    name: str | None


@dataclass(frozen=True)
class VehicleResponseDTO:
    """Output DTO returned by all vehicle read and write operations.

    Contains only primitive types safe to serialise directly to JSON without
    any ORM or Django object leaking through.

    Attributes:
        id: Vehicle UUID.
        vehicle_number: SAP ``VehicleNumber`` and unique vehicle identifier.
        license_plate: SAP ``LicensePlate``.
        commissioning_date: SAP ``CommissioningDate`` in source format.
        driver1: Main assigned driver display data.
        driver2: Assistant assigned driver display data.
        status: Current lifecycle status.
        created_at: UTC timestamp of record creation.
        updated_at: UTC timestamp of the last modification.
    """

    id: uuid.UUID
    vehicle_number: str
    license_plate: str
    status: VehicleStatus
    status_label: str
    created_at: datetime
    updated_at: datetime
    commissioning_date: str | None = field(default=None)
    driver1: VehicleAssignedDriverDTO | None = field(default=None)
    driver2: VehicleAssignedDriverDTO | None = field(default=None)


@dataclass(frozen=True)
class VehicleSAPSyncResultDTO:
    """Summary of a bulk SAP vehicle-driver → FMMS synchronisation.

    Attributes:
        total_received: Number of vehicle-driver rows returned by SAP.
        created: Number of new FMMS vehicles created.
        updated: Number of existing FMMS vehicles updated.
        decommissioned: Number of local vehicles no longer present in SAP.
        failed: Number of records that could not be synced.
    """

    total_received: int
    created: int
    updated: int
    decommissioned: int
    failed: int


@dataclass(frozen=True)
class VehicleSummaryDTO:
    """Output DTO for vehicle dashboard summary cards."""

    active_fleet_count: int
    operational_fleet_count: int
    under_repair_fleet_count: int
    unusable_fleet_count: int
    last_sap_sync_at: datetime | None
    average_odometer_km: float
    average_faults_last_30_days: float


@dataclass(frozen=True)
class RecordVehicleOdometerDTO:
    """Input DTO for recording a vehicle daily odometer reading."""

    vehicle_id: uuid.UUID
    reading_date: date
    odometer_km: int
    source: str
    request_id: str
    recorded_by: uuid.UUID


@dataclass(frozen=True)
class VehicleOdometerResponseDTO:
    """Output DTO for a daily odometer reading."""

    id: uuid.UUID
    vehicle_id: uuid.UUID
    reading_date: date
    odometer_km: int
    source: str
    recorded_by: uuid.UUID
    recorded_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class VehicleDriverAssignmentHistoryResponseDTO:
    """Output DTO for a SAP driver-assignment snapshot."""

    id: uuid.UUID
    sync_run_id: uuid.UUID
    request_id: str
    synced_at: datetime
    vehicle_id: uuid.UUID
    vehicle_number: str
    license_plate: str
    driver_role: str
    driver_customer_number: str | None


@dataclass(frozen=True)
class VehicleDriverAssignmentSnapshotResponseDTO:
    """Output DTO for one vehicle driver-assignment snapshot."""

    assigned_at: datetime
    driver: VehicleAssignedDriverDTO | None
    assistant: VehicleAssignedDriverDTO | None
