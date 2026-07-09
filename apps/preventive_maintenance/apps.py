"""Django application configuration for the Preventive Maintenance domain."""

from django.apps import AppConfig


class PreventiveMaintenanceConfig(AppConfig):
    """AppConfig for the Preventive Maintenance bounded context."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.preventive_maintenance"
    label = "preventive_maintenance"
