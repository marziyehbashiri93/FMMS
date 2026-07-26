"""Services for listing and syncing central warehouse stock from SAP."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from apps.material.application.dto.central_stock_dto import (
    CentralStockResponseDTO,
    CentralStockSyncResultDTO,
)
from apps.material.domain.interfaces.central_stock_repository import (
    ICentralStockRepository,
)
from apps.material.domain.stock_entities import CentralStock
from core.logging.structured_logger import get_structured_logger
from core.sap.dtos.central_stock import SAPCentralStockDTO
from core.sap.ports.central_stock_port import ISAPCentralStockPort

logger = get_structured_logger("material", __name__)


def _to_response_dto(stock: CentralStock) -> CentralStockResponseDTO:
    """Map domain stock row to response DTO."""
    return CentralStockResponseDTO(
        id=stock.id,
        material=stock.material,
        plant=stock.plant,
        storage_location=stock.storage_location,
        inventory_stock_type=stock.inventory_stock_type,
        material_code=stock.material_code,
        inventory_stock_type_text=stock.inventory_stock_type_text,
        quantity=stock.quantity,
        base_unit=stock.base_unit,
        stock_value=stock.stock_value,
        display_currency=stock.display_currency,
        is_active=stock.is_active,
        created_at=stock.created_at,
        updated_at=stock.updated_at,
        material_name=stock.material_name,
    )


class ListCentralStockService:
    """Return active central warehouse stock rows."""

    def __init__(self, stock_repository: ICentralStockRepository) -> None:
        self._repo = stock_repository

    def execute(
        self,
        *,
        plant: str = "",
        storage_location: str = "",
        search: str = "",
        request_id: str = "",
    ) -> list[CentralStockResponseDTO]:
        """List active stock rows with optional filters."""
        logger.info(
            "Listing central warehouse stock",
            extra={
                "domain": "material",
                "service": "ListCentralStockService",
                "operation": "execute",
                "request_id": request_id,
                "plant": plant,
                "storage_location": storage_location,
                "search": search,
            },
        )
        rows = self._repo.list_active(
            plant=plant,
            storage_location=storage_location,
            search=search,
        )
        return [_to_response_dto(row) for row in rows]


class SyncCentralStockFromSAPService:
    """Import SAP central warehouse stock rows into FMMS."""

    def __init__(
        self,
        stock_repository: ICentralStockRepository,
        central_stock_port: ISAPCentralStockPort,
    ) -> None:
        self._repo = stock_repository
        self._sap = central_stock_port

    def execute(self, request_id: str = "") -> CentralStockSyncResultDTO:
        """Synchronise SAP central warehouse stock into FMMS."""
        logger.info(
            "Syncing central warehouse stock from SAP",
            extra={
                "domain": "material",
                "service": "SyncCentralStockFromSAPService",
                "operation": "execute",
                "request_id": request_id,
            },
        )
        rows = self._sap.list_stock()
        created = 0
        updated = 0
        failed = 0
        for sap_dto in rows:
            try:
                if self._sync_one(sap_dto):
                    created += 1
                else:
                    updated += 1
            except Exception as exc:  # noqa: BLE001 - per-row isolation
                failed += 1
                logger.error(
                    "Failed to sync central stock row from SAP",
                    extra={
                        "domain": "material",
                        "service": "SyncCentralStockFromSAPService",
                        "operation": "execute",
                        "request_id": request_id,
                        "material": sap_dto.material,
                        "plant": sap_dto.plant,
                        "exception": str(exc),
                    },
                    exc_info=True,
                )
        return CentralStockSyncResultDTO(
            total_received=len(rows),
            created=created,
            updated=updated,
            failed=failed,
        )

    def _sync_one(self, sap_dto: SAPCentralStockDTO) -> bool:
        """Create or update one stock row from SAP data."""
        existing = self._repo.get_by_sap_key(
            sap_dto.material,
            sap_dto.plant,
            sap_dto.storage_location,
            sap_dto.inventory_stock_type,
        )
        now = datetime.now(tz=UTC)
        if existing is not None:
            existing.material_code = sap_dto.material_code
            # Always take SAP value (including empty). Do not keep local
            # synthetic/placeholder names when OData has no description.
            existing.material_name = sap_dto.material_name
            existing.inventory_stock_type_text = sap_dto.inventory_stock_type_text
            existing.quantity = sap_dto.quantity
            existing.base_unit = sap_dto.base_unit
            existing.stock_value = sap_dto.stock_value
            existing.display_currency = sap_dto.display_currency
            existing.is_active = True
            existing.updated_at = now
            self._repo.save(existing)
            return False

        stock = CentralStock(
            id=uuid.uuid4(),
            material=sap_dto.material,
            plant=sap_dto.plant,
            storage_location=sap_dto.storage_location,
            inventory_stock_type=sap_dto.inventory_stock_type,
            material_code=sap_dto.material_code,
            inventory_stock_type_text=sap_dto.inventory_stock_type_text,
            quantity=sap_dto.quantity,
            base_unit=sap_dto.base_unit,
            stock_value=sap_dto.stock_value,
            display_currency=sap_dto.display_currency,
            is_active=True,
            created_at=now,
            updated_at=now,
            material_name=sap_dto.material_name,
        )
        self._repo.save(stock)
        return True
