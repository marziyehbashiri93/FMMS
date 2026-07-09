"""SAP Equipment DTOs.

Represents data received from SAP for fleet equipment (vehicles).
SAP is the system of record for equipment master data.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SAPEquipmentDTO:
    """Data received from SAP describing a single equipment record.

    Attributes:
        equipment_number: The SAP equipment identifier (alphanumeric).
        description: Human-readable equipment description.
        plant: The SAP plant code where the equipment is maintained.
        functional_location: Optional SAP functional location code.
        serial_number: Optional manufacturer serial number.
        category: Optional SAP equipment category code.
        object_type: Optional SAP object type (e.g. fleet vehicle type).
    """

    equipment_number: str
    description: str
    plant: str
    functional_location: str | None = None
    serial_number: str | None = None
    category: str | None = None
    object_type: str | None = None
