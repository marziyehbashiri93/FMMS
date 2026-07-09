"""Django ORM models for the Repair bounded context.

RepairOrder is the aggregate root. RepairActivity and RepairPart are child
records that must not be accessed outside the repository boundary.
"""

from __future__ import annotations

from django.db import models

from infrastructure.database.base_model import BaseModel


class RepairOrderModel(BaseModel):
    """Persistence model for a repair order aggregate root.

    TechnicianAssignment is denormalized into two nullable columns rather
    than a separate table, as it is a small value object with no independent
    lifecycle.
    """

    vehicle_id = models.UUIDField(db_index=True)
    fault_id = models.UUIDField(db_index=True)
    status = models.CharField(max_length=20, db_index=True)
    # 'initiator_id' stores the domain-level "who created the order".
    # We cannot use 'created_by_id' as it is the auto-generated attname
    # of BaseModel.created_by (a ForeignKey).
    initiator_id = models.UUIDField()
    sap_order_number = models.CharField(max_length=30, blank=True, default="")
    completed_at = models.DateTimeField(null=True, blank=True, default=None)
    # TechnicianAssignment (value object — denormalized)
    assigned_technician_id = models.UUIDField(null=True, blank=True, default=None)
    assigned_at = models.DateTimeField(null=True, blank=True, default=None)

    class Meta:
        app_label = "repair"
        db_table = "repair_order"
        verbose_name = "Repair Order"
        verbose_name_plural = "Repair Orders"
        indexes = [
            models.Index(
                fields=["vehicle_id", "status", "is_deleted"],
                name="repair_vehicle_status_idx",
            ),
            models.Index(
                fields=["fault_id", "is_deleted"],
                name="repair_fault_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"RepairOrder {self.id} [{self.status}]"


class RepairActivityModel(models.Model):
    """Persistence model for a single repair activity within a repair order."""

    repair_order = models.ForeignKey(
        RepairOrderModel,
        on_delete=models.CASCADE,
        related_name="activities",
        db_index=True,
    )
    activity_id = models.UUIDField()
    description = models.CharField(max_length=500)
    labor_hours = models.DecimalField(max_digits=6, decimal_places=2)
    performed_by_id = models.UUIDField()
    performed_at = models.DateTimeField()
    notes = models.TextField(blank=True, default="")

    class Meta:
        app_label = "repair"
        db_table = "repair_activity"
        verbose_name = "Repair Activity"
        verbose_name_plural = "Repair Activities"
        constraints = [
            models.UniqueConstraint(
                fields=["repair_order", "activity_id"],
                name="unique_repair_activity",
            )
        ]


class RepairPartModel(models.Model):
    """Persistence model for a spare part consumed during a repair order."""

    repair_order = models.ForeignKey(
        RepairOrderModel,
        on_delete=models.CASCADE,
        related_name="parts",
        db_index=True,
    )
    part_id = models.UUIDField()
    material_number = models.CharField(max_length=18)
    quantity = models.PositiveIntegerField()
    unit_of_measure = models.CharField(max_length=10)
    goods_issue_id = models.UUIDField(null=True, blank=True, default=None)
    posted_at = models.DateTimeField(null=True, blank=True, default=None)

    class Meta:
        app_label = "repair"
        db_table = "repair_part"
        verbose_name = "Repair Part"
        verbose_name_plural = "Repair Parts"
        constraints = [
            models.UniqueConstraint(
                fields=["repair_order", "part_id"],
                name="unique_repair_part",
            )
        ]
