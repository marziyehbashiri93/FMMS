"""Application-layer DTOs for the Fault domain.

Rules:
- No ORM models, no Django objects, no database objects.
- All fields are primitive Python types or domain enums.
- Mapping DTO <-> Domain Entity happens explicitly inside each service.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from apps.authentication.application.dto.user_profile_dto import UserProfileSummaryDTO
from apps.fault.domain.entities import FaultStatus
from apps.fault.domain.value_objects import FaultSeverity


@dataclass(frozen=True)
class ReportFaultItemDTO:
    """One failed component reported inside a manual fault incident.

    Attributes:
        code: Catalog / classification code for this item.
        description: Human-readable failure detail.
        severity: Severity assigned to this item.
        component: Short label shown on the item (e.g. catalog text).
    """

    code: str
    description: str
    severity: FaultSeverity
    component: str = ""


@dataclass(frozen=True)
class ReportFaultDTO:
    """Input DTO for reporting a new fault.

    Attributes:
        vehicle_id: UUID of the affected vehicle.
        code: Fault classification code string; validated by ``FaultCode`` VO.
        description: Human-readable fault description.
        severity: Severity level.
        request_id: Correlation ID for tracing.
        reported_by: UUID of the user reporting the fault.
        inspection_id: Optional UUID of the originating inspection.
        items: Optional child items when several defects are reported together.
    """

    vehicle_id: uuid.UUID
    code: str
    description: str
    severity: FaultSeverity
    request_id: str
    reported_by: uuid.UUID
    inspection_id: uuid.UUID | None = field(default=None)
    items: list[ReportFaultItemDTO] = field(default_factory=list)


@dataclass(frozen=True)
class AssignFaultDTO:
    """Input DTO for assigning a fault to a technician.

    Attributes:
        fault_id: UUID of the fault to assign.
        technician_id: UUID of the technician receiving the assignment.
        request_id: Correlation ID for tracing.
        assigned_by: UUID of the user performing the assignment.
    """

    fault_id: uuid.UUID
    technician_id: uuid.UUID
    request_id: str
    assigned_by: uuid.UUID


@dataclass(frozen=True)
class CloseFaultDTO:
    """Input DTO for closing a fault.

    Attributes:
        fault_id: UUID of the fault to close.
        request_id: Correlation ID for tracing.
        closed_by: UUID of the user closing the fault.
    """

    fault_id: uuid.UUID
    request_id: str
    closed_by: uuid.UUID


@dataclass(frozen=True)
class DistributionFaultDecisionDTO:
    """Input DTO for distribution unit decision about a reported fault."""

    fault_id: uuid.UUID
    request_id: str
    decided_by: uuid.UUID
    note: str = ""


@dataclass(frozen=True)
class FaultItemResponseDTO:
    """Output DTO for a single fault item."""

    id: uuid.UUID
    component: str
    description: str
    severity: FaultSeverity
    inspection_item_id: uuid.UUID | None = field(default=None)


@dataclass(frozen=True)
class FaultResponseDTO:
    """Output DTO returned by all fault read and write operations.

    Contains only primitive types safe to serialise directly to JSON.

    Attributes:
        id: Fault UUID.
        vehicle_id: UUID of the affected vehicle.
        code: Fault classification code.
        description: Human-readable description.
        severity: Severity level.
        status: Current lifecycle status.
        reported_by_id: UUID of the reporter.
        reported_at: UTC timestamp when the fault was reported.
        created_at: UTC timestamp of record creation.
        updated_at: UTC timestamp of last modification.
        inspection_id: Optional originating inspection UUID.
        assigned_to_id: Optional assigned technician UUID.
        sap_notification_number: Optional SAP PM notification number.
        items: Child fault items linked to this incident.
        created_by: Reporter profile summary when resolvable from auth store.
    """

    id: uuid.UUID
    vehicle_id: uuid.UUID
    code: str
    description: str
    severity: FaultSeverity
    status: FaultStatus
    reported_by_id: uuid.UUID
    reported_at: datetime
    created_at: datetime
    updated_at: datetime
    inspection_id: uuid.UUID | None = field(default=None)
    assigned_to_id: uuid.UUID | None = field(default=None)
    sap_notification_number: str | None = field(default=None)
    distribution_decision_note: str | None = field(default=None)
    items: list[FaultItemResponseDTO] = field(default_factory=list)
    created_by: UserProfileSummaryDTO | None = field(default=None)
