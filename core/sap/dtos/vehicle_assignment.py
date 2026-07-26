"""SAP DTOs for requesting replacement vehicle assignment."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class RequestReplacementVehicleAssignmentRequest:
    """Request data for asking SAP to assign a replacement vehicle to a driver."""

    driver_customer_number: str
    unavailable_vehicle_number: str
    fault_id: str
    requested_at: datetime
    reason: str


@dataclass(frozen=True)
class SAPVehicleAssignmentRequestDTO:
    """Result returned by SAP after accepting a replacement assignment request."""

    assignment_request_number: str
    driver_customer_number: str
    unavailable_vehicle_number: str
    created_at: datetime
