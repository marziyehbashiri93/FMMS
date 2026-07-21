"""Integration URL routes."""

from rest_framework.routers import DefaultRouter

from interfaces.api.v1.integration.views import SAPSyncViewSet, SAPTransactionViewSet

router = DefaultRouter()
router.register("sap-transactions", SAPTransactionViewSet, basename="sap-transaction")
router.register("sap-sync", SAPSyncViewSet, basename="sap-sync")

urlpatterns = router.urls
