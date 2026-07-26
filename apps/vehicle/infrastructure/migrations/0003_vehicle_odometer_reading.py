# Generated manually for vehicle odometer history.

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("vehicle", "0002_vehicle_status_length_30"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="VehicleOdometerReadingModel",
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
                ("vehicle_id", models.UUIDField(db_index=True)),
                ("reading_date", models.DateField(db_index=True)),
                ("odometer_km", models.PositiveIntegerField()),
                ("source", models.CharField(default="DRIVER", max_length=30)),
                ("recorded_by_id", models.UUIDField()),
                ("recorded_at", models.DateTimeField()),
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
                "verbose_name": "Vehicle Odometer Reading",
                "verbose_name_plural": "Vehicle Odometer Readings",
                "db_table": "vehicle_odometer_reading",
                "indexes": [
                    models.Index(
                        fields=["vehicle_id", "reading_date", "is_deleted"],
                        name="vehicle_odo_vehicle_date_idx",
                    ),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        condition=models.Q(("is_deleted", False)),
                        fields=("vehicle_id", "reading_date"),
                        name="unique_vehicle_odometer_per_day",
                    ),
                ],
            },
        ),
    ]
