"""Unit tests for central warehouse stock sync and list services."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from apps.material.application.services.sync_central_stock_from_sap_service import (
    ListCentralStockService,
    SyncCentralStockFromSAPService,
)
from apps.material.domain.interfaces.central_stock_repository import (
    ICentralStockRepository,
)
from apps.material.domain.stock_entities import CentralStock
from core.sap.dtos.central_stock import SAPCentralStockDTO
from core.sap.ports.central_stock_port import ISAPCentralStockPort


class FakeCentralStockRepository(ICentralStockRepository):
    """In-memory central stock repository for unit tests."""

    def __init__(self) -> None:
        self.rows: dict[uuid.UUID, CentralStock] = {}

    def get_by_id(self, stock_id: uuid.UUID) -> CentralStock:
        return self.rows[stock_id]

    def get_by_sap_key(
        self,
        material: str,
        plant: str,
        storage_location: str,
        inventory_stock_type: str,
    ) -> CentralStock | None:
        for row in self.rows.values():
            if (
                row.material == material
                and row.plant == plant
                and row.storage_location == storage_location
                and row.inventory_stock_type == inventory_stock_type
            ):
                return row
        return None

    def get_available_quantity(self, material_number: str) -> Decimal:
        stripped = material_number.strip().lstrip("0") or "0"
        total = Decimal("0")
        for row in self.rows.values():
            if not row.is_active:
                continue
            if row.material_code == stripped or row.material.endswith(stripped):
                total += row.quantity
        return total

    def material_exists(self, material_number: str) -> bool:
        stripped = material_number.strip().lstrip("0") or "0"
        return any(
            row.is_active
            and (row.material_code == stripped or row.material.endswith(stripped))
            for row in self.rows.values()
        )

    def get_material_name(self, material_number: str) -> str:
        stripped = material_number.strip().lstrip("0") or "0"
        for row in self.rows.values():
            if row.is_active and (
                row.material_code == stripped or row.material.endswith(stripped)
            ):
                return row.material_name
        return ""

    def list_active(
        self,
        *,
        plant: str = "",
        storage_location: str = "",
        search: str = "",
    ) -> list[CentralStock]:
        rows = [row for row in self.rows.values() if row.is_active]
        if plant:
            rows = [row for row in rows if row.plant == plant]
        if storage_location:
            rows = [row for row in rows if row.storage_location == storage_location]
        if search:
            needle = search.lower()
            rows = [
                row
                for row in rows
                if needle in row.material.lower()
                or needle in row.material_code.lower()
            ]
        return rows

    def save(self, stock: CentralStock) -> CentralStock:
        self.rows[stock.id] = stock
        return stock


class FakeSAPCentralStockPort(ISAPCentralStockPort):
    """Stub SAP central stock port."""

    def __init__(self, rows: list[SAPCentralStockDTO] | None = None) -> None:
        self.rows = rows or [
            SAPCentralStockDTO(
                material="000000000060001764",
                plant="1000",
                storage_location="KH08",
                inventory_stock_type="01",
                material_code="60001764",
                material_name="روغن موتور",
                inventory_stock_type_text="Unrestricted-Use Stock",
                quantity=Decimal("149.500"),
                base_unit="L",
                stock_value=Decimal("3225552.20"),
                display_currency="IRR",
            )
        ]

    def list_stock(self) -> list[SAPCentralStockDTO]:
        return list(self.rows)


class TestSyncCentralStockFromSAPService:
    """Cover create/update paths for central stock sync."""

    def test_creates_central_stock_rows_from_sap(self) -> None:
        repo = FakeCentralStockRepository()
        sap = FakeSAPCentralStockPort()

        result = SyncCentralStockFromSAPService(repo, sap).execute()

        assert result.total_received == 1
        assert result.created == 1
        assert result.updated == 0
        assert result.failed == 0
        assert len(repo.rows) == 1

    def test_updates_existing_central_stock_row(self) -> None:
        now = datetime.now(tz=UTC)
        repo = FakeCentralStockRepository()
        existing_id = uuid.uuid4()
        repo.save(
            CentralStock(
                id=existing_id,
                material="000000000060001764",
                plant="1000",
                storage_location="KH08",
                inventory_stock_type="01",
                material_code="60001764",
                inventory_stock_type_text="Unrestricted-Use Stock",
                quantity=Decimal("10"),
                base_unit="L",
                stock_value=Decimal("1"),
                display_currency="IRR",
                is_active=True,
                created_at=now,
                updated_at=now,
            )
        )
        sap = FakeSAPCentralStockPort()

        result = SyncCentralStockFromSAPService(repo, sap).execute()

        assert result.created == 0
        assert result.updated == 1
        assert repo.rows[existing_id].quantity == Decimal("149.500")

    def test_clears_local_name_when_sap_has_no_description(self) -> None:
        now = datetime.now(tz=UTC)
        repo = FakeCentralStockRepository()
        existing_id = uuid.uuid4()
        repo.save(
            CentralStock(
                id=existing_id,
                material="000000000060001764",
                plant="1000",
                storage_location="KH08",
                inventory_stock_type="01",
                material_code="60001764",
                inventory_stock_type_text="Unrestricted-Use Stock",
                quantity=Decimal("10"),
                base_unit="L",
                stock_value=Decimal("1"),
                display_currency="IRR",
                is_active=True,
                created_at=now,
                updated_at=now,
                material_name="روغن / مایع — 60001764",
            )
        )
        sap = FakeSAPCentralStockPort(
            [
                SAPCentralStockDTO(
                    material="000000000060001764",
                    plant="1000",
                    storage_location="KH08",
                    inventory_stock_type="01",
                    material_code="60001764",
                    material_name="",
                    inventory_stock_type_text="Unrestricted-Use Stock",
                    quantity=Decimal("149.500"),
                    base_unit="L",
                    stock_value=Decimal("3225552.20"),
                    display_currency="IRR",
                )
            ]
        )

        SyncCentralStockFromSAPService(repo, sap).execute()

        assert repo.rows[existing_id].material_name == ""


class TestListCentralStockService:
    """Cover list filters for central stock."""

    def test_lists_active_rows(self) -> None:
        now = datetime.now(tz=UTC)
        repo = FakeCentralStockRepository()
        repo.save(
            CentralStock(
                id=uuid.uuid4(),
                material="000000000060001764",
                plant="1000",
                storage_location="KH08",
                inventory_stock_type="01",
                material_code="60001764",
                inventory_stock_type_text="Unrestricted-Use Stock",
                quantity=Decimal("149.500"),
                base_unit="L",
                stock_value=Decimal("3225552.20"),
                display_currency="IRR",
                is_active=True,
                created_at=now,
                updated_at=now,
            )
        )

        result = ListCentralStockService(repo).execute(storage_location="KH08")

        assert len(result) == 1
        assert result[0].material_code == "60001764"
