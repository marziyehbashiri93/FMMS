"""Unit tests for Procurement application services.

Focus: SubmitPRToSAPService idempotency, SAPTransaction lifecycle, and
port-only SAP dependency (no infrastructure imports).
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from apps.integration.domain.entities import (
    SAPObjectType,
    SAPTransaction,
    SAPTransactionStatus,
)
from apps.integration.domain.interfaces.sap_transaction_repository import (
    ISAPTransactionRepository,
)
from apps.procurement.application.dto.procurement_dto import (
    AddPRLineItemDTO,
    CreatePurchaseRequisitionDTO,
    PurchaseRequisitionResponseDTO,
    ReceivePOFromSAPDTO,
    ReceivePOLineItemDTO,
    SubmitPRToSAPDTO,
)
from apps.procurement.application.services.add_pr_line_item_service import (
    AddPRLineItemService,
)
from apps.procurement.application.services.create_purchase_requisition_service import (
    CreatePurchaseRequisitionService,
)
from apps.procurement.application.services.get_procurement_service import (
    GetPurchaseRequisitionService,
    ListPurchaseRequisitionsService,
)
from apps.procurement.application.services.receive_po_from_sap_service import (
    ReceivePOFromSAPService,
)
from apps.procurement.application.services.submit_pr_to_sap_service import (
    SubmitPRToSAPService,
)
from apps.procurement.domain.entities import (
    PRLineItem,
    PRStatus,
    PurchaseOrder,
    PurchaseRequisition,
)
from apps.procurement.domain.interfaces.procurement_repository import (
    IPurchaseOrderRepository,
    IPurchaseRequisitionRepository,
)
from apps.procurement.domain.value_objects import (
    MaterialNumber,
    Quantity,
    SAPDocumentNumber,
)
from apps.repair.domain.entities import RepairOrder, RepairOrderStatus
from apps.repair.domain.interfaces.repair_repository import IRepairOrderRepository
from core.exceptions.base_exception import (
    FMMSConflictError,
    FMMSIntegrationError,
    FMMSNotFoundError,
    FMMSValidationError,
)
from core.sap.dtos.purchase_requisition import (
    CreatePRRequest,
    SAPPRLineItemDTO,
    SAPPurchaseRequisitionDTO,
)
from core.sap.ports.purchase_requisition_port import ISAPPurchaseRequisitionPort

# ---------------------------------------------------------------------------
# Helpers / fakes
# ---------------------------------------------------------------------------


def _make_repair_order() -> RepairOrder:
    now = datetime.now(tz=UTC)
    return RepairOrder(
        id=uuid.uuid4(),
        vehicle_id=uuid.uuid4(),
        fault_id=uuid.uuid4(),
        status=RepairOrderStatus.IN_PROGRESS,
        created_by_id=uuid.uuid4(),
        created_at=now,
        updated_at=now,
    )


def _make_pr(
    *,
    repair_order_id: uuid.UUID | None = None,
    with_line: bool = True,
    status: PRStatus = PRStatus.DRAFT,
) -> PurchaseRequisition:
    now = datetime.now(tz=UTC)
    pr = PurchaseRequisition(
        id=uuid.uuid4(),
        repair_order_id=repair_order_id or uuid.uuid4(),
        status=PRStatus.DRAFT,
        requested_by_id=uuid.uuid4(),
        created_at=now,
        updated_at=now,
    )
    if with_line:
        pr.add_line_item(
            PRLineItem(
                id=uuid.uuid4(),
                material_number=MaterialNumber("10000001"),
                quantity=Quantity(value=Decimal("2"), unit_of_measure="EA"),
                description="Brake pads",
            )
        )
    if status == PRStatus.SUBMITTED:
        pr.submit()
    return pr


class FakePRRepository(IPurchaseRequisitionRepository):
    def __init__(self, initial: list[PurchaseRequisition] | None = None) -> None:
        self._store: dict[uuid.UUID, PurchaseRequisition] = {
            pr.id: pr for pr in (initial or [])
        }

    def get_by_id(self, pr_id: uuid.UUID) -> PurchaseRequisition | None:
        return self._store.get(pr_id)

    def list_by_repair_order(
        self, repair_order_id: uuid.UUID
    ) -> list[PurchaseRequisition]:
        return [
            pr for pr in self._store.values() if pr.repair_order_id == repair_order_id
        ]

    def list_by_status(self, status: PRStatus) -> list[PurchaseRequisition]:
        return [pr for pr in self._store.values() if pr.status == status]

    def save(self, pr: PurchaseRequisition) -> PurchaseRequisition:
        self._store[pr.id] = pr
        return pr

    def delete(self, pr_id: uuid.UUID) -> None:
        self._store.pop(pr_id, None)


class FakePORepository(IPurchaseOrderRepository):
    def __init__(self, initial: list[PurchaseOrder] | None = None) -> None:
        self._store: dict[uuid.UUID, PurchaseOrder] = {
            po.id: po for po in (initial or [])
        }

    def get_by_id(self, po_id: uuid.UUID) -> PurchaseOrder | None:
        return self._store.get(po_id)

    def list_by_pr(self, pr_id: uuid.UUID) -> list[PurchaseOrder]:
        return [po for po in self._store.values() if po.pr_id == pr_id]

    def list_by_status(self, status) -> list[PurchaseOrder]:
        return [po for po in self._store.values() if po.status == status]

    def save(self, po: PurchaseOrder) -> PurchaseOrder:
        self._store[po.id] = po
        return po

    def delete(self, po_id: uuid.UUID) -> None:
        self._store.pop(po_id, None)


class FakeRepairRepository(IRepairOrderRepository):
    def __init__(self, initial: list[RepairOrder] | None = None) -> None:
        self._store: dict[uuid.UUID, RepairOrder] = {o.id: o for o in (initial or [])}

    def get_by_id(self, order_id: uuid.UUID) -> RepairOrder | None:
        return self._store.get(order_id)

    def list_by_vehicle(self, vehicle_id: uuid.UUID, status=None) -> list[RepairOrder]:
        return []

    def list_by_fault(self, fault_id: uuid.UUID) -> list[RepairOrder]:
        return []

    def list_active_by_vehicle(self, vehicle_id: uuid.UUID) -> list[RepairOrder]:
        return []

    def save(self, order: RepairOrder) -> RepairOrder:
        self._store[order.id] = order
        return order

    def delete(self, order_id: uuid.UUID) -> None:
        self._store.pop(order_id, None)


class FakeSAPTransactionRepository(ISAPTransactionRepository):
    def __init__(self, initial: list[SAPTransaction] | None = None) -> None:
        self._store: dict[uuid.UUID, SAPTransaction] = {
            tx.id: tx for tx in (initial or [])
        }

    def get_by_id(self, transaction_id: uuid.UUID) -> SAPTransaction | None:
        return self._store.get(transaction_id)

    def get_by_idempotency_key(self, idempotency_key: str) -> SAPTransaction | None:
        return next(
            (
                tx
                for tx in self._store.values()
                if tx.idempotency_key == idempotency_key
            ),
            None,
        )

    def list_pending_for_retry(self) -> list[SAPTransaction]:
        return [
            tx
            for tx in self._store.values()
            if tx.status == SAPTransactionStatus.FAILED
            and tx.retry_count < tx.max_retries
        ]

    def list_by_object(
        self, object_type: SAPObjectType, object_id: uuid.UUID
    ) -> list[SAPTransaction]:
        return [
            tx
            for tx in self._store.values()
            if tx.object_type == object_type and tx.object_id == object_id
        ]

    def list_by_status(self, status: SAPTransactionStatus) -> list[SAPTransaction]:
        return [tx for tx in self._store.values() if tx.status == status]

    def save(self, transaction: SAPTransaction) -> SAPTransaction:
        self._store[transaction.id] = transaction
        return transaction


class FakeSAPPRPort(ISAPPurchaseRequisitionPort):
    def __init__(
        self, pr_number: str = "10000001", *, fail_with: Exception | None = None
    ) -> None:
        self.pr_number = pr_number
        self.fail_with = fail_with
        self.calls: list[CreatePRRequest] = []

    def create_purchase_requisition(
        self, request: CreatePRRequest
    ) -> SAPPurchaseRequisitionDTO:
        self.calls.append(request)
        if self.fail_with is not None:
            raise self.fail_with
        return SAPPurchaseRequisitionDTO(
            pr_number=self.pr_number,
            line_items=[
                SAPPRLineItemDTO(
                    item_number="00010",
                    material_number=request.line_items[0].material_number,
                    quantity=request.line_items[0].quantity,
                    unit=request.line_items[0].unit,
                )
            ],
            created_at=date.today(),
        )

    def get_purchase_requisition(self, pr_number: str) -> SAPPurchaseRequisitionDTO:
        return SAPPurchaseRequisitionDTO(
            pr_number=pr_number, line_items=[], created_at=date.today()
        )


def _submit_dto(pr_id: uuid.UUID, **kwargs: object) -> SubmitPRToSAPDTO:
    return SubmitPRToSAPDTO(
        pr_id=pr_id,
        document_type="NB",
        plant="1000",
        delivery_date=date(2026, 8, 1),
        request_id="req-sap",
        submitted_by=uuid.uuid4(),
        **kwargs,  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# Create / Add line
# ---------------------------------------------------------------------------


class TestCreatePurchaseRequisitionService:
    def test_creates_draft_pr(self) -> None:
        order = _make_repair_order()
        result = CreatePurchaseRequisitionService(
            FakePRRepository(), FakeRepairRepository([order])
        ).execute(
            CreatePurchaseRequisitionDTO(
                repair_order_id=order.id,
                request_id="req-create",
                requested_by=uuid.uuid4(),
            )
        )
        assert isinstance(result, PurchaseRequisitionResponseDTO)
        assert result.status == PRStatus.DRAFT
        assert result.repair_order_id == order.id

    def test_raises_not_found_for_missing_repair_order(self) -> None:
        with pytest.raises(FMMSNotFoundError):
            CreatePurchaseRequisitionService(
                FakePRRepository(), FakeRepairRepository()
            ).execute(
                CreatePurchaseRequisitionDTO(
                    repair_order_id=uuid.uuid4(),
                    request_id="req-norepair",
                    requested_by=uuid.uuid4(),
                )
            )


class TestAddPRLineItemService:
    def test_adds_line_item(self) -> None:
        pr = _make_pr(with_line=False)
        result = AddPRLineItemService(FakePRRepository([pr])).execute(
            AddPRLineItemDTO(
                pr_id=pr.id,
                material_number="10000002",
                quantity=Decimal("3"),
                unit_of_measure="EA",
                description="Oil filter",
                request_id="req-line",
            )
        )
        assert len(result.line_items) == 1
        assert result.line_items[0].material_number == "10000002"

    def test_raises_validation_when_price_incomplete(self) -> None:
        pr = _make_pr(with_line=False)
        with pytest.raises(FMMSValidationError):
            AddPRLineItemService(FakePRRepository([pr])).execute(
                AddPRLineItemDTO(
                    pr_id=pr.id,
                    material_number="10000002",
                    quantity=Decimal("1"),
                    unit_of_measure="EA",
                    description="X",
                    request_id="req-bad",
                    estimated_amount=Decimal("10"),
                )
            )


# ---------------------------------------------------------------------------
# SubmitPRToSAPService — critical path
# ---------------------------------------------------------------------------


class TestSubmitPRToSAPService:
    def test_submits_and_stores_sap_pr_number(self) -> None:
        pr = _make_pr()
        tx_repo = FakeSAPTransactionRepository()
        sap = FakeSAPPRPort(pr_number="45000011")

        result = SubmitPRToSAPService(FakePRRepository([pr]), tx_repo, sap).execute(
            _submit_dto(pr.id)
        )

        assert result.sap_pr_number == "45000011"
        assert result.status == PRStatus.SUBMITTED
        assert result.sap_transaction_status == SAPTransactionStatus.SUCCESS.value
        assert len(sap.calls) == 1
        assert len(tx_repo._store) == 1
        tx = next(iter(tx_repo._store.values()))
        assert tx.status == SAPTransactionStatus.SUCCESS
        assert tx.sap_document_number == "45000011"
        assert tx.response_payload is not None

    def test_idempotent_success_skips_second_sap_call(self) -> None:
        pr = _make_pr()
        pr_repo = FakePRRepository([pr])
        tx_repo = FakeSAPTransactionRepository()
        sap = FakeSAPPRPort(pr_number="45000022")
        service = SubmitPRToSAPService(pr_repo, tx_repo, sap)

        first = service.execute(_submit_dto(pr.id, idempotency_key="idem-1"))
        second = service.execute(_submit_dto(pr.id, idempotency_key="idem-1"))

        assert first.sap_pr_number == "45000022"
        assert second.sap_pr_number == "45000022"
        assert len(sap.calls) == 1

    def test_failed_transaction_is_retryable(self) -> None:
        pr = _make_pr()
        pr_repo = FakePRRepository([pr])
        tx_repo = FakeSAPTransactionRepository()
        failing = FakeSAPPRPort(fail_with=RuntimeError("SAP down"))
        service_fail = SubmitPRToSAPService(pr_repo, tx_repo, failing)

        with pytest.raises(FMMSIntegrationError):
            service_fail.execute(_submit_dto(pr.id, idempotency_key="idem-retry"))

        tx = next(iter(tx_repo._store.values()))
        assert tx.status == SAPTransactionStatus.FAILED
        assert tx.retry_count == 0

        succeeding = FakeSAPPRPort(pr_number="45000033")
        result = SubmitPRToSAPService(pr_repo, tx_repo, succeeding).execute(
            _submit_dto(pr.id, idempotency_key="idem-retry")
        )

        assert result.sap_pr_number == "45000033"
        assert result.status == PRStatus.SUBMITTED
        tx = next(iter(tx_repo._store.values()))
        assert tx.status == SAPTransactionStatus.SUCCESS
        assert tx.retry_count == 1
        assert len(succeeding.calls) == 1

    def test_raises_conflict_when_in_progress(self) -> None:
        pr = _make_pr()
        now = datetime.now(tz=UTC)
        tx = SAPTransaction(
            id=uuid.uuid4(),
            object_type=SAPObjectType.PURCHASE_REQUISITION,
            object_id=pr.id,
            idempotency_key="idem-inflight",
            status=SAPTransactionStatus.IN_PROGRESS,
            created_at=now,
            updated_at=now,
        )
        with pytest.raises(FMMSConflictError):
            SubmitPRToSAPService(
                FakePRRepository([pr]),
                FakeSAPTransactionRepository([tx]),
                FakeSAPPRPort(),
            ).execute(_submit_dto(pr.id, idempotency_key="idem-inflight"))

    def test_raises_validation_when_no_line_items(self) -> None:
        pr = _make_pr(with_line=False)
        with pytest.raises(FMMSValidationError):
            SubmitPRToSAPService(
                FakePRRepository([pr]),
                FakeSAPTransactionRepository(),
                FakeSAPPRPort(),
            ).execute(_submit_dto(pr.id))

    def test_raises_not_found(self) -> None:
        with pytest.raises(FMMSNotFoundError):
            SubmitPRToSAPService(
                FakePRRepository(),
                FakeSAPTransactionRepository(),
                FakeSAPPRPort(),
            ).execute(_submit_dto(uuid.uuid4()))

    def test_stores_request_payload_for_audit(self) -> None:
        pr = _make_pr()
        tx_repo = FakeSAPTransactionRepository()
        SubmitPRToSAPService(FakePRRepository([pr]), tx_repo, FakeSAPPRPort()).execute(
            _submit_dto(pr.id)
        )
        tx = next(iter(tx_repo._store.values()))
        assert "line_items" in tx.request_payload
        assert tx.request_payload["pr_id"] == str(pr.id)


# ---------------------------------------------------------------------------
# ReceivePOFromSAPService
# ---------------------------------------------------------------------------


class TestReceivePOFromSAPService:
    def test_creates_po_from_sap_payload(self) -> None:
        pr = _make_pr()
        pr.link_sap_pr(SAPDocumentNumber("45000011"))
        pr.submit()

        result = ReceivePOFromSAPService(
            FakePRRepository([pr]), FakePORepository()
        ).execute(
            ReceivePOFromSAPDTO(
                pr_id=pr.id,
                sap_po_number="45000100",
                vendor_number="VEND01",
                line_items=(
                    ReceivePOLineItemDTO(
                        material_number="10000001",
                        quantity=Decimal("2"),
                        unit_of_measure="EA",
                        unit_price=Decimal("100.00"),
                        currency="IRR",
                    ),
                ),
                request_id="req-po",
                created_by=uuid.uuid4(),
            )
        )

        assert result.sap_po_number == "45000100"
        assert result.pr_id == pr.id
        assert result.vendor_number == "VEND01"

    def test_raises_when_pr_not_submitted_to_sap(self) -> None:
        pr = _make_pr()
        with pytest.raises(FMMSConflictError):
            ReceivePOFromSAPService(FakePRRepository([pr]), FakePORepository()).execute(
                ReceivePOFromSAPDTO(
                    pr_id=pr.id,
                    sap_po_number="45000100",
                    vendor_number="VEND01",
                    line_items=(
                        ReceivePOLineItemDTO(
                            material_number="10000001",
                            quantity=Decimal("1"),
                            unit_of_measure="EA",
                            unit_price=Decimal("10"),
                            currency="IRR",
                        ),
                    ),
                    request_id="req-early",
                    created_by=uuid.uuid4(),
                )
            )


# ---------------------------------------------------------------------------
# Get / List
# ---------------------------------------------------------------------------


class TestGetPurchaseRequisitionService:
    def test_returns_pr(self) -> None:
        pr = _make_pr()
        result = GetPurchaseRequisitionService(FakePRRepository([pr])).execute(pr.id)
        assert result.id == pr.id

    def test_raises_not_found(self) -> None:
        with pytest.raises(FMMSNotFoundError):
            GetPurchaseRequisitionService(FakePRRepository()).execute(uuid.uuid4())


class TestListPurchaseRequisitionsService:
    def test_lists_by_repair_order(self) -> None:
        repair_id = uuid.uuid4()
        pr1 = _make_pr(repair_order_id=repair_id)
        pr2 = _make_pr(repair_order_id=repair_id)
        other = _make_pr()
        results = ListPurchaseRequisitionsService(
            FakePRRepository([pr1, pr2, other])
        ).execute(repair_order_id=repair_id)
        assert len(results) == 2
