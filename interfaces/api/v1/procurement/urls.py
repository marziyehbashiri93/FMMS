"""Procurement URL routes."""

from rest_framework.routers import DefaultRouter

from interfaces.api.v1.procurement.views import (
    PurchaseOrderViewSet,
    PurchaseRequisitionViewSet,
)

router = DefaultRouter()
router.register(
    "purchase-requisitions",
    PurchaseRequisitionViewSet,
    basename="purchase-requisition",
)
router.register("purchase-orders", PurchaseOrderViewSet, basename="purchase-order")

urlpatterns = router.urls
