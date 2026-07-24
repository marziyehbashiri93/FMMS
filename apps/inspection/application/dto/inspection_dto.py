"""Application-layer DTOs for the Inspection domain.

Rules:
- No ORM models, no Django objects, no database objects.
- All fields are primitive Python types or domain enums.
- Mapping DTO <-> Domain Entity happens explicitly inside each service.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from apps.inspection.domain.entities import InspectionStatus, InspectionType
from apps.inspection.domain.value_objects import (
    ChecklistResult,
    FailureSeverity,
    OdometerUnit,
)


@dataclass(frozen=True)
class CreateInspectionItemInputDTO:
    """One checklist result supplied when creating an inspection.

    Attributes:
        category: Category label (often from an inspection template).
        description: Human-readable description of the item being checked.
        result: The outcome of this checklist item.
        notes: Optional technician notes or observations.
        severity: Required when ``result`` is FAIL; driver-assigned fault severity.
    """

    category: str
    description: str
    result: ChecklistResult
    notes: str | None = field(default=None)
    severity: FailureSeverity | None = field(default=None)


@dataclass(frozen=True)
class CreateInspectionDTO:
    """Input DTO for creating a new inspection (starts in DRAFT).

    Attributes:
        vehicle_id: UUID of the vehicle being inspected.
        inspection_type: Type of inspection being performed.
        odometer_value: Current odometer reading value.
        odometer_unit: Unit for the odometer reading (KM or MILES).
        inspected_at: UTC timestamp when the physical inspection occurred.
        request_id: Correlation ID for tracing.
        created_by: UUID of the authenticated user creating the inspection.
        driver_id: Optional UUID of the driver conducting the inspection.
        items: Optional checklist results (typically from SAP templates).
    """

    vehicle_id: uuid.UUID
    inspection_type: InspectionType
    odometer_value: int
    odometer_unit: OdometerUnit
    inspected_at: datetime
    request_id: str
    created_by: uuid.UUID
    driver_id: uuid.UUID | None = field(default=None)
    items: list[CreateInspectionItemInputDTO] = field(default_factory=list)


@dataclass(frozen=True)
class AddInspectionItemDTO:
    """Input DTO for adding a single checklist item to a DRAFT inspection.

    Attributes:
        inspection_id: Target inspection (must be in DRAFT status).
        category: Category label (e.g. "Brakes", "Lights").
        description: Human-readable description of the item being checked.
        result: The outcome of this checklist item.
        request_id: Correlation ID for tracing.
        notes: Optional technician notes or observations.
        severity: Required when ``result`` is FAIL.
    """

    inspection_id: uuid.UUID
    category: str
    description: str
    result: ChecklistResult
    request_id: str
    notes: str | None = field(default=None)
    severity: FailureSeverity | None = field(default=None)


@dataclass(frozen=True)
class SubmitInspectionDTO:
    """Input DTO for submitting a DRAFT inspection for review.

    The service will automatically create Fault entities for any FAIL items
    found in the inspection (the "Inspection submit + automatic fault creation"
    multi-step workflow).  Transaction boundary can be added at the service
    level without rewriting business logic.

    Attributes:
        inspection_id: Target inspection UUID (must be DRAFT with ≥1 item).
        request_id: Correlation ID for tracing.
        submitted_by: UUID of the user submitting the inspection.
    """

    inspection_id: uuid.UUID
    request_id: str
    submitted_by: uuid.UUID


@dataclass(frozen=True)
class ReportInspectionFaultDTO:
    """Input DTO for explicitly reporting a fault from failed checklist items."""

    inspection_id: uuid.UUID
    request_id: str
    reported_by: uuid.UUID


@dataclass(frozen=True)
class InspectionDriverSummaryDTO:
    """Driver summary nested under inspection history responses."""

    id: uuid.UUID
    name: str


@dataclass(frozen=True)
class InspectionItemResponseDTO:
    """Output DTO for a single inspection checklist item.

    Attributes:
        id: Item UUID.
        category: Category label.
        description: Human-readable description.
        result: Checklist outcome.
        notes: Optional technician notes.
        severity: Driver-assigned severity when the item failed.
    """

    id: uuid.UUID
    category: str
    description: str
    result: ChecklistResult
    notes: str | None = field(default=None)
    severity: FailureSeverity | None = field(default=None)


@dataclass(frozen=True)
class InspectionResponseDTO:
    """Output DTO returned by all inspection read and write operations.

    Attributes:
        id: Inspection UUID.
        vehicle_id: UUID of the inspected vehicle.
        inspection_type: Type of inspection.
        odometer_value: Odometer reading value.
        odometer_unit: Odometer unit.
        status: Current lifecycle status.
        inspected_at: UTC timestamp of the physical inspection.
        created_at: UTC timestamp of record creation.
        updated_at: UTC timestamp of last modification.
        items: List of checklist item response DTOs.
        driver_id: Optional driver UUID.
        reviewed_by_id: Optional reviewer UUID.
        review_notes: Optional reviewer notes.
        has_failures: Whether any checklist item failed.
        overall_result: PASS when no failures, FAIL otherwise.
        related_fault_ids: Faults raised from this inspection, if any.
        driver: Resolved driver summary when ``driver_id`` is set.
    """

    id: uuid.UUID
    vehicle_id: uuid.UUID
    inspection_type: InspectionType
    odometer_value: int
    odometer_unit: OdometerUnit
    status: InspectionStatus
    inspected_at: datetime
    created_at: datetime
    updated_at: datetime
    items: list[InspectionItemResponseDTO] = field(default_factory=list)
    driver_id: uuid.UUID | None = field(default=None)
    reviewed_by_id: uuid.UUID | None = field(default=None)
    review_notes: str | None = field(default=None)
    has_failures: bool = field(default=False)
    overall_result: str = field(default="PASS")
    related_fault_ids: list[uuid.UUID] = field(default_factory=list)
    driver: InspectionDriverSummaryDTO | None = field(default=None)
