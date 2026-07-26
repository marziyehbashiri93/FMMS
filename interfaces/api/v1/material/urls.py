"""Material request and central stock URL routes."""

from rest_framework.routers import DefaultRouter

from interfaces.api.v1.material.views import CentralStockViewSet, MaterialRequestViewSet

router = DefaultRouter()
router.register(
    "material-requests", MaterialRequestViewSet, basename="material-request"
)
router.register("central-stock", CentralStockViewSet, basename="central-stock")

urlpatterns = router.urls
