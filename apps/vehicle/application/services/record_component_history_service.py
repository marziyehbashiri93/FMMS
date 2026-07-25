"""Record vehicle component history from consumed repair parts."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from apps.repair.domain.entities import RepairOrder, RepairPart
from apps.vehicle.domain.component_history_entities import (
    ComponentType,
    VehicleComponentHistory,
)
from apps.vehicle.domain.interfaces.component_history_repository import (
    IVehicleComponentHistoryRepository,
)
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger("vehicle", __name__)


@dataclass(frozen=True)
class VehicleComponentHistoryResponseDTO:
    """Output DTO for one component history row."""

    id: uuid.UUID
    vehicle_id: uuid.UUID
    repair_order_id: uuid.UUID
    component_type: str
    material_number: str
    quantity: Decimal
    unit_of_measure: str
    description: str
    installed_at: datetime
    recorded_by_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


def _infer_component_type(material_number: str, description: str = "") -> ComponentType:
    """Best-effort component classification from material text."""
    text = f"{material_number} {description}".lower()
    if any(token in text for token in ("battery", "باتری")):
        return ComponentType.BATTERY
    if any(token in text for token in ("tire", "tyre", "لاستیک")):
        return ComponentType.TIRE
    if any(token in text for token in ("brake", "لنت", "ترمز")):
        return ComponentType.BRAKE_PAD
    if any(token in text for token in ("alternator", "دینام")):
        return ComponentType.ALTERNATOR
    if any(token in text for token in ("engine", "موتور")):
        return ComponentType.ENGINE
    return ComponentType.OTHER


class RecordComponentHistoryFromRepairService:
    """Copy consumed repair parts into vehicle component history."""

    def __init__(self, history_repository: IVehicleComponentHistoryRepository) -> None:
        self._repo = history_repository

    def execute(
        self,
        *,
        order: RepairOrder,
        recorded_by: uuid.UUID,
        request_id: str = "",
    ) -> list[VehicleComponentHistoryResponseDTO]:
        """Persist one history row per consumed part on the repair order."""
        existing = {
            (row.material_number, str(row.quantity), row.unit_of_measure)
            for row in self._repo.list_by_repair_order(order.id)
        }
        now = datetime.now(tz=UTC)
        created: list[VehicleComponentHistoryResponseDTO] = []
        for part in order.parts:
            key = (
                part.part_quantity.material_number,
                str(part.part_quantity.quantity),
                part.part_quantity.unit_of_measure,
            )
            if key in existing:
                continue
            entry = self._from_part(order=order, part=part, recorded_by=recorded_by, now=now)
            saved = self._repo.save(entry)
            created.append(
                VehicleComponentHistoryResponseDTO(
                    id=saved.id,
                    vehicle_id=saved.vehicle_id,
                    repair_order_id=saved.repair_order_id,
                    component_type=saved.component_type.value,
                    material_number=saved.material_number,
                    quantity=saved.quantity,
                    unit_of_measure=saved.unit_of_measure,
                    description=saved.description,
                    installed_at=saved.installed_at,
                    recorded_by_id=saved.recorded_by_id,
                    created_at=saved.created_at,
                    updated_at=saved.updated_at,
                )
            )
        logger.info(
            "Recorded vehicle component history from repair",
            extra={
                "domain": "vehicle",
                "service": "RecordComponentHistoryFromRepairService",
                "repair_order_id": str(order.id),
                "vehicle_id": str(order.vehicle_id),
                "request_id": request_id,
                "created_count": len(created),
            },
        )
        return created

    @staticmethod
    def _from_part(
        *,
        order: RepairOrder,
        part: RepairPart,
        recorded_by: uuid.UUID,
        now: datetime,
    ) -> VehicleComponentHistory:
        """Build a history entity from one consumed part."""
        material = part.part_quantity.material_number
        return VehicleComponentHistory(
            id=uuid.uuid4(),
            vehicle_id=order.vehicle_id,
            repair_order_id=order.id,
            component_type=_infer_component_type(material),
            material_number=material,
            quantity=part.part_quantity.quantity,
            unit_of_measure=part.part_quantity.unit_of_measure,
            description=f"Consumed during repair {order.id}",
            installed_at=order.completed_at or now,
            recorded_by_id=recorded_by,
            created_at=now,
            updated_at=now,
        )


class ListVehicleComponentHistoryService:
    """List component history for a vehicle."""

    def __init__(self, history_repository: IVehicleComponentHistoryRepository) -> None:
        self._repo = history_repository

    def execute(
        self, vehicle_id: uuid.UUID
    ) -> list[VehicleComponentHistoryResponseDTO]:
        """Return component history rows for ``vehicle_id``."""
        return [
            VehicleComponentHistoryResponseDTO(
                id=row.id,
                vehicle_id=row.vehicle_id,
                repair_order_id=row.repair_order_id,
                component_type=row.component_type.value,
                material_number=row.material_number,
                quantity=row.quantity,
                unit_of_measure=row.unit_of_measure,
                description=row.description,
                installed_at=row.installed_at,
                recorded_by_id=row.recorded_by_id,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in self._repo.list_by_vehicle(vehicle_id)
        ]
