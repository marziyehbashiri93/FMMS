"""SAP vehicle-driver DTOs.

Represents rows received from ``ZC_VEHICLEDRIVER_CDS``. This CDS view is the
phase-1 source of truth for FMMS vehicle master data and assigned drivers.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SAPVehicleDriverDTO:
    """Vehicle and assigned driver data received from SAP.

    Attributes:
        vehicle_number: SAP ``VehicleNumber`` and unique vehicle identifier.
        license_plate: SAP ``LicensePlate``.
        commissioning_date: SAP ``CommissioningDate`` in source format.
        driver1_customer_number: SAP ``Driver1CustomerNo`` for the main driver.
        driver2_customer_number: SAP ``Driver2CustomerNo`` for the assistant driver.
        driver1_name/mobile/personnel_number/gender/nilofar_code: Main driver SAP fields.
        driver2_name/mobile/personnel_number/gender/nilofar_code: Assistant driver SAP fields.
    """

    vehicle_number: str
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
