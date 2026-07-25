from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("fault", "0004_fault_awaiting_transport"),
    ]

    operations = [
        migrations.AddField(
            model_name="faultmodel",
            name="distribution_decision_note",
            field=models.CharField(blank=True, default="", max_length=500),
        ),
    ]
