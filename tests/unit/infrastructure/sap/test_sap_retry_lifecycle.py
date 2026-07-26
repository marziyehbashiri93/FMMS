"""P0 — SAP retry lifecycle scenarios (manager + retry application service)."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock

import pytest

from apps.integration.application.services.retry_failed_sap_transactions_service import (
    RetryFailedSAPTransactionsService,
)
from apps.integration.domain.entities import (
    SAPObjectType,
    SAPTransaction,
    SAPTransactionStatus,
)
from apps.integration.domain.exceptions import (
    SAPIntegrationError,
    SAPRetryExhaustedError,
    SAPTransactionNotFoundError,
)
from apps.integration.domain.interfaces.sap_transaction_repository import (
    ISAPTransactionRepository,
)
from core.sap.dtos.measurement_document import SAPMeasurementDocumentDTO
from core.sap.dtos.pm_notification import SAPNotificationDTO
from core.sap.dtos.pm_order import SAPPMOrderDTO
from core.sap.dtos.purchase_requisition import (
    CreatePRRequest,
    SAPPRLineItemDTO,
    SAPPurchaseRequisitionDTO,
)
from core.sap.dtos.vehicle_assignment import SAPVehicleAssignmentRequestDTO
from infrastructure.sap.transaction.sap_transaction_manager import SAPTransactionManager


def _tx(
    *,
    status: SAPTransactionStatus = SAPTransactionStatus.FAILED,
    object_type: SAPObjectType = SAPObjectType.PURCHASE_REQUISITION,
    retry_count: int = 0,
    max_retries: int = 3,
    request_payload: dict[str, Any] | None = None,
) -> SAPTransaction:
    now = datetime.now(tz=UTC)
    return SAPTransaction(
        id=uuid.uuid4(),
        object_type=object_type,
        object_id=uuid.uuid4(),
        idempotency_key=f"retry-{uuid.uuid4()}",
        status=status,
        created_at=now,
        updated_at=now,
        retry_count=retry_count,
        max_retries=max_retries,
        request_payload=request_payload
        or {
            "document_type": "NB",
            "plant": "1000",
            "delivery_date": date.today().isoformat(),
            "header_text": None,
            "line_items": [
                {
                    "material_number": "10000001",
                    "quantity": "2",
                    "unit": "EA",
                    "description": "Pads",
                }
            ],
        },
    )


class FakeTxRepo(ISAPTransactionRepository):
    """In-memory SAP transaction repository for retry lifecycle tests."""

    def __init__(self, initial: list[SAPTransaction] | None = None) -> None:
        self._store: dict[uuid.UUID, SAPTransaction] = {
            tx.id: tx for tx in (initial or [])
        }

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


@pytest.mark.unit
class TestSAPRetryLifecycle:
    """FAILED → retry → SUCCESS / EXHAUSTED / skip unknown type."""

    def test_retry_all_pending_succeeds_for_registered_type(self) -> None:
        """Eligible FAILED transactions are retried to SUCCESS."""
        failed = _tx(status=SAPTransactionStatus.FAILED, retry_count=0)
        repo = FakeTxRepo([failed])
        manager = SAPTransactionManager(repository=repo)

        def adapter(_payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
            return {"pr_number": "45009999"}, "45009999"

        manager.retry_all_pending({SAPObjectType.PURCHASE_REQUISITION: adapter})
        assert repo.get_by_id(failed.id).status == SAPTransactionStatus.SUCCESS
        assert repo.get_by_id(failed.id).sap_document_number == "45009999"

    def test_retry_all_pending_skips_unregistered_object_type(self) -> None:
        """Transactions without an adapter mapping are skipped, not crashed."""
        failed = _tx(
            status=SAPTransactionStatus.FAILED,
            object_type=SAPObjectType.GOODS_RECEIPT,
        )
        repo = FakeTxRepo([failed])
        manager = SAPTransactionManager(repository=repo)
        manager.retry_all_pending({})  # empty map
        assert repo.get_by_id(failed.id).status == SAPTransactionStatus.FAILED

    def test_retry_exhaustion_marks_exhausted(self) -> None:
        """retry() with no remaining budget marks EXHAUSTED and raises."""
        exhausted = _tx(
            status=SAPTransactionStatus.FAILED, retry_count=3, max_retries=3
        )
        repo = FakeTxRepo([exhausted])
        manager = SAPTransactionManager(repository=repo)
        with pytest.raises(SAPRetryExhaustedError):
            manager.retry(exhausted.id, lambda p: ({}, "X"))
        assert repo.get_by_id(exhausted.id).status == SAPTransactionStatus.EXHAUSTED

    def test_retry_all_pending_continues_after_one_failure(self) -> None:
        """One failing retry does not abort the rest of the sweep."""
        first = _tx(status=SAPTransactionStatus.FAILED)
        second = _tx(status=SAPTransactionStatus.FAILED)
        repo = FakeTxRepo([first, second])
        manager = SAPTransactionManager(repository=repo)
        calls = {"n": 0}

        def adapter(payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
            calls["n"] += 1
            if calls["n"] == 1:
                raise SAPIntegrationError("transient")
            return {"ok": True}, "DOC-2"

        manager.retry_all_pending({SAPObjectType.PURCHASE_REQUISITION: adapter})
        statuses = {tx.status for tx in repo._store.values()}
        assert SAPTransactionStatus.FAILED in statuses
        assert SAPTransactionStatus.SUCCESS in statuses


@pytest.mark.unit
class TestRetryFailedSAPTransactionsServicePayloadRebuild:
    """Application facade rebuilds port requests from stored payloads."""

    def test_rebuilds_purchase_requisition_payload(self) -> None:
        """PR retry callable invokes the PR port with rebuilt request."""
        manager = MagicMock()
        pr_port = MagicMock()
        pr_port.create_purchase_requisition.return_value = SAPPurchaseRequisitionDTO(
            pr_number="45001111",
            line_items=[
                SAPPRLineItemDTO(
                    item_number="00010",
                    material_number="10000001",
                    quantity=Decimal("2"),
                    unit="EA",
                )
            ],
            created_at=date.today(),
        )
        order_port = MagicMock()
        notif_port = MagicMock()
        measurement_port = MagicMock()
        vehicle_assignment_port = MagicMock()

        def capture_map(adapter_map: dict) -> None:
            payload = {
                "document_type": "NB",
                "plant": "1000",
                "delivery_date": date.today().isoformat(),
                "header_text": "retry",
                "line_items": [
                    {
                        "material_number": "10000001",
                        "quantity": "2",
                        "unit": "EA",
                        "description": "Pads",
                    }
                ],
            }
            response, doc = adapter_map[SAPObjectType.PURCHASE_REQUISITION](payload)
            assert doc == "45001111"
            assert response["pr_number"] == "45001111"
            assert isinstance(
                pr_port.create_purchase_requisition.call_args.args[0], CreatePRRequest
            )

        manager.retry_all_pending.side_effect = capture_map
        RetryFailedSAPTransactionsService(
            manager,
            pr_port,
            order_port,
            notif_port,
            measurement_port,
            vehicle_assignment_port,
        ).execute(request_id="corr-rebuild")
        manager.retry_all_pending.assert_called_once()

    def test_rebuilds_pm_order_and_notification_payloads(self) -> None:
        """PM order and notification retry callables invoke their ports."""
        manager = MagicMock()
        pr_port = MagicMock()
        order_port = MagicMock()
        order_port.create_pm_order.return_value = SAPPMOrderDTO(
            order_number="40001111",
            equipment_number="100001",
            order_type="PM01",
            status="CREATED",
            planned_start=datetime.now(tz=UTC),
        )
        notif_port = MagicMock()
        notif_port.create_notification.return_value = SAPNotificationDTO(
            notification_number="10001111",
            equipment_number="100001",
            status="OSNO",
            created_at=datetime.now(tz=UTC),
        )
        measurement_port = MagicMock()
        measurement_port.update_vehicle_odometer.return_value = (
            SAPMeasurementDocumentDTO(
                measurement_document_number="49001111",
                equipment_number="100001",
                notification_number="10001111",
                odometer_km=125000,
                created_at=datetime.now(tz=UTC),
            )
        )
        vehicle_assignment_port = MagicMock()
        vehicle_assignment_port.request_replacement_assignment.return_value = (
            SAPVehicleAssignmentRequestDTO(
                assignment_request_number="VA-REQ-0001",
                driver_customer_number="6000001001",
                unavailable_vehicle_number="300001",
                created_at=datetime.now(tz=UTC),
            )
        )

        def capture_map(adapter_map: dict) -> None:
            order_payload = {
                "equipment_number": "100001",
                "order_type": "PM01",
                "description": "Retry order",
                "planned_start": datetime.now(tz=UTC).isoformat(),
                "plant": "1000",
                "work_center": None,
            }
            _, order_doc = adapter_map[SAPObjectType.REPAIR_ORDER](order_payload)
            assert order_doc == "40001111"

            notif_payload = {
                "equipment_number": "100001",
                "fault_description": "PM retry",
                "defect_code": "PM-TRIG",
                "priority": "3",
                "reported_by": "system",
                "reported_at": datetime.now(tz=UTC).isoformat(),
            }
            _, notif_doc = adapter_map[SAPObjectType.PM_WORK_ORDER](notif_payload)
            assert notif_doc == "10001111"

            measurement_payload = {
                "equipment_number": "100001",
                "notification_number": "10001111",
                "odometer_km": 125000,
                "recorded_at": datetime.now(tz=UTC).isoformat(),
                "notification_type": "EM",
            }
            _, measurement_doc = adapter_map[SAPObjectType.MEASUREMENT_DOCUMENT](
                measurement_payload
            )
            assert measurement_doc == "49001111"

            assignment_payload = {
                "fault_id": str(uuid.uuid4()),
                "driver_customer_number": "6000001001",
                "unavailable_vehicle_number": "300001",
                "requested_at": datetime.now(tz=UTC).isoformat(),
                "reason": "خرابی تایید شد",
            }
            _, assignment_doc = adapter_map[SAPObjectType.VEHICLE_ASSIGNMENT](
                assignment_payload
            )
            assert assignment_doc == "VA-REQ-0001"

        manager.retry_all_pending.side_effect = capture_map
        RetryFailedSAPTransactionsService(
            manager,
            pr_port,
            order_port,
            notif_port,
            measurement_port,
            vehicle_assignment_port,
        ).execute(request_id="corr-rebuild-2")
