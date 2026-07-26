"""Django read model for driver dashboard summaries."""

from __future__ import annotations

from django.db.models import Exists, OuterRef, Q

from apps.driver.application.dto.driver_dto import DriverSummaryDTO
from apps.driver.application.interfaces.driver_summary_reader import (
    IDriverSummaryReader,
)
from apps.driver.domain.entities import DriverStatus
from apps.driver.infrastructure.models import DriverModel
from apps.integration.infrastructure.models import SAPSyncRunItemModel
from apps.vehicle.infrastructure.models import VehicleModel


class DjangoDriverSummaryReader(IDriverSummaryReader):
    """Build driver dashboard summary values with ORM queries."""

    def get_summary(self) -> DriverSummaryDTO:
        """Return driver dashboard summary values."""
        active_drivers = DriverModel.objects.filter(
            status=DriverStatus.ACTIVE.value,
            is_deleted=False,
        )
        decommissioned_count = DriverModel.objects.filter(
            status=DriverStatus.DECOMMISSIONED.value,
            is_deleted=False,
        ).count()

        assigned_vehicle = VehicleModel.objects.filter(is_deleted=False).filter(
            (
                Q(driver1_customer_number=OuterRef("customer_number"))
                & ~Q(driver1_customer_number="")
            )
            | (
                Q(driver2_customer_number=OuterRef("customer_number"))
                & ~Q(driver2_customer_number="")
            )
        )
        with_vehicle_count = (
            active_drivers.annotate(has_vehicle=Exists(assigned_vehicle))
            .filter(has_vehicle=True)
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

        return DriverSummaryDTO(
            active_count=active_drivers.count(),
            decommissioned_count=decommissioned_count,
            with_vehicle_count=with_vehicle_count,
            last_sap_sync_at=last_sap_sync.finished_at if last_sap_sync else None,
        )
