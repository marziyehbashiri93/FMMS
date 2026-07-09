"""Vehicle URL routes."""

from rest_framework.routers import DefaultRouter

from interfaces.api.v1.vehicle.views import VehicleViewSet

router = DefaultRouter()
router.register("vehicles", VehicleViewSet, basename="vehicle")

urlpatterns = router.urls
