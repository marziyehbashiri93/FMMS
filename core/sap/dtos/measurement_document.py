"""SAP measurement document DTOs for vehicle odometer writes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class UpdateVehicleMeasurementRequest:
    """Request data for writing the latest vehicle odometer to SAP.

    Attributes:
        equipment_number: SAP vehicle/equipment number.
        notification_number: SAP PM notification number linked to the reading.
        odometer_km: Latest FMMS odometer value at fault-report time.
        recorded_at: UTC datetime when the fault/reading is recorded.
        notification_type: SAP notification type. Fault reports use ``EM``.
    """

    equipment_number: str
    notification_number: str
    odometer_km: int
    recorded_at: datetime
    notification_type: str = "EM"


@dataclass(frozen=True)
class SAPMeasurementDocumentDTO:
    """Result returned by SAP after writing a vehicle measurement document."""

    measurement_document_number: str
    equipment_number: str
    notification_number: str
    odometer_km: int
    created_at: datetime
