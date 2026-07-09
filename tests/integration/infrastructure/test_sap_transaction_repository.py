"""Integration tests for DjangoSAPTransactionRepository.

Critical path: verifies idempotency key uniqueness, retry tracking,
and the full status lifecycle.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from apps.integration.domain.entities import (
    SAPObjectType,
    SAPTransaction,
    SAPTransactionStatus,
)
from apps.integration.domain.exceptions import SAPTransactionNotFoundError
from apps.integration.domain.interfaces.sap_transaction_repository import (
    ISAPTransactionRepository,
)
from apps.integration.infrastructure.repositories import DjangoSAPTransactionRepository

pytestmark = pytest.mark.django_db


def _make_txn(
    idempotency_key: str | None = None,
    status: SAPTransactionStatus = SAPTransactionStatus.PENDING,
    object_type: SAPObjectType = SAPObjectType.FAULT,
) -> SAPTransaction:
    now = datetime.now(tz=UTC)
    repo = DjangoSAPTransactionRepository()
    txn = SAPTransaction(
        id=uuid.uuid4(),
        object_type=object_type,
        object_id=uuid.uuid4(),
        idempotency_key=idempotency_key or f"FAULT-{uuid.uuid4()}",
        status=status,
        created_at=now,
        updated_at=now,
        request_payload={"action": "CREATE_NOTIFICATION"},
    )
    return repo.save(txn)


class TestInterface:
    def test_satisfies_interface(self) -> None:
        assert isinstance(DjangoSAPTransactionRepository(), ISAPTransactionRepository)


class TestSaveAndRetrieve:
    def test_save_and_get_by_id(self) -> None:
        repo = DjangoSAPTransactionRepository()
        txn = _make_txn()
        fetched = repo.get_by_id(txn.id)
        assert fetched.id == txn.id
        assert fetched.status == SAPTransactionStatus.PENDING
        assert fetched.request_payload == {"action": "CREATE_NOTIFICATION"}

    def test_get_by_id_not_found(self) -> None:
        repo = DjangoSAPTransactionRepository()
        with pytest.raises(SAPTransactionNotFoundError):
            repo.get_by_id(uuid.uuid4())

    def test_get_by_idempotency_key(self) -> None:
        repo = DjangoSAPTransactionRepository()
        key = f"REPAIR-{uuid.uuid4()}"
        txn = _make_txn(idempotency_key=key)
        found = repo.get_by_idempotency_key(key)
        assert found is not None
        assert found.id == txn.id

    def test_get_by_idempotency_key_none_if_missing(self) -> None:
        repo = DjangoSAPTransactionRepository()
        result = repo.get_by_idempotency_key("NONEXISTENT-KEY")
        assert result is None

    def test_idempotency_key_unique_constraint(self) -> None:
        """Second save with same idempotency_key on a different UUID must fail."""
        from django.db import IntegrityError

        repo = DjangoSAPTransactionRepository()
        key = f"UNIQUE-{uuid.uuid4()}"
        _make_txn(idempotency_key=key)
        now = datetime.now(tz=UTC)
        duplicate = SAPTransaction(
            id=uuid.uuid4(),
            object_type=SAPObjectType.FAULT,
            object_id=uuid.uuid4(),
            idempotency_key=key,
            status=SAPTransactionStatus.PENDING,
            created_at=now,
            updated_at=now,
        )
        with pytest.raises(IntegrityError):
            repo.save(duplicate)


class TestStatusLifecycle:
    def test_start_transitions_to_in_progress(self) -> None:
        repo = DjangoSAPTransactionRepository()
        txn = _make_txn()
        txn.start()
        repo.save(txn)
        fetched = repo.get_by_id(txn.id)
        assert fetched.status == SAPTransactionStatus.IN_PROGRESS

    def test_succeed_stores_sap_document_number(self) -> None:
        repo = DjangoSAPTransactionRepository()
        txn = _make_txn()
        txn.start()
        now = datetime.now(tz=UTC)
        txn.succeed(
            response_payload={"NOTIF_NO": "10001234"},
            sap_document_number="10001234",
            completed_at=now,
        )
        repo.save(txn)
        fetched = repo.get_by_id(txn.id)
        assert fetched.status == SAPTransactionStatus.SUCCESS
        assert fetched.sap_document_number == "10001234"

    def test_fail_stores_error_message(self) -> None:
        repo = DjangoSAPTransactionRepository()
        txn = _make_txn()
        txn.start()
        txn.fail(error_message="SAP timeout")
        repo.save(txn)
        fetched = repo.get_by_id(txn.id)
        assert fetched.status == SAPTransactionStatus.FAILED
        assert fetched.error_message == "SAP timeout"


class TestRetry:
    def test_list_pending_for_retry(self) -> None:
        repo = DjangoSAPTransactionRepository()
        txn = _make_txn()
        txn.start()
        txn.fail(error_message="timeout")
        repo.save(txn)
        pending = repo.list_pending_for_retry()
        ids = {t.id for t in pending}
        assert txn.id in ids

    def test_exhausted_not_in_retry_list(self) -> None:
        repo = DjangoSAPTransactionRepository()
        txn = _make_txn()
        txn.start()
        txn.fail(error_message="timeout")
        txn.mark_exhausted(completed_at=datetime.now(tz=UTC))
        repo.save(txn)
        pending = repo.list_pending_for_retry()
        ids = {t.id for t in pending}
        assert txn.id not in ids


class TestListOperations:
    def test_list_by_object(self) -> None:
        repo = DjangoSAPTransactionRepository()
        obj_id = uuid.uuid4()
        _make_txn(object_type=SAPObjectType.REPAIR_ORDER)
        now = datetime.now(tz=UTC)
        txn = SAPTransaction(
            id=uuid.uuid4(),
            object_type=SAPObjectType.FAULT,
            object_id=obj_id,
            idempotency_key=f"OBJ-{uuid.uuid4()}",
            status=SAPTransactionStatus.PENDING,
            created_at=now,
            updated_at=now,
        )
        repo.save(txn)
        result = repo.list_by_object(SAPObjectType.FAULT, obj_id)
        assert len(result) == 1
        assert result[0].id == txn.id

    def test_list_by_status(self) -> None:
        repo = DjangoSAPTransactionRepository()
        _make_txn(status=SAPTransactionStatus.PENDING)
        txn2 = _make_txn(status=SAPTransactionStatus.PENDING)
        txn2.start()
        repo.save(txn2)
        in_progress = repo.list_by_status(SAPTransactionStatus.IN_PROGRESS)
        assert all(t.status == SAPTransactionStatus.IN_PROGRESS for t in in_progress)
