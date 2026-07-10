"""Application-layer DTOs for the Vehicle domain.

Rules enforced here:
- No ORM models, no Django serializers, no database objects.
- All fields are primitive Python types or enums from the domain layer.
- Mapping between DTO <-> Domain Entity happens explicitly inside each service.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from apps.vehicle.domain.entities import VehicleCategory, VehicleStatus


@dataclass(frozen=True)
class CreateVehicleDTO:
    """Input DTO for creating a new fleet vehicle.

    Attributes:
        plate_number: Raw plate string; the service will validate via the
            ``PlateNumber`` value object.
        vin: 17-character Vehicle Identification Number.
        make: Manufacturer name (e.g. "Toyota").
        model: Vehicle model name (e.g. "Hilux").
        year: Manufacturing year (four-digit integer).
        category: Operational category of the vehicle.
        chassis_number: Optional chassis identifier.
        sap_equipment_number: Optional SAP PM equipment number.
        request_id: Correlation ID propagated from the HTTP layer for tracing.
        created_by: UUID of the authenticated user performing the action.
    """

    plate_number: str
    vin: str
    make: str
    model: str
    year: int
    category: VehicleCategory
    request_id: str
    created_by: uuid.UUID
    chassis_number: str | None = field(default=None)
    sap_equipment_number: str | None = field(default=None)


@dataclass(frozen=True)
class UpdateVehicleDTO:
    """Input DTO for updating mutable fields of an existing vehicle.

    Only the fields present in this DTO may be updated via the
    ``UpdateVehicleService``.  Status transitions are handled separately
    by dedicated service operations.

    Attributes:
        vehicle_id: Target vehicle to update.
        request_id: Correlation ID for tracing.
        updated_by: UUID of the authenticated user performing the action.
        make: Optional new manufacturer name.
        model: Optional new model name.
        year: Optional new manufacturing year.
        category: Optional new operational category.
        chassis_number: Optional new chassis number.
        sap_equipment_number: Optional updated SAP equipment number.
    """

    vehicle_id: uuid.UUID
    request_id: str
    updated_by: uuid.UUID
    make: str | None = field(default=None)
    model: str | None = field(default=None)
    year: int | None = field(default=None)
    category: VehicleCategory | None = field(default=None)
    chassis_number: str | None = field(default=None)
    sap_equipment_number: str | None = field(default=None)


@dataclass(frozen=True)
class DeactivateVehicleDTO:
    """Input DTO for deactivating a vehicle.

    Attributes:
        vehicle_id: Target vehicle to deactivate.
        request_id: Correlation ID for tracing.
        requested_by: UUID of the user requesting deactivation.
    """

    vehicle_id: uuid.UUID
    request_id: str
    requested_by: uuid.UUID


@dataclass(frozen=True)
class ActivateVehicleDTO:
    """Input DTO for re-activating a vehicle after maintenance.

    Attributes:
        vehicle_id: Target vehicle to activate.
        request_id: Correlation ID for tracing.
        requested_by: UUID of the supervisor/admin performing activation.
    """

    vehicle_id: uuid.UUID
    request_id: str
    requested_by: uuid.UUID


@dataclass(frozen=True)
class VehicleResponseDTO:
    """Output DTO returned by all vehicle read and write operations.

    Contains only primitive types safe to serialise directly to JSON without
    any ORM or Django object leaking through.

    Attributes:
        id: Vehicle UUID.
        plate_number: Normalised plate string.
        vin: 17-character VIN.
        make: Manufacturer name.
        model: Model name.
        year: Manufacturing year.
        category: Operational category.
        status: Current lifecycle status.
        created_at: UTC timestamp of record creation.
        updated_at: UTC timestamp of the last modification.
        chassis_number: Optional chassis identifier.
        sap_equipment_number: Optional SAP equipment number.
    """

    id: uuid.UUID
    plate_number: str
    vin: str
    make: str
    model: str
    year: int
    category: VehicleCategory
    status: VehicleStatus
    created_at: datetime
    updated_at: datetime
    chassis_number: str | None = field(default=None)
    sap_equipment_number: str | None = field(default=None)


@dataclass(frozen=True)
class VehicleSAPSyncResultDTO:
    """Summary of a bulk SAP equipment → FMMS vehicle synchronisation.

    Attributes:
        total_received: Number of equipment records returned by SAP.
        created: Number of new FMMS vehicles created.
        updated: Number of existing FMMS vehicles updated.
        failed: Number of records that could not be synced.
    """

    total_received: int
    created: int
    updated: int
    failed: int
