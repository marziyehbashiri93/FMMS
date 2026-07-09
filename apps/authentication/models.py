"""
Authentication app model registry.

Exposes infrastructure models to Django's app registry.
This file exists solely to satisfy Django's model discovery mechanism —
business logic stays in infrastructure/models.py.
"""

from apps.authentication.infrastructure.models import FMMSUser, FMMSUserRole

__all__ = ["FMMSUser", "FMMSUserRole"]
