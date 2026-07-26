# Generated for SAP vehicle-driver OData alignment.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("driver", "0001_initial"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="drivermodel",
            name="unique_active_license_number",
        ),
        migrations.RenameField(
            model_name="drivermodel",
            old_name="license_number",
            new_name="customer_number",
        ),
        migrations.RenameField(
            model_name="drivermodel",
            old_name="full_name",
            new_name="name",
        ),
        migrations.RenameField(
            model_name="drivermodel",
            old_name="phone",
            new_name="mobile",
        ),
        migrations.RemoveField(
            model_name="drivermodel",
            name="email",
        ),
        migrations.RemoveField(
            model_name="drivermodel",
            name="license_class",
        ),
        migrations.AlterField(
            model_name="drivermodel",
            name="customer_number",
            field=models.CharField(db_index=True, max_length=20),
        ),
        migrations.AlterField(
            model_name="drivermodel",
            name="mobile",
            field=models.CharField(blank=True, default="", max_length=20),
        ),
        migrations.AddField(
            model_name="drivermodel",
            name="gender",
            field=models.CharField(blank=True, default="", max_length=20),
        ),
        migrations.AddField(
            model_name="drivermodel",
            name="nilofar_code",
            field=models.CharField(blank=True, default="", max_length=20),
        ),
        migrations.AddField(
            model_name="drivermodel",
            name="personnel_number",
            field=models.CharField(blank=True, default="", max_length=20),
        ),
        migrations.AddConstraint(
            model_name="drivermodel",
            constraint=models.UniqueConstraint(
                condition=models.Q(("is_deleted", False)),
                fields=("customer_number",),
                name="unique_active_customer_number",
            ),
        ),
    ]
