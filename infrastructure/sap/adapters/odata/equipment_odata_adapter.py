"""Equipment OData Adapter — implements ISAPEquipmentPort.

Reads equipment master data from SAP using the configured Equipment OData service.
All response mapping (ACL) is handled privately in this adapter.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from typing import Any

from apps.integration.domain.exceptions import SAPIntegrationError
from core.sap.dtos.equipment import SAPEquipmentDTO
from core.sap.ports.equipment_port import ISAPEquipmentPort
from infrastructure.sap.client.base import ISAPClient, SAPClientError

logger = logging.getLogger(__name__)

_DEFAULT_SERVICE = "API_EQUIPMENT"
_DEFAULT_ENTITY_SET = "Equipment"
_DEFAULT_PAGE_SIZE = 200


class EquipmentODataAdapter(ISAPEquipmentPort):
    """Reads SAP equipment master data via the API_EQUIPMENT OData service.

    Args:
        client: An ``ISAPClient`` instance (mock or production OData client).
    """

    def __init__(
        self,
        client: ISAPClient,
        service: str = _DEFAULT_SERVICE,
        entity_set: str = _DEFAULT_ENTITY_SET,
        page_size: int = _DEFAULT_PAGE_SIZE,
        extra_filter: str = "",
        response_format: str = "json",
    ) -> None:
        self._client = client
        self._service = service
        self._entity_set = entity_set
        self._page_size = page_size
        self._extra_filter = extra_filter
        self._response_format = response_format.lower()

    # ------------------------------------------------------------------
    # Port implementation
    # ------------------------------------------------------------------

    def get_equipment(self, equipment_number: str) -> SAPEquipmentDTO:
        """Retrieve a single equipment record from SAP.

        Args:
            equipment_number: The SAP equipment identifier.

        Returns:
            A populated ``SAPEquipmentDTO``.

        Raises:
            SAPIntegrationError: On SAP error or transport failure.
        """
        logger.info(
            "Fetching SAP equipment",
            extra={"equipment_number": equipment_number, "domain": "integration"},
        )
        if self._response_format == "xml":
            for item in self._list_equipment_from_xml():
                if item.equipment_number == equipment_number:
                    return item
            raise SAPIntegrationError(
                f"Equipment {equipment_number!r} was not found in SAP XML response."
            )

        try:
            response = self._client.odata_get(
                service=self._service,
                entity=f"{self._entity_set}('{equipment_number}')",
            )
        except SAPClientError as exc:
            raise SAPIntegrationError(
                f"Failed to fetch equipment {equipment_number!r}: {exc}"
            ) from exc

        return self._map_single(response.get("d", response))

    def list_equipment(self, plant: str | None = None) -> list[SAPEquipmentDTO]:
        """Retrieve all equipment records, optionally filtered by plant.

        Args:
            plant: Optional SAP plant code.

        Returns:
            A list of ``SAPEquipmentDTO`` objects.

        Raises:
            SAPIntegrationError: On SAP error or transport failure.
        """
        if self._response_format == "xml":
            return self._list_equipment_from_xml(plant=plant)

        filter_parts = []
        if plant:
            filter_parts.append(f"Plant eq '{plant}'")
        if self._extra_filter:
            filter_parts.append(f"({self._extra_filter})")

        logger.info(
            "Listing SAP equipment",
            extra={"plant": plant, "domain": "integration"},
        )

        results: list[dict[str, Any]] = []
        skip = 0
        try:
            while True:
                params: dict[str, Any] = {
                    "$top": self._page_size,
                    "$skip": skip,
                }
                if filter_parts:
                    params["$filter"] = " and ".join(filter_parts)
                response = self._client.odata_get(
                    service=self._service,
                    entity=self._entity_set,
                    params=params,
                )
                payload = response.get("d", response)
                page = payload.get("results", [])
                results.extend(page)
                has_next = bool(payload.get("__next"))
                if not has_next:
                    break
                skip += self._page_size
        except SAPClientError as exc:
            raise SAPIntegrationError(
                f"Failed to list equipment (plant={plant!r}): {exc}"
            ) from exc

        return [self._map_single(item) for item in results]

    def _list_equipment_from_xml(
        self, plant: str | None = None
    ) -> list[SAPEquipmentDTO]:
        """Retrieve and map fleet vehicle-driver XML."""
        try:
            xml_text = self._client.odata_get_xml(
                service=self._service,
                entity=self._entity_set,
            )
        except SAPClientError as exc:
            raise SAPIntegrationError(
                f"Failed to list equipment XML (plant={plant!r}): {exc}"
            ) from exc

        rows = _parse_simple_table_xml(xml_text)
        mapped = [self._map_single(row) for row in rows]
        if not plant:
            return mapped
        return [item for item in mapped if item.plant == plant]

    # ------------------------------------------------------------------
    # ACL — SAP response → domain DTO
    # ------------------------------------------------------------------

    @staticmethod
    def _map_single(data: dict[str, Any]) -> SAPEquipmentDTO:
        """Map a raw SAP equipment record to ``SAPEquipmentDTO``."""
        return SAPEquipmentDTO(
            equipment_number=_first_present(
                data,
                "VehicleNumber",
                "vehicleNumber",
                "Equipment",
                "EquipmentId",
                "EquipmentNumber",
            ),
            description=_first_present(
                data,
                "EquipmentName",
                "EquipmentDesc",
                "EquipmentDescription",
                "Description",
            ),
            plant=_first_present(data, "Plant", "MaintenancePlant") or "",
            functional_location=_first_present(data, "FunctionalLocation") or None,
            serial_number=_first_present(
                data,
                "SerialNumber",
                "ManufacturerSerialNumber",
                "ManufactSerialNumber",
            )
            or None,
            category=_first_present(data, "EquipmentCategory") or None,
            object_type=_first_present(data, "ObjectType", "TechnicalObjectType")
            or None,
            license_plate=_first_present(data, "LicensePlate") or None,
            commissioning_date=_first_present(data, "CommissioningDate") or None,
            driver1_customer_number=_first_present(
                data,
                "Driver1CustomerNo",
                "CustomerNumber1",
                "Customer1Number",
                "CustomerNumber",
            )
            or None,
            driver2_customer_number=_first_present(
                data,
                "Driver2CustomerNo",
                "CustomerNumber2",
                "Customer2Number",
            )
            or None,
            driver1_name=_first_present(data, "Driver1Name") or None,
            driver1_mobile=_first_present(data, "Driver1Mobile") or None,
            driver1_personnel_number=_first_present(data, "Driver1PersonnelNo") or None,
            driver1_gender=_first_present(data, "Driver1Gender") or None,
            driver1_nilofar_code=_first_present(data, "Driver1NilofarCode") or None,
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
            return str(value)
    return ""


def _parse_simple_table_xml(xml_text: str) -> list[dict[str, str]]:
    """Parse SAP XML shaped as Root/Columns/Rows into dictionaries."""
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
