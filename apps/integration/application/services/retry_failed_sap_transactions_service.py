"""Application service that retries failed SAP write transactions.

Delegates entirely to ``ISAPTransactionManager.retry_all_pending``.
Rebuilds adapter callables from stored request payloads so Celery tasks
never touch ORM models or contain SAP mapping business rules beyond
payload → port request reconstruction.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from apps.integration.domain.entities import SAPObjectType
from core.logging.structured_logger import get_structured_logger
from core.sap.dtos.pm_notification import CreatePMNotificationRequest
from core.sap.dtos.pm_order import CreatePMOrderRequest
from core.sap.dtos.purchase_requisition import CreatePRRequest, PRLineItemRequest
from core.sap.ports.pm_notification_port import ISAPPMNotificationPort
from core.sap.ports.pm_order_port import ISAPPMOrderPort
from core.sap.ports.purchase_requisition_port import ISAPPurchaseRequisitionPort
from core.sap.ports.sap_transaction_manager_port import (
    ISAPTransactionManager,
    SAPAdapterCallable,
)

logger = get_structured_logger("integration", __name__)


class RetryFailedSAPTransactionsService:
    """Retry eligible FAILED SAP transactions through the write gateway.

    Args:
        sap_transaction_manager: Sole SAP write gateway.
        sap_pr_port: Purchase requisition write port.
        sap_pm_order_port: PM order write port.
        sap_pm_notification_port: PM notification write port.
    """

    def __init__(
        self,
        sap_transaction_manager: ISAPTransactionManager,
        sap_pr_port: ISAPPurchaseRequisitionPort,
        sap_pm_order_port: ISAPPMOrderPort,
        sap_pm_notification_port: ISAPPMNotificationPort,
    ) -> None:
        self._manager = sap_transaction_manager
        self._pr_port = sap_pr_port
        self._pm_order_port = sap_pm_order_port
        self._pm_notification_port = sap_pm_notification_port

    def execute(self, *, request_id: str = "") -> None:
        """Retry all pending-for-retry SAP transactions.

        Args:
            request_id: Correlation id for structured logging.
        """
        logger.info(
            "Retrying failed SAP transactions",
            extra={
                "domain": "integration",
                "service": "RetryFailedSAPTransactionsService",
                "operation": "execute",
                "request_id": request_id,
            },
        )
        self._manager.retry_all_pending(self._build_adapter_call_map())
        logger.info(
            "SAP retry sweep completed",
            extra={
                "domain": "integration",
                "service": "RetryFailedSAPTransactionsService",
                "operation": "execute",
                "request_id": request_id,
                "result": "success",
            },
        )

    def _build_adapter_call_map(self) -> dict[SAPObjectType, SAPAdapterCallable]:
        """Map object types to adapter callables rebuilt from request payloads."""
        return {
            SAPObjectType.PURCHASE_REQUISITION: self._retry_purchase_requisition,
            SAPObjectType.REPAIR_ORDER: self._retry_pm_order,
            SAPObjectType.PM_WORK_ORDER: self._retry_pm_notification,
        }

    def _retry_purchase_requisition(
        self, payload: dict[str, Any]
    ) -> tuple[dict[str, Any], str]:
        """Rebuild and execute a PR create from a stored audit payload."""
        line_items: list[PRLineItemRequest] = []
        for index, item in enumerate(payload.get("line_items", []), start=1):
            line_items.append(
                PRLineItemRequest(
                    item_number=f"{index * 10:05d}",
                    material_number=str(item["material_number"]),
                    quantity=Decimal(str(item["quantity"])),
                    unit=str(item["unit"]),
                    delivery_date=date.fromisoformat(str(payload["delivery_date"])),
                    plant=str(payload["plant"]),
                    description=item.get("description"),
                )
            )
        request = CreatePRRequest(
            document_type=str(payload["document_type"]),
            line_items=line_items,
            header_text=payload.get("header_text"),
        )
        response = self._pr_port.create_purchase_requisition(request)
        return (
            {
                "pr_number": response.pr_number,
                "line_item_count": len(response.line_items),
                "created_at": str(response.created_at),
            },
            response.pr_number,
        )

    def _retry_pm_order(self, payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
        """Rebuild and execute a PM order create from a stored audit payload."""
        planned_start = datetime.fromisoformat(str(payload["planned_start"]))
        if planned_start.tzinfo is None:
            planned_start = planned_start.replace(tzinfo=UTC)
        request = CreatePMOrderRequest(
            equipment_number=str(payload["equipment_number"]),
            order_type=str(payload["order_type"]),
            description=str(payload["description"]),
            planned_start=planned_start,
            plant=payload.get("plant"),
            work_center=payload.get("work_center"),
        )
        response = self._pm_order_port.create_pm_order(request)
        return {"order_number": response.order_number}, response.order_number

    def _retry_pm_notification(
        self, payload: dict[str, Any]
    ) -> tuple[dict[str, Any], str]:
        """Rebuild and execute a PM notification create from a stored payload."""
        reported_at_raw = payload.get("reported_at")
        if reported_at_raw:
            reported_at = datetime.fromisoformat(str(reported_at_raw))
            if reported_at.tzinfo is None:
                reported_at = reported_at.replace(tzinfo=UTC)
        else:
            reported_at = datetime.now(tz=UTC)
        request = CreatePMNotificationRequest(
            equipment_number=str(payload["equipment_number"]),
            fault_description=str(
                payload.get("fault_description") or "PM notification retry"
            ),
            defect_code=str(payload.get("defect_code") or "PM-TRIG"),
            priority=str(payload.get("priority") or "3"),
            reported_by=str(payload.get("reported_by") or "system"),
            reported_at=reported_at,
        )
        response = self._pm_notification_port.create_notification(request)
        return (
            {"notification_number": response.notification_number},
            response.notification_number,
        )
