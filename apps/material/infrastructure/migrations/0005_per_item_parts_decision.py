"""Add per-item decision fields and PARTIALLY_ISSUED header status support."""

from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):
    """Persist per-item stock/purchase decisions on material request lines."""

    dependencies = [
        ("material", "0004_central_stock_material_name"),
    ]

    operations = [
        migrations.AddField(
            model_name="materialrequestitemmodel",
            name="from_catalog",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="materialrequestitemmodel",
            name="decision",
            field=models.CharField(default="PENDING", max_length=20),
        ),
        migrations.AddField(
            model_name="materialrequestitemmodel",
            name="item_status",
            field=models.CharField(default="PENDING", max_length=30),
        ),
        migrations.AddField(
            model_name="materialrequestitemmodel",
            name="available_quantity_snapshot",
            field=models.DecimalField(
                blank=True, decimal_places=3, max_digits=18, null=True
            ),
        ),
        migrations.AlterField(
            model_name="materialrequestmodel",
            name="status",
            field=models.CharField(db_index=True, max_length=30),
        ),
    ]
