"""Application services for vehicle handovers."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from apps.handover.application.dto.handover_dto import (
    ConfirmVehicleHandoverDTO,
    VehicleHandoverResponseDTO,
)
from apps.handover.domain.entities import VehicleHandover, VehicleHandoverStatus
from apps.handover.domain.interfaces.handover_repository import (
    IVehicleHandoverRepository,
)
from apps.repair.application.services._timeline_helper import (
    record_repair_timeline_event,
)
from apps.repair.application.services.repair_order_timeline_service import (
    RecordRepairOrderEventService,
)
from apps.repair.domain.entities import (
    RepairOrder,
    RepairOrderEventType,
    RepairOrderStatus,
    WorkshopType,
)
from apps.repair.domain.interfaces.external_invoice_repository import (
    IExternalRepairInvoiceRepository,
)
from apps.repair.domain.interfaces.repair_repository import IRepairOrderRepository
from apps.vehicle.domain.interfaces.vehicle_repository import IVehicleRepository
from core.exceptions.translation import load_or_not_found
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger("handover", __name__)


def _to_dto(handover: VehicleHandover) -> VehicleHandoverResponseDTO:
    """Map aggregate to response DTO."""
    return VehicleHandoverResponseDTO(
        id=handover.id,
        repair_order_id=handover.repair_order_id,
        vehicle_id=handover.vehicle_id,
        status=handover.status,
        created_at=handover.created_at,
        updated_at=handover.updated_at,
        comment=handover.comment,
        driver_id=handover.driver_id,
        confirmed_at=handover.confirmed_at,
    )


class CreateVehicleHandoverService:
    """Create handover record after technical completion."""

    def __init__(self, handover_repository: IVehicleHandoverRepository) -> None:
        self._repo = handover_repository

    def execute(self, *, repair_order_id: uuid.UUID, vehicle_id: uuid.UUID) -> None:
        """Create handover when absent for repair order."""
        existing = self._repo.get_by_repair_order(repair_order_id)
        if existing is not None:
            return
        now = datetime.now(tz=UTC)
        self._repo.save(
            VehicleHandover(
                id=uuid.uuid4(),
                repair_order_id=repair_order_id,
                vehicle_id=vehicle_id,
                status=VehicleHandoverStatus.WAITING_DRIVER_CONFIRMATION,
                created_at=now,
                updated_at=now,
            )
        )


class ListVehicleHandoversService:
    """List handovers."""

    def __init__(self, handover_repository: IVehicleHandoverRepository) -> None:
        self._repo = handover_repository

    def execute(self) -> list[VehicleHandoverResponseDTO]:
        """List all handovers."""
        return [_to_dto(item) for item in self._repo.list_all()]


class ConfirmVehicleHandoverService:
    """Confirm handover and update repair/vehicle states."""

    def __init__(
        self,
        handover_repository: IVehicleHandoverRepository,
        repair_order_repository: IRepairOrderRepository,
        vehicle_repository: IVehicleRepository,
        event_recorder: RecordRepairOrderEventService | None = None,
        invoice_repository: IExternalRepairInvoiceRepository | None = None,
    ) -> None:
        self._handover_repo = handover_repository
        self._repair_repo = repair_order_repository
        self._vehicle_repo = vehicle_repository
        self._event_recorder = event_recorder
        # Kept for DI compatibility; invoices are uploaded by transport later.
        self._invoice_repo = invoice_repository

    def execute(self, dto: ConfirmVehicleHandoverDTO) -> VehicleHandoverResponseDTO:
        """Confirm handover and apply driver decision.

        On accept, the repair moves to transport final approval. External
        workshop invoices are uploaded later by transport (not by the driver).

        On reject, opens a new RepairOrder for the same vehicle/fault without
        creating a duplicate Fault. The vehicle remains unavailable.
        """
        handover = load_or_not_found(
            lambda: self._handover_repo.get_by_id(dto.handover_id),
            message=f"Vehicle handover '{dto.handover_id}' not found.",
            details={"handover_id": str(dto.handover_id)},
        )
        repair_order = load_or_not_found(
            lambda: self._repair_repo.get_by_id(handover.repair_order_id),
            message=f"Repair order '{handover.repair_order_id}' not found.",
            details={"repair_order_id": str(handover.repair_order_id)},
        )

        handover.confirm(
            dto.accepted,
            dto.comment,
            confirmed_at=datetime.now(tz=UTC),
            driver_id=dto.confirmed_by,
        )
        handover.updated_at = datetime.now(tz=UTC)
        saved_handover = self._handover_repo.save(handover)

        repair_order.confirm_handover(dto.accepted)
        repair_order.updated_at = datetime.now(tz=UTC)
        self._repair_repo.save(repair_order)

        if dto.accepted:
            record_repair_timeline_event(
                self._event_recorder,
                repair_order.id,
                RepairOrderEventType.DRIVER_ACCEPTED,
                "تحویل خودرو توسط راننده تایید شد.",
                created_by_id=dto.confirmed_by,
                request_id=dto.request_id,
            )
            waiting_message = "در انتظار تایید نهایی واحد ترابری."
            if repair_order.workshop_type == WorkshopType.EXTERNAL:
                waiting_message = (
                    "در انتظار تایید نهایی واحد ترابری و آپلود فاکتور تعمیرگاه بیرونی."
                )
            record_repair_timeline_event(
                self._event_recorder,
                repair_order.id,
                RepairOrderEventType.WAITING_TRANSPORT_FINAL_APPROVAL,
                waiting_message,
                created_by_id=dto.confirmed_by,
                request_id=dto.request_id,
            )
        else:
            now = datetime.now(tz=UTC)
            follow_up = RepairOrder(
                id=uuid.uuid4(),
                vehicle_id=repair_order.vehicle_id,
                fault_id=repair_order.fault_id,
                status=RepairOrderStatus.CREATED,
                created_by_id=dto.confirmed_by or repair_order.created_by_id,
                created_at=now,
                updated_at=now,
            )
            self._repair_repo.save(follow_up)
            record_repair_timeline_event(
                self._event_recorder,
                repair_order.id,
                RepairOrderEventType.DRIVER_REJECTED,
                "تحویل خودرو توسط راننده رد شد؛ درخواست تعمیر جدید ثبت شد.",
                created_by_id=dto.confirmed_by,
                request_id=dto.request_id,
            )
            logger.info(
                "Created follow-up repair order after driver rejection",
                extra={
                    "domain": "handover",
                    "service": "ConfirmVehicleHandoverService",
                    "operation": "execute",
                    "request_id": dto.request_id,
                    "entity_id": str(follow_up.id),
                    "rejected_repair_order_id": str(repair_order.id),
                    "vehicle_id": str(repair_order.vehicle_id),
                },
            )
        return _to_dto(saved_handover)
