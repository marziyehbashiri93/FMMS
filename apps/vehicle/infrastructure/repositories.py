"""Concrete Django ORM implementation of IVehicleRepository.

This class is the Anti-Corruption Layer between the domain and the database.
It maps ORM model instances to domain entities and vice versa.
The domain layer never sees Django ORM objects.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from apps.vehicle.domain.entities import Vehicle, VehicleCategory, VehicleStatus
from apps.vehicle.domain.exceptions import VehicleNotFoundError
from apps.vehicle.domain.interfaces.vehicle_repository import IVehicleRepository
from apps.vehicle.domain.value_objects import (
    VIN,
    ChassisNumber,
    PlateNumber,
    SAPEquipmentNumber,
)
from apps.vehicle.infrastructure.models import VehicleModel
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
        plate_number=PlateNumber(orm.plate_number),
        vin=VIN(orm.vin),
        make=orm.make,
        model=orm.model,
        year=orm.year,
        category=VehicleCategory(orm.category),
        status=VehicleStatus(orm.status),
        created_at=orm.created_at,
        updated_at=orm.updated_at,
        chassis_number=(
            ChassisNumber(orm.chassis_number) if orm.chassis_number else None
        ),
        sap_equipment_number=(
            SAPEquipmentNumber(orm.sap_equipment_number)
            if orm.sap_equipment_number
            else None
        ),
    )


def _to_orm_dict(vehicle: Vehicle) -> dict[str, object]:
    """Map a Vehicle domain entity to a dict of ORM field values.

    Args:
        vehicle: The domain entity to map.

    Returns:
        A dict suitable for ``VehicleModel.objects.update_or_create(defaults=...)``.
    """
    return {
        "plate_number": vehicle.plate_number.value,
        "vin": vehicle.vin.value,
        "make": vehicle.make,
        "model": vehicle.model,
        "year": vehicle.year,
        "category": vehicle.category.value,
        "status": vehicle.status.value,
        "chassis_number": (
            vehicle.chassis_number.value if vehicle.chassis_number else ""
        ),
        "sap_equipment_number": (
            vehicle.sap_equipment_number.value if vehicle.sap_equipment_number else ""
        ),
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
                plate_number=plate_number.value, is_deleted=False
            )
        except VehicleModel.DoesNotExist:
            raise VehicleNotFoundError(plate_number.value) from None
        return _to_domain(orm)

    def get_by_sap_equipment_number(
        self, sap_equipment_number: SAPEquipmentNumber
    ) -> Vehicle | None:
        """Retrieve a vehicle by SAP equipment number, if linked.

        Args:
            sap_equipment_number: Validated SAP PM equipment number.

        Returns:
            The matching ``Vehicle`` domain entity, or ``None``.
        """
        logger.debug(
            "get_by_sap_equipment_number",
            extra={"sap_equipment_number": sap_equipment_number.value},
        )
        orm = VehicleModel.objects.filter(
            sap_equipment_number=sap_equipment_number.value,
            is_deleted=False,
        ).first()
        return _to_domain(orm) if orm else None

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
            plate_number=plate_number.value, is_deleted=False
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
