"""Integration URL routes."""

from rest_framework.routers import DefaultRouter

from interfaces.api.v1.integration.views import SAPTransactionViewSet

router = DefaultRouter()
router.register("sap-transactions", SAPTransactionViewSet, basename="sap-transaction")

urlpatterns = router.urls
