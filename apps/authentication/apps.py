"""Authentication application configuration."""

from django.apps import AppConfig


class AuthenticationConfig(AppConfig):
    """
    Django AppConfig for the FMMS authentication domain.

    Registered as 'authentication' label to keep migrations clean
    and avoid conflicts with Django's built-in auth app.
    """

    name = "apps.authentication"
    label = "authentication"
    default_auto_field = "django.db.models.BigAutoField"
    verbose_name = "Authentication"
