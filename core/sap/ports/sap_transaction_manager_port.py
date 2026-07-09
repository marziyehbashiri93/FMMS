"""Port for the SAP write transaction gateway.

Application services depend on this abstraction only. The concrete
``SAPTransactionManager`` lives in infrastructure and is wired at the
composition root.

Architecture::

    Application Service
            |
    ISAPTransactionManager  (this port)
            |
    SAP Port (domain write port)
            |
    SAP Adapter
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from apps.integration.domain.entities import SAPObjectType

#: Adapter callable signature used by the write gateway.
#: ``(request_payload) -> (response_payload, sap_document_number)``.
SAPAdapterCallable = Callable[[dict[str, Any]], tuple[dict[str, Any], str]]


class ISAPTransactionManager(ABC):
    """Sole gateway for tracked SAP write operations.

    Owns idempotency, ``SAPTransaction`` lifecycle, and retry orchestration.
    Application services must not manage ``SAPTransaction`` state themselves.
    """

    @abstractmethod
    def execute(
        self,
        object_type: SAPObjectType,
        object_id: uuid.UUID,
        idempotency_key: str,
        request_payload: dict[str, Any],
        adapter_call: SAPAdapterCallable,
    ) -> tuple[dict[str, Any], str]:
        """Execute a tracked SAP write.

        Args:
            object_type: FMMS business object type being synced.
            object_id: UUID of the FMMS business object.
            idempotency_key: Deterministic key preventing duplicate submissions.
            request_payload: Audit/replay payload stored on the transaction.
            adapter_call: Callable wrapping the SAP port/adapter write.

        Returns:
            ``(response_payload, sap_document_number)``.
        """

    @abstractmethod
    def retry(
        self,
        transaction_id: uuid.UUID,
        adapter_call: SAPAdapterCallable,
    ) -> tuple[dict[str, Any], str]:
        """Retry a previously failed SAP transaction.

        Args:
            transaction_id: UUID of the FAILED transaction.
            adapter_call: Callable wrapping the SAP port/adapter write.

        Returns:
            ``(response_payload, sap_document_number)`` on success.
        """

    @abstractmethod
    def retry_all_pending(
        self,
        adapter_call_map: dict[SAPObjectType, SAPAdapterCallable],
    ) -> None:
        """Retry all FAILED transactions that still have retry budget.

        Args:
            adapter_call_map: Maps object type to the adapter callable to use.
        """
