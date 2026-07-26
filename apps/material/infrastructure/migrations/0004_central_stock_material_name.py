"""Add material_name to central warehouse stock cache."""

from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):
    """Store SAP material description alongside central stock rows."""

    dependencies = [
        ("material", "0003_central_stock"),
    ]

    operations = [
        migrations.AddField(
            model_name="centralstockmodel",
            name="material_name",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
    ]
