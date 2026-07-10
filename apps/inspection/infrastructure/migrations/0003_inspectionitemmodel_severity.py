"""Add optional severity to inspection checklist items."""

from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):
    """Persist driver-assigned failure severity on inspection items."""

    dependencies = [
        ("inspection", "0002_inspection_template"),
    ]

    operations = [
        migrations.AddField(
            model_name="inspectionitemmodel",
            name="severity",
            field=models.CharField(blank=True, default="", max_length=10),
        ),
    ]
