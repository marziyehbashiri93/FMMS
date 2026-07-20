# Generated for SAP vehicle-driver OData alignment.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("vehicle", "0004_vehicle_sap_driver_links"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="vehiclemodel",
            name="unique_active_plate_number",
        ),
        migrations.RemoveIndex(
            model_name="vehiclemodel",
            name="vehicle_sap_eq_idx",
        ),
        migrations.RenameField(
            model_name="vehiclemodel",
            old_name="plate_number",
            new_name="license_plate",
        ),
        migrations.RenameField(
            model_name="vehiclemodel",
            old_name="sap_equipment_number",
            new_name="vehicle_number",
        ),
        migrations.RenameField(
            model_name="vehiclemodel",
            old_name="primary_driver_customer_number",
            new_name="driver1_customer_number",
        ),
        migrations.RenameField(
            model_name="vehiclemodel",
            old_name="assistant_driver_customer_number",
            new_name="driver2_customer_number",
        ),
        migrations.RemoveField(
            model_name="vehiclemodel",
            name="category",
        ),
        migrations.RemoveField(
            model_name="vehiclemodel",
            name="chassis_number",
        ),
        migrations.RemoveField(
            model_name="vehiclemodel",
            name="make",
        ),
        migrations.RemoveField(
            model_name="vehiclemodel",
            name="model",
        ),
        migrations.RemoveField(
            model_name="vehiclemodel",
            name="vin",
        ),
        migrations.RemoveField(
            model_name="vehiclemodel",
            name="year",
        ),
        migrations.AddField(
            model_name="vehiclemodel",
            name="commissioning_date",
            field=models.CharField(blank=True, default="", max_length=8),
        ),
        migrations.AlterField(
            model_name="vehiclemodel",
            name="license_plate",
            field=models.CharField(db_index=True, max_length=20),
        ),
        migrations.AlterField(
            model_name="vehiclemodel",
            name="vehicle_number",
            field=models.CharField(db_index=True, max_length=18),
        ),
        migrations.AddIndex(
            model_name="vehiclemodel",
            index=models.Index(fields=["vehicle_number"], name="vehicle_number_idx"),
        ),
        migrations.AddConstraint(
            model_name="vehiclemodel",
            constraint=models.UniqueConstraint(
                condition=models.Q(("is_deleted", False)),
                fields=("license_plate",),
                name="unique_active_license_plate",
            ),
        ),
        migrations.AddConstraint(
            model_name="vehiclemodel",
            constraint=models.UniqueConstraint(
                condition=models.Q(("is_deleted", False)),
                fields=("vehicle_number",),
                name="unique_active_vehicle_number",
            ),
        ),
    ]
