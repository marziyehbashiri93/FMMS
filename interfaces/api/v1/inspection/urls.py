"""Inspection URL routes."""

from rest_framework.routers import DefaultRouter

from interfaces.api.v1.inspection.views import InspectionViewSet

router = DefaultRouter()
router.register("inspections", InspectionViewSet, basename="inspection")

urlpatterns = router.urls
