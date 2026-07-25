"""Repair URL routes."""

from rest_framework.routers import DefaultRouter

from interfaces.api.v1.repair.external_invoice_views import ExternalInvoiceViewSet
from interfaces.api.v1.repair.views import (
    ExternalWorkshopReferralViewSet,
    RepairOrderViewSet,
)

router = DefaultRouter()
router.register("repair-orders", RepairOrderViewSet, basename="repair-order")
router.register(
    "external-invoices", ExternalInvoiceViewSet, basename="external-invoice"
)
router.register(
    "external-workshop-referrals",
    ExternalWorkshopReferralViewSet,
    basename="external-workshop-referral",
)

urlpatterns = router.urls
