"""Read port for resolving current vehicle assignments for drivers."""

from __future__ import annotations

from abc import ABC, abstractmethod

from apps.driver.application.dto.driver_dto import DriverAssignedVehicleDTO


class IDriverVehicleAssignmentReader(ABC):
    """Resolve current vehicles assigned to driver customer numbers."""

    @abstractmethod
    def vehicles_by_driver_customer_numbers(
        self,
        customer_numbers: set[str],
    ) -> tuple[
        dict[str, DriverAssignedVehicleDTO],
        dict[str, DriverAssignedVehicleDTO],
    ]:
        """Return vehicles keyed by driver customer number for both roles."""
