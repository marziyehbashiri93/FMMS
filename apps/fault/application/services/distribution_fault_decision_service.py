"""Distribution-unit decision service for reported faults."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from apps.fault.application.dto.fault_dto import (
    CloseFaultDTO,
    DistributionFaultDecisionDTO,
    FaultResponseDTO,
)
from apps.fault.application.services.close_fault_service import CloseFaultService
from apps.fault.application.services.report_fault_service import _to_response_dto
from apps.fault.domain.entities import FaultStatus
from apps.fault.domain.interfaces.fault_repository import IFaultRepository
from apps.integration.domain.entities import SAPObjectType
from apps.integration.domain.exceptions import SAPIntegrationError
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
)
from apps.repair.domain.interfaces.repair_repository import IRepairOrderRepository
from apps.vehicle.domain.entities import VehicleStatus
from apps.vehicle.domain.interfaces.vehicle_repository import IVehicleRepository
from core.exceptions.base_exception import FMMSStateError
from core.exceptions.translation import load_or_not_found
from core.logging.structured_logger import get_structured_logger
from core.sap.dtos.vehicle_assignment import RequestReplacementVehicleAssignmentRequest
from core.sap.ports.sap_transaction_manager_port import ISAPTransactionManager
from core.sap.ports.vehicle_assignment_port import ISAPVehicleAssignmentPort

logger = get_structured_logger("fault", __name__)


class DistributionFaultDecisionService:
    """Apply distribution unit usable/unusable decisions for a fault."""

    def __init__(
        self,
        fault_repository: IFaultRepository,
        vehicle_repository: IVehicleRepository,
        repair_order_repository: IRepairOrderRepository,
        event_recorder: RecordRepairOrderEventService | None = None,
        sap_transaction_manager: ISAPTransactionManager | None = None,
        sap_vehicle_assignment_port: ISAPVehicleAssignmentPort | None = None,
    ) -> None:
        self._fault_repo = fault_repository
        self._vehicle_repo = vehicle_repository
        self._repair_repo = repair_order_repository
        self._event_recorder = event_recorder
        self._sap_tx = sap_transaction_manager
        self._sap_vehicle_assignment = sap_vehicle_assignment_port

    def mark_usable(self, dto: DistributionFaultDecisionDTO) -> FaultResponseDTO:
        """Reject the reported fault and return the vehicle to active use."""
        close_service = CloseFaultService(
            self._fault_repo,
            self._repair_repo,
            self._event_recorder,
        )
        result = close_service.execute(
            CloseFaultDTO(
                fault_id=dto.fault_id,
                request_id=dto.request_id,
                closed_by=dto.decided_by,
            )
        )
        fault = load_or_not_found(
            lambda: self._fault_repo.get_by_id(dto.fault_id),
            message=f"Fault '{dto.fault_id}' not found.",
            details={"fault_id": str(dto.fault_id)},
        )
        if dto.note:
            fault.distribution_decision_note = dto.note
            fault.updated_at = datetime.now(tz=UTC)
            fault = self._fault_repo.save(fault)
        vehicle = load_or_not_found(
            lambda: self._vehicle_repo.get_by_id(fault.vehicle_id),
            message=f"Vehicle '{fault.vehicle_id}' not found.",
            details={"vehicle_id": str(fault.vehicle_id)},
        )
        if vehicle.status != VehicleStatus.ACTIVE:
            vehicle.transition_to(VehicleStatus.ACTIVE)
            vehicle.updated_at = datetime.now(tz=UTC)
            self._vehicle_repo.save(vehicle)
        logger.info(
            "Distribution marked fault vehicle as usable",
            extra={
                "domain": "fault",
                "fault_id": str(dto.fault_id),
                "vehicle_id": str(vehicle.id),
                "request_id": dto.request_id,
            },
        )
        return result

    def mark_unusable(self, dto: DistributionFaultDecisionDTO) -> FaultResponseDTO:
        """Approve the fault as making the vehicle unavailable.

        Moves the fault out of ``OPEN`` (awaiting distribution) into
        ``AWAITING_TRANSPORT`` so the queue no longer treats it as pending.
        """
        fault = load_or_not_found(
            lambda: self._fault_repo.get_by_id(dto.fault_id),
            message=f"Fault '{dto.fault_id}' not found.",
            details={"fault_id": str(dto.fault_id)},
        )
        if fault.status != FaultStatus.OPEN:
            raise FMMSStateError(
                message="Distribution decision is only allowed for open faults.",
                error_code="FAULT_NOT_AWAITING_DISTRIBUTION",
                details={
                    "fault_id": str(dto.fault_id),
                    "status": fault.status.value,
                },
            )

        vehicle = load_or_not_found(
            lambda: self._vehicle_repo.get_by_id(fault.vehicle_id),
            message=f"Vehicle '{fault.vehicle_id}' not found.",
            details={"vehicle_id": str(fault.vehicle_id)},
        )
        now = datetime.now(tz=UTC)
        if vehicle.status != VehicleStatus.OUT_OF_SERVICE:
            vehicle.transition_to(VehicleStatus.OUT_OF_SERVICE)
            vehicle.updated_at = now
            self._vehicle_repo.save(vehicle)

        fault.mark_awaiting_transport()
        if dto.note:
            fault.distribution_decision_note = dto.note
        fault.updated_at = now
        fault = self._fault_repo.save(fault)
        repair = self._ensure_repair_order_for_transport_queue(
            fault_id=fault.id,
            vehicle_id=fault.vehicle_id,
            created_by=dto.decided_by,
            now=now,
            request_id=dto.request_id,
        )

        self._request_replacement_assignment(
            dto=dto,
            vehicle_number=vehicle.vehicle_number.value,
            driver_customer_number=vehicle.driver1_customer_number or "",
            reason=dto.note or fault.description.value,
        )
        logger.info(
            "Distribution marked fault vehicle as unusable",
            extra={
                "domain": "fault",
                "fault_id": str(dto.fault_id),
                "vehicle_id": str(vehicle.id),
                "request_id": dto.request_id,
                "fault_status": fault.status.value,
                "repair_order_id": str(repair.id),
            },
        )
        return _to_response_dto(fault)

    def _ensure_repair_order_for_transport_queue(
        self,
        *,
        fault_id: uuid.UUID,
        vehicle_id: uuid.UUID,
        created_by: uuid.UUID,
        now: datetime,
        request_id: str,
    ) -> RepairOrder:
        """Create the transport queue repair order when one does not exist."""
        existing = [
            order
            for order in self._repair_repo.list_by_fault(fault_id)
            if order.status
            not in {
                RepairOrderStatus.COMPLETED,
                RepairOrderStatus.CANCELLED,
                RepairOrderStatus.REJECTED_BY_TRANSPORT,
                RepairOrderStatus.REJECTED_BY_DRIVER,
            }
        ]
        if existing:
            return existing[0]

        repair = RepairOrder(
            id=uuid.uuid4(),
            vehicle_id=vehicle_id,
            fault_id=fault_id,
            status=RepairOrderStatus.CREATED,
            created_by_id=created_by,
            created_at=now,
            updated_at=now,
        )
        saved = self._repair_repo.save(repair)
        record_repair_timeline_event(
            self._event_recorder,
            saved.id,
            RepairOrderEventType.DISTRIBUTION_APPROVED,
            "توزیع خرابی را تأیید کرد و درخواست وارد صف ترابری شد.",
            created_by_id=created_by,
            request_id=request_id,
        )
        return saved

    def _request_replacement_assignment(
        self,
        *,
        dto: DistributionFaultDecisionDTO,
        vehicle_number: str,
        driver_customer_number: str,
        reason: str,
    ) -> None:
        """Send a replacement assignment request to SAP when configured."""
        if (
            self._sap_tx is None
            or self._sap_vehicle_assignment is None
            or not driver_customer_number
        ):
            return

        requested_at = datetime.now(tz=UTC)
        request = RequestReplacementVehicleAssignmentRequest(
            driver_customer_number=driver_customer_number,
            unavailable_vehicle_number=vehicle_number,
            fault_id=str(dto.fault_id),
            requested_at=requested_at,
            reason=reason,
        )
        payload: dict[str, Any] = {
            "fault_id": str(dto.fault_id),
            "driver_customer_number": request.driver_customer_number,
            "unavailable_vehicle_number": request.unavailable_vehicle_number,
            "requested_at": request.requested_at.isoformat(),
            "reason": request.reason,
            "request_id": dto.request_id,
        }

        def adapter_call(_: dict[str, Any]) -> tuple[dict[str, Any], str]:
            response = self._sap_vehicle_assignment.request_replacement_assignment(
                request
            )
            return (
                {
                    "assignment_request_number": response.assignment_request_number,
                    "driver_customer_number": response.driver_customer_number,
                    "unavailable_vehicle_number": response.unavailable_vehicle_number,
                },
                response.assignment_request_number,
            )

        try:
            self._sap_tx.execute(
                object_type=SAPObjectType.VEHICLE_ASSIGNMENT,
                object_id=dto.fault_id,
                idempotency_key=f"fault-replacement-assignment:{dto.fault_id}",
                request_payload=payload,
                adapter_call=adapter_call,
            )
        except SAPIntegrationError as exc:
            logger.error(
                "SAP replacement vehicle assignment request failed",
                extra={
                    "domain": "fault",
                    "fault_id": str(dto.fault_id),
                    "request_id": dto.request_id,
                    "error": str(exc),
                },
            )
