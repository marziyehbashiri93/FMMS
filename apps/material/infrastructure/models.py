"""Django ORM models for material requests."""

from __future__ import annotations

from decimal import Decimal

from django.db import models

from infrastructure.database.base_model import BaseModel


class MaterialRequestModel(BaseModel):
    """Persistence model for material requests."""

    repair_order_id = models.UUIDField(db_index=True)
    status = models.CharField(max_length=30, db_index=True)
    # Domain "requested_by" — cannot use created_by_id (BaseModel FK attname).
    requested_by_id = models.UUIDField()

    class Meta:
        app_label = "material"
        db_table = "material_request"
        indexes = [
            models.Index(
                fields=["repair_order_id", "is_deleted"], name="mr_repair_idx"
            ),
            models.Index(fields=["status", "is_deleted"], name="mr_status_idx"),
        ]


class MaterialRequestItemModel(models.Model):
    """Persistence model for material request items."""

    material_request = models.ForeignKey(
        MaterialRequestModel,
        on_delete=models.CASCADE,
        related_name="items",
    )
    item_id = models.UUIDField()
    material_number = models.CharField(max_length=18)
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    unit_of_measure = models.CharField(max_length=10)

    class Meta:
        app_label = "material"
        db_table = "material_request_item"


class InventoryTransactionModel(models.Model):
    """Placeholder inventory transaction for issued stock."""

    material_request_id = models.UUIDField(db_index=True)
    quantity = models.DecimalField(
        max_digits=12, decimal_places=3, default=Decimal("0")
    )
    transaction_type = models.CharField(max_length=30, default="STOCK_ISSUE")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "material"
        db_table = "inventory_transaction"
