"""Django ORM models for the Driver bounded context."""

from __future__ import annotations

from django.db import models

from infrastructure.database.base_model import BaseModel


class DriverModel(BaseModel):
    """Persistence model for a fleet driver.

    The ``assigned_vehicle_id`` is a plain UUIDField — not a Django FK —
    to preserve domain boundary independence (Vehicle is a separate aggregate).
    """

    full_name = models.CharField(max_length=200)
    license_number = models.CharField(max_length=20, db_index=True)
    license_class = models.CharField(max_length=5)
    phone = models.CharField(max_length=20)
    email = models.CharField(max_length=254, blank=True, default="")
    status = models.CharField(max_length=20, db_index=True)
    assigned_vehicle_id = models.UUIDField(
        null=True, blank=True, default=None, db_index=True
    )

    class Meta:
        app_label = "driver"
        db_table = "driver"
        verbose_name = "Driver"
        verbose_name_plural = "Drivers"
        constraints = [
            models.UniqueConstraint(
                fields=["license_number"],
                condition=models.Q(is_deleted=False),
                name="unique_active_license_number",
            ),
        ]
        indexes = [
            models.Index(
                fields=["status", "is_deleted"], name="driver_status_deleted_idx"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.full_name} ({self.license_number})"
