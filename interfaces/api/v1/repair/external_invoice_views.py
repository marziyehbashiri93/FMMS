"""External repair invoice API views."""

from __future__ import annotations

import uuid

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.repair.application.dto.repair_dto import (
    ApproveExternalInvoiceDTO,
    UploadExternalInvoiceDTO,
)
from core.permissions import IsReadOnlyOrTechnicianOrAbove, IsSupervisorOrAbove
from interfaces.api.v1 import deps
from interfaces.api.v1.repair.serializers import (
    ExternalInvoiceResponseSerializer,
    ExternalInvoiceUploadSerializer,
)
from interfaces.api.v1.utils import request_id_from, user_id_from


class RepairOrderExternalInvoiceMixin:
    """Mixin to upload external invoice from repair-order endpoint."""

    @extend_schema(
        request=ExternalInvoiceUploadSerializer,
        responses=ExternalInvoiceResponseSerializer,
    )
    @action(detail=True, methods=["post"], url_path="invoice")
    def invoice(self, request: Request, pk: str | None = None) -> Response:
        """Upload external invoice for repair order."""
        serializer = ExternalInvoiceUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = deps.get_upload_external_invoice_service().execute(
            UploadExternalInvoiceDTO(
                repair_order_id=uuid.UUID(str(pk)),
                amount=serializer.validated_data["amount"],
                currency=serializer.validated_data["currency"],
                vendor_id=serializer.validated_data.get("vendor_id") or None,
                document=serializer.validated_data.get("document") or None,
                request_id=request_id_from(request),
                uploaded_by=user_id_from(request),
            )
        )
        return Response(
            ExternalInvoiceResponseSerializer(result).data,
            status=status.HTTP_201_CREATED,
        )


class ExternalInvoiceViewSet(GenericViewSet):
    """Expose external invoice APIs."""

    permission_classes = [IsReadOnlyOrTechnicianOrAbove]

    @extend_schema(responses=ExternalInvoiceResponseSerializer(many=True))
    def list(self, request: Request) -> Response:
        """List external invoices."""
        items = deps.get_list_external_invoices_service().execute()
        return Response(ExternalInvoiceResponseSerializer(items, many=True).data)

    @extend_schema(responses=ExternalInvoiceResponseSerializer)
    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsSupervisorOrAbove],
    )
    def approve(self, request: Request, pk: str | None = None) -> Response:
        """Approve uploaded external invoice."""
        result = deps.get_approve_external_invoice_service().execute(
            ApproveExternalInvoiceDTO(
                invoice_id=uuid.UUID(str(pk)),
                request_id=request_id_from(request),
                approved_by=user_id_from(request),
            )
        )
        return Response(ExternalInvoiceResponseSerializer(result).data)
