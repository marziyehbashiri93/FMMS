"""Vehicle-driver OData adapter for ``ZC_VEHICLEDRIVER_CDS``."""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from typing import Any

from apps.integration.domain.exceptions import SAPIntegrationError
from core.sap.dtos.vehicle_driver import SAPVehicleDriverDTO
from core.sap.ports.vehicle_driver_port import ISAPVehicleDriverPort
from infrastructure.sap.client.base import ISAPClient, SAPClientError

logger = logging.getLogger(__name__)

_DEFAULT_SERVICE = "ZC_VEHICLEDRIVER_CDS"
_DEFAULT_ENTITY_SET = ""


class VehicleDriverODataAdapter(ISAPVehicleDriverPort):
    """Reads vehicle and driver assignment data from SAP OData XML."""

    def __init__(
        self,
        client: ISAPClient,
        service: str = _DEFAULT_SERVICE,
        entity_set: str = _DEFAULT_ENTITY_SET,
    ) -> None:
        self._client = client
        self._service = service
        self._entity_set = entity_set

    def get_vehicle_driver(self, vehicle_number: str) -> SAPVehicleDriverDTO:
        """Retrieve one vehicle-driver row by SAP ``VehicleNumber``."""
        for item in self.list_vehicle_drivers():
            if item.vehicle_number == vehicle_number:
                return item
        raise SAPIntegrationError(
            f"VehicleNumber {vehicle_number!r} was not found in SAP response."
        )

    def list_vehicle_drivers(
        self,
        plant: str | None = None,
    ) -> list[SAPVehicleDriverDTO]:
        """Retrieve and map all vehicle-driver rows from SAP XML."""
        logger.info(
            "Listing SAP vehicle-driver rows",
            extra={"plant": plant, "domain": "integration"},
        )
        try:
            xml_text = self._client.odata_get_xml(
                service=self._service,
                entity=self._entity_set,
            )
        except SAPClientError as exc:
            raise SAPIntegrationError(
                f"Failed to list vehicle-driver data (plant={plant!r}): {exc}"
            ) from exc

        return [_map_row(row) for row in _parse_simple_table_xml(xml_text)]


def _map_row(data: dict[str, Any]) -> SAPVehicleDriverDTO:
    """Map one ``ZC_VEHICLEDRIVER_CDS`` row to ``SAPVehicleDriverDTO``."""
    return SAPVehicleDriverDTO(
        vehicle_number=_first_present(data, "VehicleNumber", "vehicleNumber"),
        license_plate=_first_present(data, "LicensePlate") or None,
        commissioning_date=_first_present(data, "CommissioningDate") or None,
        driver1_customer_number=_first_present(data, "Driver1CustomerNo") or None,
        driver1_name=_first_present(data, "Driver1Name") or None,
        driver1_mobile=_first_present(data, "Driver1Mobile") or None,
        driver1_personnel_number=_first_present(data, "Driver1PersonnelNo") or None,
        driver1_gender=_first_present(data, "Driver1Gender") or None,
        driver1_nilofar_code=_first_present(data, "Driver1NilofarCode") or None,
        driver2_customer_number=_first_present(data, "Driver2CustomerNo") or None,
        driver2_name=_first_present(data, "Driver2Name") or None,
        driver2_mobile=_first_present(data, "Driver2Mobile") or None,
        driver2_personnel_number=_first_present(data, "Driver2PersonnelNo") or None,
        driver2_gender=_first_present(data, "Driver2Gender") or None,
        driver2_nilofar_code=_first_present(data, "Driver2NilofarCode") or None,
    )


def _first_present(data: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return str(value).strip()
    return ""


def _parse_simple_table_xml(xml_text: str) -> list[dict[str, str]]:
    """Parse SAP XML shaped as ``Root/Columns/Rows`` into dictionaries."""
    root = ET.fromstring(xml_text)  # noqa: S314
    columns = [
        str(column.attrib.get("Name", "")).strip()
        for column in root.findall("./Columns/Column")
    ]
    rows: list[dict[str, str]] = []
    for row in root.findall("./Rows/Row"):
        values = [value.text or "" for value in row.findall("./Value")]
        rows.append(
            {
                column: values[index].strip() if index < len(values) else ""
                for index, column in enumerate(columns)
                if column
            }
        )
    return rows
