"""Domain exceptions for the SAP Integration bounded context."""

from __future__ import annotations

from core.domain.exceptions import DomainError, DomainNotFoundError


class IntegrationDomainError(DomainError):
    """Base class for all SAP Integration domain exceptions."""


class SAPIntegrationError(IntegrationDomainError):
    """Raised when a SAP integration call fails with an error response.

    Args:
        message: Human-readable error description.
        sap_error_code: Optional SAP error code from the response.
    """

    def __init__(self, message: str, sap_error_code: str | None = None) -> None:
        super().__init__(message)
        self.sap_error_code = sap_error_code


class SAPRetryExhaustedError(IntegrationDomainError):
    """Raised when a SAP transaction has exhausted all retry attempts.

    Args:
        transaction_id: The ID of the exhausted transaction.
        max_retries: The maximum number of retries that were attempted.
    """

    def __init__(self, transaction_id: object, max_retries: int) -> None:
        super().__init__(
            f"SAP transaction '{transaction_id}' exhausted all {max_retries} "
            f"retry attempts."
        )
        self.transaction_id = transaction_id
        self.max_retries = max_retries


class SAPIdempotencyError(IntegrationDomainError):
    """Raised when a duplicate SAP transaction is detected via idempotency key.

    Args:
        idempotency_key: The duplicate idempotency key.
        existing_transaction_id: ID of the existing transaction with this key.
    """

    def __init__(self, idempotency_key: str, existing_transaction_id: object) -> None:
        super().__init__(
            f"A SAP transaction with idempotency key '{idempotency_key}' "
            f"already exists: '{existing_transaction_id}'."
        )
        self.idempotency_key = idempotency_key
        self.existing_transaction_id = existing_transaction_id


class SAPTransactionNotFoundError(IntegrationDomainError, DomainNotFoundError):
    """Raised when a SAP transaction cannot be located by its identifier.

    Args:
        transaction_id: The identifier that was searched for.
    """

    def __init__(self, transaction_id: object) -> None:
        super().__init__(f"SAP transaction not found: '{transaction_id}'.")
        self.transaction_id = transaction_id
