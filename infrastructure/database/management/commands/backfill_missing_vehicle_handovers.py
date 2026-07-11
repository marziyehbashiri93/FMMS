"""Management command: backfill VehicleHandover rows for orphaned repair orders.

Repairs inconsistent rows where ``RepairOrder.status`` is
``WAITING_DRIVER_CONFIRMATION`` but no ``VehicleHandover`` exists — typically
caused by partial commits before vehicle state-machine and transaction fixes.
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Exists, OuterRef

from apps.handover.infrastructure.models import VehicleHandoverModel
from apps.repair.application.services._timeline_helper import (
    record_repair_timeline_event,
)
from apps.repair.domain.entities import RepairOrderEventType, RepairOrderStatus
from apps.repair.infrastructure.models import RepairOrderEventModel, RepairOrderModel
from apps.vehicle.domain.entities import VehicleStatus
from apps.vehicle.infrastructure.models import VehicleModel
from interfaces.api.v1 import deps


class Command(BaseCommand):
    """Create missing handovers and align vehicle status for waiting repair orders."""

    help = (
        "Backfill VehicleHandover records for repair orders in "
        "WAITING_DRIVER_CONFIRMATION that have no linked handover."
    )

    def add_arguments(self, parser: Any) -> None:
        """Register CLI flags."""
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report rows that would be repaired without writing.",
        )

    def handle(self, *args: object, **options: object) -> None:
        """Execute the backfill."""
        dry_run = bool(options.get("dry_run"))
        orphans = self._orphaned_repair_orders()

        self.stdout.write(
            f"Found {orphans.count()} repair order(s) waiting on driver without handover."
        )
        if dry_run:
            for row in orphans:
                vehicle = VehicleModel.objects.filter(id=row.vehicle_id).first()
                vehicle_status = vehicle.status if vehicle else "MISSING"
                self.stdout.write(
                    f"  - repair_order={row.id} vehicle={row.vehicle_id} "
                    f"vehicle_status={vehicle_status}"
                )
            self.stdout.write(self.style.NOTICE("Dry run — no changes written."))
            return

        repaired = 0
        for row in orphans:
            with transaction.atomic():
                self._repair_row(row)
            repaired += 1

        self.stdout.write(self.style.SUCCESS(f"Repaired {repaired} repair order(s)."))

    def _orphaned_repair_orders(self) -> Any:
        """Return repair orders waiting on driver with no handover row."""
        handover_exists = VehicleHandoverModel.objects.filter(
            repair_order_id=OuterRef("pk"),
            is_deleted=False,
        )
        return (
            RepairOrderModel.objects.filter(
                status=RepairOrderStatus.WAITING_DRIVER_CONFIRMATION.value,
                is_deleted=False,
            )
            .annotate(has_handover=Exists(handover_exists))
            .filter(has_handover=False)
        )

    def _repair_row(self, row: RepairOrderModel) -> None:
        """Create handover, align vehicle status, and backfill missing events."""
        create_handover = deps.get_create_vehicle_handover_service()
        create_handover.execute(
            repair_order_id=row.id,
            vehicle_id=row.vehicle_id,
        )

        vehicle_repo = deps.get_vehicle_repository()
        vehicle = vehicle_repo.get_by_id(row.vehicle_id)
        if vehicle.status != VehicleStatus.WAITING_DRIVER_CONFIRMATION:
            if vehicle.status == VehicleStatus.INACTIVE:
                vehicle.mark_under_repair()
            vehicle.mark_waiting_driver_confirmation()
        vehicle_repo.save(vehicle)

        event_recorder = deps.get_record_repair_order_event_service()
        existing_types = set(
            RepairOrderEventModel.objects.filter(
                repair_order_id=row.id,
                is_deleted=False,
            ).values_list("event_type", flat=True)
        )
        if RepairOrderEventType.REPAIR_COMPLETED.value not in existing_types:
            record_repair_timeline_event(
                event_recorder,
                row.id,
                RepairOrderEventType.REPAIR_COMPLETED,
                "تعمیر فنی تکمیل شد.",
            )
        if RepairOrderEventType.WAITING_DRIVER_CONFIRMATION.value not in existing_types:
            record_repair_timeline_event(
                event_recorder,
                row.id,
                RepairOrderEventType.WAITING_DRIVER_CONFIRMATION,
                "تعمیر انجام شد و در انتظار تایید راننده است.",
            )
