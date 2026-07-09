"""Django ORM models for the SAP Integration bounded context.

SAPTransactionModel enforces the idempotency key uniqueness required by ADR-008.
"""

from __future__ import annotations

from django.db import models

from infrastructure.database.base_model import BaseModel


class SAPTransactionModel(BaseModel):
    """Persistence model for a SAP integration transaction aggregate root.

    The ``idempotency_key`` has a unique constraint — the repository must
    check this key before creating a new transaction to prevent duplicates.

    Attributes:
        object_type: The FMMS business object type being synchronized.
        object_id: UUID of the FMMS business object.
        idempotency_key: Unique key generated per operation to prevent duplicates.
        status: Current lifecycle status of this transaction.
        retry_count: Number of retry attempts completed.
        max_retries: Maximum retry attempts allowed.
        request_payload: JSON payload sent to SAP.
        response_payload: JSON response received from SAP (nullable).
        sap_document_number: SAP-assigned document number on success (optional).
        error_message: Last error text from SAP (optional).
        completed_at: UTC timestamp when the transaction reached a terminal state.
    """

    object_type = models.CharField(max_length=30, db_index=True)
    object_id = models.UUIDField(db_index=True)
    idempotency_key = models.CharField(max_length=255)
    status = models.CharField(max_length=20, db_index=True)
    retry_count = models.PositiveSmallIntegerField(default=0)
    max_retries = models.PositiveSmallIntegerField(default=3)
    request_payload = models.JSONField(default=dict)
    response_payload = models.JSONField(null=True, blank=True, default=None)
    sap_document_number = models.CharField(max_length=30, blank=True, default="")
    error_message = models.TextField(blank=True, default="")
    completed_at = models.DateTimeField(null=True, blank=True, default=None)

    class Meta:
        app_label = "integration"
        db_table = "sap_transaction"
        verbose_name = "SAP Transaction"
        verbose_name_plural = "SAP Transactions"
        constraints = [
            models.UniqueConstraint(
                fields=["idempotency_key"],
                name="unique_sap_idempotency_key",
            ),
        ]
        indexes = [
            models.Index(
                fields=["object_type", "object_id"],
                name="sap_tx_object_idx",
            ),
            models.Index(
                fields=["status", "retry_count"],
                name="sap_tx_retry_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"SAPTransaction {self.id} [{self.status}]"
