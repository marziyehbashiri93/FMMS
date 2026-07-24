"""Fault URL routes."""

from rest_framework.routers import DefaultRouter

from interfaces.api.v1.fault.views import FaultCatalogViewSet, FaultViewSet

router = DefaultRouter()
router.register("faults", FaultViewSet, basename="fault")
router.register("fault-catalogs", FaultCatalogViewSet, basename="fault-catalog")

urlpatterns = router.urls
