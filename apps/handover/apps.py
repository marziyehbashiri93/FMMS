"""Django application configuration for vehicle handovers."""

from django.apps import AppConfig


class HandoverConfig(AppConfig):
    """AppConfig for handover context."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.handover"
    label = "handover"
