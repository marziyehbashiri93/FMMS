"""SAP measurement document write port."""

from __future__ import annotations

from abc import ABC, abstractmethod

from core.sap.dtos.measurement_document import (
    SAPMeasurementDocumentDTO,
    UpdateVehicleMeasurementRequest,
)


class ISAPMeasurementDocumentPort(ABC):
    """Business contract for writing vehicle odometer measurements to SAP."""

    @abstractmethod
    def update_vehicle_odometer(
        self,
        request: UpdateVehicleMeasurementRequest,
    ) -> SAPMeasurementDocumentDTO:
        """Write the latest vehicle odometer value to SAP."""
