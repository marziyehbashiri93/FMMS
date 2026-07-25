"""Service for explicitly reporting a fault from a submitted checklist."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from apps.fault.application.dto.fault_dto import FaultResponseDTO
from apps.fault.application.interfaces.vehicle_odometer_reader import (
    IFaultVehicleOdometerReader,
)
from apps.fault.application.services.report_fault_service import (
    _create_sap_pm_notification,
    _to_response_dto,
    _update_sap_vehicle_measurement,
)
from apps.fault.domain.entities import Fault, FaultItem, FaultStatus
from apps.fault.domain.interfaces.fault_repository import IFaultRepository
from apps.fault.domain.value_objects import FaultCode, FaultDescription, FaultSeverity
from apps.inspection.application.dto.inspection_dto import ReportInspectionFaultDTO
from apps.inspection.domain.entities import InspectionItem, InspectionStatus
from apps.inspection.domain.interfaces.inspection_repository import (
    IInspectionRepository,
)
from apps.repair.domain.interfaces.repair_repository import IRepairOrderRepository
from apps.vehicle.domain.interfaces.vehicle_repository import IVehicleRepository
from core.exceptions.base_exception import FMMSConflictError, FMMSValidationError
from core.exceptions.translation import load_or_not_found
from core.logging.structured_logger import get_structured_logger
from core.sap.ports.measurement_document_port import ISAPMeasurementDocumentPort
from core.sap.ports.pm_notification_port import ISAPPMNotificationPort
from core.sap.ports.sap_transaction_manager_port import ISAPTransactionManager
from core.workflow import assert_vehicle_has_no_open_flow

logger = get_structured_logger("inspection", __name__)

_DEFAULT_FAULT_CODE = "INSP-FAIL"
_DEFAULT_FAULT_SEVERITY = FaultSeverity.MEDIUM
_MULTI_FAILURE_DESCRIPTION = "Multiple inspection failures"
_SEVERITY_RANK: dict[FaultSeverity, int] = {
    FaultSeverity.LOW: 0,
    FaultSeverity.MEDIUM: 1,
    FaultSeverity.HIGH: 2,
    FaultSeverity.CRITICAL: 3,
}


class ReportInspectionFaultService:
    """Create one open fault from failed checklist items (no repair order yet).

    Repair orders are created only after distribution confirms the vehicle is
    unusable / needs repair, so checklist and manual fault paths stay aligned.
    """

    def __init__(
        self,
        inspection_repository: IInspectionRepository,
        fault_repository: IFaultRepository,
        repair_order_repository: IRepairOrderRepository,
        vehicle_repository: IVehicleRepository | None = None,
        sap_transaction_manager: ISAPTransactionManager | None = None,
        sap_pm_notification_port: ISAPPMNotificationPort | None = None,
        sap_measurement_port: ISAPMeasurementDocumentPort | None = None,
        odometer_reader: IFaultVehicleOdometerReader | None = None,
    ) -> None:
        self._inspection_repo = inspection_repository
        self._fault_repo = fault_repository
        self._repair_repo = repair_order_repository
        self._vehicle_repo = vehicle_repository
        self._sap_tx = sap_transaction_manager
        self._sap_pm_notification = sap_pm_notification_port
        self._sap_measurement = sap_measurement_port
        self._odometer_reader = odometer_reader

    def execute(self, dto: ReportInspectionFaultDTO) -> FaultResponseDTO:
        """Report failed checklist items as a single fault incident."""
        logger.info(
            "Reporting inspection fault",
            extra={
                "domain": "inspection",
                "service": "ReportInspectionFaultService",
                "operation": "execute",
                "request_id": dto.request_id,
                "inspection_id": str(dto.inspection_id),
                "reported_by": str(dto.reported_by),
            },
        )

        inspection = load_or_not_found(
            lambda: self._inspection_repo.get_by_id(dto.inspection_id),
            message=f"Inspection '{dto.inspection_id}' not found.",
            details={"inspection_id": str(dto.inspection_id)},
        )
        if inspection.status == InspectionStatus.DRAFT:
            raise FMMSConflictError(
                message="Checklist must be submitted before reporting a fault.",
                error_code="CHECKLIST_NOT_SUBMITTED",
                details={
                    "inspection_id": str(inspection.id),
                    "status": inspection.status.value,
                },
            )

        failed_items = inspection.failed_items()
        if not failed_items:
            raise FMMSValidationError(
                message="Checklist has no failed items to report.",
                error_code="CHECKLIST_HAS_NO_FAILURES",
                details={"inspection_id": str(inspection.id)},
            )
        existing_faults = self._fault_repo.list_by_inspection(inspection.id)
        if existing_faults:
            raise FMMSConflictError(
                message="A fault has already been reported for this checklist.",
                error_code="CHECKLIST_FAULT_ALREADY_REPORTED",
                details={
                    "inspection_id": str(inspection.id),
                    "fault_ids": [str(fault.id) for fault in existing_faults],
                },
            )

        assert_vehicle_has_no_open_flow(
            inspection.vehicle_id,
            fault_repository=self._fault_repo,
            repair_order_repository=self._repair_repo,
        )

        now = datetime.now(tz=UTC)
        fault = _build_fault_from_failed_items(
            inspection_id=inspection.id,
            vehicle_id=inspection.vehicle_id,
            failed_items=failed_items,
            reported_by_id=dto.reported_by,
            now=now,
        )
        saved = self._fault_repo.save(fault)
        vehicle = None
        if self._vehicle_repo is not None:
            vehicle = load_or_not_found(
                lambda: self._vehicle_repo.get_by_id(inspection.vehicle_id),
                message=f"Vehicle '{inspection.vehicle_id}' not found.",
                details={"vehicle_id": str(inspection.vehicle_id)},
            )
        if (
            vehicle is not None
            and self._sap_tx is not None
            and self._sap_pm_notification is not None
        ):
            notification_number = _create_sap_pm_notification(
                sap_tx=self._sap_tx,
                sap_pm_notification=self._sap_pm_notification,
                fault=saved,
                vehicle_number=vehicle.vehicle_number.value,
                request_id=dto.request_id,
            )
            if notification_number:
                saved.link_sap_notification(notification_number)
                saved.updated_at = datetime.now(tz=UTC)
                saved = self._fault_repo.save(saved)
                if self._sap_measurement is not None and self._odometer_reader is not None:
                    _update_sap_vehicle_measurement(
                        sap_tx=self._sap_tx,
                        sap_measurement=self._sap_measurement,
                        odometer_reader=self._odometer_reader,
                        fault=saved,
                        vehicle_number=vehicle.vehicle_number.value,
                        notification_number=notification_number,
                        request_id=dto.request_id,
                    )

        logger.info(
            "Inspection fault reported successfully",
            extra={
                "domain": "inspection",
                "service": "ReportInspectionFaultService",
                "operation": "execute",
                "request_id": dto.request_id,
                "inspection_id": str(inspection.id),
                "fault_id": str(saved.id),
                "result": "success",
            },
        )
        return _to_response_dto(saved)


def _build_fault_from_failed_items(
    inspection_id: uuid.UUID,
    vehicle_id: uuid.UUID,
    failed_items: list[InspectionItem],
    reported_by_id: uuid.UUID,
    now: datetime,
) -> Fault:
    """Construct one fault aggregate from failed inspection checklist items."""
    fault_id = uuid.uuid4()
    if len(failed_items) == 1:
        item = failed_items[0]
        summary = f"[{item.category}] {item.description}"[:500]
    else:
        summary = _MULTI_FAILURE_DESCRIPTION

    item_severities = [_item_fault_severity(item) for item in failed_items]
    overall_severity = _max_fault_severity(item_severities)

    return Fault(
        id=fault_id,
        vehicle_id=vehicle_id,
        code=FaultCode(_DEFAULT_FAULT_CODE),
        description=FaultDescription(summary),
        severity=overall_severity,
        status=FaultStatus.OPEN,
        reported_by_id=reported_by_id,
        reported_at=now,
        inspection_id=inspection_id,
        created_at=now,
        updated_at=now,
        items=[
            _build_fault_item(
                fault_id=fault_id,
                item=item,
                now=now,
            )
            for item in failed_items
        ],
    )


def _build_fault_item(
    fault_id: uuid.UUID,
    item: InspectionItem,
    now: datetime,
) -> FaultItem:
    """Construct a ``FaultItem`` from a failed inspection checklist item."""
    detail = (item.notes or item.description or "").strip() or item.description
    return FaultItem(
        id=uuid.uuid4(),
        fault_id=fault_id,
        inspection_item_id=item.id,
        component=item.description,
        description=detail[:500],
        severity=_item_fault_severity(item),
        created_at=now,
        updated_at=now,
    )


def _item_fault_severity(item: InspectionItem) -> FaultSeverity:
    """Map a failed inspection item to fault severity."""
    if item.severity is None:
        return _DEFAULT_FAULT_SEVERITY
    return FaultSeverity(item.severity.value)


def _max_fault_severity(severities: list[FaultSeverity]) -> FaultSeverity:
    """Return the highest severity from a non-empty list."""
    return max(severities, key=lambda level: _SEVERITY_RANK[level])
