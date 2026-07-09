"""Service that submits a Purchase Requisition to SAP.

Architecture::

    SubmitPRToSAPService
            |
    ISAPTransactionManager
            |
    ISAPPurchaseRequisitionPort
            |
    SAP Adapter (wired at composition root)

The service owns procurement workflow only. ``SAPTransaction`` lifecycle,
idempotency, and retry are owned exclusively by ``ISAPTransactionManager``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from apps.integration.domain.entities import SAPObjectType
from apps.integration.domain.exceptions import (
    SAPIdempotencyError,
    SAPIntegrationError,
    SAPRetryExhaustedError,
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
    FMMSValidationError,
)
from core.exceptions.translation import load_or_not_found
from core.logging.structured_logger import get_structured_logger
from core.sap.dtos.purchase_requisition import CreatePRRequest, PRLineItemRequest
from core.sap.ports.purchase_requisition_port import ISAPPurchaseRequisitionPort
from core.sap.ports.sap_transaction_manager_port import ISAPTransactionManager

logger = get_structured_logger("procurement", __name__)


class SubmitPRToSAPService:
    """Submit a PR to SAP through the SAP write gateway.

    Args:
        pr_repository: Concrete ``IPurchaseRequisitionRepository``.
        sap_transaction_manager: ``ISAPTransactionManager`` write gateway.
        sap_pr_port: Abstract ``ISAPPurchaseRequisitionPort`` only.
    """

    def __init__(
        self,
        pr_repository: IPurchaseRequisitionRepository,
        sap_transaction_manager: ISAPTransactionManager,
        sap_pr_port: ISAPPurchaseRequisitionPort,
    ) -> None:
        self._pr_repo = pr_repository
        self._tx_manager = sap_transaction_manager
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
            FMMSConflictError: If an in-flight or exhausted transaction blocks submit.
            FMMSIntegrationError: If the SAP write fails.
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

        pr = load_or_not_found(
            lambda: self._pr_repo.get_by_id(dto.pr_id),
            message=f"Purchase requisition '{dto.pr_id}' not found.",
            details={"pr_id": str(dto.pr_id)},
        )

        if not pr.line_items:
            raise FMMSValidationError(
                message="Cannot submit a PR with no line items.",
                details={"pr_id": str(dto.pr_id)},
            )

        idempotency_key = dto.idempotency_key or f"pr-submit:{dto.pr_id}"
        request_payload = _build_request_payload(pr, dto)
        create_request = _to_create_pr_request(pr, dto)

        def adapter_call(payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
            """Invoke the PR port and normalize the gateway response tuple."""
            del payload  # audit payload already stored by the manager
            try:
                sap_response = self._sap.create_purchase_requisition(create_request)
            except SAPIntegrationError:
                raise
            except Exception as exc:
                raise SAPIntegrationError(str(exc)) from exc
            response_payload: dict[str, Any] = {
                "pr_number": sap_response.pr_number,
                "line_item_count": len(sap_response.line_items),
                "created_at": str(sap_response.created_at),
            }
            return response_payload, sap_response.pr_number

        try:
            response_payload, sap_doc_number = self._tx_manager.execute(
                object_type=SAPObjectType.PURCHASE_REQUISITION,
                object_id=pr.id,
                idempotency_key=idempotency_key,
                request_payload=request_payload,
                adapter_call=adapter_call,
            )
        except SAPIdempotencyError as exc:
            raise FMMSConflictError(
                message=(
                    f"SAP submission for PR '{dto.pr_id}' is already in progress "
                    f"(transaction '{exc.existing_transaction_id}')."
                ),
                details={
                    "pr_id": str(dto.pr_id),
                    "sap_transaction_id": str(exc.existing_transaction_id),
                    "idempotency_key": idempotency_key,
                },
            ) from exc
        except SAPRetryExhaustedError as exc:
            raise FMMSConflictError(
                message=(
                    f"SAP submission for PR '{dto.pr_id}' is exhausted; "
                    "manual intervention required."
                ),
                details={
                    "pr_id": str(dto.pr_id),
                    "sap_transaction_id": str(exc.transaction_id),
                },
            ) from exc
        except SAPIntegrationError as exc:
            raise FMMSIntegrationError(
                message=f"SAP PR submission failed: {exc}",
                details={
                    "pr_id": str(pr.id),
                    "idempotency_key": idempotency_key,
                },
            ) from exc

        if not sap_doc_number:
            raise FMMSIntegrationError(
                message="SAP PR submission returned an empty document number.",
                details={"pr_id": str(pr.id), "idempotency_key": idempotency_key},
            )

        completed_at = datetime.now(tz=UTC)
        pr.link_sap_pr(SAPDocumentNumber(sap_doc_number))
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
                "sap_pr_number": sap_doc_number,
                "response_keys": list(response_payload.keys()),
            },
        )
        return _pr_to_response_dto(saved)


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
