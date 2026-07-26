import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("repair", "0006_transport_rejection_and_external_referral"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="externalworkshopreferralrequestmodel",
            name="deleted_by",
            field=models.ForeignKey(
                blank=True,
                help_text="User who soft-deleted this record.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="%(app_label)s_%(class)s_deleted",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
