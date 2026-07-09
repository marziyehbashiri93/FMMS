"""Repair URL routes."""

from rest_framework.routers import DefaultRouter

from interfaces.api.v1.repair.views import RepairOrderViewSet

router = DefaultRouter()
router.register("repair-orders", RepairOrderViewSet, basename="repair-order")

urlpatterns = router.urls
