"""Clear non-OData synthetic central-stock material names.

The ZI_STOCK_KH08_CDS fixture has no MaterialName column. Older local rows
were filled with unit-based placeholders such as «روغن / مایع — 60001764».
Those are not SAP source data and must be removed.
"""

from __future__ import annotations

from django.db import migrations
from django.db.models import Q


_SYNTHETIC_PREFIXES = (
    "روغن / مایع — ",
    "مواد فله — ",
    "مجموعه قطعه — ",
    "قطعه یدکی — ",
)


def clear_synthetic_names(apps, schema_editor) -> None:
    """Blank material_name values that match known synthetic prefixes."""
    del schema_editor
    CentralStockModel = apps.get_model("material", "CentralStockModel")
    query = Q()
    for prefix in _SYNTHETIC_PREFIXES:
        query |= Q(material_name__startswith=prefix)
    CentralStockModel.objects.filter(query).exclude(material_name="").update(
        material_name=""
    )


def noop_reverse(apps, schema_editor) -> None:
    """Synthetic names are not restored."""
    del apps, schema_editor


class Migration(migrations.Migration):
    """Data migration clearing fabricated central stock names."""

    dependencies = [
        ("material", "0005_per_item_parts_decision"),
    ]

    operations = [
        migrations.RunPython(clear_synthetic_names, noop_reverse),
    ]
