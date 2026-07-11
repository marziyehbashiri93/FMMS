"""Django ORM models for the Vehicle bounded context.

These models are the persistence layer only. Business logic lives in
``apps.vehicle.domain.entities``. No domain rules are enforced here.
"""

from __future__ import annotations

from django.db import models

from infrastructure.database.base_model import BaseModel


class VehicleModel(BaseModel):
    """Persistence model for a fleet vehicle.

    Stores all vehicle attributes as flat fields. Cross-domain references
    (e.g. repair orders) are resolved at the repository or service layer —
    never through Django ForeignKey to other app models.

    Attributes:
        plate_number: Unique vehicle plate number (max 20 chars).
        vin: 17-character Vehicle Identification Number.
        chassis_number: Optional chassis number (max 50 chars).
        sap_equipment_number: Optional SAP PM equipment number (max 18 digits).
        make: Manufacturer name.
        model: Vehicle model name.
        year: Manufacturing year.
        category: Vehicle category (LIGHT, HEAVY, MOTORCYCLE, SPECIAL).
        status: Current lifecycle status (ACTIVE, INACTIVE, UNDER_REPAIR, SUSPENDED).
    """

    plate_number = models.CharField(max_length=20, db_index=True)
    vin = models.CharField(max_length=17, db_index=True)
    chassis_number = models.CharField(max_length=50, blank=True, default="")
    sap_equipment_number = models.CharField(
        max_length=18, blank=True, default="", db_index=True
    )
    make = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    year = models.PositiveSmallIntegerField()
    category = models.CharField(max_length=20)
    status = models.CharField(max_length=30, db_index=True)

    class Meta:
        app_label = "vehicle"
        db_table = "vehicle"
        verbose_name = "Vehicle"
        verbose_name_plural = "Vehicles"
        constraints = [
            models.UniqueConstraint(
                fields=["plate_number"],
                condition=models.Q(is_deleted=False),
                name="unique_active_plate_number",
            ),
        ]
        indexes = [
            models.Index(
                fields=["status", "is_deleted"], name="vehicle_status_deleted_idx"
            ),
            models.Index(fields=["sap_equipment_number"], name="vehicle_sap_eq_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.plate_number} ({self.make} {self.model})"
