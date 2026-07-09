"""Fault URL routes."""

from rest_framework.routers import DefaultRouter

from interfaces.api.v1.fault.views import FaultViewSet

router = DefaultRouter()
router.register("faults", FaultViewSet, basename="fault")

urlpatterns = router.urls
