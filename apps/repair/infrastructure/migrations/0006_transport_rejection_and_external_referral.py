import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
import uuid


class Migration(migrations.Migration):
    dependencies = [
        ("repair", "0005_repair_order_status_length_40"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="repairordermodel",
            name="transport_rejection_reason",
            field=models.CharField(blank=True, default="", max_length=500),
        ),
        migrations.CreateModel(
            name="ExternalWorkshopReferralRequestModel",
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
                ("repair_order_id", models.UUIDField(db_index=True)),
                ("vehicle_id", models.UUIDField(db_index=True)),
                ("fault_id", models.UUIDField(db_index=True)),
                ("status", models.CharField(db_index=True, max_length=20)),
                ("workshop_id", models.CharField(blank=True, default="", max_length=64)),
                ("reason", models.CharField(blank=True, default="", max_length=500)),
                ("requested_by_id", models.UUIDField()),
                ("requested_at", models.DateTimeField()),
                ("approved_by_id", models.UUIDField(blank=True, default=None, null=True)),
                ("approved_at", models.DateTimeField(blank=True, default=None, null=True)),
                ("rejected_by_id", models.UUIDField(blank=True, default=None, null=True)),
                ("rejected_at", models.DateTimeField(blank=True, default=None, null=True)),
                (
                    "rejection_reason",
                    models.CharField(blank=True, default="", max_length=500),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(app_label)s_%(class)s_created",
                        to="authentication.fmmsuser",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(app_label)s_%(class)s_updated",
                        to="authentication.fmmsuser",
                    ),
                ),
            ],
            options={
                "verbose_name": "External Workshop Referral Request",
                "verbose_name_plural": "External Workshop Referral Requests",
                "db_table": "external_workshop_referral_request",
            },
        ),
        migrations.AddIndex(
            model_name="externalworkshopreferralrequestmodel",
            index=models.Index(
                fields=["repair_order_id", "status", "is_deleted"],
                name="ext_ref_order_status_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="externalworkshopreferralrequestmodel",
            index=models.Index(
                fields=["status", "is_deleted"],
                name="ext_ref_status_idx",
            ),
        ),
    ]
