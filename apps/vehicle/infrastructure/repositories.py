"""Concrete Django ORM implementation of IVehicleRepository.

This class is the Anti-Corruption Layer between the domain and the database.
It maps ORM model instances to domain entities and vice versa.
The domain layer never sees Django ORM objects.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

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
    """Concrete repository for Vehicle aggregates backed by Django ORM.

    Soft-delete is transparent: every read filters ``is_deleted=False``.
    All public methods accept and return domain entities exclusively.
    """

    def get_by_id(self, vehicle_id: uuid.UUID) -> Vehicle:
        """Retrieve a vehicle by UUID.

        Args:
            vehicle_id: The UUID of the vehicle.

        Returns:
            The matching ``Vehicle`` domain entity.

        Raises:
            VehicleNotFoundError: If no active vehicle exists with this ID.
        """
        logger.debug("get_by_id", extra={"vehicle_id": str(vehicle_id)})
        try:
            orm = VehicleModel.objects.get(id=vehicle_id, is_deleted=False)
        except VehicleModel.DoesNotExist:
            raise VehicleNotFoundError(vehicle_id) from None
        return _to_domain(orm)

    def get_by_plate(self, plate_number: PlateNumber) -> Vehicle:
        """Retrieve a vehicle by plate number.

        Args:
            plate_number: The validated ``PlateNumber`` value object.

        Returns:
            The matching ``Vehicle`` domain entity.

        Raises:
            VehicleNotFoundError: If no active vehicle with this plate exists.
        """
        logger.debug("get_by_plate", extra={"plate_number": plate_number.value})
        try:
            orm = VehicleModel.objects.get(
                license_plate=plate_number.value, is_deleted=False
            )
        except VehicleModel.DoesNotExist:
            raise VehicleNotFoundError(plate_number.value) from None
        return _to_domain(orm)

    def get_by_vehicle_number(
        self, vehicle_number: SAPVehicleNumber, include_deleted: bool = False
    ) -> Vehicle | None:
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
        if not include_deleted:
            qs = qs.filter(is_deleted=False)
        orm = qs.first()
        return _to_domain(orm) if orm else None

    def list_vehicle_numbers(self) -> set[str]:
        """Return all non-empty SAP VehicleNumber values stored locally."""
        return set(
            VehicleModel.objects.exclude(vehicle_number="").values_list(
                "vehicle_number", flat=True
            )
        )

    def list_active(self) -> list[Vehicle]:
        """Return all ACTIVE vehicles.

        Returns:
            A list of active ``Vehicle`` domain entities.
        """
        qs = VehicleModel.objects.filter(
            status=VehicleStatus.ACTIVE.value, is_deleted=False
        )
        return [_to_domain(orm) for orm in qs]

    def list_by_status(self, status: VehicleStatus) -> list[Vehicle]:
        """Return all vehicles matching a given status.

        Args:
            status: The ``VehicleStatus`` to filter by.

        Returns:
            A list of matching ``Vehicle`` domain entities.
        """
        qs = VehicleModel.objects.filter(status=status.value, is_deleted=False)
        return [_to_domain(orm) for orm in qs]

    def exists_by_plate(self, plate_number: PlateNumber) -> bool:
        """Check whether a non-deleted vehicle with the given plate exists.

        Args:
            plate_number: The plate number to check.

        Returns:
            ``True`` if a vehicle with this plate exists.
        """
        return VehicleModel.objects.filter(
            license_plate=plate_number.value, is_deleted=False
        ).exists()

    def save(self, vehicle: Vehicle) -> Vehicle:
        """Persist a new or updated vehicle.

        Uses ``update_or_create`` keyed on ``id`` so this method is idempotent.

        Args:
            vehicle: The ``Vehicle`` domain entity to persist.

        Returns:
            The same ``Vehicle`` entity (unchanged).

        Raises:
            VehicleAlreadyExistsError: If a different vehicle already holds
                this plate number (unique constraint violation).
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

    def delete(self, vehicle_id: uuid.UUID) -> None:
        """Soft-delete a vehicle record.

        Args:
            vehicle_id: UUID of the vehicle to delete.

        Raises:
            VehicleNotFoundError: If no active vehicle exists with this ID.
        """
        logger.debug("delete", extra={"vehicle_id": str(vehicle_id)})
        updated = VehicleModel.objects.filter(id=vehicle_id, is_deleted=False).update(
            is_deleted=True,
            deleted_at=datetime.now(tz=UTC),
        )
        if updated == 0:
            raise VehicleNotFoundError(vehicle_id)

    def decommission_missing_from_sap(self, seen_vehicle_numbers: set[str]) -> int:
        """Soft-delete vehicles whose SAP VehicleNumber was not returned by SAP."""
        now = datetime.now(tz=UTC)
        qs = VehicleModel.objects.filter(is_deleted=False).exclude(vehicle_number="")
        if seen_vehicle_numbers:
            qs = qs.exclude(vehicle_number__in=seen_vehicle_numbers)
        return qs.update(
            status=VehicleStatus.DECOMMISSIONED.value,
            is_deleted=True,
            deleted_at=now,
            updated_at=now,
        )

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
