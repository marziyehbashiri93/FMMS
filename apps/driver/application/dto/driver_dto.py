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
