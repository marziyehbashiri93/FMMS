"""Model shim — re-exports ORM models for Django auto-discovery.

Django's model registry scans ``<app>.models``. The actual model
definition lives in ``apps.vehicle.infrastructure.models`` to maintain
Clean Architecture layering. This shim satisfies Django without coupling.
"""

from apps.vehicle.infrastructure.models import VehicleModel, VehicleOdometerReadingModel

__all__ = ["VehicleModel", "VehicleOdometerReadingModel"]
