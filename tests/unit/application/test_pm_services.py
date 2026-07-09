"""Unit tests for Preventive Maintenance application services.

In-memory fakes only — no database, no network, no Celery/schedulers.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from apps.preventive_maintenance.application.dto.pm_dto import (
    CompletePMWorkOrderDTO,
    CreatePMPlanDTO,
    PMPlanResponseDTO,
    TriggerPMWorkOrderDTO,
)
from apps.preventive_maintenance.application.services.complete_pm_work_order_service import (
    CompletePMWorkOrderService,
)
from apps.preventive_maintenance.application.services.create_pm_plan_service import (
    CreatePMPlanService,
)
from apps.preventive_maintenance.application.services.get_pm_service import (
    GetPMPlanService,
    ListPMPlansService,
    ListPMWorkOrdersService,
)
from apps.preventive_maintenance.application.services.trigger_pm_work_order_service import (
    TriggerPMWorkOrderService,
)
from apps.preventive_maintenance.domain.entities import (
    PMPlan,
    PMPlanStatus,
    PMWorkOrder,
    PMWorkOrderStatus,
)
from apps.preventive_maintenance.domain.exceptions import (
    PMAlreadyTriggeredError,
    PMInvalidStateTransitionError,
)
from apps.preventive_maintenance.domain.interfaces.pm_repository import (
    IPMPlanRepository,
    IPMWorkOrderRepository,
)
from apps.preventive_maintenance.domain.value_objects import (
    IntervalUnit,
    MaintenanceInterval,
    TriggerCondition,
    TriggerType,
)
from apps.vehicle.domain.entities import Vehicle, VehicleCategory, VehicleStatus
from apps.vehicle.domain.interfaces.vehicle_repository import IVehicleRepository
from apps.vehicle.domain.value_objects import VIN, PlateNumber, SAPEquipmentNumber
from core.exceptions.base_exception import FMMSConflictError, FMMSNotFoundError
from core.sap.dtos.pm_notification import (
    CreatePMNotificationRequest,
    SAPNotificationDTO,
)
from core.sap.ports.pm_notification_port import ISAPPMNotificationPort

# ---------------------------------------------------------------------------
# Helpers / fakes
# ---------------------------------------------------------------------------


def _make_vehicle(*, with_sap: bool = False) -> Vehicle:
    return Vehicle(
        id=uuid.uuid4(),
        plate_number=PlateNumber("PMPLT001"),
        vin=VIN("1HGCM82633A004352"),
        make="Toyota",
        model="Hilux",
        year=2022,
        category=VehicleCategory.LIGHT,
        status=VehicleStatus.ACTIVE,
        created_at=datetime.now(tz=UTC),
        updated_at=datetime.now(tz=UTC),
        sap_equipment_number=SAPEquipmentNumber("200001") if with_sap else None,
    )


def _make_plan(
    *,
    vehicle_id: uuid.UUID | None = None,
    status: PMPlanStatus = PMPlanStatus.ACTIVE,
) -> PMPlan:
    now = datetime.now(tz=UTC)
    return PMPlan(
        id=uuid.uuid4(),
        vehicle_id=vehicle_id or uuid.uuid4(),
        name="10k Service",
        description="Every 10,000 km service",
        interval=MaintenanceInterval(value=10000, unit=IntervalUnit.KM),
        trigger_condition=TriggerCondition(
            trigger_type=TriggerType.MILEAGE_BASED, threshold=10000
        ),
        status=status,
        created_by_id=uuid.uuid4(),
        created_at=now,
        updated_at=now,
    )


def _make_work_order(
    *,
    plan_id: uuid.UUID,
    vehicle_id: uuid.UUID,
    status: PMWorkOrderStatus = PMWorkOrderStatus.TRIGGERED,
) -> PMWorkOrder:
    now = datetime.now(tz=UTC)
    wo = PMWorkOrder(
        id=uuid.uuid4(),
        plan_id=plan_id,
        vehicle_id=vehicle_id,
        status=PMWorkOrderStatus.SCHEDULED,
        scheduled_date=now,
        created_at=now,
        updated_at=now,
    )
    if status == PMWorkOrderStatus.TRIGGERED:
        wo.trigger(triggered_at=now)
    elif status == PMWorkOrderStatus.IN_PROGRESS:
        wo.trigger(triggered_at=now)
        wo.start()
    elif status == PMWorkOrderStatus.COMPLETED:
        wo.trigger(triggered_at=now)
        wo.start()
        wo.complete(completed_at=now)
    elif status == PMWorkOrderStatus.OVERDUE:
        wo.mark_overdue()
    return wo


class FakePMPlanRepository(IPMPlanRepository):
    def __init__(self, initial: list[PMPlan] | None = None) -> None:
        self._store: dict[uuid.UUID, PMPlan] = {p.id: p for p in (initial or [])}

    def get_by_id(self, plan_id: uuid.UUID) -> PMPlan | None:
        return self._store.get(plan_id)

    def list_by_vehicle(
        self, vehicle_id: uuid.UUID, status: PMPlanStatus | None = None
    ) -> list[PMPlan]:
        plans = [p for p in self._store.values() if p.vehicle_id == vehicle_id]
        if status is not None:
            plans = [p for p in plans if p.status == status]
        return plans

    def list_active(self) -> list[PMPlan]:
        return [p for p in self._store.values() if p.status == PMPlanStatus.ACTIVE]

    def save(self, plan: PMPlan) -> PMPlan:
        self._store[plan.id] = plan
        return plan

    def delete(self, plan_id: uuid.UUID) -> None:
        self._store.pop(plan_id, None)


class FakePMWorkOrderRepository(IPMWorkOrderRepository):
    def __init__(self, initial: list[PMWorkOrder] | None = None) -> None:
        self._store: dict[uuid.UUID, PMWorkOrder] = {
            wo.id: wo for wo in (initial or [])
        }

    def get_by_id(self, work_order_id: uuid.UUID) -> PMWorkOrder | None:
        return self._store.get(work_order_id)

    def list_by_plan(
        self, plan_id: uuid.UUID, status: PMWorkOrderStatus | None = None
    ) -> list[PMWorkOrder]:
        orders = [wo for wo in self._store.values() if wo.plan_id == plan_id]
        if status is not None:
            orders = [wo for wo in orders if wo.status == status]
        return orders

    def list_overdue(self) -> list[PMWorkOrder]:
        return [
            wo for wo in self._store.values() if wo.status == PMWorkOrderStatus.OVERDUE
        ]

    def save(self, work_order: PMWorkOrder) -> PMWorkOrder:
        self._store[work_order.id] = work_order
        return work_order


class FakeVehicleRepository(IVehicleRepository):
    def __init__(self, initial: list[Vehicle] | None = None) -> None:
        self._store: dict[uuid.UUID, Vehicle] = {v.id: v for v in (initial or [])}

    def get_by_id(self, vehicle_id: uuid.UUID) -> Vehicle | None:
        return self._store.get(vehicle_id)

    def get_by_plate(self, plate_number: PlateNumber) -> Vehicle | None:
        return None

    def exists_by_plate(self, plate_number: PlateNumber) -> bool:
        return False

    def list_active(self) -> list[Vehicle]:
        return [v for v in self._store.values() if v.status == VehicleStatus.ACTIVE]

    def list_by_status(self, status: VehicleStatus) -> list[Vehicle]:
        return [v for v in self._store.values() if v.status == status]

    def save(self, vehicle: Vehicle) -> Vehicle:
        self._store[vehicle.id] = vehicle
        return vehicle

    def delete(self, vehicle_id: uuid.UUID) -> None:
        self._store.pop(vehicle_id, None)


class FakeSAPPMNotificationPort(ISAPPMNotificationPort):
    def __init__(self, notification_number: str = "10001234") -> None:
        self.notification_number = notification_number
        self.calls: list[CreatePMNotificationRequest] = []

    def create_notification(
        self, request: CreatePMNotificationRequest
    ) -> SAPNotificationDTO:
        self.calls.append(request)
        return SAPNotificationDTO(
            notification_number=self.notification_number,
            equipment_number=request.equipment_number,
            status="OSNO",
            created_at=datetime.now(tz=UTC),
        )

    def close_notification(self, notification_number: str) -> SAPNotificationDTO:
        return SAPNotificationDTO(
            notification_number=notification_number,
            equipment_number="200001",
            status="NOCO",
            created_at=datetime.now(tz=UTC),
        )


# ---------------------------------------------------------------------------
# CreatePMPlanService
# ---------------------------------------------------------------------------


class TestCreatePMPlanService:
    def test_creates_active_plan(self) -> None:
        vehicle = _make_vehicle()
        result = CreatePMPlanService(
            FakePMPlanRepository(), FakeVehicleRepository([vehicle])
        ).execute(
            CreatePMPlanDTO(
                vehicle_id=vehicle.id,
                name="Oil Change",
                description="Periodic oil change",
                interval_value=5000,
                interval_unit=IntervalUnit.KM,
                trigger_type=TriggerType.MILEAGE_BASED,
                trigger_threshold=5000,
                request_id="req-create",
                created_by=uuid.uuid4(),
            )
        )

        assert isinstance(result, PMPlanResponseDTO)
        assert result.status == PMPlanStatus.ACTIVE
        assert result.interval_value == 5000

    def test_raises_not_found_for_missing_vehicle(self) -> None:
        with pytest.raises(FMMSNotFoundError):
            CreatePMPlanService(
                FakePMPlanRepository(), FakeVehicleRepository()
            ).execute(
                CreatePMPlanDTO(
                    vehicle_id=uuid.uuid4(),
                    name="X",
                    description="Y",
                    interval_value=30,
                    interval_unit=IntervalUnit.DAYS,
                    trigger_type=TriggerType.TIME_BASED,
                    trigger_threshold=30,
                    request_id="req-noveh",
                    created_by=uuid.uuid4(),
                )
            )


# ---------------------------------------------------------------------------
# TriggerPMWorkOrderService
# ---------------------------------------------------------------------------


class TestTriggerPMWorkOrderService:
    def test_triggers_work_order_from_active_plan(self) -> None:
        vehicle = _make_vehicle()
        plan = _make_plan(vehicle_id=vehicle.id)
        service = TriggerPMWorkOrderService(
            FakePMPlanRepository([plan]),
            FakePMWorkOrderRepository(),
            FakeVehicleRepository([vehicle]),
        )

        result = service.execute(
            TriggerPMWorkOrderDTO(
                plan_id=plan.id,
                scheduled_date=datetime.now(tz=UTC),
                request_id="req-trig",
                triggered_by=uuid.uuid4(),
            )
        )

        assert result.status == PMWorkOrderStatus.TRIGGERED
        assert result.plan_id == plan.id
        assert result.triggered_at is not None

    def test_raises_when_plan_not_active(self) -> None:
        vehicle = _make_vehicle()
        plan = _make_plan(vehicle_id=vehicle.id, status=PMPlanStatus.SUSPENDED)
        service = TriggerPMWorkOrderService(
            FakePMPlanRepository([plan]),
            FakePMWorkOrderRepository(),
            FakeVehicleRepository([vehicle]),
        )

        with pytest.raises(FMMSConflictError):
            service.execute(
                TriggerPMWorkOrderDTO(
                    plan_id=plan.id,
                    scheduled_date=datetime.now(tz=UTC),
                    request_id="req-susp",
                    triggered_by=uuid.uuid4(),
                )
            )

    def test_raises_when_active_work_order_exists(self) -> None:
        vehicle = _make_vehicle()
        plan = _make_plan(vehicle_id=vehicle.id)
        existing = _make_work_order(
            plan_id=plan.id, vehicle_id=vehicle.id, status=PMWorkOrderStatus.TRIGGERED
        )
        service = TriggerPMWorkOrderService(
            FakePMPlanRepository([plan]),
            FakePMWorkOrderRepository([existing]),
            FakeVehicleRepository([vehicle]),
        )

        with pytest.raises(PMAlreadyTriggeredError):
            service.execute(
                TriggerPMWorkOrderDTO(
                    plan_id=plan.id,
                    scheduled_date=datetime.now(tz=UTC),
                    request_id="req-dup",
                    triggered_by=uuid.uuid4(),
                )
            )

    def test_creates_sap_notification_when_requested(self) -> None:
        vehicle = _make_vehicle(with_sap=True)
        plan = _make_plan(vehicle_id=vehicle.id)
        sap = FakeSAPPMNotificationPort(notification_number="10009999")
        service = TriggerPMWorkOrderService(
            FakePMPlanRepository([plan]),
            FakePMWorkOrderRepository(),
            FakeVehicleRepository([vehicle]),
            sap_pm_notification_port=sap,
        )

        result = service.execute(
            TriggerPMWorkOrderDTO(
                plan_id=plan.id,
                scheduled_date=datetime.now(tz=UTC),
                request_id="req-sap",
                triggered_by=uuid.uuid4(),
                create_sap_notification=True,
            )
        )

        assert result.sap_notification_number == "10009999"
        assert len(sap.calls) == 1
        assert sap.calls[0].equipment_number == "200001"

    def test_raises_when_sap_requested_without_port(self) -> None:
        vehicle = _make_vehicle(with_sap=True)
        plan = _make_plan(vehicle_id=vehicle.id)
        service = TriggerPMWorkOrderService(
            FakePMPlanRepository([plan]),
            FakePMWorkOrderRepository(),
            FakeVehicleRepository([vehicle]),
            sap_pm_notification_port=None,
        )

        with pytest.raises(FMMSConflictError):
            service.execute(
                TriggerPMWorkOrderDTO(
                    plan_id=plan.id,
                    scheduled_date=datetime.now(tz=UTC),
                    request_id="req-noport",
                    triggered_by=uuid.uuid4(),
                    create_sap_notification=True,
                )
            )

    def test_raises_not_found_for_missing_plan(self) -> None:
        with pytest.raises(FMMSNotFoundError):
            TriggerPMWorkOrderService(
                FakePMPlanRepository(),
                FakePMWorkOrderRepository(),
                FakeVehicleRepository(),
            ).execute(
                TriggerPMWorkOrderDTO(
                    plan_id=uuid.uuid4(),
                    scheduled_date=datetime.now(tz=UTC),
                    request_id="req-ghost",
                    triggered_by=uuid.uuid4(),
                )
            )


# ---------------------------------------------------------------------------
# CompletePMWorkOrderService
# ---------------------------------------------------------------------------


class TestCompletePMWorkOrderService:
    def test_completes_triggered_work_order(self) -> None:
        plan_id = uuid.uuid4()
        vehicle_id = uuid.uuid4()
        wo = _make_work_order(
            plan_id=plan_id, vehicle_id=vehicle_id, status=PMWorkOrderStatus.TRIGGERED
        )
        completed_at = datetime.now(tz=UTC)

        result = CompletePMWorkOrderService(FakePMWorkOrderRepository([wo])).execute(
            CompletePMWorkOrderDTO(
                work_order_id=wo.id,
                completed_at=completed_at,
                request_id="req-complete",
                completed_by=uuid.uuid4(),
            )
        )

        assert result.status == PMWorkOrderStatus.COMPLETED
        assert result.completed_at == completed_at

    def test_completes_in_progress_work_order(self) -> None:
        wo = _make_work_order(
            plan_id=uuid.uuid4(),
            vehicle_id=uuid.uuid4(),
            status=PMWorkOrderStatus.IN_PROGRESS,
        )
        result = CompletePMWorkOrderService(FakePMWorkOrderRepository([wo])).execute(
            CompletePMWorkOrderDTO(
                work_order_id=wo.id,
                completed_at=datetime.now(tz=UTC),
                request_id="req-ip",
                completed_by=uuid.uuid4(),
            )
        )

        assert result.status == PMWorkOrderStatus.COMPLETED

    def test_raises_when_already_completed(self) -> None:
        wo = _make_work_order(
            plan_id=uuid.uuid4(),
            vehicle_id=uuid.uuid4(),
            status=PMWorkOrderStatus.COMPLETED,
        )
        with pytest.raises(PMInvalidStateTransitionError):
            CompletePMWorkOrderService(FakePMWorkOrderRepository([wo])).execute(
                CompletePMWorkOrderDTO(
                    work_order_id=wo.id,
                    completed_at=datetime.now(tz=UTC),
                    request_id="req-re",
                    completed_by=uuid.uuid4(),
                )
            )

    def test_raises_not_found(self) -> None:
        with pytest.raises(FMMSNotFoundError):
            CompletePMWorkOrderService(FakePMWorkOrderRepository()).execute(
                CompletePMWorkOrderDTO(
                    work_order_id=uuid.uuid4(),
                    completed_at=datetime.now(tz=UTC),
                    request_id="req-ghost",
                    completed_by=uuid.uuid4(),
                )
            )


# ---------------------------------------------------------------------------
# Get / List
# ---------------------------------------------------------------------------


class TestGetPMPlanService:
    def test_returns_plan(self) -> None:
        plan = _make_plan()
        result = GetPMPlanService(FakePMPlanRepository([plan])).execute(plan.id)
        assert result.id == plan.id

    def test_raises_not_found(self) -> None:
        with pytest.raises(FMMSNotFoundError):
            GetPMPlanService(FakePMPlanRepository()).execute(uuid.uuid4())


class TestListPMPlansService:
    def test_lists_by_vehicle(self) -> None:
        vehicle_id = uuid.uuid4()
        p1 = _make_plan(vehicle_id=vehicle_id)
        p2 = _make_plan(vehicle_id=vehicle_id)
        other = _make_plan()
        results = ListPMPlansService(FakePMPlanRepository([p1, p2, other])).execute(
            vehicle_id=vehicle_id
        )
        assert len(results) == 2


class TestListPMWorkOrdersService:
    def test_lists_by_plan(self) -> None:
        plan_id = uuid.uuid4()
        vehicle_id = uuid.uuid4()
        wo1 = _make_work_order(plan_id=plan_id, vehicle_id=vehicle_id)
        wo2 = _make_work_order(plan_id=plan_id, vehicle_id=vehicle_id)
        other = _make_work_order(plan_id=uuid.uuid4(), vehicle_id=vehicle_id)
        results = ListPMWorkOrdersService(
            FakePMWorkOrderRepository([wo1, wo2, other])
        ).execute(plan_id=plan_id)
        assert len(results) == 2
