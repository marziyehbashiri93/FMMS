"""Django application configuration for the Driver domain."""

from django.apps import AppConfig


class DriverConfig(AppConfig):
    """AppConfig for the Driver bounded context."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.driver"
    label = "driver"
