"""SAP vehicle-driver port.

Defines the read contract for the Golestan ``ZC_VEHICLEDRIVER_CDS`` OData view.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from core.sap.dtos.vehicle_driver import SAPVehicleDriverDTO


class ISAPVehicleDriverPort(ABC):
    """Business contract for reading vehicle-driver data from SAP."""

    @abstractmethod
    def get_vehicle_driver(self, vehicle_number: str) -> SAPVehicleDriverDTO:
        """Retrieve one SAP vehicle-driver row by ``VehicleNumber``.

        Args:
            vehicle_number: SAP ``VehicleNumber``.

        Returns:
            A populated ``SAPVehicleDriverDTO``.

        Raises:
            SAPIntegrationError: If SAP returns an error or the row is not found.
        """

    @abstractmethod
    def list_vehicle_drivers(
        self,
        plant: str | None = None,
    ) -> list[SAPVehicleDriverDTO]:
        """Retrieve SAP vehicle-driver rows.

        Args:
            plant: Reserved for compatibility with scheduled sync configuration.

        Returns:
            A list of ``SAPVehicleDriverDTO`` objects. May be empty.

        Raises:
            SAPIntegrationError: If SAP returns an error response.
        """
