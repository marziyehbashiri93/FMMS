"""Remove manual driver-to-vehicle assignment state.

Vehicle-driver links come from SAP OData through vehicle ``Driver1CustomerNo``
and ``Driver2CustomerNo`` fields. FMMS does not assign drivers to vehicles.
"""

from __future__ import annotations

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("driver", "0002_align_driver_with_sap_customer"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="drivermodel",
            name="assigned_vehicle_id",
        ),
    ]
