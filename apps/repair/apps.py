"""Django application configuration for the Repair domain."""

from django.apps import AppConfig


class RepairConfig(AppConfig):
    """AppConfig for the Repair bounded context."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.repair"
    label = "repair"
