"""Django application configuration for the Reporting domain.

Note:
    This domain is a Phase 2 scope placeholder.
    No business logic or models exist in Phase 1.
"""

from django.apps import AppConfig


class ReportingConfig(AppConfig):
    """AppConfig for the Reporting bounded context (Phase 2)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.reporting"
    label = "reporting"
