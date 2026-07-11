from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("repair", "0004_workflow_v2_fields_and_invoices"),
    ]

    operations = [
        migrations.AlterField(
            model_name="repairordermodel",
            name="status",
            field=models.CharField(db_index=True, max_length=40),
        ),
    ]
