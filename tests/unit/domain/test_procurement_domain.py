"""Unit tests for the Procurement domain layer."""

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
from apps.procurement.domain.exceptions import (
    PONotFoundError,
    PRNotFoundError,
    ProcurementInvalidStateTransitionError,
)
from apps.procurement.domain.value_objects import (
    MaterialNumber,
    Money,
    Quantity,
    SAPDocumentNumber,
    VendorNumber,
)


def _make_pr(**kwargs: object) -> PurchaseRequisition:
    defaults: dict[str, object] = {
        "id": uuid.uuid4(),
        "repair_order_id": uuid.uuid4(),
        "status": PRStatus.DRAFT,
        "requested_by_id": uuid.uuid4(),
        "created_at": datetime.now(tz=UTC),
        "updated_at": datetime.now(tz=UTC),
    }
    defaults.update(kwargs)
    return PurchaseRequisition(**defaults)  # type: ignore[arg-type]


def _make_po(**kwargs: object) -> PurchaseOrder:
    defaults: dict[str, object] = {
        "id": uuid.uuid4(),
        "pr_id": uuid.uuid4(),
        "vendor_number": VendorNumber("V001"),
        "status": POStatus.CREATED,
        "created_by_id": uuid.uuid4(),
        "created_at": datetime.now(tz=UTC),
        "updated_at": datetime.now(tz=UTC),
    }
    defaults.update(kwargs)
    return PurchaseOrder(**defaults)  # type: ignore[arg-type]


def _make_pr_line() -> PRLineItem:
    return PRLineItem(
        id=uuid.uuid4(),
        material_number=MaterialNumber("000000123456"),
        quantity=Quantity(value=Decimal("10"), unit_of_measure="EA"),
        description="Brake pad set",
    )


def _make_po_line() -> POLineItem:
    return POLineItem(
        id=uuid.uuid4(),
        material_number=MaterialNumber("000000123456"),
        quantity=Quantity(value=Decimal("10"), unit_of_measure="EA"),
        unit_price=Money(amount=Decimal("150.00"), currency="IRR"),
    )


class TestValueObjects:
    def test_material_number_valid(self) -> None:
        mn = MaterialNumber("000000123456")
        assert mn.value == "000000123456"

    def test_material_number_non_digit_raises(self) -> None:
        with pytest.raises(ValueError, match="only digits"):
            MaterialNumber("MAT-001")

    def test_quantity_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            Quantity(value=Decimal("0"), unit_of_measure="EA")

    def test_money_negative_raises(self) -> None:
        with pytest.raises(ValueError, match="non-negative"):
            Money(amount=Decimal("-1"), currency="IRR")

    def test_money_invalid_currency(self) -> None:
        with pytest.raises(ValueError, match="ISO 4217"):
            Money(amount=Decimal("100"), currency="IR1")

    def test_money_valid(self) -> None:
        m = Money(amount=Decimal("1500.00"), currency="IRR")
        assert m.currency == "IRR"
        assert str(m) == "1500.00 IRR"

    def test_vendor_number_too_long(self) -> None:
        with pytest.raises(ValueError, match="10"):
            VendorNumber("V" * 11)

    def test_sap_doc_number(self) -> None:
        doc = SAPDocumentNumber("4500000001")
        assert doc.value == "4500000001"


class TestPurchaseRequisitionLifecycle:
    def test_initial_draft(self) -> None:
        pr = _make_pr()
        assert pr.status == PRStatus.DRAFT

    def test_add_line_item(self) -> None:
        pr = _make_pr()
        pr.add_line_item(_make_pr_line())
        assert len(pr.line_items) == 1

    def test_submit(self) -> None:
        pr = _make_pr()
        pr.submit()
        assert pr.status == PRStatus.SUBMITTED

    def test_approve(self) -> None:
        pr = _make_pr(status=PRStatus.SUBMITTED)
        approver = uuid.uuid4()
        pr.approve(approved_by_id=approver)
        assert pr.status == PRStatus.APPROVED
        assert pr.approved_by_id == approver

    def test_reject(self) -> None:
        pr = _make_pr(status=PRStatus.SUBMITTED)
        pr.reject()
        assert pr.status == PRStatus.REJECTED

    def test_cannot_add_item_after_submit(self) -> None:
        pr = _make_pr(status=PRStatus.SUBMITTED)
        with pytest.raises(ProcurementInvalidStateTransitionError):
            pr.add_line_item(_make_pr_line())

    def test_invalid_transition(self) -> None:
        pr = _make_pr(status=PRStatus.APPROVED)
        with pytest.raises(ProcurementInvalidStateTransitionError):
            pr.submit()

    def test_link_sap_pr(self) -> None:
        pr = _make_pr()
        pr.link_sap_pr(SAPDocumentNumber("1000000001"))
        assert pr.sap_pr_number is not None
        assert pr.sap_pr_number.value == "1000000001"


class TestPurchaseOrderLifecycle:
    def test_initial_created(self) -> None:
        po = _make_po()
        assert po.status == POStatus.CREATED

    def test_approve(self) -> None:
        po = _make_po()
        approver = uuid.uuid4()
        po.approve(approved_by_id=approver)
        assert po.status == POStatus.APPROVED

    def test_partial_receipt(self) -> None:
        po = _make_po(status=POStatus.APPROVED)
        po.record_partial_receipt()
        assert po.status == POStatus.PARTIALLY_RECEIVED

    def test_full_receipt(self) -> None:
        po = _make_po(status=POStatus.APPROVED)
        po.record_full_receipt()
        assert po.status == POStatus.RECEIVED

    def test_cancel(self) -> None:
        po = _make_po()
        po.cancel()
        assert po.status == POStatus.CANCELLED

    def test_total_value(self) -> None:
        po = _make_po()
        po.line_items.append(_make_po_line())
        assert po.total_value == Decimal("1500.00")

    def test_po_line_fully_received(self) -> None:
        line = _make_po_line()
        line.received_quantity = Decimal("10")
        assert line.is_fully_received is True


class TestProcurementExceptions:
    def test_pr_not_found(self) -> None:
        err = PRNotFoundError("pr-id")
        assert "pr-id" in str(err)

    def test_po_not_found(self) -> None:
        err = PONotFoundError("po-id")
        assert "po-id" in str(err)
