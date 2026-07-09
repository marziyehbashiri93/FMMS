"""Django ORM models for the Fault bounded context."""

from __future__ import annotations

from django.db import models

from infrastructure.database.base_model import BaseModel


class FaultModel(BaseModel):
    """Persistence model for a vehicle fault aggregate root.

    Cross-domain references (vehicle, inspection) are UUIDFields — not FKs —
    to maintain aggregate boundary independence.
    """

    vehicle_id = models.UUIDField(db_index=True)
    code = models.CharField(max_length=20, db_index=True)
    description = models.CharField(max_length=500)
    reported_at = models.DateTimeField()
    severity = models.CharField(max_length=10, db_index=True)
    status = models.CharField(max_length=20, db_index=True)
    reported_by_id = models.UUIDField()
    inspection_id = models.UUIDField(null=True, blank=True, default=None)
    sap_defect_code = models.CharField(max_length=30, blank=True, default="")
    sap_notification_number = models.CharField(max_length=30, blank=True, default="")
    assigned_to_id = models.UUIDField(null=True, blank=True, default=None)

    class Meta:
        app_label = "fault"
        db_table = "fault"
        verbose_name = "Fault"
        verbose_name_plural = "Faults"
        indexes = [
            models.Index(
                fields=["vehicle_id", "status", "is_deleted"],
                name="fault_vehicle_status_idx",
            ),
            models.Index(
                fields=["severity", "status", "is_deleted"],
                name="fault_severity_status_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"Fault {self.id} [{self.severity}/{self.status}]"
