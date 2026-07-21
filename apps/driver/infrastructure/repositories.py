"""Concrete Django ORM implementation of IDriverRepository."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from apps.driver.domain.entities import Driver, DriverStatus
from apps.driver.domain.exceptions import DriverNotFoundError
from apps.driver.domain.interfaces.driver_repository import IDriverRepository
from apps.driver.domain.value_objects import CustomerNumber
from apps.driver.infrastructure.models import DriverModel
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger(domain="driver", module=__name__)


def _to_domain(orm: DriverModel) -> Driver:
    """Map a DriverModel ORM instance to a Driver domain entity."""
    return Driver(
        id=uuid.UUID(str(orm.id)),
        customer_number=CustomerNumber(orm.customer_number),
        name=orm.name,
        status=DriverStatus(orm.status),
        created_at=orm.created_at,
        updated_at=orm.updated_at,
        mobile=orm.mobile or None,
        personnel_number=orm.personnel_number or None,
        gender=orm.gender or None,
        nilofar_code=orm.nilofar_code or None,
    )


def _to_orm_dict(driver: Driver) -> dict[str, object]:
    """Map a Driver domain entity to ORM field values."""
    return {
        "customer_number": driver.customer_number.value,
        "name": driver.name,
        "mobile": driver.mobile or "",
        "personnel_number": driver.personnel_number or "",
        "gender": driver.gender or "",
        "nilofar_code": driver.nilofar_code or "",
        "status": driver.status.value,
        "updated_at": datetime.now(tz=UTC),
    }


class DjangoDriverRepository(IDriverRepository):
    """Concrete repository for Driver aggregates backed by Django ORM."""

    def get_by_id(self, driver_id: uuid.UUID) -> Driver:
        """Retrieve a driver by UUID."""
        try:
            orm = DriverModel.objects.get(id=driver_id)
        except DriverModel.DoesNotExist:
            raise DriverNotFoundError(driver_id) from None
        return _to_domain(orm)

    def get_by_customer_number(self, customer_number: CustomerNumber) -> Driver:
        """Retrieve a driver by SAP customer number."""
        try:
            orm = DriverModel.objects.get(customer_number=customer_number.value)
        except DriverModel.DoesNotExist:
            raise DriverNotFoundError(customer_number.value) from None
        return _to_domain(orm)

    def list_by_status(self, status: DriverStatus) -> list[Driver]:
        """Return all drivers matching a given status."""
        qs = DriverModel.objects.filter(status=status.value)
        return [_to_domain(orm) for orm in qs]

    def list_all(self) -> list[Driver]:
        """Return all drivers regardless of status."""
        return [_to_domain(orm) for orm in DriverModel.objects.all()]

    def list_by_customer_numbers(self, customer_numbers: set[str]) -> list[Driver]:
        """Return drivers matching the provided SAP customer numbers."""
        if not customer_numbers:
            return []
        qs = DriverModel.objects.filter(customer_number__in=customer_numbers)
        return [_to_domain(orm) for orm in qs]

    def decommission_missing_from_sap(self, seen_customer_numbers: set[str]) -> int:
        """Mark drivers absent from SAP as DECOMMISSIONED without soft-delete."""
        now = datetime.now(tz=UTC)
        qs = DriverModel.objects.exclude(
            status=DriverStatus.DECOMMISSIONED.value
        ).exclude(customer_number__in=seen_customer_numbers)
        return qs.update(
            status=DriverStatus.DECOMMISSIONED.value,
            updated_at=now,
        )

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
