from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("authentication", "0002_add_username"),
    ]

    operations = [
        migrations.AlterField(
            model_name="fmmsuser",
            name="role",
            field=models.CharField(
                choices=[
                    ("ADMIN", "Administrator"),
                    ("SUPERVISOR", "Supervisor"),
                    ("DISTRIBUTION", "Distribution Supervisor"),
                    ("TRANSPORT", "Transport Supervisor"),
                    ("WAREHOUSE", "Warehouse Supervisor"),
                    ("TECHNICIAN", "Technician"),
                    ("DRIVER", "Driver"),
                    ("VIEWER", "Viewer (read-only)"),
                ],
                db_index=True,
                default="VIEWER",
                help_text="FMMS role — controls API permissions.",
                max_length=20,
            ),
        ),
    ]
