"""Django application configuration for the Procurement domain."""

from django.apps import AppConfig


class ProcurementConfig(AppConfig):
    """AppConfig for the Procurement bounded context."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.procurement"
    label = "procurement"
