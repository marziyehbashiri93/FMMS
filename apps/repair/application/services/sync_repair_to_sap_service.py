"""Service that syncs a repair order to SAP as a PM Order.

SAP dependency rule (M6):
- Depends only on ``ISAPPMOrderPort`` from ``core/sap/ports/``.
- Never imports ``infrastructure.sap``, adapters, or ``SAPTransactionManager``.
- Idempotency / transaction wrapping is applied at the composition root
  when the concrete port is wired.

Workflow:
1. Load repair order and linked vehicle.
2. Require vehicle to have an SAP equipment number.
3. Call ``ISAPPMOrderPort.create_pm_order``.
4. Store the returned SAP order number on the domain entity.
5. Persist the updated repair order.
"""

from __future__ import annotations

from datetime import UTC, datetime

from apps.repair.application.dto.repair_dto import (
    RepairOrderResponseDTO,
    SyncRepairToSAPDTO,
)
from apps.repair.application.services.create_repair_order_service import (
    _to_response_dto,
)
from apps.repair.domain.interfaces.repair_repository import IRepairOrderRepository
from apps.vehicle.domain.interfaces.vehicle_repository import IVehicleRepository
from core.exceptions.base_exception import FMMSConflictError, FMMSNotFoundError
from core.logging.structured_logger import get_structured_logger
from core.sap.dtos.pm_order import CreatePMOrderRequest
from core.sap.ports.pm_order_port import ISAPPMOrderPort

logger = get_structured_logger("repair", __name__)


class SyncRepairToSAPService:
    """Orchestrates creation of a SAP PM Order for a repair order.

    Args:
        repair_order_repository: Concrete ``IRepairOrderRepository``.
        vehicle_repository: Concrete ``IVehicleRepository`` for equipment number.
        sap_pm_order_port: Abstract ``ISAPPMOrderPort`` (never a concrete adapter).
    """

    def __init__(
        self,
        repair_order_repository: IRepairOrderRepository,
        vehicle_repository: IVehicleRepository,
        sap_pm_order_port: ISAPPMOrderPort,
    ) -> None:
        self._repair_repo = repair_order_repository
        self._vehicle_repo = vehicle_repository
        self._sap = sap_pm_order_port

    def execute(self, dto: SyncRepairToSAPDTO) -> RepairOrderResponseDTO:
        """Create a SAP PM Order and link the document number to the repair order.

        Args:
            dto: Sync request.

        Returns:
            ``RepairOrderResponseDTO`` with ``sap_order_number`` populated.

        Raises:
            FMMSNotFoundError: If repair order or vehicle does not exist.
            FMMSConflictError: If the vehicle has no SAP equipment number, or
                the repair order is already linked to a SAP order.
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

        order = self._repair_repo.get_by_id(dto.repair_order_id)
        if order is None:
            raise FMMSNotFoundError(
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

        vehicle = self._vehicle_repo.get_by_id(order.vehicle_id)
        if vehicle is None:
            raise FMMSNotFoundError(
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

        sap_response = self._sap.create_pm_order(
            CreatePMOrderRequest(
                equipment_number=vehicle.sap_equipment_number.value,
                order_type=dto.order_type,
                description=dto.description,
                planned_start=dto.planned_start,
                plant=dto.plant,
                work_center=dto.work_center,
            )
        )

        order.link_sap_order(sap_response.order_number)
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
                "sap_order_number": sap_response.order_number,
            },
        )

        return _to_response_dto(saved)
