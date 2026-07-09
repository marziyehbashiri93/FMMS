"""FMMS API v1 route composition."""

from django.urls import include, path

urlpatterns = [
    path("auth/", include("interfaces.api.v1.auth.urls")),
    path("", include("interfaces.api.v1.vehicle.urls")),
    path("", include("interfaces.api.v1.driver.urls")),
    path("", include("interfaces.api.v1.inspection.urls")),
    path("", include("interfaces.api.v1.fault.urls")),
    path("", include("interfaces.api.v1.repair.urls")),
    path("", include("interfaces.api.v1.preventive_maintenance.urls")),
    path("", include("interfaces.api.v1.procurement.urls")),
    path("", include("interfaces.api.v1.integration.urls")),
]
