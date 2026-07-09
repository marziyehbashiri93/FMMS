"""Concrete Django ORM implementation of IDriverRepository."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from apps.driver.domain.entities import Driver, DriverStatus
from apps.driver.domain.exceptions import DriverNotFoundError
from apps.driver.domain.interfaces.driver_repository import IDriverRepository
from apps.driver.domain.value_objects import DriverContact, LicenseClass, LicenseNumber
from apps.driver.infrastructure.models import DriverModel
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger(domain="driver", module=__name__)


def _to_domain(orm: DriverModel) -> Driver:
    """Map a DriverModel ORM instance to a Driver domain entity."""
    return Driver(
        id=uuid.UUID(str(orm.id)),
        full_name=orm.full_name,
        license_number=LicenseNumber(orm.license_number),
        license_class=LicenseClass(orm.license_class),
        contact=DriverContact(phone=orm.phone, email=orm.email or None),
        status=DriverStatus(orm.status),
        created_at=orm.created_at,
        updated_at=orm.updated_at,
        assigned_vehicle_id=orm.assigned_vehicle_id,
    )


def _to_orm_dict(driver: Driver) -> dict[str, object]:
    """Map a Driver domain entity to ORM field values."""
    return {
        "full_name": driver.full_name,
        "license_number": driver.license_number.value,
        "license_class": driver.license_class.value,
        "phone": driver.contact.phone,
        "email": driver.contact.email or "",
        "status": driver.status.value,
        "assigned_vehicle_id": driver.assigned_vehicle_id,
        "updated_at": datetime.now(tz=UTC),
    }


class DjangoDriverRepository(IDriverRepository):
    """Concrete repository for Driver aggregates backed by Django ORM."""

    def get_by_id(self, driver_id: uuid.UUID) -> Driver:
        """Retrieve a driver by UUID."""
        try:
            orm = DriverModel.objects.get(id=driver_id, is_deleted=False)
        except DriverModel.DoesNotExist:
            raise DriverNotFoundError(driver_id) from None
        return _to_domain(orm)

    def get_by_license(self, license_number: LicenseNumber) -> Driver:
        """Retrieve a driver by license number."""
        try:
            orm = DriverModel.objects.get(
                license_number=license_number.value, is_deleted=False
            )
        except DriverModel.DoesNotExist:
            raise DriverNotFoundError(license_number.value) from None
        return _to_domain(orm)

    def get_by_vehicle(self, vehicle_id: uuid.UUID) -> Driver | None:
        """Retrieve the driver currently assigned to a vehicle."""
        orm = DriverModel.objects.filter(
            assigned_vehicle_id=vehicle_id,
            status=DriverStatus.ACTIVE.value,
            is_deleted=False,
        ).first()
        return _to_domain(orm) if orm else None

    def list_by_status(self, status: DriverStatus) -> list[Driver]:
        """Return all drivers matching a given status."""
        qs = DriverModel.objects.filter(status=status.value, is_deleted=False)
        return [_to_domain(orm) for orm in qs]

    def exists_by_license(self, license_number: LicenseNumber) -> bool:
        """Check whether a driver with the given license number exists."""
        return DriverModel.objects.filter(
            license_number=license_number.value, is_deleted=False
        ).exists()

    def save(self, driver: Driver) -> Driver:
        """Persist a new or updated driver."""
        obj, created = DriverModel.objects.update_or_create(
            id=driver.id,
            defaults=_to_orm_dict(driver),
        )
        if created:
            obj.created_at = driver.created_at
            obj.save(update_fields=["created_at"])
        logger.debug("saved", extra={"driver_id": str(driver.id), "is_new": created})
        return driver

    def delete(self, driver_id: uuid.UUID) -> None:
        """Soft-delete a driver record."""
        updated = DriverModel.objects.filter(id=driver_id, is_deleted=False).update(
            is_deleted=True,
            deleted_at=datetime.now(tz=UTC),
        )
        if updated == 0:
            raise DriverNotFoundError(driver_id)
