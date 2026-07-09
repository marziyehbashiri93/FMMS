"""P1 — SAP / PR transaction rollback and failure non-mutation scenarios."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from apps.integration.domain.entities import (
    SAPObjectType,
    SAPTransaction,
    SAPTransactionStatus,
)
from apps.integration.domain.exceptions import (
    SAPIdempotencyError,
    SAPIntegrationError,
    SAPRetryExhaustedError,
    SAPTransactionNotFoundError,
)
from apps.integration.domain.interfaces.sap_transaction_repository import (
    ISAPTransactionRepository,
)
from apps.procurement.application.dto.procurement_dto import SubmitPRToSAPDTO
from apps.procurement.application.services.submit_pr_to_sap_service import (
    SubmitPRToSAPService,
)
from apps.procurement.domain.entities import PRLineItem, PRStatus, PurchaseRequisition
from apps.procurement.domain.value_objects import MaterialNumber, Quantity
from core.exceptions.base_exception import FMMSConflictError, FMMSIntegrationError
from core.sap.ports.sap_transaction_manager_port import ISAPTransactionManager
from infrastructure.sap.transaction.sap_transaction_manager import SAPTransactionManager


class FakeTxRepo(ISAPTransactionRepository):
    """Minimal in-memory SAP transaction repository."""

    def __init__(self) -> None:
        self._store: dict[uuid.UUID, SAPTransaction] = {}

    def get_by_id(self, transaction_id: uuid.UUID) -> SAPTransaction:
        try:
            return self._store[transaction_id]
        except KeyError as exc:
            raise SAPTransactionNotFoundError(transaction_id) from exc

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


def _draft_pr() -> PurchaseRequisition:
    now = datetime.now(tz=UTC)
    pr = PurchaseRequisition(
        id=uuid.uuid4(),
        repair_order_id=uuid.uuid4(),
        status=PRStatus.DRAFT,
        requested_by_id=uuid.uuid4(),
        created_at=now,
        updated_at=now,
    )
    pr.add_line_item(
        PRLineItem(
            id=uuid.uuid4(),
            material_number=MaterialNumber("10000001"),
            quantity=Quantity(value=Decimal("2"), unit_of_measure="EA"),
            description="Brake pads",
        )
    )
    return pr


def _submit_dto(pr_id: uuid.UUID, **overrides: object) -> SubmitPRToSAPDTO:
    payload: dict[str, object] = {
        "pr_id": pr_id,
        "document_type": "NB",
        "plant": "1000",
        "delivery_date": date.today(),
        "request_id": "corr-rb",
        "submitted_by": uuid.uuid4(),
    }
    payload.update(overrides)
    return SubmitPRToSAPDTO(**payload)  # type: ignore[arg-type]


@pytest.mark.unit
class TestTransactionRollbackScenarios:
    """Failures must not promote domain aggregates or leave SUCCESS txs."""

    def test_manager_failure_marks_failed_not_success(self) -> None:
        """Adapter failure leaves transaction FAILED with no SAP document."""
        repo = FakeTxRepo()
        manager = SAPTransactionManager(repository=repo)

        def boom(_payload: dict) -> tuple[dict, str]:
            raise SAPIntegrationError("RFCs down")

        with pytest.raises(SAPIntegrationError):
            manager.execute(
                object_type=SAPObjectType.PURCHASE_REQUISITION,
                object_id=uuid.uuid4(),
                idempotency_key=f"pr-{uuid.uuid4()}",
                request_payload={
                    "plant": "1000",
                    "delivery_date": date.today().isoformat(),
                },
                adapter_call=boom,
            )

        txs = list(repo._store.values())
        assert len(txs) == 1
        assert txs[0].status == SAPTransactionStatus.FAILED
        assert txs[0].sap_document_number is None

    def test_pr_submit_failure_does_not_mutate_pr_status(self) -> None:
        """Failed SAP submit keeps the PR in DRAFT (no false SUBMITTED)."""
        pr = _draft_pr()
        pr_repo = MagicMock()
        pr_repo.get_by_id.return_value = pr
        pr_repo.save.side_effect = lambda entity: entity

        manager = MagicMock(spec=ISAPTransactionManager)
        manager.execute.side_effect = SAPIntegrationError("SAP timeout")

        service = SubmitPRToSAPService(
            pr_repository=pr_repo,
            sap_transaction_manager=manager,
            sap_pr_port=MagicMock(),
        )
        with pytest.raises(FMMSIntegrationError):
            service.execute(_submit_dto(pr.id, request_id="corr-rb-1"))

        assert pr.status == PRStatus.DRAFT
        assert pr.sap_pr_number is None
        pr_repo.save.assert_not_called()

    def test_exhausted_idempotency_key_raises_conflict_without_save(self) -> None:
        """EXHAUSTED key cannot be re-submitted; PR stays DRAFT."""
        pr = _draft_pr()
        pr_repo = MagicMock()
        pr_repo.get_by_id.return_value = pr

        manager = MagicMock(spec=ISAPTransactionManager)
        manager.execute.side_effect = SAPRetryExhaustedError(
            transaction_id=uuid.uuid4(), max_retries=3
        )

        service = SubmitPRToSAPService(
            pr_repository=pr_repo,
            sap_transaction_manager=manager,
            sap_pr_port=MagicMock(),
        )
        with pytest.raises(FMMSConflictError):
            service.execute(
                _submit_dto(
                    pr.id,
                    request_id="corr-rb-2",
                    idempotency_key="pr-exhausted-1",
                )
            )
        assert pr.status == PRStatus.DRAFT
        pr_repo.save.assert_not_called()

    def test_in_flight_idempotency_raises_without_domain_mutation(self) -> None:
        """In-flight idempotency conflict must not mutate the PR."""
        pr = _draft_pr()
        pr_repo = MagicMock()
        pr_repo.get_by_id.return_value = pr

        manager = MagicMock(spec=ISAPTransactionManager)
        manager.execute.side_effect = SAPIdempotencyError(
            idempotency_key="pr-inflight-1",
            existing_transaction_id=uuid.uuid4(),
        )

        service = SubmitPRToSAPService(
            pr_repository=pr_repo,
            sap_transaction_manager=manager,
            sap_pr_port=MagicMock(),
        )
        with pytest.raises(FMMSConflictError):
            service.execute(
                _submit_dto(
                    pr.id,
                    request_id="corr-rb-3",
                    idempotency_key="pr-inflight-1",
                )
            )
        assert pr.status == PRStatus.DRAFT
        pr_repo.save.assert_not_called()
