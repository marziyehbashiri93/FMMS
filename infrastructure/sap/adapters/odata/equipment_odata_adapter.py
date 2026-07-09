"""Equipment OData Adapter — implements ISAPEquipmentPort.

Reads equipment master data from SAP using the API_EQUIPMENT OData service.
All response mapping (ACL) is handled privately in this adapter.
"""

from __future__ import annotations

import logging
from typing import Any

from apps.integration.domain.exceptions import SAPIntegrationError
from core.sap.dtos.equipment import SAPEquipmentDTO
from core.sap.ports.equipment_port import ISAPEquipmentPort
from infrastructure.sap.client.base import ISAPClient, SAPClientError

logger = logging.getLogger(__name__)

_SERVICE = "API_EQUIPMENT"


class EquipmentODataAdapter(ISAPEquipmentPort):
    """Reads SAP equipment master data via the API_EQUIPMENT OData service.

    Args:
        client: An ``ISAPClient`` instance (mock or production OData client).
    """

    def __init__(self, client: ISAPClient) -> None:
        self._client = client

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
        try:
            response = self._client.odata_get(
                service=_SERVICE,
                entity=f"Equipment('{equipment_number}')",
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
        params: dict[str, Any] = {}
        if plant:
            params["$filter"] = f"Plant eq '{plant}'"

        logger.info(
            "Listing SAP equipment",
            extra={"plant": plant, "domain": "integration"},
        )
        try:
            response = self._client.odata_get(
                service=_SERVICE,
                entity="EquipmentSet",
                params=params,
            )
        except SAPClientError as exc:
            raise SAPIntegrationError(
                f"Failed to list equipment (plant={plant!r}): {exc}"
            ) from exc

        results: list[dict[str, Any]] = response.get("d", {}).get("results", [])
        return [self._map_single(item) for item in results]

    # ------------------------------------------------------------------
    # ACL — SAP response → domain DTO
    # ------------------------------------------------------------------

    @staticmethod
    def _map_single(data: dict[str, Any]) -> SAPEquipmentDTO:
        """Map a raw SAP equipment record to ``SAPEquipmentDTO``."""
        return SAPEquipmentDTO(
            equipment_number=data.get("EquipmentId", ""),
            description=data.get("EquipmentDesc", ""),
            plant=data.get("Plant", ""),
            functional_location=data.get("FunctionalLocation") or None,
            serial_number=data.get("SerialNumber") or None,
            category=data.get("EquipmentCategory") or None,
            object_type=data.get("ObjectType") or None,
        )
