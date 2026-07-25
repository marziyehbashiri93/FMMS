"""Concrete Django ORM implementation of IVehicleRepository.

This class is the Anti-Corruption Layer between the domain and the database.
It maps ORM model instances to domain entities and vice versa.
The domain layer never sees Django ORM objects.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from django.db.models import Q

from apps.vehicle.domain.entities import Vehicle, VehicleStatus
from apps.vehicle.domain.exceptions import VehicleNotFoundError
from apps.vehicle.domain.interfaces.vehicle_repository import IVehicleRepository
from apps.vehicle.domain.value_objects import PlateNumber, SAPVehicleNumber
from apps.vehicle.infrastructure.models import (
    VehicleDriverAssignmentHistoryModel,
    VehicleModel,
)
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger(domain="vehicle", module=__name__)

# Retired API_EQUIPMENT mock vehicles (plates EQ10000001 / EQ10000002).
_OBSOLETE_LEGACY_MOCK_VEHICLE_NUMBERS: frozenset[str] = frozenset(
    {"10000001", "10000002"}
)


def _to_domain(orm: VehicleModel) -> Vehicle:
    """Map a VehicleModel ORM instance to a Vehicle domain entity.

    Args:
        orm: The ORM model instance to map.

    Returns:
        A fully constructed ``Vehicle`` domain entity.
    """
    return Vehicle(
        id=uuid.UUID(str(orm.id)),
        vehicle_number=SAPVehicleNumber(orm.vehicle_number),
        license_plate=PlateNumber(orm.license_plate),
        status=VehicleStatus(orm.status),
        created_at=orm.created_at,
        updated_at=orm.updated_at,
        commissioning_date=orm.commissioning_date or None,
        driver1_customer_number=orm.driver1_customer_number or None,
        driver2_customer_number=orm.driver2_customer_number or None,
    )


def _to_orm_dict(vehicle: Vehicle) -> dict[str, object]:
    """Map a Vehicle domain entity to a dict of ORM field values.

    Args:
        vehicle: The domain entity to map.

    Returns:
        A dict suitable for ``VehicleModel.objects.update_or_create(defaults=...)``.
    """
    return {
        "vehicle_number": vehicle.vehicle_number.value,
        "license_plate": vehicle.license_plate.value,
        "commissioning_date": vehicle.commissioning_date or "",
        "driver1_customer_number": vehicle.driver1_customer_number or "",
        "driver2_customer_number": vehicle.driver2_customer_number or "",
        "status": vehicle.status.value,
        "is_deleted": False,
        "deleted_at": None,
        "updated_at": datetime.now(tz=UTC),
    }


class DjangoVehicleRepository(IVehicleRepository):
    """Concrete repository for Vehicle aggregates backed by Django ORM."""

    uses_transactions = True

    def get_by_id(self, vehicle_id: uuid.UUID) -> Vehicle:
        """Retrieve a vehicle by UUID.

        Args:
            vehicle_id: The UUID of the vehicle.

        Returns:
            The matching ``Vehicle`` domain entity.

        Raises:
            VehicleNotFoundError: If no vehicle exists with this ID.
        """
        logger.debug("get_by_id", extra={"vehicle_id": str(vehicle_id)})
        try:
            orm = VehicleModel.objects.get(id=vehicle_id)
        except VehicleModel.DoesNotExist:
            raise VehicleNotFoundError(vehicle_id) from None
        return _to_domain(orm)

    def get_by_vehicle_number(self, vehicle_number: SAPVehicleNumber) -> Vehicle | None:
        """Retrieve a vehicle by SAP VehicleNumber, if linked.

        Args:
            vehicle_number: Validated SAP VehicleNumber.

        Returns:
            The matching ``Vehicle`` domain entity, or ``None``.
        """
        logger.debug(
            "get_by_vehicle_number",
            extra={"vehicle_number": vehicle_number.value},
        )
        qs = VehicleModel.objects.filter(vehicle_number=vehicle_number.value)
        orm = qs.first()
        return _to_domain(orm) if orm else None

    def list_active(self) -> list[Vehicle]:
        """Return all ACTIVE vehicles.

        Returns:
            A list of active ``Vehicle`` domain entities.
        """
        qs = VehicleModel.objects.filter(status=VehicleStatus.ACTIVE.value)
        return [_to_domain(orm) for orm in qs]

    def list_by_status(self, status: VehicleStatus) -> list[Vehicle]:
        """Return all vehicles matching a given status.

        Args:
            status: The ``VehicleStatus`` to filter by.

        Returns:
            A list of matching ``Vehicle`` domain entities.
        """
        qs = VehicleModel.objects.filter(status=status.value)
        return [_to_domain(orm) for orm in qs]

    def list_filtered(
        self,
        *,
        status: VehicleStatus | None = None,
        ordering: str = "",
        search: str = "",
    ) -> list[Vehicle]:
        """Return vehicles filtered and ordered by database query.

        When ``status`` is omitted, all non-deleted vehicles are returned so
        the UI ``همه وضعیت‌ها`` filter and plate/number search cover the full
        fleet (not only ``ACTIVE``).
        """
        qs = VehicleModel.objects.filter(is_deleted=False)
        if status is not None:
            qs = qs.filter(status=status.value)
        needle = search.strip()
        if needle:
            qs = qs.filter(
                Q(license_plate__icontains=needle)
                | Q(vehicle_number__icontains=needle)
            )
        if ordering:
            qs = qs.order_by(ordering)
        return [_to_domain(orm) for orm in qs]

    def save(self, vehicle: Vehicle) -> Vehicle:
        """Persist a new or updated vehicle.

        Uses ``update_or_create`` keyed on ``id`` so this method is idempotent.

        Args:
            vehicle: The ``Vehicle`` domain entity to persist.

        Returns:
            The same ``Vehicle`` entity (unchanged).

        Raises:
            IntegrityError: If another vehicle already holds the same SAP key.
        """
        logger.debug("save", extra={"vehicle_id": str(vehicle.id)})
        defaults = _to_orm_dict(vehicle)
        obj, created = VehicleModel.objects.update_or_create(
            id=vehicle.id,
            defaults=defaults,
        )
        if created:
            obj.created_at = vehicle.created_at
            obj.save(update_fields=["created_at"])
        logger.debug(
            "saved",
            extra={"vehicle_id": str(vehicle.id), "is_new": created},
        )
        return vehicle

    def decommission_missing_from_sap(self, seen_vehicle_numbers: set[str]) -> int:
        """Mark vehicles absent from SAP as DECOMMISSIONED without soft-delete.

        Also hard-deletes retired demo equipment rows (``10000001`` /
        ``10000002`` / ``EQ…`` plates) left over from the old
        ``API_EQUIPMENT`` mock so they never reappear in the vehicle list.
        """
        now = datetime.now(tz=UTC)
        qs = VehicleModel.objects.exclude(
            status=VehicleStatus.DECOMMISSIONED.value
        ).exclude(vehicle_number="")
        if seen_vehicle_numbers:
            qs = qs.exclude(vehicle_number__in=seen_vehicle_numbers)
        updated = qs.update(
            status=VehicleStatus.DECOMMISSIONED.value,
            updated_at=now,
        )
        VehicleModel.objects.filter(
            vehicle_number__in=_OBSOLETE_LEGACY_MOCK_VEHICLE_NUMBERS
        ).delete()
        return updated

    def record_driver_assignment_snapshot(
        self,
        *,
        vehicle: Vehicle,
        sync_run_id: uuid.UUID,
        synced_at: datetime,
        request_id: str = "",
    ) -> None:
        """Persist both SAP driver roles for one vehicle sync occurrence."""
        VehicleDriverAssignmentHistoryModel.objects.bulk_create(
            [
                VehicleDriverAssignmentHistoryModel(
                    sync_run_id=sync_run_id,
                    request_id=request_id,
                    synced_at=synced_at,
                    vehicle_id=vehicle.id,
                    vehicle_number=vehicle.vehicle_number.value,
                    license_plate=vehicle.license_plate.value,
                    driver_role=VehicleDriverAssignmentHistoryModel.DriverRole.DRIVER,
                    driver_customer_number=vehicle.driver1_customer_number or "",
                ),
                VehicleDriverAssignmentHistoryModel(
                    sync_run_id=sync_run_id,
                    request_id=request_id,
                    synced_at=synced_at,
                    vehicle_id=vehicle.id,
                    vehicle_number=vehicle.vehicle_number.value,
                    license_plate=vehicle.license_plate.value,
                    driver_role=(
                        VehicleDriverAssignmentHistoryModel.DriverRole.ASSISTANT
                    ),
                    driver_customer_number=vehicle.driver2_customer_number or "",
                ),
            ]
        )
