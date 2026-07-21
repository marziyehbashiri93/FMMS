"""Django ORM models for the Vehicle bounded context.

These models are the persistence layer only. Business logic lives in
``apps.vehicle.domain.entities``. No domain rules are enforced here.
"""

from __future__ import annotations

from django.db import models

from infrastructure.database.base_model import BaseModel


class VehicleModel(BaseModel):
    """Persistence model for a SAP-sourced fleet vehicle.

    Stores all vehicle attributes as flat fields. Cross-domain references
    (e.g. repair orders) are resolved at the repository or service layer —
    never through Django ForeignKey to other app models.

    TODO: Split SAP master-data models from ``BaseModel`` once the shared audit
    model is reviewed. Vehicles are never deleted by FMMS, so ``is_deleted`` is
    inherited for now but must not drive business visibility.

    Attributes:
        vehicle_number: SAP ``VehicleNumber`` and unique vehicle identifier.
        license_plate: SAP ``LicensePlate``.
        commissioning_date: SAP ``CommissioningDate`` in source format.
        driver1_customer_number: SAP customer number for the main driver.
        driver2_customer_number: SAP customer number for the assistant driver.
        status: Current lifecycle status.
    """

    vehicle_number = models.CharField(max_length=18, db_index=True)
    license_plate = models.CharField(max_length=20, db_index=True)
    commissioning_date = models.CharField(max_length=8, blank=True, default="")
    driver1_customer_number = models.CharField(
        max_length=20, blank=True, default="", db_index=True
    )
    driver2_customer_number = models.CharField(
        max_length=20, blank=True, default="", db_index=True
    )
    status = models.CharField(max_length=30, db_index=True)

    class Meta:
        app_label = "vehicle"
        db_table = "vehicle"
        verbose_name = "Vehicle"
        verbose_name_plural = "Vehicles"
        constraints = [
            models.UniqueConstraint(
                fields=["license_plate"],
                name="unique_vehicle_license_plate",
            ),
            models.UniqueConstraint(
                fields=["vehicle_number"],
                name="unique_vehicle_number",
            ),
        ]
        indexes = [
            models.Index(fields=["status"], name="vehicle_status_idx"),
            models.Index(fields=["vehicle_number"], name="vehicle_number_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.vehicle_number} ({self.license_plate})"


class VehicleDriverAssignmentHistoryModel(BaseModel):
    """SAP driver assignment snapshot captured during every vehicle sync."""

    class DriverRole(models.TextChoices):
        DRIVER = "DRIVER", "Driver"
        ASSISTANT = "ASSISTANT", "Assistant"

    sync_run_id = models.UUIDField(db_index=True)
    request_id = models.CharField(max_length=100, blank=True, default="")
    synced_at = models.DateTimeField(db_index=True)
    vehicle_id = models.UUIDField(db_index=True)
    vehicle_number = models.CharField(max_length=18, db_index=True)
    license_plate = models.CharField(max_length=20, blank=True, default="")
    driver_role = models.CharField(
        max_length=20,
        choices=DriverRole.choices,
        db_index=True,
    )
    driver_customer_number = models.CharField(
        max_length=20, blank=True, default="", db_index=True
    )

    class Meta:
        app_label = "vehicle"
        db_table = "vehicle_driver_assignment_history"
        verbose_name = "Vehicle Driver Assignment History"
        verbose_name_plural = "Vehicle Driver Assignment Histories"
        indexes = [
            models.Index(
                fields=["vehicle_number", "synced_at"],
                name="veh_drv_hist_vehicle_time_idx",
            ),
            models.Index(
                fields=["driver_customer_number", "synced_at"],
                name="veh_drv_hist_driver_time_idx",
            ),
            models.Index(
                fields=["sync_run_id", "vehicle_number"],
                name="veh_drv_hist_run_vehicle_idx",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.synced_at.isoformat()} {self.vehicle_number} "
            f"{self.driver_role}: {self.driver_customer_number or '-'}"
        )


class VehicleOdometerReadingModel(BaseModel):
    """Daily odometer reading recorded inside FMMS by operational users."""

    vehicle_id = models.UUIDField(db_index=True)
    reading_date = models.DateField(db_index=True)
    odometer_km = models.PositiveIntegerField()
    source = models.CharField(max_length=30, default="DRIVER")
    recorded_by_id = models.UUIDField()
    recorded_at = models.DateTimeField()

    class Meta:
        app_label = "vehicle"
        db_table = "vehicle_odometer_reading"
        verbose_name = "Vehicle Odometer Reading"
        verbose_name_plural = "Vehicle Odometer Readings"
        constraints = [
            models.UniqueConstraint(
                fields=["vehicle_id", "reading_date"],
                condition=models.Q(is_deleted=False),
                name="unique_vehicle_odometer_per_day",
            ),
        ]
        indexes = [
            models.Index(
                fields=["vehicle_id", "reading_date", "is_deleted"],
                name="vehicle_odo_vehicle_date_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.vehicle_id} {self.reading_date}: {self.odometer_km} km"
