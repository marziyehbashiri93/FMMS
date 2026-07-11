"""Vehicle handover URL routes."""

from rest_framework.routers import DefaultRouter

from interfaces.api.v1.handover.views import VehicleHandoverViewSet

router = DefaultRouter()
router.register(
    "vehicle-handovers", VehicleHandoverViewSet, basename="vehicle-handover"
)

urlpatterns = router.urls
