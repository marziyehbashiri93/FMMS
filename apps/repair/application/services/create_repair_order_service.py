"""Service that orchestrates creation of a new repair order.

Cross-domain checks performed here:
- Vehicle must exist (IVehicleRepository).
- Fault must exist (IFaultRepository) and belong to the same vehicle.

No state-machine logic lives here — all transitions delegate to the entity.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from apps.fault.domain.interfaces.fault_repository import IFaultRepository
from apps.repair.application.dto.repair_dto import (
    CreateRepairOrderDTO,
    RepairOrderResponseDTO,
)
from apps.repair.domain.entities import RepairOrder, RepairOrderStatus
from apps.repair.domain.interfaces.repair_repository import IRepairOrderRepository
from apps.vehicle.domain.interfaces.vehicle_repository import IVehicleRepository
from core.exceptions.base_exception import FMMSConflictError, FMMSNotFoundError
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger("repair", __name__)


def _to_response_dto(order: RepairOrder) -> RepairOrderResponseDTO:
    """Map a ``RepairOrder`` domain entity → ``RepairOrderResponseDTO``."""
    from apps.repair.application.dto.repair_dto import (  # noqa: PLC0415
        RepairActivityResponseDTO,
        RepairPartResponseDTO,
    )

    return RepairOrderResponseDTO(
        id=order.id,
        vehicle_id=order.vehicle_id,
        fault_id=order.fault_id,
        status=order.status,
        created_by_id=order.created_by_id,
        created_at=order.created_at,
        updated_at=order.updated_at,
        completed_at=order.completed_at,
        sap_order_number=order.sap_order_number,
        technician_id=order.assignment.technician_id if order.assignment else None,
        assigned_at=order.assignment.assigned_at if order.assignment else None,
        activities=[
            RepairActivityResponseDTO(
                id=a.id,
                description=a.description,
                labor_hours=a.labor_hours.hours,
                performed_by_id=a.performed_by_id,
                performed_at=a.performed_at,
                notes=a.notes,
            )
            for a in order.activities
        ],
        parts=[
            RepairPartResponseDTO(
                id=p.id,
                material_number=p.part_quantity.material_number,
                quantity=p.part_quantity.quantity,
                unit_of_measure=p.part_quantity.unit_of_measure,
                goods_issue_id=p.goods_issue_id,
                posted_at=p.posted_at,
            )
            for p in order.parts
        ],
    )


class CreateRepairOrderService:
    """Orchestrates creation of a new repair order.

    Args:
        repair_order_repository: Concrete ``IRepairOrderRepository``.
        vehicle_repository: Concrete ``IVehicleRepository`` for existence check.
        fault_repository: Concrete ``IFaultRepository`` for existence and
            vehicle-match check.
    """

    def __init__(
        self,
        repair_order_repository: IRepairOrderRepository,
        vehicle_repository: IVehicleRepository,
        fault_repository: IFaultRepository,
    ) -> None:
        self._repair_repo = repair_order_repository
        self._vehicle_repo = vehicle_repository
        self._fault_repo = fault_repository

    def execute(self, dto: CreateRepairOrderDTO) -> RepairOrderResponseDTO:
        """Create and persist a new repair order in CREATED status.

        Args:
            dto: Input data.

        Returns:
            ``RepairOrderResponseDTO`` in CREATED status.

        Raises:
            FMMSNotFoundError: If vehicle or fault does not exist.
            FMMSConflictError: If the fault belongs to a different vehicle.
        """
        logger.info(
            "Creating repair order",
            extra={
                "domain": "repair",
                "service": "CreateRepairOrderService",
                "operation": "execute",
                "request_id": dto.request_id,
                "vehicle_id": str(dto.vehicle_id),
                "fault_id": str(dto.fault_id),
            },
        )

        vehicle = self._vehicle_repo.get_by_id(dto.vehicle_id)
        if vehicle is None:
            raise FMMSNotFoundError(
                message=f"Vehicle '{dto.vehicle_id}' not found.",
                details={"vehicle_id": str(dto.vehicle_id)},
            )

        fault = self._fault_repo.get_by_id(dto.fault_id)
        if fault is None:
            raise FMMSNotFoundError(
                message=f"Fault '{dto.fault_id}' not found.",
                details={"fault_id": str(dto.fault_id)},
            )

        if fault.vehicle_id != dto.vehicle_id:
            raise FMMSConflictError(
                message=(
                    f"Fault '{dto.fault_id}' belongs to vehicle '{fault.vehicle_id}', "
                    f"not '{dto.vehicle_id}'."
                ),
                details={
                    "fault_id": str(dto.fault_id),
                    "fault_vehicle_id": str(fault.vehicle_id),
                    "requested_vehicle_id": str(dto.vehicle_id),
                },
            )

        now = datetime.now(tz=UTC)
        order = RepairOrder(
            id=uuid.uuid4(),
            vehicle_id=dto.vehicle_id,
            fault_id=dto.fault_id,
            status=RepairOrderStatus.CREATED,
            created_by_id=dto.created_by,
            created_at=now,
            updated_at=now,
        )

        saved = self._repair_repo.save(order)

        logger.info(
            "Repair order created successfully",
            extra={
                "domain": "repair",
                "service": "CreateRepairOrderService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(saved.id),
                "result": "success",
            },
        )

        return _to_response_dto(saved)
