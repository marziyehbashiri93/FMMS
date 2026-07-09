"""Service that syncs a repair order to SAP as a PM Order.

Architecture::

    SyncRepairToSAPService
            |
    ISAPTransactionManager
            |
    ISAPPMOrderPort
            |
    SAP Adapter (wired at composition root)

``SAPTransaction`` lifecycle is owned exclusively by ``ISAPTransactionManager``.
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
from apps.repair.application.dto.repair_dto import (
    RepairOrderResponseDTO,
    SyncRepairToSAPDTO,
)
from apps.repair.application.services.create_repair_order_service import (
    _to_response_dto,
)
from apps.repair.domain.interfaces.repair_repository import IRepairOrderRepository
from apps.vehicle.domain.interfaces.vehicle_repository import IVehicleRepository
from core.exceptions.base_exception import FMMSConflictError, FMMSIntegrationError
from core.exceptions.translation import load_or_not_found
from core.logging.structured_logger import get_structured_logger
from core.sap.dtos.pm_order import CreatePMOrderRequest
from core.sap.ports.pm_order_port import ISAPPMOrderPort
from core.sap.ports.sap_transaction_manager_port import ISAPTransactionManager

logger = get_structured_logger("repair", __name__)


class SyncRepairToSAPService:
    """Orchestrates creation of a SAP PM Order for a repair order.

    Args:
        repair_order_repository: Concrete ``IRepairOrderRepository``.
        vehicle_repository: Concrete ``IVehicleRepository`` for equipment number.
        sap_transaction_manager: ``ISAPTransactionManager`` write gateway.
        sap_pm_order_port: Abstract ``ISAPPMOrderPort`` (never a concrete adapter).
    """

    def __init__(
        self,
        repair_order_repository: IRepairOrderRepository,
        vehicle_repository: IVehicleRepository,
        sap_transaction_manager: ISAPTransactionManager,
        sap_pm_order_port: ISAPPMOrderPort,
    ) -> None:
        self._repair_repo = repair_order_repository
        self._vehicle_repo = vehicle_repository
        self._tx_manager = sap_transaction_manager
        self._sap = sap_pm_order_port

    def execute(self, dto: SyncRepairToSAPDTO) -> RepairOrderResponseDTO:
        """Create a SAP PM Order and link the document number to the repair order.

        Args:
            dto: Sync request.

        Returns:
            ``RepairOrderResponseDTO`` with ``sap_order_number`` populated.

        Raises:
            FMMSNotFoundError: If repair order or vehicle does not exist.
            FMMSConflictError: If equipment is missing, already synced, or
                an in-flight/exhausted SAP transaction blocks the write.
            FMMSIntegrationError: If the SAP write fails.
        """
        logger.info(
            "Syncing repair order to SAP",
            extra={
                "domain": "repair",
                "service": "SyncRepairToSAPService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(dto.repair_order_id),
            },
        )

        order = load_or_not_found(
            lambda: self._repair_repo.get_by_id(dto.repair_order_id),
            message=f"Repair order '{dto.repair_order_id}' not found.",
            details={"repair_order_id": str(dto.repair_order_id)},
        )

        if order.sap_order_number:
            raise FMMSConflictError(
                message=(
                    f"Repair order '{dto.repair_order_id}' is already linked to "
                    f"SAP order '{order.sap_order_number}'."
                ),
                details={
                    "repair_order_id": str(dto.repair_order_id),
                    "sap_order_number": order.sap_order_number,
                },
            )

        vehicle = load_or_not_found(
            lambda: self._vehicle_repo.get_by_id(order.vehicle_id),
            message=f"Vehicle '{order.vehicle_id}' not found.",
            details={"vehicle_id": str(order.vehicle_id)},
        )

        if vehicle.sap_equipment_number is None:
            raise FMMSConflictError(
                message=(
                    f"Vehicle '{order.vehicle_id}' has no SAP equipment number; "
                    "cannot create PM Order."
                ),
                details={"vehicle_id": str(order.vehicle_id)},
            )

        create_request = CreatePMOrderRequest(
            equipment_number=vehicle.sap_equipment_number.value,
            order_type=dto.order_type,
            description=dto.description,
            planned_start=dto.planned_start,
            plant=dto.plant,
            work_center=dto.work_center,
        )
        request_payload: dict[str, Any] = {
            "repair_order_id": str(order.id),
            "equipment_number": create_request.equipment_number,
            "order_type": create_request.order_type,
            "description": create_request.description,
            "planned_start": create_request.planned_start.isoformat(),
            "plant": create_request.plant,
            "work_center": create_request.work_center,
        }
        idempotency_key = f"repair-pm-order:{order.id}"

        def adapter_call(payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
            """Invoke the PM order port and normalize the gateway response."""
            del payload
            try:
                sap_response = self._sap.create_pm_order(create_request)
            except SAPIntegrationError:
                raise
            except Exception as exc:
                raise SAPIntegrationError(str(exc)) from exc
            return (
                {"order_number": sap_response.order_number},
                sap_response.order_number,
            )

        try:
            _response_payload, sap_doc_number = self._tx_manager.execute(
                object_type=SAPObjectType.REPAIR_ORDER,
                object_id=order.id,
                idempotency_key=idempotency_key,
                request_payload=request_payload,
                adapter_call=adapter_call,
            )
        except SAPIdempotencyError as exc:
            raise FMMSConflictError(
                message=(
                    f"SAP sync for repair order '{order.id}' is already in progress "
                    f"(transaction '{exc.existing_transaction_id}')."
                ),
                details={
                    "repair_order_id": str(order.id),
                    "sap_transaction_id": str(exc.existing_transaction_id),
                },
            ) from exc
        except SAPRetryExhaustedError as exc:
            raise FMMSConflictError(
                message=(
                    f"SAP sync for repair order '{order.id}' is exhausted; "
                    "manual intervention required."
                ),
                details={
                    "repair_order_id": str(order.id),
                    "sap_transaction_id": str(exc.transaction_id),
                },
            ) from exc
        except SAPIntegrationError as exc:
            raise FMMSIntegrationError(
                message=f"SAP PM Order creation failed: {exc}",
                details={
                    "repair_order_id": str(order.id),
                    "idempotency_key": idempotency_key,
                },
            ) from exc

        if not sap_doc_number:
            raise FMMSIntegrationError(
                message="SAP PM Order creation returned an empty document number.",
                details={"repair_order_id": str(order.id)},
            )

        order.link_sap_order(sap_doc_number)
        order.updated_at = datetime.now(tz=UTC)
        saved = self._repair_repo.save(order)

        logger.info(
            "Repair order synced to SAP successfully",
            extra={
                "domain": "repair",
                "service": "SyncRepairToSAPService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(saved.id),
                "result": "success",
                "sap_order_number": sap_doc_number,
            },
        )

        return _to_response_dto(saved)
