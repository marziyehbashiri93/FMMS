"""Add AWAITING_TRANSPORT fault status and migrate distribution-confirmed rows."""

from __future__ import annotations

from django.db import migrations, models


def forwards_migrate_distribution_assigned(apps, schema_editor) -> None:
    """Move technician-less ASSIGNED faults to AWAITING_TRANSPORT."""
    del schema_editor
    fault_model = apps.get_model("fault", "FaultModel")
    fault_model.objects.filter(
        status="ASSIGNED",
        assigned_to_id__isnull=True,
        is_deleted=False,
    ).update(status="AWAITING_TRANSPORT")


def backwards_migrate_awaiting_transport(apps, schema_editor) -> None:
    """Collapse AWAITING_TRANSPORT back to ASSIGNED."""
    del schema_editor
    fault_model = apps.get_model("fault", "FaultModel")
    fault_model.objects.filter(
        status="AWAITING_TRANSPORT",
        is_deleted=False,
    ).update(status="ASSIGNED")


class Migration(migrations.Migration):
    """Data migration for the distribution vs technician status split."""

    dependencies = [
        ("fault", "0003_fault_catalog"),
    ]

    operations = [
        migrations.AlterField(
            model_name="faultmodel",
            name="status",
            field=models.CharField(db_index=True, max_length=32),
        ),
        migrations.RunPython(
            forwards_migrate_distribution_assigned,
            backwards_migrate_awaiting_transport,
        ),
    ]
