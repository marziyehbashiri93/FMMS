"""Material request URL routes."""

from rest_framework.routers import DefaultRouter

from interfaces.api.v1.material.views import MaterialRequestViewSet

router = DefaultRouter()
router.register(
    "material-requests", MaterialRequestViewSet, basename="material-request"
)

urlpatterns = router.urls
