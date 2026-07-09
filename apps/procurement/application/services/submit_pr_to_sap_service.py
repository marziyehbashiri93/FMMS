"""Service that submits a Purchase Requisition to SAP.

SAP dependency rules (M6):
- Depends only on ``ISAPPurchaseRequisitionPort`` from ``core/sap/ports/``.
- Never imports ``infrastructure.sap``, adapters, or ``SAPTransactionManager``.
- Owns ``SAPTransaction`` domain lifecycle for idempotency, audit, and retry
  compatibility (PENDING → IN_PROGRESS → SUCCESS | FAILED).

Workflow (transaction-boundary ready):
1. Load PR; require ≥1 line item.
2. Resolve idempotency key (default ``pr-submit:{pr_id}``).
3. If an existing SUCCESS transaction exists for the key, return current PR
   without calling SAP again.
4. Create or reuse a FAILED/RETRYING transaction; call ``start()``.
5. Persist transaction (IN_PROGRESS) before the SAP call.
6. Call ``ISAPPurchaseRequisitionPort.create_purchase_requisition``.
7. On success: ``succeed()``, link SAP PR number, ``submit()`` PR, save both.
8. On failure: ``fail()``, save transaction, re-raise ``FMMSIntegrationError``.

Retry workers can later call ``prepare_retry()`` on FAILED transactions and
re-invoke this service with the same idempotency key.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from apps.integration.domain.entities import (
    SAPObjectType,
    SAPTransaction,
    SAPTransactionStatus,
)
from apps.integration.domain.interfaces.sap_transaction_repository import (
    ISAPTransactionRepository,
)
from apps.procurement.application.dto.procurement_dto import (
    PurchaseRequisitionResponseDTO,
    SubmitPRToSAPDTO,
)
from apps.procurement.application.services.create_purchase_requisition_service import (
    _pr_to_response_dto,
)
from apps.procurement.domain.entities import PurchaseRequisition
from apps.procurement.domain.interfaces.procurement_repository import (
    IPurchaseRequisitionRepository,
)
from apps.procurement.domain.value_objects import SAPDocumentNumber
from core.exceptions.base_exception import (
    FMMSConflictError,
    FMMSIntegrationError,
    FMMSNotFoundError,
    FMMSValidationError,
)
from core.logging.structured_logger import get_structured_logger
from core.sap.dtos.purchase_requisition import CreatePRRequest, PRLineItemRequest
from core.sap.ports.purchase_requisition_port import ISAPPurchaseRequisitionPort

logger = get_structured_logger("procurement", __name__)


class SubmitPRToSAPService:
    """Submit a PR to SAP with SAPTransaction idempotency and lifecycle.

    Args:
        pr_repository: Concrete ``IPurchaseRequisitionRepository``.
        sap_transaction_repository: Concrete ``ISAPTransactionRepository``.
        sap_pr_port: Abstract ``ISAPPurchaseRequisitionPort`` only.
    """

    def __init__(
        self,
        pr_repository: IPurchaseRequisitionRepository,
        sap_transaction_repository: ISAPTransactionRepository,
        sap_pr_port: ISAPPurchaseRequisitionPort,
    ) -> None:
        self._pr_repo = pr_repository
        self._tx_repo = sap_transaction_repository
        self._sap = sap_pr_port

    def execute(self, dto: SubmitPRToSAPDTO) -> PurchaseRequisitionResponseDTO:
        """Submit the PR to SAP and persist the SAP document number.

        Args:
            dto: Submission request.

        Returns:
            ``PurchaseRequisitionResponseDTO`` with SAP PR number when successful.

        Raises:
            FMMSNotFoundError: If the PR does not exist.
            FMMSValidationError: If the PR has no line items.
            FMMSConflictError: If a non-retryable in-flight transaction exists,
                or the PR is already linked and not eligible for resubmit.
            FMMSIntegrationError: If the SAP port call fails.
        """
        logger.info(
            "Submitting PR to SAP",
            extra={
                "domain": "procurement",
                "service": "SubmitPRToSAPService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(dto.pr_id),
            },
        )

        pr = self._pr_repo.get_by_id(dto.pr_id)
        if pr is None:
            raise FMMSNotFoundError(
                message=f"Purchase requisition '{dto.pr_id}' not found.",
                details={"pr_id": str(dto.pr_id)},
            )

        if not pr.line_items:
            raise FMMSValidationError(
                message="Cannot submit a PR with no line items.",
                details={"pr_id": str(dto.pr_id)},
            )

        idempotency_key = dto.idempotency_key or f"pr-submit:{dto.pr_id}"
        existing_tx = self._tx_repo.get_by_idempotency_key(idempotency_key)

        if existing_tx is not None:
            if existing_tx.status == SAPTransactionStatus.SUCCESS:
                logger.info(
                    "Idempotent hit — returning existing successful SAP submission",
                    extra={
                        "domain": "procurement",
                        "service": "SubmitPRToSAPService",
                        "operation": "execute",
                        "request_id": dto.request_id,
                        "entity_id": str(dto.pr_id),
                        "result": "idempotent_success",
                        "sap_transaction_id": str(existing_tx.id),
                    },
                )
                return _pr_to_response_dto(
                    pr,
                    sap_transaction_id=existing_tx.id,
                    sap_transaction_status=existing_tx.status.value,
                )

            if existing_tx.status in {
                SAPTransactionStatus.PENDING,
                SAPTransactionStatus.IN_PROGRESS,
            }:
                raise FMMSConflictError(
                    message=(
                        f"SAP submission for PR '{dto.pr_id}' is already in progress "
                        f"(transaction '{existing_tx.id}')."
                    ),
                    details={
                        "pr_id": str(dto.pr_id),
                        "sap_transaction_id": str(existing_tx.id),
                        "status": existing_tx.status.value,
                    },
                )

            if existing_tx.status == SAPTransactionStatus.EXHAUSTED:
                raise FMMSConflictError(
                    message=(
                        f"SAP submission for PR '{dto.pr_id}' is exhausted; "
                        "manual intervention required."
                    ),
                    details={
                        "pr_id": str(dto.pr_id),
                        "sap_transaction_id": str(existing_tx.id),
                    },
                )

        now = datetime.now(tz=UTC)
        request_payload = _build_request_payload(pr, dto)
        tx = self._prepare_transaction(
            existing_tx=existing_tx,
            pr_id=pr.id,
            idempotency_key=idempotency_key,
            request_payload=request_payload,
            now=now,
        )
        tx.start()
        tx.updated_at = now
        self._tx_repo.save(tx)

        try:
            sap_response = self._sap.create_purchase_requisition(
                _to_create_pr_request(pr, dto)
            )
        except Exception as exc:
            tx.fail(error_message=str(exc))
            tx.updated_at = datetime.now(tz=UTC)
            self._tx_repo.save(tx)
            logger.info(
                "SAP PR submission failed",
                extra={
                    "domain": "procurement",
                    "service": "SubmitPRToSAPService",
                    "operation": "execute",
                    "request_id": dto.request_id,
                    "entity_id": str(pr.id),
                    "result": "failed",
                    "sap_transaction_id": str(tx.id),
                },
            )
            raise FMMSIntegrationError(
                message=f"SAP PR submission failed: {exc}",
                details={
                    "pr_id": str(pr.id),
                    "sap_transaction_id": str(tx.id),
                    "idempotency_key": idempotency_key,
                },
            ) from exc

        completed_at = datetime.now(tz=UTC)
        response_payload: dict[str, Any] = {
            "pr_number": sap_response.pr_number,
            "line_item_count": len(sap_response.line_items),
            "created_at": str(sap_response.created_at),
        }
        tx.succeed(
            response_payload=response_payload,
            sap_document_number=sap_response.pr_number,
            completed_at=completed_at,
        )
        tx.updated_at = completed_at
        self._tx_repo.save(tx)

        pr.link_sap_pr(SAPDocumentNumber(sap_response.pr_number))
        if pr.status.value == "DRAFT":
            pr.submit()
        pr.updated_at = completed_at
        saved = self._pr_repo.save(pr)

        logger.info(
            "PR submitted to SAP successfully",
            extra={
                "domain": "procurement",
                "service": "SubmitPRToSAPService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(saved.id),
                "result": "success",
                "sap_pr_number": sap_response.pr_number,
                "sap_transaction_id": str(tx.id),
            },
        )
        return _pr_to_response_dto(
            saved,
            sap_transaction_id=tx.id,
            sap_transaction_status=tx.status.value,
        )

    def _prepare_transaction(
        self,
        *,
        existing_tx: SAPTransaction | None,
        pr_id: uuid.UUID,
        idempotency_key: str,
        request_payload: dict[str, Any],
        now: datetime,
    ) -> SAPTransaction:
        """Create a new PENDING transaction or prepare an existing one for retry.

        Args:
            existing_tx: Prior transaction for the idempotency key, if any.
            pr_id: Purchase requisition UUID.
            idempotency_key: Unique submission key.
            request_payload: Audit payload for the SAP call.
            now: Current UTC timestamp.

        Returns:
            A ``SAPTransaction`` ready for ``start()``.
        """
        if existing_tx is None:
            return SAPTransaction(
                id=uuid.uuid4(),
                object_type=SAPObjectType.PURCHASE_REQUISITION,
                object_id=pr_id,
                idempotency_key=idempotency_key,
                status=SAPTransactionStatus.PENDING,
                created_at=now,
                updated_at=now,
                request_payload=request_payload,
            )

        if existing_tx.status == SAPTransactionStatus.FAILED:
            existing_tx.prepare_retry()
            existing_tx.request_payload = request_payload
            existing_tx.updated_at = now
            return existing_tx

        if existing_tx.status == SAPTransactionStatus.RETRYING:
            existing_tx.request_payload = request_payload
            existing_tx.updated_at = now
            return existing_tx

        raise FMMSConflictError(
            message=(
                f"Cannot prepare SAP transaction '{existing_tx.id}' "
                f"from status '{existing_tx.status}'."
            ),
            details={
                "sap_transaction_id": str(existing_tx.id),
                "status": existing_tx.status.value,
            },
        )


def _build_request_payload(
    pr: PurchaseRequisition, dto: SubmitPRToSAPDTO
) -> dict[str, Any]:
    """Build a serialisable audit payload for the SAPTransaction record."""
    return {
        "pr_id": str(pr.id),
        "document_type": dto.document_type,
        "plant": dto.plant,
        "delivery_date": dto.delivery_date.isoformat(),
        "header_text": dto.header_text,
        "line_items": [
            {
                "material_number": item.material_number.value,
                "quantity": str(item.quantity.value),
                "unit": item.quantity.unit_of_measure,
                "description": item.description,
            }
            for item in pr.line_items
        ],
    }


def _to_create_pr_request(
    pr: PurchaseRequisition, dto: SubmitPRToSAPDTO
) -> CreatePRRequest:
    """Map domain PR + DTO → SAP ``CreatePRRequest``."""
    line_items: list[PRLineItemRequest] = []
    for index, item in enumerate(pr.line_items, start=1):
        line_items.append(
            PRLineItemRequest(
                item_number=f"{index * 10:05d}",
                material_number=item.material_number.value,
                quantity=item.quantity.value,
                unit=item.quantity.unit_of_measure,
                delivery_date=dto.delivery_date,
                plant=dto.plant,
                description=item.description,
            )
        )
    return CreatePRRequest(
        document_type=dto.document_type,
        line_items=line_items,
        header_text=dto.header_text,
    )
