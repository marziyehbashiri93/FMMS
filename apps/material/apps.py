"""Django application configuration for the Material bounded context."""

from django.apps import AppConfig


class MaterialConfig(AppConfig):
    """AppConfig for material requests."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.material"
    label = "material"
