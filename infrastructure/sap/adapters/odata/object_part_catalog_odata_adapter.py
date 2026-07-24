"""Object Part Catalog OData Adapter — implements ISAPObjectPartCatalogPort."""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from typing import Any

from apps.integration.domain.exceptions import SAPIntegrationError
from core.sap.dtos.object_part_catalog import SAPObjectPartDTO
from core.sap.ports.object_part_catalog_port import ISAPObjectPartCatalogPort
from infrastructure.sap.client.base import ISAPClient, SAPClientError

logger = logging.getLogger(__name__)

_SERVICE = "OBJECT_PART_CATALOG"
_XML_SERVICE = "ZI_FLEET_CAT_B_CDS"
_DEFAULT_ENTITY_SET = ""


class ObjectPartCatalogODataAdapter(ISAPObjectPartCatalogPort):
    """Reads SAP object part catalog data via OData.

    Args:
        client: An ``ISAPClient`` instance.
    """

    def __init__(
        self,
        client: ISAPClient,
        service: str = _SERVICE,
        entity_set: str = _DEFAULT_ENTITY_SET,
    ) -> None:
        self._client = client
        self._service = service
        self._entity_set = entity_set

    def get_catalog(self, catalog_type: str) -> list[SAPObjectPartDTO]:
        """Retrieve all object parts for a given catalog type.

        Args:
            catalog_type: SAP catalog type identifier.

        Returns:
            A list of ``SAPObjectPartDTO`` objects.

        Raises:
            SAPIntegrationError: On SAP error or transport failure.
        """
        logger.info(
            "Fetching SAP object part catalog",
            extra={"catalog_type": catalog_type, "domain": "integration"},
        )
        if self._service != _SERVICE:
            return self._get_catalog_from_xml(catalog_type)

        try:
            response = self._client.odata_get(
                service=self._service,
                entity="CatalogSet",
                params={"$filter": f"CatalogType eq '{catalog_type}'"},
            )
        except SAPClientError as exc:
            raise SAPIntegrationError(
                f"Failed to fetch object part catalog (type={catalog_type!r}): {exc}"
            ) from exc

        results: list[dict[str, Any]] = response.get("d", {}).get("results", [])
        return [self._map_single(item) for item in results]

    def get_part_by_code(
        self,
        code: str,
        code_group: str,
        catalog_type: str,
    ) -> SAPObjectPartDTO:
        """Retrieve a specific object part by code and group.

        Args:
            code: The object part code.
            code_group: The code group.
            catalog_type: The SAP catalog type.

        Returns:
            A populated ``SAPObjectPartDTO``.

        Raises:
            SAPIntegrationError: On SAP error or transport failure.
        """
        logger.info(
            "Fetching SAP object part",
            extra={"code": code, "code_group": code_group, "domain": "integration"},
        )
        if self._service != _SERVICE:
            for item in self.get_catalog(catalog_type):
                if item.code == code and item.code_group == code_group:
                    return item
            raise SAPIntegrationError(
                f"Object part {code!r}/{code_group!r} was not found in SAP catalog."
            )

        try:
            response = self._client.odata_get(
                service=self._service,
                entity=f"CatalogEntry(Code='{code}',CodeGroup='{code_group}')",
            )
        except SAPClientError as exc:
            raise SAPIntegrationError(
                f"Failed to fetch object part {code!r}/{code_group!r}: {exc}"
            ) from exc

        return self._map_single(response.get("d", response))

    def _get_catalog_from_xml(self, catalog_type: str) -> list[SAPObjectPartDTO]:
        """Retrieve and map catalog rows from SAP XML."""
        try:
            xml_text = self._client.odata_get_xml(
                service=self._service or _XML_SERVICE,
                entity=self._entity_set,
            )
        except SAPClientError as exc:
            raise SAPIntegrationError(
                f"Failed to fetch object part XML catalog "
                f"(type={catalog_type!r}): {exc}"
            ) from exc
        return [
            self._map_xml_row(item, catalog_type)
            for item in _parse_simple_table_xml(xml_text)
        ]

    @staticmethod
    def _map_single(data: dict[str, Any]) -> SAPObjectPartDTO:
        """Map a raw SAP catalog record to ``SAPObjectPartDTO``."""
        return SAPObjectPartDTO(
            code_group=data.get("CodeGroup", ""),
            code=data.get("Code", ""),
            group_text=data.get("GroupText", ""),
            code_text=data.get("CodeText", ""),
            defect_class=data.get("DefectClass", ""),
            defect_class_text=data.get("DefectClassText", ""),
            catalog_type=data.get("CatalogType", ""),
        )

    @staticmethod
    def _map_xml_row(data: dict[str, str], catalog_type: str) -> SAPObjectPartDTO:
        """Map one simple-table XML row to ``SAPObjectPartDTO``."""
        return SAPObjectPartDTO(
            code_group=str(data.get("CodeGroup", "")).strip(),
            code=str(data.get("Code", "")).strip(),
            group_text=str(data.get("GroupText", "")).strip(),
            code_text=str(data.get("CodeText", "")).strip(),
            defect_class=str(data.get("DefectClass", "")).strip(),
            defect_class_text=str(data.get("DefectClassText", "")).strip(),
            catalog_type=catalog_type,
        )


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
