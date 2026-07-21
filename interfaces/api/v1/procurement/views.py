"""Thin procurement REST API view sets."""

from __future__ import annotations

import uuid

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.procurement.application.dto.procurement_dto import (
    AddPRLineItemDTO,
    CreatePurchaseRequisitionDTO,
    ReceivePOFromSAPDTO,
    ReceivePOLineItemDTO,
    SubmitPRToSAPDTO,
)
from apps.procurement.domain.entities import PRStatus
from core.permissions import IsReadOnlyOrTechnicianOrAbove, IsSupervisorOrAbove
from interfaces.api.v1 import deps
from interfaces.api.v1.procurement.serializers import (
    PRLineItemCreateSerializer,
    PurchaseOrderResponseSerializer,
    PurchaseRequisitionCreateSerializer,
    PurchaseRequisitionResponseSerializer,
    ReceivePOFromSAPSerializer,
    SubmitPRToSAPSerializer,
)
from interfaces.api.v1.schema_tags import API_TAGS
from interfaces.api.v1.utils import paginate_dto_list, request_id_from, user_id_from


class PurchaseRequisitionViewSet(GenericViewSet):
    """Expose purchase requisition application services through REST endpoints."""

    permission_classes = [IsReadOnlyOrTechnicianOrAbove]

    @extend_schema(
        tags=[API_TAGS.procurement],
        responses=PurchaseRequisitionResponseSerializer,
    )
    def retrieve(self, request: Request, pk: str | None = None) -> Response:
        """Retrieve one purchase requisition."""
        result = deps.get_get_purchase_requisition_service().execute(
            uuid.UUID(str(pk)), request_id_from(request)
        )
        return Response(PurchaseRequisitionResponseSerializer(result).data)

    @extend_schema(
        tags=[API_TAGS.procurement],
        responses=PurchaseRequisitionResponseSerializer(many=True),
    )
    def list(self, request: Request) -> Response:
        """List purchase requisitions with optional filters."""
        repair_order_raw = request.query_params.get("repair_order_id")
        status_raw = request.query_params.get("status")
        repair_order_id = uuid.UUID(repair_order_raw) if repair_order_raw else None
        pr_status = PRStatus(status_raw) if status_raw else None
        items = deps.get_list_purchase_requisitions_service().execute(
            repair_order_id=repair_order_id,
            status=pr_status,
            request_id=request_id_from(request),
        )
        page = paginate_dto_list(self, items)
        serializer = PurchaseRequisitionResponseSerializer(
            page if page is not None else items, many=True
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @extend_schema(
        tags=[API_TAGS.procurement],
        request=PurchaseRequisitionCreateSerializer,
        responses=PurchaseRequisitionResponseSerializer,
    )
    def create(self, request: Request) -> Response:
        """Create a draft purchase requisition."""
        serializer = PurchaseRequisitionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = deps.get_create_purchase_requisition_service().execute(
            CreatePurchaseRequisitionDTO(
                repair_order_id=serializer.validated_data["repair_order_id"],
                request_id=request_id_from(request),
                requested_by=user_id_from(request),
            )
        )
        return Response(
            PurchaseRequisitionResponseSerializer(result).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        tags=[API_TAGS.procurement],
        request=PRLineItemCreateSerializer,
        responses=PurchaseRequisitionResponseSerializer,
    )
    @action(detail=True, methods=["post"], url_path="line-items")
    def line_items(self, request: Request, pk: str | None = None) -> Response:
        """Add a line item to a draft PR."""
        serializer = PRLineItemCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = deps.get_add_pr_line_item_service().execute(
            AddPRLineItemDTO(
                pr_id=uuid.UUID(str(pk)),
                request_id=request_id_from(request),
                **serializer.validated_data,
            )
        )
        return Response(PurchaseRequisitionResponseSerializer(result).data)

    @extend_schema(
        tags=[API_TAGS.procurement],
        request=SubmitPRToSAPSerializer,
        responses=PurchaseRequisitionResponseSerializer,
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="submit-sap",
        permission_classes=[IsSupervisorOrAbove],
    )
    def submit_sap(self, request: Request, pk: str | None = None) -> Response:
        """Submit a purchase requisition to SAP."""
        serializer = SubmitPRToSAPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = deps.get_submit_pr_to_sap_service().execute(
            SubmitPRToSAPDTO(
                pr_id=uuid.UUID(str(pk)),
                request_id=request_id_from(request),
                submitted_by=user_id_from(request),
                **serializer.validated_data,
            )
        )
        return Response(PurchaseRequisitionResponseSerializer(result).data)


class PurchaseOrderViewSet(GenericViewSet):
    """Expose purchase order application services through REST endpoints."""

    permission_classes = [IsReadOnlyOrTechnicianOrAbove]

    @extend_schema(
        tags=[API_TAGS.procurement],
        responses=PurchaseOrderResponseSerializer,
    )
    def retrieve(self, request: Request, pk: str | None = None) -> Response:
        """Retrieve one purchase order."""
        result = deps.get_get_purchase_order_service().execute(
            uuid.UUID(str(pk)), request_id_from(request)
        )
        return Response(PurchaseOrderResponseSerializer(result).data)

    @extend_schema(
        tags=[API_TAGS.procurement],
        request=ReceivePOFromSAPSerializer,
        responses=PurchaseOrderResponseSerializer,
    )
    def create(self, request: Request) -> Response:
        """Receive a purchase order from SAP."""
        serializer = ReceivePOFromSAPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        line_items = tuple(
            ReceivePOLineItemDTO(**item) for item in data.pop("line_items")
        )
        result = deps.get_receive_po_from_sap_service().execute(
            ReceivePOFromSAPDTO(
                **data,
                line_items=line_items,
                request_id=request_id_from(request),
                created_by=user_id_from(request),
            )
        )
        return Response(
            PurchaseOrderResponseSerializer(result).data,
            status=status.HTTP_201_CREATED,
        )
