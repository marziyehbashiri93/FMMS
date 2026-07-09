"""Integration tests for procurement repositories."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from apps.procurement.domain.entities import (
    POLineItem,
    POStatus,
    PRLineItem,
    PRStatus,
    PurchaseOrder,
    PurchaseRequisition,
)
from apps.procurement.domain.exceptions import PONotFoundError, PRNotFoundError
from apps.procurement.domain.interfaces.procurement_repository import (
    IPurchaseOrderRepository,
    IPurchaseRequisitionRepository,
)
from apps.procurement.domain.value_objects import (
    MaterialNumber,
    Money,
    Quantity,
    SAPDocumentNumber,
    VendorNumber,
)
from apps.procurement.infrastructure.repositories import (
    DjangoPurchaseOrderRepository,
    DjangoPurchaseRequisitionRepository,
)

pytestmark = pytest.mark.django_db


def _line_item() -> PRLineItem:
    return PRLineItem(
        id=uuid.uuid4(),
        material_number=MaterialNumber("000000012345"),
        quantity=Quantity(value=Decimal("10"), unit_of_measure="EA"),
        description="Oil filter",
        estimated_price=Money(amount=Decimal("50.00"), currency="IRR"),
    )


def _make_pr(
    repair_order_id: uuid.UUID | None = None,
    status: PRStatus = PRStatus.DRAFT,
) -> PurchaseRequisition:
    now = datetime.now(tz=UTC)
    repo = DjangoPurchaseRequisitionRepository()
    pr = PurchaseRequisition(
        id=uuid.uuid4(),
        repair_order_id=repair_order_id or uuid.uuid4(),
        status=status,
        requested_by_id=uuid.uuid4(),
        created_at=now,
        updated_at=now,
        line_items=[_line_item()],
    )
    return repo.save(pr)


def _make_po(
    pr_id: uuid.UUID | None = None,
    status: POStatus = POStatus.CREATED,
) -> PurchaseOrder:
    now = datetime.now(tz=UTC)
    repo = DjangoPurchaseOrderRepository()
    po = PurchaseOrder(
        id=uuid.uuid4(),
        pr_id=pr_id or uuid.uuid4(),
        vendor_number=VendorNumber("0000001001"),
        status=status,
        created_by_id=uuid.uuid4(),
        created_at=now,
        updated_at=now,
        line_items=[
            POLineItem(
                id=uuid.uuid4(),
                material_number=MaterialNumber("000000012345"),
                quantity=Quantity(value=Decimal("10"), unit_of_measure="EA"),
                unit_price=Money(amount=Decimal("45.00"), currency="IRR"),
            )
        ],
    )
    return repo.save(po)


class TestPRInterface:
    def test_satisfies_interface(self) -> None:
        assert isinstance(
            DjangoPurchaseRequisitionRepository(), IPurchaseRequisitionRepository
        )


class TestPurchaseRequisition:
    def test_save_and_get(self) -> None:
        repo = DjangoPurchaseRequisitionRepository()
        pr = _make_pr()
        fetched = repo.get_by_id(pr.id)
        assert fetched.id == pr.id
        assert fetched.status == PRStatus.DRAFT
        assert len(fetched.line_items) == 1
        assert fetched.line_items[0].material_number.value == "000000012345"

    def test_get_not_found(self) -> None:
        repo = DjangoPurchaseRequisitionRepository()
        with pytest.raises(PRNotFoundError):
            repo.get_by_id(uuid.uuid4())

    def test_list_by_repair_order(self) -> None:
        repo = DjangoPurchaseRequisitionRepository()
        ro_id = uuid.uuid4()
        _make_pr(repair_order_id=ro_id)
        _make_pr(repair_order_id=ro_id)
        _make_pr()
        result = repo.list_by_repair_order(ro_id)
        assert len(result) == 2

    def test_list_by_status(self) -> None:
        repo = DjangoPurchaseRequisitionRepository()
        _make_pr(status=PRStatus.DRAFT)
        _make_pr(status=PRStatus.SUBMITTED)
        draft = repo.list_by_status(PRStatus.DRAFT)
        assert all(pr.status == PRStatus.DRAFT for pr in draft)

    def test_estimated_price_preserved(self) -> None:
        repo = DjangoPurchaseRequisitionRepository()
        pr = _make_pr()
        fetched = repo.get_by_id(pr.id)
        ep = fetched.line_items[0].estimated_price
        assert ep is not None
        assert ep.amount == Decimal("50.00")
        assert ep.currency == "IRR"

    def test_sap_pr_number_persisted(self) -> None:
        repo = DjangoPurchaseRequisitionRepository()
        pr = _make_pr()
        pr.link_sap_pr(SAPDocumentNumber("4500000001"))
        repo.save(pr)
        fetched = repo.get_by_id(pr.id)
        assert fetched.sap_pr_number is not None
        assert fetched.sap_pr_number.value == "4500000001"

    def test_delete_soft_deletes(self) -> None:
        repo = DjangoPurchaseRequisitionRepository()
        pr = _make_pr()
        repo.delete(pr.id)
        with pytest.raises(PRNotFoundError):
            repo.get_by_id(pr.id)

    def test_delete_nonexistent_raises(self) -> None:
        repo = DjangoPurchaseRequisitionRepository()
        with pytest.raises(PRNotFoundError):
            repo.delete(uuid.uuid4())


class TestPOInterface:
    def test_satisfies_interface(self) -> None:
        assert isinstance(DjangoPurchaseOrderRepository(), IPurchaseOrderRepository)


class TestPurchaseOrder:
    def test_save_and_get(self) -> None:
        repo = DjangoPurchaseOrderRepository()
        po = _make_po()
        fetched = repo.get_by_id(po.id)
        assert fetched.id == po.id
        assert fetched.vendor_number.value == "0000001001"
        assert len(fetched.line_items) == 1

    def test_get_not_found(self) -> None:
        repo = DjangoPurchaseOrderRepository()
        with pytest.raises(PONotFoundError):
            repo.get_by_id(uuid.uuid4())

    def test_list_by_pr(self) -> None:
        repo = DjangoPurchaseOrderRepository()
        pr_id = uuid.uuid4()
        _make_po(pr_id=pr_id)
        _make_po(pr_id=pr_id)
        _make_po()
        result = repo.list_by_pr(pr_id)
        assert len(result) == 2

    def test_list_by_status(self) -> None:
        repo = DjangoPurchaseOrderRepository()
        _make_po(status=POStatus.CREATED)
        _make_po(status=POStatus.APPROVED)
        draft = repo.list_by_status(POStatus.CREATED)
        assert all(po.status == POStatus.CREATED for po in draft)

    def test_delete_soft_deletes(self) -> None:
        repo = DjangoPurchaseOrderRepository()
        po = _make_po()
        repo.delete(po.id)
        with pytest.raises(PONotFoundError):
            repo.get_by_id(po.id)

    def test_delete_nonexistent_raises(self) -> None:
        repo = DjangoPurchaseOrderRepository()
        with pytest.raises(PONotFoundError):
            repo.delete(uuid.uuid4())
