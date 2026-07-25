"""Add SAP personnel_number link field on FMMSUser."""

from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):
    """Link FMMS login users to SAP master data via personnel number."""

    dependencies = [
        ("authentication", "0004_add_workshop_supervisor_role"),
    ]

    operations = [
        migrations.AddField(
            model_name="fmmsuser",
            name="personnel_number",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="",
                help_text=(
                    "SAP personnel number (کد پرسنلی). Links this login user to "
                    "SAP driver/employee master data."
                ),
                max_length=20,
            ),
        ),
        migrations.AddConstraint(
            model_name="fmmsuser",
            constraint=models.UniqueConstraint(
                condition=~models.Q(personnel_number=""),
                fields=("personnel_number",),
                name="unique_fmms_user_personnel_number",
            ),
        ),
    ]
