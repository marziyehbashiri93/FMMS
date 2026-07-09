"""Application-layer DTOs for the Preventive Maintenance domain.

Rules:
- No ORM models, no Django objects, no database objects.
- All fields are primitive Python types or domain enums.
- Mapping DTO <-> Domain Entity happens explicitly inside each service.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from apps.preventive_maintenance.domain.entities import PMPlanStatus, PMWorkOrderStatus
from apps.preventive_maintenance.domain.value_objects import IntervalUnit, TriggerType


@dataclass(frozen=True)
class CreatePMPlanDTO:
    """Input DTO for creating a new preventive maintenance plan.

    Attributes:
        vehicle_id: UUID of the target vehicle.
        name: Human-readable plan name.
        description: Detailed description of maintenance activities.
        interval_value: Positive interval magnitude.
        interval_unit: Unit for the interval (DAYS, KM, HOURS).
        trigger_type: Condition type that triggers a work order.
        trigger_threshold: Positive threshold value.
        request_id: Correlation ID for tracing.
        created_by: UUID of the authenticated user creating the plan.
    """

    vehicle_id: uuid.UUID
    name: str
    description: str
    interval_value: int
    interval_unit: IntervalUnit
    trigger_type: TriggerType
    trigger_threshold: int
    request_id: str
    created_by: uuid.UUID


@dataclass(frozen=True)
class TriggerPMWorkOrderDTO:
    """Input DTO for triggering a PM work order from an active plan.

    Cross-domain / workflow guards enforced by the service:
    - Plan must be ACTIVE.
    - No non-terminal work order may already exist for the plan.
    - Optional SAP PM notification via ``ISAPPMNotificationPort`` only.

    Attributes:
        plan_id: UUID of the parent PM plan.
        scheduled_date: Due date for the generated work order.
        request_id: Correlation ID for tracing.
        triggered_by: UUID of the user/system initiating the trigger.
        create_sap_notification: When True, create a SAP PM notification
            via the injected port (requires vehicle SAP equipment number).
        defect_code: SAP defect code used when creating a notification.
        priority: SAP priority code (default Medium = "3").
        notes: Optional notes stored on the work order.
    """

    plan_id: uuid.UUID
    scheduled_date: datetime
    request_id: str
    triggered_by: uuid.UUID
    create_sap_notification: bool = field(default=False)
    defect_code: str = field(default="PM-TRIG")
    priority: str = field(default="3")
    notes: str | None = field(default=None)


@dataclass(frozen=True)
class CompletePMWorkOrderDTO:
    """Input DTO for completing a PM work order.

    Attributes:
        work_order_id: UUID of the work order to complete.
        completed_at: UTC timestamp of physical completion.
        request_id: Correlation ID for tracing.
        completed_by: UUID of the user completing the work order.
        notes: Optional completion notes.
    """

    work_order_id: uuid.UUID
    completed_at: datetime
    request_id: str
    completed_by: uuid.UUID
    notes: str | None = field(default=None)


@dataclass(frozen=True)
class PMPlanResponseDTO:
    """Output DTO for PM plan read and write operations."""

    id: uuid.UUID
    vehicle_id: uuid.UUID
    name: str
    description: str
    interval_value: int
    interval_unit: IntervalUnit
    trigger_type: TriggerType
    trigger_threshold: int
    status: PMPlanStatus
    created_by_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    last_triggered_at: datetime | None = field(default=None)
    next_due_at: datetime | None = field(default=None)


@dataclass(frozen=True)
class PMWorkOrderResponseDTO:
    """Output DTO for PM work order read and write operations."""

    id: uuid.UUID
    plan_id: uuid.UUID
    vehicle_id: uuid.UUID
    status: PMWorkOrderStatus
    scheduled_date: datetime
    created_at: datetime
    updated_at: datetime
    triggered_at: datetime | None = field(default=None)
    completed_at: datetime | None = field(default=None)
    notes: str | None = field(default=None)
    sap_order_number: str | None = field(default=None)
    sap_notification_number: str | None = field(default=None)
