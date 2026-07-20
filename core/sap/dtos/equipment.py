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
        license_plate: Optional fleet license plate from SAP vehicle-driver view.
        commissioning_date: Optional SAP commissioning date in source format.
        driver1_customer_number: SAP Driver1CustomerNo for the main driver.
        driver2_customer_number: SAP Driver2CustomerNo for the assistant driver.
        driver1_name/mobile/personnel_number/gender/nilofar_code: Main driver SAP fields.
        driver2_name/mobile/personnel_number/gender/nilofar_code: Assistant driver SAP fields.
    """

    equipment_number: str
    description: str
    plant: str
    functional_location: str | None = None
    serial_number: str | None = None
    category: str | None = None
    object_type: str | None = None
    license_plate: str | None = None
    commissioning_date: str | None = None
    driver1_customer_number: str | None = None
    driver2_customer_number: str | None = None
    driver1_name: str | None = None
    driver1_mobile: str | None = None
    driver1_personnel_number: str | None = None
    driver1_gender: str | None = None
    driver1_nilofar_code: str | None = None
    driver2_name: str | None = None
    driver2_mobile: str | None = None
    driver2_personnel_number: str | None = None
    driver2_gender: str | None = None
    driver2_nilofar_code: str | None = None
