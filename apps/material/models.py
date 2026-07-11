"""Model shim for Django app auto-discovery."""

from apps.material.infrastructure.models import (
    MaterialRequestItemModel,
    MaterialRequestModel,
)

__all__ = ["MaterialRequestModel", "MaterialRequestItemModel"]
