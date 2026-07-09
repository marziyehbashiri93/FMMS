"""Abstract repository interface for the SAPTransaction aggregate."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from apps.integration.domain.entities import (
    SAPObjectType,
    SAPTransaction,
    SAPTransactionStatus,
)


class ISAPTransactionRepository(ABC):
    """Port (interface) for persisting and retrieving SAPTransaction aggregates."""

    @abstractmethod
    def get_by_id(self, transaction_id: uuid.UUID) -> SAPTransaction:
        """Retrieve a SAP transaction by its unique identifier.

        Args:
            transaction_id: The UUID of the transaction.

        Returns:
            The matching ``SAPTransaction`` aggregate.

        Raises:
            SAPTransactionNotFoundError: If no transaction exists with this ID.
        """

    @abstractmethod
    def get_by_idempotency_key(self, idempotency_key: str) -> SAPTransaction | None:
        """Retrieve a SAP transaction by its idempotency key.

        Used to detect and prevent duplicate submissions before creating a new
        transaction.

        Args:
            idempotency_key: The unique idempotency key string.

        Returns:
            The matching ``SAPTransaction`` aggregate, or ``None`` if not found.
        """

    @abstractmethod
    def list_pending_for_retry(self) -> list[SAPTransaction]:
        """Return all failed transactions that are eligible for retry.

        Returns:
            A list of ``SAPTransaction`` aggregates with FAILED status where
            ``retry_count < max_retries``.
        """

    @abstractmethod
    def list_by_object(
        self,
        object_type: SAPObjectType,
        object_id: uuid.UUID,
    ) -> list[SAPTransaction]:
        """Return all transactions for a specific FMMS business object.

        Args:
            object_type: The type of FMMS business object.
            object_id: The UUID of the FMMS business object.

        Returns:
            A list of ``SAPTransaction`` aggregates, ordered by creation time.
        """

    @abstractmethod
    def list_by_status(self, status: SAPTransactionStatus) -> list[SAPTransaction]:
        """Return all transactions matching a given status.

        Args:
            status: The ``SAPTransactionStatus`` to filter by.

        Returns:
            A list of ``SAPTransaction`` aggregates.
        """

    @abstractmethod
    def save(self, transaction: SAPTransaction) -> SAPTransaction:
        """Persist a new or updated SAP transaction aggregate.

        Args:
            transaction: The ``SAPTransaction`` aggregate to save.

        Returns:
            The saved ``SAPTransaction`` aggregate.
        """
