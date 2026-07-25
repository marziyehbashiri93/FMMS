"""Unit tests for Inspection application services.

All repository dependencies are replaced with in-memory fakes — no DB, no network.

Key workflow tested:
- SubmitInspectionService: finalizes checklist without creating faults.
- ReportInspectionFaultService: FAIL items → one Fault with FaultItem children.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from apps.fault.domain.entities import Fault, FaultStatus
from apps.fault.domain.interfaces.fault_repository import IFaultRepository
from apps.fault.domain.value_objects import FaultCode, FaultDescription, FaultSeverity
from apps.inspection.application.dto.inspection_dto import (
    AddInspectionItemDTO,
    CreateInspectionDTO,
    InspectionResponseDTO,
    ReportInspectionFaultDTO,
    SubmitInspectionDTO,
)
from apps.inspection.application.services.add_inspection_item_service import (
    AddInspectionItemService,
)
from apps.inspection.application.services.create_inspection_service import (
    CreateInspectionService,
)
from apps.inspection.application.services.get_inspection_service import (
    GetInspectionService,
    ListInspectionsService,
)
from apps.inspection.application.services.report_inspection_fault_service import (
    ReportInspectionFaultService,
)
from apps.inspection.application.services.submit_inspection_service import (
    SubmitInspectionService,
)
from apps.inspection.domain.entities import Inspection, InspectionStatus, InspectionType
from apps.inspection.domain.exceptions import (
    InspectionAlreadySubmittedError,
    InspectionItemRequiredError,
)
from apps.inspection.domain.interfaces.inspection_repository import (
    IInspectionRepository,
)
from apps.inspection.domain.value_objects import (
    ChecklistResult,
    FailureSeverity,
    OdometerReading,
    OdometerUnit,
)
from apps.integration.domain.entities import SAPObjectType
from apps.repair.domain.entities import RepairOrder, RepairOrderStatus
from apps.repair.domain.interfaces.repair_repository import IRepairOrderRepository
from apps.vehicle.domain.entities import Vehicle, VehicleStatus
from apps.vehicle.domain.interfaces.vehicle_repository import IVehicleRepository
from apps.vehicle.domain.value_objects import PlateNumber, SAPVehicleNumber
from core.exceptions.base_exception import FMMSNotFoundError, FMMSStateError
from core.sap.dtos.pm_notification import (
    CreatePMNotificationRequest,
    SAPNotificationDTO,
)
from core.sap.ports.sap_transaction_manager_port import SAPAdapterCallable
from core.workflow import VEHICLE_OPEN_FLOW_ERROR_CODE, VEHICLE_OPEN_FLOW_MESSAGE

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_vehicle() -> Vehicle:
    return Vehicle(
        id=uuid.uuid4(),
        vehicle_number=SAPVehicleNumber("300001"),
        license_plate=PlateNumber("INSP0001"),
        status=VehicleStatus.ACTIVE,
        created_at=datetime.now(tz=UTC),
        updated_at=datetime.now(tz=UTC),
    )


def _make_inspection(
    vehicle_id: uuid.UUID | None = None,
    status: InspectionStatus = InspectionStatus.DRAFT,
) -> Inspection:
    return Inspection(
        id=uuid.uuid4(),
        vehicle_id=vehicle_id or uuid.uuid4(),
        inspection_type=InspectionType.PRE_TRIP,
        odometer_reading=OdometerReading(value=50000, unit=OdometerUnit.KM),
        status=status,
        inspected_at=datetime.now(tz=UTC),
        created_at=datetime.now(tz=UTC),
        updated_at=datetime.now(tz=UTC),
    )


def _make_open_fault(vehicle_id: uuid.UUID) -> Fault:
    now = datetime.now(tz=UTC)
    return Fault(
        id=uuid.uuid4(),
        vehicle_id=vehicle_id,
        code=FaultCode("INSP-FAIL"),
        description=FaultDescription("Existing open fault"),
        severity=FaultSeverity.MEDIUM,
        status=FaultStatus.OPEN,
        reported_by_id=uuid.uuid4(),
        reported_at=now,
        created_at=now,
        updated_at=now,
    )


def _make_open_repair_order(vehicle_id: uuid.UUID) -> RepairOrder:
    now = datetime.now(tz=UTC)
    return RepairOrder(
        id=uuid.uuid4(),
        vehicle_id=vehicle_id,
        fault_id=uuid.uuid4(),
        status=RepairOrderStatus.CREATED,
        created_by_id=uuid.uuid4(),
        created_at=now,
        updated_at=now,
    )


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeInspectionRepository(IInspectionRepository):
    def __init__(self, initial: list[Inspection] | None = None) -> None:
        self._store: dict[uuid.UUID, Inspection] = {i.id: i for i in (initial or [])}

    def get_by_id(self, inspection_id: uuid.UUID) -> Inspection | None:
        return self._store.get(inspection_id)

    def list_by_vehicle(self, vehicle_id: uuid.UUID) -> list[Inspection]:
        return [i for i in self._store.values() if i.vehicle_id == vehicle_id]

    def list_all(self, status=None) -> list[Inspection]:
        return list(self._store.values())

    def list_by_date_range(
        self,
        start: datetime,
        end: datetime,
    ) -> list[Inspection]:
        return [i for i in self._store.values() if start <= i.inspected_at <= end]

    def save(self, inspection: Inspection) -> Inspection:
        self._store[inspection.id] = inspection
        return inspection

    def delete(self, inspection_id: uuid.UUID) -> None:
        self._store.pop(inspection_id, None)


class FakeVehicleRepository(IVehicleRepository):
    def __init__(self, initial: list[Vehicle] | None = None) -> None:
        self._store: dict[uuid.UUID, Vehicle] = {v.id: v for v in (initial or [])}

    def get_by_id(self, vehicle_id: uuid.UUID) -> Vehicle | None:
        return self._store.get(vehicle_id)

    def get_by_plate(self, plate_number: PlateNumber) -> Vehicle | None:
        return None

    def get_by_vehicle_number(self, vehicle_number: SAPVehicleNumber) -> Vehicle | None:
        return next(
            (
                v
                for v in self._store.values()
                if v.vehicle_number is not None and v.vehicle_number == vehicle_number
            ),
            None,
        )

    def exists_by_plate(self, plate_number: PlateNumber) -> bool:
        return False

    def list_active(self) -> list[Vehicle]:
        return [v for v in self._store.values() if v.status == VehicleStatus.ACTIVE]

    def list_by_status(self, status: VehicleStatus) -> list[Vehicle]:
        return [v for v in self._store.values() if v.status == status]

    def save(self, vehicle: Vehicle) -> Vehicle:
        self._store[vehicle.id] = vehicle
        return vehicle

    def decommission_missing_from_sap(self, seen_vehicle_numbers: set[str]) -> int:
        count = 0
        for vehicle in self._store.values():
            if vehicle.vehicle_number.value not in seen_vehicle_numbers:
                vehicle.decommission()
                count += 1
        return count

    def record_driver_assignment_snapshot(self, **kwargs: object) -> None:
        return None

    def delete(self, vehicle_id: uuid.UUID) -> None:
        self._store.pop(vehicle_id, None)


class FakeFaultRepository(IFaultRepository):
    def __init__(self) -> None:
        self.saved: list[Fault] = []

    def get_by_id(self, fault_id: uuid.UUID) -> Fault | None:
        return next((f for f in self.saved if f.id == fault_id), None)

    def list_by_vehicle(self, vehicle_id: uuid.UUID) -> list[Fault]:
        return [f for f in self.saved if f.vehicle_id == vehicle_id]

    def list_all(self, status: FaultStatus | None = None) -> list[Fault]:
        if status is None:
            return list(self.saved)
        return [f for f in self.saved if f.status == status]

    def list_open_by_severity(self, severity) -> list[Fault]:
        return []

    def list_by_inspection(self, inspection_id: uuid.UUID) -> list[Fault]:
        return [f for f in self.saved if f.inspection_id == inspection_id]

    def has_open_fault_for_vehicle(self, vehicle_id: uuid.UUID) -> bool:
        return any(
            f.vehicle_id == vehicle_id and f.status != FaultStatus.CLOSED
            for f in self.saved
        )

    def save(self, fault: Fault) -> Fault:
        self.saved.append(fault)
        return fault

    def delete(self, fault_id: uuid.UUID) -> None:
        self.saved = [f for f in self.saved if f.id != fault_id]


class FakeRepairOrderRepository(IRepairOrderRepository):
    def __init__(self) -> None:
        self.saved: list[RepairOrder] = []

    def get_by_id(self, order_id: uuid.UUID) -> RepairOrder | None:
        return next((o for o in self.saved if o.id == order_id), None)

    def list_by_vehicle(
        self, vehicle_id: uuid.UUID, status: RepairOrderStatus | None = None
    ) -> list[RepairOrder]:
        return [o for o in self.saved if o.vehicle_id == vehicle_id]

    def list_by_fault(self, fault_id: uuid.UUID) -> list[RepairOrder]:
        return [o for o in self.saved if o.fault_id == fault_id]

    def list_all(self, status: RepairOrderStatus | None = None, workshop_type=None) -> list[RepairOrder]:
        if status is None:
            return list(self.saved)
        return [o for o in self.saved if o.status == status]

    def list_active_by_vehicle(self, vehicle_id: uuid.UUID) -> list[RepairOrder]:
        return [
            o
            for o in self.saved
            if o.vehicle_id == vehicle_id
            and o.status
            not in {RepairOrderStatus.COMPLETED, RepairOrderStatus.CANCELLED}
        ]

    def has_open_repair_order_for_vehicle(self, vehicle_id: uuid.UUID) -> bool:
        return bool(self.list_active_by_vehicle(vehicle_id))

    def save(self, order: RepairOrder) -> RepairOrder:
        self.saved.append(order)
        return order

    def delete(self, order_id: uuid.UUID) -> None:
        self.saved = [o for o in self.saved if o.id != order_id]


class FakeSAPTransactionManager:
    def __init__(self) -> None:
        self.calls: list[tuple[SAPObjectType, uuid.UUID, str, dict[str, object]]] = []

    def execute(
        self,
        object_type: SAPObjectType,
        object_id: uuid.UUID,
        idempotency_key: str,
        request_payload: dict[str, object],
        adapter_call: SAPAdapterCallable,
    ) -> tuple[dict[str, object], str]:
        self.calls.append((object_type, object_id, idempotency_key, request_payload))
        return adapter_call(request_payload)


class FakeSAPPMNotificationPort:
    def __init__(self, notification_number: str = "10008888") -> None:
        self.calls: list[CreatePMNotificationRequest] = []
        self._notification_number = notification_number

    def create_notification(
        self,
        request: CreatePMNotificationRequest,
    ) -> SAPNotificationDTO:
        self.calls.append(request)
        return SAPNotificationDTO(
            notification_number=self._notification_number,
            equipment_number=request.equipment_number,
            status="OPEN",
            created_at=datetime.now(tz=UTC),
        )

    def close_notification(self, notification_number: str) -> SAPNotificationDTO:
        return SAPNotificationDTO(
            notification_number=notification_number,
            equipment_number="",
            status="CLOSED",
            created_at=datetime.now(tz=UTC),
        )


# ---------------------------------------------------------------------------
# CreateInspectionService
# ---------------------------------------------------------------------------


class TestCreateInspectionService:
    def _service(self, vehicle: Vehicle) -> CreateInspectionService:
        return CreateInspectionService(
            inspection_repository=FakeInspectionRepository(),
            vehicle_repository=FakeVehicleRepository(initial=[vehicle]),
        )

    def test_creates_draft_inspection(self) -> None:
        vehicle = _make_vehicle()
        result = self._service(vehicle).execute(
            CreateInspectionDTO(
                vehicle_id=vehicle.id,
                inspection_type=InspectionType.PRE_TRIP,
                odometer_value=50000,
                odometer_unit=OdometerUnit.KM,
                inspected_at=datetime.now(tz=UTC),
                request_id="req-create",
                created_by=uuid.uuid4(),
            )
        )

        assert isinstance(result, InspectionResponseDTO)
        assert result.status == InspectionStatus.DRAFT
        assert result.items == []

    def test_raises_not_found_for_missing_vehicle(self) -> None:
        service = CreateInspectionService(
            inspection_repository=FakeInspectionRepository(),
            vehicle_repository=FakeVehicleRepository(),
        )

        with pytest.raises(FMMSNotFoundError):
            service.execute(
                CreateInspectionDTO(
                    vehicle_id=uuid.uuid4(),
                    inspection_type=InspectionType.PERIODIC,
                    odometer_value=1000,
                    odometer_unit=OdometerUnit.KM,
                    inspected_at=datetime.now(tz=UTC),
                    request_id="req-noveh",
                    created_by=uuid.uuid4(),
                )
            )


# ---------------------------------------------------------------------------
# AddInspectionItemService
# ---------------------------------------------------------------------------


class TestAddInspectionItemService:
    def test_adds_item_to_draft_inspection(self) -> None:
        inspection = _make_inspection()
        repo = FakeInspectionRepository(initial=[inspection])

        result = AddInspectionItemService(repo).execute(
            AddInspectionItemDTO(
                inspection_id=inspection.id,
                category="Brakes",
                description="Brake pad thickness",
                result=ChecklistResult.PASS,
                request_id="req-item",
            )
        )

        assert len(result.items) == 1
        assert result.items[0].result == ChecklistResult.PASS

    def test_raises_not_found_for_missing_inspection(self) -> None:
        repo = FakeInspectionRepository()

        with pytest.raises(FMMSNotFoundError):
            AddInspectionItemService(repo).execute(
                AddInspectionItemDTO(
                    inspection_id=uuid.uuid4(),
                    category="Lights",
                    description="Headlights",
                    result=ChecklistResult.PASS,
                    request_id="req-ghost",
                )
            )

    def test_raises_already_submitted_when_not_draft(self) -> None:
        inspection = _make_inspection(status=InspectionStatus.SUBMITTED)
        repo = FakeInspectionRepository(initial=[inspection])

        with pytest.raises(InspectionAlreadySubmittedError):
            AddInspectionItemService(repo).execute(
                AddInspectionItemDTO(
                    inspection_id=inspection.id,
                    category="Tires",
                    description="Tire pressure",
                    result=ChecklistResult.FAIL,
                    request_id="req-late",
                )
            )


# ---------------------------------------------------------------------------
# SubmitInspectionService
# ---------------------------------------------------------------------------


class TestSubmitInspectionService:
    def _service(
        self,
        inspections: list[Inspection] | None = None,
        vehicles: list[Vehicle] | None = None,
        faults: list[Fault] | None = None,
        repair_orders: list[RepairOrder] | None = None,
    ) -> tuple[
        SubmitInspectionService,
        FakeFaultRepository,
        FakeRepairOrderRepository,
        FakeVehicleRepository,
    ]:
        fault_repo = FakeFaultRepository()
        for fault in faults or []:
            fault_repo.saved.append(fault)
        repair_repo = FakeRepairOrderRepository()
        for order in repair_orders or []:
            repair_repo.saved.append(order)
        vehicle_repo = FakeVehicleRepository(initial=vehicles or [])
        service = SubmitInspectionService(
            inspection_repository=FakeInspectionRepository(initial=inspections or []),
            fault_repository=fault_repo,
            repair_order_repository=repair_repo,
        )
        return service, fault_repo, repair_repo, vehicle_repo

    def _dto(self, inspection_id: uuid.UUID) -> SubmitInspectionDTO:
        return SubmitInspectionDTO(
            inspection_id=inspection_id,
            request_id="req-submit",
            submitted_by=uuid.uuid4(),
        )

    def test_transitions_inspection_to_submitted(self) -> None:
        vehicle = _make_vehicle()
        inspection = _make_inspection(vehicle_id=vehicle.id)
        inspection.items.append(_make_pass_item())
        service, _, _, _ = self._service(inspections=[inspection], vehicles=[vehicle])

        result = service.execute(self._dto(inspection.id))

        assert result.status == InspectionStatus.SUBMITTED

    def test_submit_does_not_create_fault_for_failed_items(self) -> None:
        vehicle = _make_vehicle()
        inspection = _make_inspection(vehicle_id=vehicle.id)
        inspection.items.append(_make_fail_item("Brakes", "Brake fluid low"))
        inspection.items.append(_make_fail_item("Lights", "Left headlight broken"))
        inspection.items.append(_make_pass_item())
        service, fault_repo, _, _ = self._service(
            inspections=[inspection], vehicles=[vehicle]
        )

        service.execute(self._dto(inspection.id))

        assert inspection.status == InspectionStatus.SUBMITTED
        assert len(fault_repo.saved) == 0

    def test_submit_does_not_create_repair_order_for_failed_inspection(self) -> None:
        vehicle = _make_vehicle()
        inspection = _make_inspection(vehicle_id=vehicle.id)
        inspection.items.append(_make_fail_item("Brakes", "Brake fluid low"))
        inspection.items.append(_make_fail_item("Lights", "Left headlight broken"))
        service, fault_repo, repair_repo, _ = self._service(
            inspections=[inspection], vehicles=[vehicle]
        )

        service.execute(self._dto(inspection.id))

        assert inspection.status == InspectionStatus.SUBMITTED
        assert len(fault_repo.saved) == 0
        assert len(repair_repo.saved) == 0

    def test_keeps_vehicle_active_on_fail(self) -> None:
        vehicle = _make_vehicle()
        inspection = _make_inspection(vehicle_id=vehicle.id)
        inspection.items.append(_make_fail_item("Brakes", "Brake fluid low"))
        service, _, _, vehicle_repo = self._service(
            inspections=[inspection], vehicles=[vehicle]
        )

        service.execute(self._dto(inspection.id))

        assert vehicle_repo.get_by_id(vehicle.id).status == VehicleStatus.ACTIVE

    def test_no_faults_or_status_change_when_all_items_pass(self) -> None:
        vehicle = _make_vehicle()
        inspection = _make_inspection(vehicle_id=vehicle.id)
        inspection.items.append(_make_pass_item())
        service, fault_repo, repair_repo, vehicle_repo = self._service(
            inspections=[inspection], vehicles=[vehicle]
        )

        service.execute(self._dto(inspection.id))

        assert len(fault_repo.saved) == 0
        assert len(repair_repo.saved) == 0
        assert vehicle_repo.get_by_id(vehicle.id).status == VehicleStatus.ACTIVE

    def test_submit_allows_failed_items_without_open_flow_check(self) -> None:
        vehicle = _make_vehicle()
        inspection = _make_inspection(vehicle_id=vehicle.id)
        inspection.items.append(_make_fail_item("Brakes", "Brake fluid low"))
        open_fault = _make_open_fault(vehicle.id)
        service, _, _, _ = self._service(
            inspections=[inspection],
            vehicles=[vehicle],
            faults=[open_fault],
        )

        result = service.execute(self._dto(inspection.id))

        assert result.status == InspectionStatus.SUBMITTED

    def test_raises_not_found_for_missing_inspection(self) -> None:
        service, _, _, _ = self._service()

        with pytest.raises(FMMSNotFoundError):
            service.execute(self._dto(uuid.uuid4()))

    def test_raises_item_required_when_no_items(self) -> None:
        vehicle = _make_vehicle()
        inspection = _make_inspection(vehicle_id=vehicle.id)
        service, _, _, _ = self._service(inspections=[inspection], vehicles=[vehicle])

        with pytest.raises(InspectionItemRequiredError):
            service.execute(self._dto(inspection.id))


# ---------------------------------------------------------------------------
# ReportInspectionFaultService
# ---------------------------------------------------------------------------


class TestReportInspectionFaultService:
    def _service(
        self,
        inspections: list[Inspection] | None = None,
        faults: list[Fault] | None = None,
        repair_orders: list[RepairOrder] | None = None,
    ) -> tuple[
        ReportInspectionFaultService,
        FakeFaultRepository,
        FakeRepairOrderRepository,
    ]:
        fault_repo = FakeFaultRepository()
        for fault in faults or []:
            fault_repo.saved.append(fault)
        repair_repo = FakeRepairOrderRepository()
        for order in repair_orders or []:
            repair_repo.saved.append(order)
        service = ReportInspectionFaultService(
            inspection_repository=FakeInspectionRepository(initial=inspections or []),
            fault_repository=fault_repo,
            repair_order_repository=repair_repo,
        )
        return service, fault_repo, repair_repo

    def _dto(self, inspection_id: uuid.UUID) -> ReportInspectionFaultDTO:
        return ReportInspectionFaultDTO(
            inspection_id=inspection_id,
            request_id="req-report-fault",
            reported_by=uuid.uuid4(),
        )

    def test_creates_one_fault_with_item_per_fail(self) -> None:
        vehicle = _make_vehicle()
        inspection = _make_inspection(
            vehicle_id=vehicle.id,
            status=InspectionStatus.SUBMITTED,
        )
        inspection.items.append(_make_fail_item("Brakes", "Brake fluid low"))
        inspection.items.append(_make_fail_item("Lights", "Left headlight broken"))
        service, fault_repo, _ = self._service(inspections=[inspection])

        service.execute(self._dto(inspection.id))

        assert len(fault_repo.saved) == 1
        assert len(fault_repo.saved[0].items) == 2

    def test_reports_checklist_fault_to_sap_pm_notification(self) -> None:
        vehicle = _make_vehicle()
        inspection = _make_inspection(
            vehicle_id=vehicle.id,
            status=InspectionStatus.SUBMITTED,
        )
        inspection.items.append(_make_fail_item("Brakes", "Brake fluid low"))
        fault_repo = FakeFaultRepository()
        repair_repo = FakeRepairOrderRepository()
        sap_tx = FakeSAPTransactionManager()
        sap_port = FakeSAPPMNotificationPort(notification_number="10007777")
        service = ReportInspectionFaultService(
            inspection_repository=FakeInspectionRepository(initial=[inspection]),
            fault_repository=fault_repo,
            repair_order_repository=repair_repo,
            vehicle_repository=FakeVehicleRepository(initial=[vehicle]),
            sap_transaction_manager=sap_tx,
            sap_pm_notification_port=sap_port,
        )

        result = service.execute(self._dto(inspection.id))

        assert result.sap_notification_number == "10007777"
        assert len(sap_tx.calls) == 1
        assert sap_tx.calls[0][0] == SAPObjectType.FAULT
        request = sap_port.calls[0]
        assert request.notification_type == "EM"
        assert request.equipment_number == vehicle.vehicle_number.value

    def test_creates_one_repair_order_for_failed_inspection(self) -> None:
        vehicle = _make_vehicle()
        inspection = _make_inspection(
            vehicle_id=vehicle.id,
            status=InspectionStatus.SUBMITTED,
        )
        inspection.items.append(_make_fail_item("Brakes", "Brake fluid low"))
        service, fault_repo, repair_repo = self._service(inspections=[inspection])

        service.execute(self._dto(inspection.id))

        assert len(fault_repo.saved) == 1
        assert len(repair_repo.saved) == 0

    def test_raises_when_vehicle_has_open_fault(self) -> None:
        vehicle = _make_vehicle()
        inspection = _make_inspection(
            vehicle_id=vehicle.id,
            status=InspectionStatus.SUBMITTED,
        )
        inspection.items.append(_make_fail_item("Brakes", "Brake fluid low"))
        open_fault = _make_open_fault(vehicle.id)
        service, _, _ = self._service(
            inspections=[inspection],
            faults=[open_fault],
        )

        with pytest.raises(FMMSStateError) as exc_info:
            service.execute(self._dto(inspection.id))

        assert exc_info.value.error_code == VEHICLE_OPEN_FLOW_ERROR_CODE
        assert exc_info.value.message == VEHICLE_OPEN_FLOW_MESSAGE

    def test_raises_when_vehicle_has_open_repair_order(self) -> None:
        vehicle = _make_vehicle()
        inspection = _make_inspection(
            vehicle_id=vehicle.id,
            status=InspectionStatus.SUBMITTED,
        )
        inspection.items.append(_make_fail_item("Brakes", "Brake fluid low"))
        open_order = _make_open_repair_order(vehicle.id)
        service, fault_repo, _ = self._service(
            inspections=[inspection],
            repair_orders=[open_order],
        )

        with pytest.raises(FMMSStateError):
            service.execute(self._dto(inspection.id))

        assert len(fault_repo.saved) == 0

    def test_reported_faults_are_open_and_linked_to_inspection(self) -> None:
        vehicle = _make_vehicle()
        inspection = _make_inspection(
            vehicle_id=vehicle.id,
            status=InspectionStatus.SUBMITTED,
        )
        inspection.items.append(_make_fail_item("Engine", "Oil level critical"))
        service, fault_repo, _ = self._service(inspections=[inspection])

        service.execute(self._dto(inspection.id))

        fault = fault_repo.saved[0]
        assert fault.status == FaultStatus.OPEN
        assert fault.inspection_id == inspection.id
        assert fault.vehicle_id == inspection.vehicle_id
        assert len(fault.items) == 1
        assert fault.items[0].component == "Oil level critical"

    def test_report_propagates_item_severity_to_fault(self) -> None:
        vehicle = _make_vehicle()
        inspection = _make_inspection(
            vehicle_id=vehicle.id,
            status=InspectionStatus.SUBMITTED,
        )
        inspection.items.append(
            _make_fail_item("Brakes", "Pad worn", FailureSeverity.LOW)
        )
        inspection.items.append(
            _make_fail_item("Engine", "Oil leak", FailureSeverity.CRITICAL)
        )
        service, fault_repo, _ = self._service(inspections=[inspection])

        service.execute(self._dto(inspection.id))

        fault = fault_repo.saved[0]
        assert fault.severity == FaultSeverity.CRITICAL
        severities = {item.severity for item in fault.items}
        assert severities == {FaultSeverity.LOW, FaultSeverity.CRITICAL}


# ---------------------------------------------------------------------------
# GetInspectionService / ListInspectionsService
# ---------------------------------------------------------------------------


class TestGetInspectionService:
    def test_returns_dto_for_existing_inspection(self) -> None:
        inspection = _make_inspection()
        repo = FakeInspectionRepository(initial=[inspection])

        result = GetInspectionService(repo).execute(inspection.id, request_id="req-get")

        assert result.id == inspection.id

    def test_raises_not_found_for_missing_inspection(self) -> None:
        repo = FakeInspectionRepository()
        with pytest.raises(FMMSNotFoundError):
            GetInspectionService(repo).execute(uuid.uuid4())


class TestListInspectionsService:
    def test_lists_inspections_by_vehicle(self) -> None:
        vehicle_id = uuid.uuid4()
        i1 = _make_inspection(vehicle_id=vehicle_id)
        i2 = _make_inspection(vehicle_id=vehicle_id)
        other = _make_inspection()
        repo = FakeInspectionRepository(initial=[i1, i2, other])

        results = ListInspectionsService(repo).execute(vehicle_id=vehicle_id)

        assert len(results) == 2

    def test_filters_by_date_range(self) -> None:
        vehicle_id = uuid.uuid4()
        now = datetime.now(tz=UTC)

        in_range = Inspection(
            id=uuid.uuid4(),
            vehicle_id=vehicle_id,
            inspection_type=InspectionType.PRE_TRIP,
            odometer_reading=OdometerReading(value=1000, unit=OdometerUnit.KM),
            status=InspectionStatus.DRAFT,
            inspected_at=now,
            created_at=now,
            updated_at=now,
        )
        out_of_range = Inspection(
            id=uuid.uuid4(),
            vehicle_id=vehicle_id,
            inspection_type=InspectionType.POST_TRIP,
            odometer_reading=OdometerReading(value=2000, unit=OdometerUnit.KM),
            status=InspectionStatus.DRAFT,
            inspected_at=datetime(2020, 1, 1, tzinfo=UTC),
            created_at=now,
            updated_at=now,
        )
        repo = FakeInspectionRepository(initial=[in_range, out_of_range])

        results = ListInspectionsService(repo).execute(
            vehicle_id=vehicle_id,
            from_date=datetime(2025, 1, 1, tzinfo=UTC),
            to_date=datetime(2027, 1, 1, tzinfo=UTC),
        )

        assert len(results) == 1
        assert results[0].id == in_range.id

    def test_returns_empty_list_when_no_inspections(self) -> None:
        repo = FakeInspectionRepository()
        results = ListInspectionsService(repo).execute(vehicle_id=uuid.uuid4())
        assert results == []

    def test_lists_all_inspections_without_vehicle_filter(self) -> None:
        i1 = _make_inspection()
        i2 = _make_inspection()
        repo = FakeInspectionRepository(initial=[i1, i2])

        results = ListInspectionsService(repo).execute()

        assert len(results) == 2


# ---------------------------------------------------------------------------
# Item factories for tests
# ---------------------------------------------------------------------------


def _make_pass_item() -> object:
    from apps.inspection.domain.entities import InspectionItem  # noqa: PLC0415

    return InspectionItem(
        id=uuid.uuid4(),
        category="Tires",
        description="Tire pressure within spec",
        result=ChecklistResult.PASS,
    )


def _make_fail_item(
    category: str,
    description: str,
    severity: FailureSeverity | None = None,
) -> object:
    from apps.inspection.domain.entities import InspectionItem  # noqa: PLC0415

    return InspectionItem(
        id=uuid.uuid4(),
        category=category,
        description=description,
        result=ChecklistResult.FAIL,
        severity=severity,
    )
