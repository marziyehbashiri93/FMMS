"""Django application configuration for the Fault domain."""

from django.apps import AppConfig


class FaultConfig(AppConfig):
    """AppConfig for the Fault bounded context."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.fault"
    label = "fault"
