"""Query-side service for vehicle dashboard summary cards."""

from __future__ import annotations

from datetime import timedelta

from django.db.models import Avg, OuterRef, QuerySet, Subquery
from django.utils import timezone

from apps.fault.domain.entities import FaultStatus
from apps.fault.infrastructure.models import FaultModel
from apps.integration.infrastructure.models import SAPSyncRunItemModel
from apps.repair.domain.entities import RepairOrderStatus
from apps.repair.infrastructure.models import RepairOrderModel
from apps.vehicle.application.dto.vehicle_dto import VehicleSummaryDTO
from apps.vehicle.domain.entities import VehicleStatus
from apps.vehicle.infrastructure.models import VehicleModel, VehicleOdometerReadingModel

_ACTIVE_FLEET_EXCLUDED_STATUSES = frozenset({VehicleStatus.DECOMMISSIONED})
_UNUSABLE_STATUSES = frozenset(
    {
        VehicleStatus.INACTIVE,
        VehicleStatus.SUSPENDED,
        VehicleStatus.OUT_OF_SERVICE,
    }
)
_REPAIR_TERMINAL_STATUSES = frozenset(
    {
        RepairOrderStatus.COMPLETED,
        RepairOrderStatus.CANCELLED,
        RepairOrderStatus.ACCEPTED_BY_DRIVER,
        RepairOrderStatus.REJECTED_BY_DRIVER,
    }
)
_FAULT_LOOKBACK_DAYS = 30
_ODOMETER_AVERAGE_DIGITS = 2


class GetVehicleSummaryService:
    """Build summary values required by the vehicle dashboard."""

    def execute(self) -> VehicleSummaryDTO:
        """Return vehicle dashboard summary values."""
        active_fleet = VehicleModel.objects.filter(is_deleted=False).exclude(
            status__in=[status.value for status in _ACTIVE_FLEET_EXCLUDED_STATUSES]
        )
        active_vehicle_ids = active_fleet.values_list("id", flat=True)
        active_fleet_count = active_fleet.count()

        open_fault_vehicle_ids = set(
            FaultModel.objects.filter(
                vehicle_id__in=active_vehicle_ids,
                is_deleted=False,
            )
            .exclude(status=FaultStatus.CLOSED.value)
            .values_list("vehicle_id", flat=True)
        )
        open_repair_vehicle_ids = set(
            RepairOrderModel.objects.filter(
                vehicle_id__in=active_vehicle_ids,
                is_deleted=False,
            )
            .exclude(status__in=[status.value for status in _REPAIR_TERMINAL_STATUSES])
            .values_list("vehicle_id", flat=True)
        )

        operational_fleet_count = (
            active_fleet.filter(status=VehicleStatus.ACTIVE.value)
            .exclude(id__in=open_fault_vehicle_ids | open_repair_vehicle_ids)
            .count()
        )
        last_sap_sync = (
            SAPSyncRunItemModel.objects.filter(
                name="vehicles",
                status="SUCCESS",
                is_deleted=False,
                sync_run__is_deleted=False,
            )
            .order_by("-finished_at")
            .first()
        )
        recent_fault_count = FaultModel.objects.filter(
            vehicle_id__in=active_vehicle_ids,
            is_deleted=False,
            reported_at__gte=timezone.now() - timedelta(days=_FAULT_LOOKBACK_DAYS),
        ).count()

        return VehicleSummaryDTO(
            active_fleet_count=active_fleet_count,
            operational_fleet_count=operational_fleet_count,
            under_repair_fleet_count=active_fleet.filter(
                status__in=[
                    VehicleStatus.UNDER_REPAIR.value,
                    VehicleStatus.UNDER_EXTERNAL_REPAIR.value,
                ]
            ).count(),
            unusable_fleet_count=active_fleet.filter(
                status__in=[status.value for status in _UNUSABLE_STATUSES]
            ).count(),
            last_sap_sync_at=last_sap_sync.finished_at if last_sap_sync else None,
            average_odometer_km=_latest_odometer_average(active_fleet),
            average_faults_last_30_days=_average(
                recent_fault_count,
                active_fleet_count,
            ),
        )


def _latest_odometer_average(active_fleet: QuerySet[VehicleModel]) -> float:
    """Return average latest odometer value across active fleet vehicles."""
    latest_reading = (
        VehicleOdometerReadingModel.objects.filter(
            vehicle_id=OuterRef("id"),
            is_deleted=False,
        )
        .order_by("-reading_date", "-created_at")
        .values("odometer_km")[:1]
    )
    value = (
        active_fleet.annotate(latest_odometer=Subquery(latest_reading))
        .exclude(latest_odometer__isnull=True)
        .aggregate(value=Avg("latest_odometer"))["value"]
    )
    return round(float(value or 0), _ODOMETER_AVERAGE_DIGITS)


def _average(total: int, count: int) -> float:
    """Return rounded average while avoiding division by zero."""
    if count == 0:
        return 0.0
    return round(total / count, _ODOMETER_AVERAGE_DIGITS)
