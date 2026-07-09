"""Preventive maintenance URL routes."""

from rest_framework.routers import DefaultRouter

from interfaces.api.v1.preventive_maintenance.views import (
    PMPlanViewSet,
    PMWorkOrderViewSet,
)

router = DefaultRouter()
router.register("pm-plans", PMPlanViewSet, basename="pm-plan")
router.register("pm-work-orders", PMWorkOrderViewSet, basename="pm-work-order")

urlpatterns = router.urls
