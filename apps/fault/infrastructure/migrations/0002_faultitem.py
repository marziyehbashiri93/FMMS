"""Add fault_item table for aggregated inspection failure components."""

from __future__ import annotations

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    """Create fault_item child records for multi-item fault incidents."""

    dependencies = [
        ("fault", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="FaultItemModel",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Unique record identifier (UUID4).",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="UTC timestamp when this record was created.",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        help_text="UTC timestamp of the last update to this record.",
                    ),
                ),
                (
                    "is_deleted",
                    models.BooleanField(
                        db_index=True,
                        default=False,
                        help_text="True if this record has been soft-deleted. Never physically remove records.",
                    ),
                ),
                (
                    "deleted_at",
                    models.DateTimeField(
                        blank=True,
                        help_text="UTC timestamp of soft deletion.",
                        null=True,
                    ),
                ),
                ("fault_id", models.UUIDField(db_index=True)),
                (
                    "inspection_item_id",
                    models.UUIDField(blank=True, default=None, null=True),
                ),
                ("component", models.CharField(max_length=100)),
                ("description", models.CharField(max_length=500)),
                ("severity", models.CharField(db_index=True, max_length=10)),
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
                "verbose_name": "Fault Item",
                "verbose_name_plural": "Fault Items",
                "db_table": "fault_item",
                "indexes": [
                    models.Index(
                        fields=["fault_id", "is_deleted"],
                        name="fault_item_fault_idx",
                    ),
                ],
            },
        ),
    ]
