"""Services for reading SAP driver-assignment history snapshots."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from django.db.models import QuerySet

from apps.driver.domain.interfaces.driver_repository import IDriverRepository
from apps.vehicle.application.dto.vehicle_dto import (
    VehicleDriverAssignmentHistoryResponseDTO,
)
from apps.vehicle.domain.interfaces.vehicle_repository import IVehicleRepository
from apps.vehicle.infrastructure.models import VehicleDriverAssignmentHistoryModel
from core.exceptions.translation import load_or_not_found


class ListVehicleDriverAssignmentHistoryService:
    """List historical SAP driver assignments for one vehicle."""

    def __init__(self, vehicle_repository: IVehicleRepository) -> None:
        self._vehicle_repo = vehicle_repository

    def execute(
        self,
        vehicle_id: uuid.UUID,
        *,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[VehicleDriverAssignmentHistoryResponseDTO]:
        """Return assignment snapshots for ``vehicle_id`` in an optional date range."""
        load_or_not_found(
            lambda: self._vehicle_repo.get_by_id(vehicle_id),
            message=f"Vehicle '{vehicle_id}' not found.",
            details={"vehicle_id": str(vehicle_id)},
        )
        qs = VehicleDriverAssignmentHistoryModel.objects.filter(
            vehicle_id=vehicle_id,
            is_deleted=False,
        )
        qs = _apply_sync_date_filters(qs, from_date, to_date)
        return [
            _to_response_dto(obj) for obj in qs.order_by("-synced_at", "driver_role")
        ]


class ListDriverVehicleAssignmentHistoryService:
    """List historical SAP vehicle assignments for one driver."""

    def __init__(self, driver_repository: IDriverRepository) -> None:
        self._driver_repo = driver_repository

    def execute(
        self,
        driver_id: uuid.UUID,
        *,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[VehicleDriverAssignmentHistoryResponseDTO]:
        """Return vehicle assignment snapshots for ``driver_id`` in a date range."""
        driver = load_or_not_found(
            lambda: self._driver_repo.get_by_id(driver_id),
            message=f"Driver '{driver_id}' not found.",
            details={"driver_id": str(driver_id)},
        )
        qs = VehicleDriverAssignmentHistoryModel.objects.filter(
            driver_customer_number=driver.customer_number.value,
            is_deleted=False,
        )
        qs = _apply_sync_date_filters(qs, from_date, to_date)
        return [
            _to_response_dto(obj) for obj in qs.order_by("-synced_at", "vehicle_number")
        ]


def _apply_sync_date_filters(
    qs: QuerySet[Any, VehicleDriverAssignmentHistoryModel],
    from_date: date | None,
    to_date: date | None,
) -> QuerySet[Any, VehicleDriverAssignmentHistoryModel]:
    """Apply optional date filters to a driver-assignment queryset."""
    if from_date is not None:
        qs = qs.filter(synced_at__date__gte=from_date)
    if to_date is not None:
        qs = qs.filter(synced_at__date__lte=to_date)
    return qs


def _to_response_dto(
    obj: VehicleDriverAssignmentHistoryModel,
) -> VehicleDriverAssignmentHistoryResponseDTO:
    """Map an assignment history ORM row to an API-safe DTO."""
    return VehicleDriverAssignmentHistoryResponseDTO(
        id=obj.id,
        sync_run_id=obj.sync_run_id,
        request_id=obj.request_id,
        synced_at=obj.synced_at,
        vehicle_id=obj.vehicle_id,
        vehicle_number=obj.vehicle_number,
        license_plate=obj.license_plate,
        driver_role=obj.driver_role,
        driver_customer_number=obj.driver_customer_number or None,
    )
