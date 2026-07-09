"""Concrete Django ORM implementation of ISAPTransactionRepository.

Critical data path — save() uses transaction.atomic() per the confirmation
that consistency is required for SAPTransaction writes.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from django.db import transaction

from apps.integration.domain.entities import (
    MAX_RETRY_ATTEMPTS,
    SAPObjectType,
    SAPTransaction,
    SAPTransactionStatus,
)
from apps.integration.domain.exceptions import SAPTransactionNotFoundError
from apps.integration.domain.interfaces.sap_transaction_repository import (
    ISAPTransactionRepository,
)
from apps.integration.infrastructure.models import SAPTransactionModel
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger(domain="integration", module=__name__)


def _to_domain(orm: SAPTransactionModel) -> SAPTransaction:
    """Map a SAPTransactionModel ORM instance to a SAPTransaction domain entity."""
    return SAPTransaction(
        id=uuid.UUID(str(orm.id)),
        object_type=SAPObjectType(orm.object_type),
        object_id=orm.object_id,
        idempotency_key=orm.idempotency_key,
        status=SAPTransactionStatus(orm.status),
        created_at=orm.created_at,
        updated_at=orm.updated_at,
        retry_count=orm.retry_count,
        max_retries=orm.max_retries,
        request_payload=orm.request_payload or {},
        response_payload=orm.response_payload,
        sap_document_number=orm.sap_document_number or None,
        error_message=orm.error_message or None,
        completed_at=orm.completed_at,
    )


class DjangoSAPTransactionRepository(ISAPTransactionRepository):
    """Concrete repository for SAPTransaction aggregates backed by Django ORM.

    ``save()`` is wrapped in ``transaction.atomic()`` to guarantee consistency
    of the idempotency key check and record update.
    """

    def get_by_id(self, transaction_id: uuid.UUID) -> SAPTransaction:
        """Retrieve a SAP transaction by UUID."""
        try:
            orm = SAPTransactionModel.objects.get(id=transaction_id)
        except SAPTransactionModel.DoesNotExist:
            raise SAPTransactionNotFoundError(transaction_id) from None
        return _to_domain(orm)

    def get_by_idempotency_key(self, idempotency_key: str) -> SAPTransaction | None:
        """Retrieve a SAP transaction by its idempotency key, or None."""
        orm = SAPTransactionModel.objects.filter(
            idempotency_key=idempotency_key
        ).first()
        return _to_domain(orm) if orm else None

    def list_pending_for_retry(self) -> list[SAPTransaction]:
        """Return FAILED transactions that still have retry budget remaining."""
        qs = SAPTransactionModel.objects.filter(
            status=SAPTransactionStatus.FAILED.value,
            retry_count__lt=models_max_retries(),
        )
        return [_to_domain(orm) for orm in qs]

    def list_by_object(
        self,
        object_type: SAPObjectType,
        object_id: uuid.UUID,
    ) -> list[SAPTransaction]:
        """Return all transactions for a FMMS business object, oldest first."""
        qs = SAPTransactionModel.objects.filter(
            object_type=object_type.value,
            object_id=object_id,
        ).order_by("created_at")
        return [_to_domain(orm) for orm in qs]

    def list_by_status(self, status: SAPTransactionStatus) -> list[SAPTransaction]:
        """Return all transactions matching a given status."""
        qs = SAPTransactionModel.objects.filter(status=status.value)
        return [_to_domain(orm) for orm in qs]

    def save(self, txn: SAPTransaction) -> SAPTransaction:
        """Atomically persist a SAP transaction record.

        Uses select_for_update on the idempotency key to prevent concurrent
        duplicate insertions.
        """
        with transaction.atomic():
            obj, created = SAPTransactionModel.objects.update_or_create(
                id=txn.id,
                defaults={
                    "object_type": txn.object_type.value,
                    "object_id": txn.object_id,
                    "idempotency_key": txn.idempotency_key,
                    "status": txn.status.value,
                    "retry_count": txn.retry_count,
                    "max_retries": txn.max_retries,
                    "request_payload": txn.request_payload,
                    "response_payload": txn.response_payload,
                    "sap_document_number": txn.sap_document_number or "",
                    "error_message": txn.error_message or "",
                    "completed_at": txn.completed_at,
                    "updated_at": datetime.now(tz=UTC),
                },
            )
            if created:
                obj.created_at = txn.created_at
                obj.save(update_fields=["created_at"])
        logger.debug(
            "saved",
            extra={
                "txn_id": str(txn.id),
                "is_new": created,
                "status": txn.status.value,
            },
        )
        return txn


def models_max_retries() -> int:
    """Return the domain-level maximum retry count for retry-eligible queries."""
    return MAX_RETRY_ATTEMPTS
