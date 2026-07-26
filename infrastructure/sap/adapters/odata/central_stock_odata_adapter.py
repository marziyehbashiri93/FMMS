"""Central warehouse stock OData adapter — implements ISAPCentralStockPort.

Reads stock from SAP CDS ``ZI_STOCK_KH08_CDS`` (storage location KH08).
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from decimal import Decimal, InvalidOperation
from typing import Any

from apps.integration.domain.exceptions import SAPIntegrationError
from core.sap.dtos.central_stock import SAPCentralStockDTO
from core.sap.ports.central_stock_port import ISAPCentralStockPort
from infrastructure.sap.client.base import ISAPClient, SAPClientError

logger = logging.getLogger(__name__)

_SERVICE = "ZI_STOCK_KH08_CDS"
_DEFAULT_ENTITY_SET = ""


class CentralStockODataAdapter(ISAPCentralStockPort):
    """Reads central spare-parts warehouse stock via OData XML.

    Args:
        client: An ``ISAPClient`` instance.
        service: OData service name (default ``ZI_STOCK_KH08_CDS``).
        entity_set: Optional entity set path; empty for root feed.
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

    def list_stock(self) -> list[SAPCentralStockDTO]:
        """Retrieve all central warehouse stock rows.

        Returns:
            A list of ``SAPCentralStockDTO`` objects.

        Raises:
            SAPIntegrationError: On SAP error or transport failure.
        """
        logger.info(
            "Listing SAP central warehouse stock",
            extra={"service": self._service, "domain": "integration"},
        )
        try:
            xml_text = self._client.odata_get_xml(
                service=self._service,
                entity=self._entity_set,
            )
        except SAPClientError as exc:
            raise SAPIntegrationError(
                f"Failed to list central warehouse stock: {exc}"
            ) from exc

        return [self._map_single(item) for item in _parse_simple_table_xml(xml_text)]

    @staticmethod
    def _map_single(data: dict[str, Any]) -> SAPCentralStockDTO:
        """Map a raw SAP stock record to ``SAPCentralStockDTO``."""
        return SAPCentralStockDTO(
            material=str(data.get("Material", "")).strip(),
            plant=str(data.get("Plant", "")).strip(),
            storage_location=str(data.get("StorageLocation", "")).strip(),
            inventory_stock_type=str(data.get("InventoryStockType", "")).strip(),
            material_code=str(data.get("MaterialCode", "")).strip(),
            material_name=_material_name_from_row(data),
            inventory_stock_type_text=str(
                data.get("InventoryStockTypeText", "")
            ).strip(),
            quantity=_to_decimal(data.get("MatlWrhsStkQtyInMatlBaseUnit")),
            base_unit=str(data.get("MaterialBaseUnit", "")).strip(),
            stock_value=_to_decimal(data.get("StockValueInDisplayCurrency")),
            display_currency=str(data.get("DisplayCurrency", "")).strip(),
        )


def _material_name_from_row(data: dict[str, Any]) -> str:
    """Extract material description from known SAP column aliases."""
    for key in (
        "MaterialName",
        "MaterialDescription",
        "ProductDescription",
        "MaterialText",
        "ProductDesc",
        "MaterialDesc",
    ):
        value = str(data.get(key, "")).strip()
        if value:
            return value
    return ""


def _to_decimal(raw: Any) -> Decimal:
    """Parse SAP numeric string to Decimal; invalid values become zero."""
    text = str(raw or "0").strip().replace(",", "")
    if not text:
        return Decimal("0")
    try:
        return Decimal(text)
    except InvalidOperation:
        return Decimal("0")


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
