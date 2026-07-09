"""Driver URL routes."""

from rest_framework.routers import DefaultRouter

from interfaces.api.v1.driver.views import DriverViewSet

router = DefaultRouter()
router.register("drivers", DriverViewSet, basename="driver")

urlpatterns = router.urls
