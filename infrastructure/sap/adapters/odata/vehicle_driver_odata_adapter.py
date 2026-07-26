"""Vehicle-driver OData adapter for ``ZC_VEHICLEDRIVER_CDS``."""

from __future__ import annotations

from datetime import UTC, datetime
import logging
import re
from typing import Any
from urllib.parse import parse_qsl, urlparse

from apps.integration.domain.exceptions import SAPIntegrationError
from core.sap.dtos.vehicle_driver import SAPVehicleDriverDTO
from core.sap.ports.vehicle_driver_port import ISAPVehicleDriverPort
from infrastructure.sap.client.base import ISAPClient, SAPClientError

logger = logging.getLogger(__name__)

_DEFAULT_SERVICE = "ZC_VEHICLEDRIVER_CDS"
_DEFAULT_ENTITY_SET = "ZC_VehicleDriver"
_SAP_DATE_RE = re.compile(r"^/Date\((-?\d+)\)/$")


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
        """Retrieve and map all vehicle-driver rows from SAP JSON OData."""
        logger.info(
            "Listing SAP vehicle-driver rows",
            extra={"plant": plant, "domain": "integration"},
        )
        try:
            rows = self._list_all_pages()
        except SAPClientError as exc:
            raise SAPIntegrationError(
                f"Failed to list vehicle-driver data (plant={plant!r}): {exc}"
            ) from exc

        return [_map_row(row) for row in rows]

    def _list_all_pages(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        entity = self._entity_set
        params: dict[str, Any] | None = None
        seen_next_urls: set[str] = set()

        while True:
            payload = self._client.odata_get(
                service=self._service,
                entity=entity,
                params=params,
            )
            page_rows, next_url = _extract_results_page(payload)
            rows.extend(page_rows)
            if not next_url:
                return rows
            if next_url in seen_next_urls:
                raise SAPIntegrationError(
                    "SAP vehicle-driver pagination loop detected."
                )
            seen_next_urls.add(next_url)
            entity, params = _entity_and_params_from_next_url(
                next_url=next_url,
                default_entity=self._entity_set,
            )


def _map_row(data: dict[str, Any]) -> SAPVehicleDriverDTO:
    """Map one ``ZC_VEHICLEDRIVER_CDS`` row to ``SAPVehicleDriverDTO``."""
    return SAPVehicleDriverDTO(
        vehicle_number=_first_present(data, "VehicleNumber", "vehicleNumber"),
        license_plate=_first_present(data, "LicensePlate", "licensePlate") or None,
        commissioning_date=_normalize_sap_date(
            data.get("CommissioningDate") or data.get("commissioningDate")
        ),
        driver1_customer_number=_first_present(
            data, "Driver1CustomerNo", "Driver1CustomerNumber"
        )
        or None,
        driver1_name=_first_present(data, "Driver1Name") or None,
        driver1_mobile=_first_present(data, "Driver1Mobile") or None,
        driver1_personnel_number=_first_present(data, "Driver1PersonnelNo") or None,
        driver1_gender=_first_present(data, "Driver1Gender") or None,
        driver1_nilofar_code=_first_present(data, "Driver1NilofarCode") or None,
        driver2_customer_number=_first_present(
            data, "Driver2CustomerNo", "Driver2CustomerNumber"
        )
        or None,
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


def _normalize_sap_date(raw: Any) -> str | None:
    """Normalize SAP JSON date values to ``YYYYMMDD``."""
    if raw in (None, ""):
        return None
    text = str(raw).strip()
    if not text:
        return None
    if re.fullmatch(r"\d{8}", text):
        return text
    match = _SAP_DATE_RE.fullmatch(text)
    if match:
        milliseconds = int(match.group(1))
        return datetime.fromtimestamp(milliseconds / 1000, tz=UTC).strftime("%Y%m%d")
    logger.warning(
        "Invalid SAP vehicle commissioning date; marked for review",
        extra={"raw_commissioning_date": text, "review_status": "NEEDS_REVIEW"},
    )
    return None


def _extract_results_page(payload: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    """Extract one SAP JSON OData page from ``d.results``."""
    d_value = payload.get("d") if isinstance(payload, dict) else None
    if not isinstance(d_value, dict):
        raise SAPIntegrationError("Invalid SAP vehicle-driver response: missing d.")
    results = d_value.get("results")
    if not isinstance(results, list):
        raise SAPIntegrationError(
            "Invalid SAP vehicle-driver response: missing d.results."
        )
    if not all(isinstance(item, dict) for item in results):
        raise SAPIntegrationError(
            "Invalid SAP vehicle-driver response: d.results must contain objects."
        )
    next_url = d_value.get("__next") or ""
    return results, str(next_url).strip()


def _entity_and_params_from_next_url(
    *,
    next_url: str,
    default_entity: str,
) -> tuple[str, dict[str, Any]]:
    parsed = urlparse(next_url)
    params = {
        key: value
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key not in {"sap-client", "$format"}
    }
    path_parts = [part for part in parsed.path.split("/") if part]
    entity = default_entity
    if path_parts:
        last_part = path_parts[-1]
        if last_part and not last_part.lower().startswith("$skiptoken"):
            entity = last_part
    return entity, params
