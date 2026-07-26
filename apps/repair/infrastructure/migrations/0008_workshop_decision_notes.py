from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("repair", "0007_external_referral_deleted_by"),
    ]

    operations = [
        migrations.AddField(
            model_name="repairordermodel",
            name="transport_approval_note",
            field=models.CharField(blank=True, default="", max_length=500),
        ),
        migrations.AddField(
            model_name="repairordermodel",
            name="workshop_decision_note",
            field=models.CharField(blank=True, default="", max_length=500),
        ),
    ]
