"""Add central warehouse stock cache for ZI_STOCK_KH08_CDS sync."""

from __future__ import annotations

import uuid
from decimal import Decimal

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    """Create ``central_stock`` table for SAP KH08 inventory snapshot."""

    dependencies = [
        ("material", "0002_alter_inventorytransactionmodel_id_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CentralStockModel",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("material", models.CharField(db_index=True, max_length=40)),
                ("plant", models.CharField(db_index=True, max_length=10)),
                ("storage_location", models.CharField(db_index=True, max_length=10)),
                (
                    "inventory_stock_type",
                    models.CharField(db_index=True, max_length=10),
                ),
                ("material_code", models.CharField(db_index=True, max_length=40)),
                ("inventory_stock_type_text", models.CharField(max_length=100)),
                (
                    "quantity",
                    models.DecimalField(
                        decimal_places=3, default=Decimal("0"), max_digits=18
                    ),
                ),
                ("base_unit", models.CharField(max_length=10)),
                (
                    "stock_value",
                    models.DecimalField(
                        decimal_places=2, default=Decimal("0"), max_digits=18
                    ),
                ),
                ("display_currency", models.CharField(default="", max_length=5)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        help_text="User who created this record.",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(app_label)s_%(class)s_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "deleted_by",
                    models.ForeignKey(
                        blank=True,
                        help_text="User who soft-deleted this record.",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(app_label)s_%(class)s_deleted",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        help_text="User who last updated this record.",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(app_label)s_%(class)s_updated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Central Stock",
                "verbose_name_plural": "Central Stock",
                "db_table": "central_stock",
            },
        ),
        migrations.AddConstraint(
            model_name="centralstockmodel",
            constraint=models.UniqueConstraint(
                condition=models.Q(("is_deleted", False)),
                fields=(
                    "material",
                    "plant",
                    "storage_location",
                    "inventory_stock_type",
                ),
                name="unique_active_central_stock_sap_key",
            ),
        ),
        migrations.AddIndex(
            model_name="centralstockmodel",
            index=models.Index(
                fields=["is_active", "is_deleted"],
                name="central_stock_active_del_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="centralstockmodel",
            index=models.Index(
                fields=["plant", "storage_location"],
                name="central_stock_plant_sloc_idx",
            ),
        ),
    ]
