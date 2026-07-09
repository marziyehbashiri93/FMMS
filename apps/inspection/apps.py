"""Django application configuration for the Inspection domain."""

from django.apps import AppConfig


class InspectionConfig(AppConfig):
    """AppConfig for the Inspection bounded context."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.inspection"
    label = "inspection"
