"""Domain entities for the SAP Integration bounded context.

SAPTransaction is the aggregate root for all SAP communication records.
It enforces idempotency and tracks retry state per ADR-008.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from apps.integration.domain.exceptions import (
    SAPRetryExhaustedError,
)


class SAPTransactionStatus(StrEnum):
    """Lifecycle states of a SAP integration transaction.

    Attributes:
        PENDING: Transaction is queued and has not been attempted yet.
        IN_PROGRESS: Transaction is currently being processed.
        SUCCESS: Transaction completed successfully in SAP.
        FAILED: Transaction failed; may be eligible for retry.
        RETRYING: Transaction is being retried after a failure.
        EXHAUSTED: All retry attempts have been consumed; manual intervention required.
    """

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    RETRYING = "RETRYING"
    EXHAUSTED = "EXHAUSTED"


class SAPObjectType(StrEnum):
    """The type of FMMS business object being synchronized with SAP.

    Attributes:
        VEHICLE: SAP PM Equipment master data.
        FAULT: SAP PM Notification.
        REPAIR_ORDER: SAP PM Work Order.
        PM_WORK_ORDER: SAP PM Planned Maintenance Order.
        PURCHASE_REQUISITION: SAP MM Purchase Requisition.
        PURCHASE_ORDER: SAP MM Purchase Order.
        GOODS_RECEIPT: SAP MM Goods Receipt posting.
        GOODS_ISSUE: SAP MM Goods Issue posting.
    """

    VEHICLE = "VEHICLE"
    FAULT = "FAULT"
    REPAIR_ORDER = "REPAIR_ORDER"
    PM_WORK_ORDER = "PM_WORK_ORDER"
    PURCHASE_REQUISITION = "PURCHASE_REQUISITION"
    PURCHASE_ORDER = "PURCHASE_ORDER"
    GOODS_RECEIPT = "GOODS_RECEIPT"
    GOODS_ISSUE = "GOODS_ISSUE"


_ALLOWED_TRANSITIONS: dict[SAPTransactionStatus, frozenset[SAPTransactionStatus]] = {
    SAPTransactionStatus.PENDING: frozenset({SAPTransactionStatus.IN_PROGRESS}),
    SAPTransactionStatus.IN_PROGRESS: frozenset(
        {SAPTransactionStatus.SUCCESS, SAPTransactionStatus.FAILED}
    ),
    SAPTransactionStatus.FAILED: frozenset(
        {SAPTransactionStatus.RETRYING, SAPTransactionStatus.EXHAUSTED}
    ),
    SAPTransactionStatus.RETRYING: frozenset(
        {SAPTransactionStatus.IN_PROGRESS, SAPTransactionStatus.EXHAUSTED}
    ),
    SAPTransactionStatus.SUCCESS: frozenset(),
    SAPTransactionStatus.EXHAUSTED: frozenset(),
}

MAX_RETRY_ATTEMPTS: int = 3


@dataclass
class SAPTransaction:
    """Aggregate root tracking a single SAP integration call with idempotency.

    Each call to SAP is recorded as a ``SAPTransaction``. The idempotency key
    prevents duplicate submissions. Retry state is managed here; the Celery
    task layer invokes ``prepare_retry()`` or ``mark_exhausted()`` based on
    the retry count.

    Attributes:
        id: Unique identifier for this transaction.
        object_type: The FMMS business object type being synced.
        object_id: UUID of the FMMS business object.
        idempotency_key: Unique key to detect duplicate submissions.
        status: Current lifecycle status.
        retry_count: Number of retry attempts made so far.
        max_retries: Maximum allowed retry attempts.
        request_payload: The payload sent to SAP (stored for audit/replay).
        response_payload: The response received from SAP (optional).
        sap_document_number: The SAP document number from a successful response.
        error_message: Last error message from SAP (optional).
        created_at: UTC timestamp of creation.
        updated_at: UTC timestamp of last update.
        completed_at: UTC timestamp of terminal state (optional).
    """

    id: uuid.UUID
    object_type: SAPObjectType
    object_id: uuid.UUID
    idempotency_key: str
    status: SAPTransactionStatus
    created_at: datetime
    updated_at: datetime
    retry_count: int = field(default=0)
    max_retries: int = field(default=MAX_RETRY_ATTEMPTS)
    request_payload: dict[str, Any] = field(default_factory=dict)
    response_payload: dict[str, Any] | None = field(default=None)
    sap_document_number: str | None = field(default=None)
    error_message: str | None = field(default=None)
    completed_at: datetime | None = field(default=None)

    def start(self) -> None:
        """Mark the transaction as in progress.

        Raises:
            ValueError: If the transition is not permitted.
        """
        self._transition_to(SAPTransactionStatus.IN_PROGRESS)

    def succeed(
        self,
        response_payload: dict[str, Any],
        sap_document_number: str | None,
        completed_at: datetime,
    ) -> None:
        """Record a successful SAP response.

        Args:
            response_payload: The raw SAP response body.
            sap_document_number: The SAP-assigned document number (if applicable).
            completed_at: UTC timestamp of completion.
        """
        self._transition_to(SAPTransactionStatus.SUCCESS)
        self.response_payload = response_payload
        self.sap_document_number = sap_document_number
        self.completed_at = completed_at
        self.error_message = None

    def fail(self, error_message: str) -> None:
        """Record a failed SAP response.

        Args:
            error_message: Human-readable description of the failure.
        """
        self._transition_to(SAPTransactionStatus.FAILED)
        self.error_message = error_message

    def prepare_retry(self) -> None:
        """Increment the retry count and transition to RETRYING.

        Raises:
            SAPRetryExhaustedError: If the maximum retry count has been reached.
        """
        if self.retry_count >= self.max_retries:
            raise SAPRetryExhaustedError(
                transaction_id=self.id, max_retries=self.max_retries
            )
        self._transition_to(SAPTransactionStatus.RETRYING)
        self.retry_count += 1

    def mark_exhausted(self, completed_at: datetime) -> None:
        """Mark the transaction as permanently exhausted.

        Args:
            completed_at: UTC timestamp when exhaustion was recorded.
        """
        self._transition_to(SAPTransactionStatus.EXHAUSTED)
        self.completed_at = completed_at

    def _transition_to(self, target: SAPTransactionStatus) -> None:
        """Guard and apply a status transition.

        Args:
            target: The desired new status.

        Raises:
            ValueError: If the transition is not permitted from the current state.
        """
        allowed = _ALLOWED_TRANSITIONS.get(self.status, frozenset())
        if target not in allowed:
            raise ValueError(
                f"Cannot transition SAPTransaction from '{self.status.value}' "
                f"to '{target.value}'."
            )
        self.status = target

    @property
    def is_terminal(self) -> bool:
        """Return True if the transaction has reached a terminal state."""
        return self.status in {
            SAPTransactionStatus.SUCCESS,
            SAPTransactionStatus.EXHAUSTED,
        }

    @property
    def can_retry(self) -> bool:
        """Return True if a retry attempt is possible."""
        return (
            self.status == SAPTransactionStatus.FAILED
            and self.retry_count < self.max_retries
        )
