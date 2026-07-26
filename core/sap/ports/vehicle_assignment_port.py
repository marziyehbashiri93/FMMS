"""SAP port for requesting replacement vehicle assignment."""

from __future__ import annotations

from abc import ABC, abstractmethod

from core.sap.dtos.vehicle_assignment import (
    RequestReplacementVehicleAssignmentRequest,
    SAPVehicleAssignmentRequestDTO,
)


class ISAPVehicleAssignmentPort(ABC):
    """Business contract for requesting replacement vehicle assignment from SAP."""

    @abstractmethod
    def request_replacement_assignment(
        self,
        request: RequestReplacementVehicleAssignmentRequest,
    ) -> SAPVehicleAssignmentRequestDTO:
        """Ask SAP to assign a replacement vehicle to the affected driver."""
