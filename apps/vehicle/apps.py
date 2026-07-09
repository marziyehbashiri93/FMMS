"""Django application configuration for the Vehicle domain."""

from django.apps import AppConfig


class VehicleConfig(AppConfig):
    """AppConfig for the Vehicle bounded context."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.vehicle"
    label = "vehicle"
