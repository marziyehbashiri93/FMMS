"""API integration tests for SAP transaction read endpoints."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from rest_framework.test import APIClient

from apps.integration.domain.entities import (
    SAPObjectType,
    SAPTransaction,
    SAPTransactionStatus,
)
from apps.integration.infrastructure.repositories import DjangoSAPTransactionRepository

pytestmark = pytest.mark.django_db


class TestIntegrationAPI:
    """Cover SAP transaction list and retrieve endpoints."""

    def test_list_and_retrieve_sap_transactions(
        self, authenticated_client: APIClient
    ) -> None:
        """Seed a transaction and read it through the API."""
        now = datetime.now(tz=UTC)
        txn = SAPTransaction(
            id=uuid.uuid4(),
            object_type=SAPObjectType.FAULT,
            object_id=uuid.uuid4(),
            idempotency_key=f"FAULT-{uuid.uuid4()}",
            status=SAPTransactionStatus.PENDING,
            created_at=now,
            updated_at=now,
            request_payload={"action": "CREATE_NOTIFICATION"},
        )
        saved = DjangoSAPTransactionRepository().save(txn)

        listed = authenticated_client.get("/api/v1/sap-transactions/")
        assert listed.status_code == 200
        assert listed.data["count"] >= 1

        filtered = authenticated_client.get("/api/v1/sap-transactions/?status=PENDING")
        assert filtered.status_code == 200
        assert filtered.data["count"] >= 1

        retrieved = authenticated_client.get(f"/api/v1/sap-transactions/{saved.id}/")
        assert retrieved.status_code == 200
        assert retrieved.data["id"] == str(saved.id)
        assert retrieved.data["status"] == "PENDING"
