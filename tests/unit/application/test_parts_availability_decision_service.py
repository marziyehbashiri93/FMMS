"""Unit tests for transport parts availability decision."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from apps.material.application.dto.material_request_dto import (
    PartsAvailabilityDecisionDTO,
    PartsItemDecisionDTO,
)
from apps.material.application.services.parts_availability_decision_service import (
    DecidePartsAvailabilityService,
    IssuePurchasedPartsService,
)
from apps.material.domain.entities import (
    MaterialItemDecision,
    MaterialItemStatus,
    MaterialRequest,
    MaterialRequestItem,
    MaterialRequestStatus,
)
from apps.material.domain.interfaces.central_stock_repository import (
    ICentralStockRepository,
)
from apps.material.domain.interfaces.inventory_transaction_repository import (
    IInventoryTransactionRepository,
)
from apps.material.domain.interfaces.material_request_repository import (
    IMaterialRequestRepository,
)
from apps.material.domain.stock_entities import CentralStock
from core.exceptions.base_exception import FMMSValidationError


class FakeMRRepo(IMaterialRequestRepository):
    """In-memory material request repository."""

    def __init__(self, request: MaterialRequest) -> None:
        self.request = request

    def get_by_id(self, material_request_id: uuid.UUID) -> MaterialRequest:
        assert material_request_id == self.request.id
        return self.request

    def list_all(self, *, status=None):
        return [self.request]

    def list_by_repair_order(self, repair_order_id: uuid.UUID):
        return [self.request] if self.request.repair_order_id == repair_order_id else []

    def save(self, material_request: MaterialRequest) -> MaterialRequest:
        self.request = material_request
        return material_request


class FakeStockRepo(ICentralStockRepository):
    """In-memory central stock repository."""

    def __init__(self, qty: Decimal, *, exists: bool | None = None) -> None:
        self.qty = qty
        self.exists = qty > 0 if exists is None else exists

    def get_by_id(self, stock_id: uuid.UUID) -> CentralStock:
        raise NotImplementedError

    def get_by_sap_key(self, material, plant, storage_location, inventory_stock_type):
        return None

    def get_available_quantity(self, material_number: str) -> Decimal:
        return self.qty

    def material_exists(self, material_number: str) -> bool:
        return self.exists

    def get_material_name(self, material_number: str) -> str:
        return "قطعه تست" if self.exists else ""

    def list_active(self, *, plant="", storage_location="", search=""):
        return []

    def save(self, stock: CentralStock) -> CentralStock:
        return stock


class FakeInventoryTx(IInventoryTransactionRepository):
    """Capture stock-issue calls."""

    def __init__(self) -> None:
        self.issued: list[uuid.UUID] = []

    def create_issue_for_material_request(self, material_request_id: uuid.UUID) -> None:
        self.issued.append(material_request_id)


class FakePRService:
    """Stub PR create service."""

    def execute(self, dto):
        return type("PR", (), {"id": uuid.uuid4()})()


class FakeAddLine:
    """Stub PR line service that enforces SAP material-number rules."""

    def __init__(self) -> None:
        self.calls = 0
        self.dtos: list = []

    def execute(self, dto) -> None:
        from apps.procurement.domain.value_objects import (  # noqa: PLC0415
            MaterialNumber,
            Quantity,
        )

        MaterialNumber(dto.material_number)
        Quantity(value=dto.quantity, unit_of_measure=dto.unit_of_measure)
        self.calls += 1
        self.dtos.append(dto)


def _request(*, from_catalog: bool = True) -> MaterialRequest:
    now = datetime.now(tz=UTC)
    return MaterialRequest(
        id=uuid.uuid4(),
        repair_order_id=uuid.uuid4(),
        status=MaterialRequestStatus.REQUESTED,
        created_by_id=uuid.uuid4(),
        created_at=now,
        updated_at=now,
        items=[
            MaterialRequestItem(
                id=uuid.uuid4(),
                material_number="60001764",
                quantity=Decimal("2"),
                unit_of_measure="L",
                from_catalog=from_catalog,
            )
        ],
    )


def _decision(
    request: MaterialRequest,
    decision: MaterialItemDecision,
    *,
    enforce_stock_check: bool = True,
) -> PartsAvailabilityDecisionDTO:
    return PartsAvailabilityDecisionDTO(
        material_request_id=request.id,
        items=(
            PartsItemDecisionDTO(
                item_id=request.items[0].id,
                decision=decision,
            ),
        ),
        request_id="req-1",
        decided_by=uuid.uuid4(),
        enforce_stock_check=enforce_stock_check,
    )


def test_available_path_issues_stock() -> None:
    request = _request()
    repo = FakeMRRepo(request)
    tx = FakeInventoryTx()
    service = DecidePartsAvailabilityService(
        repo,
        FakeStockRepo(Decimal("10")),
        tx,
        FakePRService(),
        FakeAddLine(),
    )

    result = service.execute(
        _decision(request, MaterialItemDecision.FROM_STOCK)
    )

    assert result.status == MaterialRequestStatus.STOCK_ISSUED
    assert result.items[0].decision == MaterialItemDecision.FROM_STOCK
    assert result.items[0].item_status == MaterialItemStatus.READY
    assert tx.issued == [request.id]


def test_available_path_rejects_insufficient_stock() -> None:
    request = _request()
    service = DecidePartsAvailabilityService(
        FakeMRRepo(request),
        FakeStockRepo(Decimal("1")),
        FakeInventoryTx(),
        FakePRService(),
        FakeAddLine(),
    )

    with pytest.raises(FMMSValidationError):
        service.execute(_decision(request, MaterialItemDecision.FROM_STOCK))


def test_from_stock_rejects_non_catalog_part() -> None:
    request = _request(from_catalog=False)
    service = DecidePartsAvailabilityService(
        FakeMRRepo(request),
        FakeStockRepo(Decimal("0"), exists=False),
        FakeInventoryTx(),
        FakePRService(),
        FakeAddLine(),
    )

    with pytest.raises(FMMSValidationError) as exc:
        service.execute(_decision(request, MaterialItemDecision.FROM_STOCK))
    assert exc.value.error_code == "MATERIAL_NOT_IN_CENTRAL_CATALOG"


def test_unavailable_path_creates_purchase_required() -> None:
    request = _request(from_catalog=False)
    add_line = FakeAddLine()
    service = DecidePartsAvailabilityService(
        FakeMRRepo(request),
        FakeStockRepo(Decimal("0"), exists=False),
        FakeInventoryTx(),
        FakePRService(),
        add_line,
    )

    result = service.execute(_decision(request, MaterialItemDecision.PURCHASE))

    assert result.status == MaterialRequestStatus.PURCHASE_REQUIRED
    assert result.items[0].item_status == MaterialItemStatus.PURCHASE_REQUIRED
    assert add_line.calls == 1


def test_purchase_path_accepts_free_text_material_name() -> None:
    """Out-of-catalog Persian names must not crash PR line creation."""
    now = datetime.now(tz=UTC)
    request = MaterialRequest(
        id=uuid.uuid4(),
        repair_order_id=uuid.uuid4(),
        status=MaterialRequestStatus.REQUESTED,
        created_by_id=uuid.uuid4(),
        created_at=now,
        updated_at=now,
        items=[
            MaterialRequestItem(
                id=uuid.uuid4(),
                material_number="دینام",
                quantity=Decimal("1"),
                unit_of_measure="-",
                from_catalog=False,
            )
        ],
    )
    add_line = FakeAddLine()
    service = DecidePartsAvailabilityService(
        FakeMRRepo(request),
        FakeStockRepo(Decimal("0"), exists=False),
        FakeInventoryTx(),
        FakePRService(),
        add_line,
    )

    result = service.execute(_decision(request, MaterialItemDecision.PURCHASE))

    assert result.status == MaterialRequestStatus.PURCHASE_REQUIRED
    assert add_line.calls == 1
    assert add_line.dtos[0].material_number == "000000000000000000"
    assert "دینام" in add_line.dtos[0].description
    assert add_line.dtos[0].unit_of_measure == "EA"


def test_mixed_path_sets_partially_issued() -> None:
    now = datetime.now(tz=UTC)
    stock_item = MaterialRequestItem(
        id=uuid.uuid4(),
        material_number="60001764",
        quantity=Decimal("1"),
        unit_of_measure="-",
        from_catalog=True,
    )
    purchase_item = MaterialRequestItem(
        id=uuid.uuid4(),
        material_number="2528",
        quantity=Decimal("1"),
        unit_of_measure="-",
        from_catalog=False,
    )
    request = MaterialRequest(
        id=uuid.uuid4(),
        repair_order_id=uuid.uuid4(),
        status=MaterialRequestStatus.REQUESTED,
        created_by_id=uuid.uuid4(),
        created_at=now,
        updated_at=now,
        items=[stock_item, purchase_item],
    )

    class MixedStockRepo(FakeStockRepo):
        def get_available_quantity(self, material_number: str) -> Decimal:
            return Decimal("10") if material_number == "60001764" else Decimal("0")

        def material_exists(self, material_number: str) -> bool:
            return material_number == "60001764"

    add_line = FakeAddLine()
    service = DecidePartsAvailabilityService(
        FakeMRRepo(request),
        MixedStockRepo(Decimal("10")),
        FakeInventoryTx(),
        FakePRService(),
        add_line,
    )

    result = service.execute(
        PartsAvailabilityDecisionDTO(
            material_request_id=request.id,
            items=(
                PartsItemDecisionDTO(
                    item_id=stock_item.id,
                    decision=MaterialItemDecision.FROM_STOCK,
                ),
                PartsItemDecisionDTO(
                    item_id=purchase_item.id,
                    decision=MaterialItemDecision.PURCHASE,
                ),
            ),
            request_id="req-mixed",
            decided_by=uuid.uuid4(),
        )
    )

    assert result.status == MaterialRequestStatus.PARTIALLY_ISSUED
    assert add_line.calls == 1


def test_issue_purchased_parts_moves_to_stock_issued() -> None:
    now = datetime.now(tz=UTC)
    request = _request()
    request.status = MaterialRequestStatus.PURCHASE_REQUIRED
    request.items[0].decision = MaterialItemDecision.PURCHASE
    request.items[0].item_status = MaterialItemStatus.PURCHASE_REQUIRED
    request.updated_at = now
    tx = FakeInventoryTx()
    service = IssuePurchasedPartsService(FakeMRRepo(request), tx)

    result = service.execute(
        material_request_id=request.id,
        request_id="req-4",
        decided_by=uuid.uuid4(),
    )

    assert result.status == MaterialRequestStatus.STOCK_ISSUED
    assert result.items[0].item_status == MaterialItemStatus.READY
    assert tx.issued == [request.id]
