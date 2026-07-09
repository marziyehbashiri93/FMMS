"""Unit tests for the SAP Integration domain layer."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from apps.integration.domain.entities import (
    MAX_RETRY_ATTEMPTS,
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


def _make_transaction(**kwargs: object) -> SAPTransaction:
    defaults: dict[str, object] = {
        "id": uuid.uuid4(),
        "object_type": SAPObjectType.FAULT,
        "object_id": uuid.uuid4(),
        "idempotency_key": str(uuid.uuid4()),
        "status": SAPTransactionStatus.PENDING,
        "created_at": datetime.now(tz=UTC),
        "updated_at": datetime.now(tz=UTC),
    }
    defaults.update(kwargs)
    return SAPTransaction(**defaults)  # type: ignore[arg-type]


class TestSAPTransactionLifecycle:
    def test_initial_state(self) -> None:
        tx = _make_transaction()
        assert tx.status == SAPTransactionStatus.PENDING
        assert tx.retry_count == 0
        assert tx.is_terminal is False

    def test_start(self) -> None:
        tx = _make_transaction()
        tx.start()
        assert tx.status == SAPTransactionStatus.IN_PROGRESS

    def test_succeed(self) -> None:
        tx = _make_transaction(status=SAPTransactionStatus.IN_PROGRESS)
        now = datetime.now(tz=UTC)
        tx.succeed(
            response_payload={"result": "ok"},
            sap_document_number="SAP-DOC-001",
            completed_at=now,
        )
        assert tx.status == SAPTransactionStatus.SUCCESS
        assert tx.sap_document_number == "SAP-DOC-001"
        assert tx.is_terminal is True

    def test_fail(self) -> None:
        tx = _make_transaction(status=SAPTransactionStatus.IN_PROGRESS)
        tx.fail(error_message="Connection timeout.")
        assert tx.status == SAPTransactionStatus.FAILED
        assert tx.error_message == "Connection timeout."
        assert tx.can_retry is True

    def test_prepare_retry_increments_count(self) -> None:
        tx = _make_transaction(status=SAPTransactionStatus.FAILED)
        tx.prepare_retry()
        assert tx.retry_count == 1
        assert tx.status == SAPTransactionStatus.RETRYING

    def test_retry_exhaustion_raises(self) -> None:
        tx = _make_transaction(
            status=SAPTransactionStatus.FAILED,
            retry_count=MAX_RETRY_ATTEMPTS,
        )
        with pytest.raises(SAPRetryExhaustedError) as exc_info:
            tx.prepare_retry()
        assert exc_info.value.max_retries == MAX_RETRY_ATTEMPTS

    def test_mark_exhausted(self) -> None:
        tx = _make_transaction(status=SAPTransactionStatus.FAILED)
        now = datetime.now(tz=UTC)
        tx.mark_exhausted(completed_at=now)
        assert tx.status == SAPTransactionStatus.EXHAUSTED
        assert tx.is_terminal is True
        assert tx.completed_at == now

    def test_invalid_transition_raises(self) -> None:
        tx = _make_transaction(status=SAPTransactionStatus.SUCCESS)
        with pytest.raises(ValueError, match="Cannot transition"):
            tx.start()

    def test_can_retry_false_after_exhausted(self) -> None:
        tx = _make_transaction(
            status=SAPTransactionStatus.FAILED,
            retry_count=MAX_RETRY_ATTEMPTS,
        )
        assert tx.can_retry is False

    def test_max_retries_default(self) -> None:
        tx = _make_transaction()
        assert tx.max_retries == MAX_RETRY_ATTEMPTS


class TestSAPIntegrationExceptions:
    def test_integration_error(self) -> None:
        err = SAPIntegrationError("SAP returned error", sap_error_code="RFC_ERR")
        assert "SAP returned error" in str(err)
        assert err.sap_error_code == "RFC_ERR"

    def test_retry_exhausted_error(self) -> None:
        err = SAPRetryExhaustedError(transaction_id="tx-001", max_retries=3)
        assert "tx-001" in str(err)
        assert err.max_retries == 3

    def test_idempotency_error(self) -> None:
        err = SAPIdempotencyError("key-001", "tx-existing")
        assert "key-001" in str(err)
        assert err.idempotency_key == "key-001"

    def test_not_found_error(self) -> None:
        err = SAPTransactionNotFoundError("tx-abc")
        assert "tx-abc" in str(err)
