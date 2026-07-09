"""Django application configuration for the Integration domain."""

from django.apps import AppConfig


class IntegrationConfig(AppConfig):
    """AppConfig for the SAP Integration bounded context."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.integration"
    label = "integration"
