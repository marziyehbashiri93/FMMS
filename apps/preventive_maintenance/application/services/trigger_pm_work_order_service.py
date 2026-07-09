"""Service that triggers a PM work order from an active plan.

Architecture for optional SAP write::

    TriggerPMWorkOrderService
            |
    ISAPTransactionManager
            |
    ISAPPMNotificationPort
            |
    SAP Adapter (wired at composition root)

Workflow:
1. Load plan — must be ACTIVE.
2. Ensure no non-terminal work order already exists for the plan.
3. Create a SCHEDULED work order, then call ``PMWorkOrder.trigger()``.
4. Record the trigger on the plan via ``PMPlan.record_trigger()``.
5. Optionally create a SAP PM notification through ``ISAPTransactionManager``.
6. Persist plan and work order.

No Celery tasks, schedulers, or background workers are created here.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from apps.integration.domain.entities import SAPObjectType
from apps.integration.domain.exceptions import (
    SAPIdempotencyError,
    SAPIntegrationError,
    SAPRetryExhaustedError,
)
from apps.preventive_maintenance.application.dto.pm_dto import (
    PMWorkOrderResponseDTO,
    TriggerPMWorkOrderDTO,
)
from apps.preventive_maintenance.domain.entities import PMWorkOrder, PMWorkOrderStatus
from apps.preventive_maintenance.domain.exceptions import PMAlreadyTriggeredError
from apps.preventive_maintenance.domain.interfaces.pm_repository import (
    IPMPlanRepository,
    IPMWorkOrderRepository,
)
from apps.vehicle.domain.interfaces.vehicle_repository import IVehicleRepository
from core.exceptions.base_exception import FMMSConflictError, FMMSIntegrationError
from core.exceptions.translation import load_or_not_found
from core.logging.structured_logger import get_structured_logger
from core.sap.dtos.pm_notification import CreatePMNotificationRequest
from core.sap.ports.pm_notification_port import ISAPPMNotificationPort
from core.sap.ports.sap_transaction_manager_port import ISAPTransactionManager

logger = get_structured_logger("preventive_maintenance", __name__)

_ACTIVE_WO_STATUSES: frozenset[PMWorkOrderStatus] = frozenset(
    {
        PMWorkOrderStatus.SCHEDULED,
        PMWorkOrderStatus.TRIGGERED,
        PMWorkOrderStatus.IN_PROGRESS,
        PMWorkOrderStatus.OVERDUE,
    }
)


def _work_order_to_response_dto(
    work_order: PMWorkOrder,
    sap_notification_number: str | None = None,
) -> PMWorkOrderResponseDTO:
    """Map ``PMWorkOrder`` → ``PMWorkOrderResponseDTO``."""
    return PMWorkOrderResponseDTO(
        id=work_order.id,
        plan_id=work_order.plan_id,
        vehicle_id=work_order.vehicle_id,
        status=work_order.status,
        scheduled_date=work_order.scheduled_date,
        created_at=work_order.created_at,
        updated_at=work_order.updated_at,
        triggered_at=work_order.triggered_at,
        completed_at=work_order.completed_at,
        notes=work_order.notes,
        sap_order_number=work_order.sap_order_number,
        sap_notification_number=sap_notification_number,
    )


class TriggerPMWorkOrderService:
    """Orchestrates generation of a PM work order from an active plan.

    Args:
        pm_plan_repository: Concrete ``IPMPlanRepository``.
        pm_work_order_repository: Concrete ``IPMWorkOrderRepository``.
        vehicle_repository: Concrete ``IVehicleRepository`` (SAP equipment lookup).
        sap_transaction_manager: Write gateway required when creating SAP notifications.
        sap_pm_notification_port: Optional ``ISAPPMNotificationPort`` used only
            when ``create_sap_notification`` is True.
    """

    def __init__(
        self,
        pm_plan_repository: IPMPlanRepository,
        pm_work_order_repository: IPMWorkOrderRepository,
        vehicle_repository: IVehicleRepository,
        sap_transaction_manager: ISAPTransactionManager | None = None,
        sap_pm_notification_port: ISAPPMNotificationPort | None = None,
    ) -> None:
        self._plan_repo = pm_plan_repository
        self._wo_repo = pm_work_order_repository
        self._vehicle_repo = vehicle_repository
        self._tx_manager = sap_transaction_manager
        self._sap = sap_pm_notification_port

    def execute(self, dto: TriggerPMWorkOrderDTO) -> PMWorkOrderResponseDTO:
        """Trigger a new work order for the given plan.

        Args:
            dto: Trigger request.

        Returns:
            ``PMWorkOrderResponseDTO`` in TRIGGERED status.

        Raises:
            FMMSNotFoundError: If plan or vehicle does not exist.
            FMMSConflictError: If the plan is not ACTIVE, or SAP notification
                was requested without equipment / port / manager.
            FMMSIntegrationError: If the SAP notification write fails.
            PMAlreadyTriggeredError: If a non-terminal work order already exists.
        """
        logger.info(
            "Triggering PM work order",
            extra={
                "domain": "preventive_maintenance",
                "service": "TriggerPMWorkOrderService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(dto.plan_id),
            },
        )

        plan = load_or_not_found(
            lambda: self._plan_repo.get_by_id(dto.plan_id),
            message=f"PM plan '{dto.plan_id}' not found.",
            details={"plan_id": str(dto.plan_id)},
        )

        if not plan.is_active:
            raise FMMSConflictError(
                message=f"PM plan '{dto.plan_id}' is not ACTIVE (status={plan.status}).",
                details={"plan_id": str(dto.plan_id), "status": plan.status},
            )

        existing = self._wo_repo.list_by_plan(dto.plan_id)
        if any(wo.status in _ACTIVE_WO_STATUSES for wo in existing):
            raise PMAlreadyTriggeredError(dto.plan_id)

        now = datetime.now(tz=UTC)
        work_order = PMWorkOrder(
            id=uuid.uuid4(),
            plan_id=plan.id,
            vehicle_id=plan.vehicle_id,
            status=PMWorkOrderStatus.SCHEDULED,
            scheduled_date=dto.scheduled_date,
            created_at=now,
            updated_at=now,
            notes=dto.notes,
        )
        work_order.trigger(triggered_at=now)

        plan.record_trigger(triggered_at=now)
        plan.updated_at = now

        sap_notification_number: str | None = None
        if dto.create_sap_notification:
            sap_notification_number = self._create_sap_notification(
                work_order_id=work_order.id,
                plan_vehicle_id=plan.vehicle_id,
                plan_name=plan.name,
                dto=dto,
                now=now,
            )

        self._plan_repo.save(plan)
        saved = self._wo_repo.save(work_order)

        logger.info(
            "PM work order triggered successfully",
            extra={
                "domain": "preventive_maintenance",
                "service": "TriggerPMWorkOrderService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(saved.id),
                "result": "success",
                "sap_notification_number": sap_notification_number,
            },
        )

        return _work_order_to_response_dto(saved, sap_notification_number)

    def _create_sap_notification(
        self,
        work_order_id: uuid.UUID,
        plan_vehicle_id: uuid.UUID,
        plan_name: str,
        dto: TriggerPMWorkOrderDTO,
        now: datetime,
    ) -> str:
        """Create a SAP PM notification through the write gateway.

        Args:
            work_order_id: Newly created work order UUID (idempotency object).
            plan_vehicle_id: Vehicle linked to the plan.
            plan_name: Plan name used as fault description.
            dto: Original trigger DTO.
            now: Current UTC timestamp.

        Returns:
            SAP-assigned notification number.

        Raises:
            FMMSConflictError: If port/manager is missing or vehicle has no equipment.
            FMMSNotFoundError: If vehicle does not exist.
            FMMSIntegrationError: If the SAP write fails.
        """
        sap_port = self._sap
        tx_manager = self._tx_manager
        if sap_port is None or tx_manager is None:
            raise FMMSConflictError(
                message=(
                    "SAP PM notification requested but ISAPPMNotificationPort "
                    "and/or ISAPTransactionManager was not injected."
                ),
                details={"plan_id": str(dto.plan_id)},
            )

        vehicle = load_or_not_found(
            lambda: self._vehicle_repo.get_by_id(plan_vehicle_id),
            message=f"Vehicle '{plan_vehicle_id}' not found.",
            details={"vehicle_id": str(plan_vehicle_id)},
        )
        if vehicle.sap_equipment_number is None:
            raise FMMSConflictError(
                message=(
                    f"Vehicle '{plan_vehicle_id}' has no SAP equipment number; "
                    "cannot create PM notification."
                ),
                details={"vehicle_id": str(plan_vehicle_id)},
            )

        create_request = CreatePMNotificationRequest(
            equipment_number=vehicle.sap_equipment_number.value,
            fault_description=f"PM triggered: {plan_name}",
            defect_code=dto.defect_code,
            priority=dto.priority,
            reported_by=str(dto.triggered_by),
            reported_at=now,
        )
        request_payload: dict[str, Any] = {
            "work_order_id": str(work_order_id),
            "plan_id": str(dto.plan_id),
            "equipment_number": create_request.equipment_number,
            "fault_description": create_request.fault_description,
            "defect_code": create_request.defect_code,
            "priority": create_request.priority,
            "reported_by": create_request.reported_by,
            "reported_at": create_request.reported_at.isoformat(),
        }
        idempotency_key = f"pm-notification:{work_order_id}"

        def adapter_call(payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
            """Invoke the PM notification port and normalize the response."""
            del payload
            try:
                response = sap_port.create_notification(create_request)
            except SAPIntegrationError:
                raise
            except Exception as exc:
                raise SAPIntegrationError(str(exc)) from exc
            return (
                {"notification_number": response.notification_number},
                response.notification_number,
            )

        try:
            _response_payload, sap_doc_number = tx_manager.execute(
                object_type=SAPObjectType.PM_WORK_ORDER,
                object_id=work_order_id,
                idempotency_key=idempotency_key,
                request_payload=request_payload,
                adapter_call=adapter_call,
            )
        except SAPIdempotencyError as exc:
            raise FMMSConflictError(
                message=(
                    f"SAP notification for work order '{work_order_id}' is already "
                    f"in progress (transaction '{exc.existing_transaction_id}')."
                ),
                details={
                    "work_order_id": str(work_order_id),
                    "sap_transaction_id": str(exc.existing_transaction_id),
                },
            ) from exc
        except SAPRetryExhaustedError as exc:
            raise FMMSConflictError(
                message=(
                    f"SAP notification for work order '{work_order_id}' is exhausted; "
                    "manual intervention required."
                ),
                details={
                    "work_order_id": str(work_order_id),
                    "sap_transaction_id": str(exc.transaction_id),
                },
            ) from exc
        except SAPIntegrationError as exc:
            raise FMMSIntegrationError(
                message=f"SAP PM notification failed: {exc}",
                details={
                    "work_order_id": str(work_order_id),
                    "idempotency_key": idempotency_key,
                },
            ) from exc

        if not sap_doc_number:
            raise FMMSIntegrationError(
                message="SAP PM notification returned an empty document number.",
                details={"work_order_id": str(work_order_id)},
            )
        return sap_doc_number
