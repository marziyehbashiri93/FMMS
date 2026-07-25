"""Material request and central stock API viewsets."""

from __future__ import annotations

import uuid

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.material.application.dto.material_request_dto import (
    CreateMaterialRequestDTO,
    CreateMaterialRequestItemDTO,
    MaterialRequestDecisionDTO,
    PartsAvailabilityDecisionDTO,
    PartsItemDecisionDTO,
)
from apps.material.domain.entities import MaterialItemDecision, MaterialRequestStatus
from core.permissions import (
    IsReadOnlyOrTechnicianOrAbove,
    IsTransportSupervisorOrAbove,
    IsWorkshopSupervisorOrAbove,
)
from interfaces.api.v1 import deps
from interfaces.api.v1.material.serializers import (
    CentralStockResponseSerializer,
    MaterialRequestCreateSerializer,
    MaterialRequestResponseSerializer,
    PartsAvailabilityDecisionSerializer,
)
from interfaces.api.v1.schema_tags import API_TAGS
from interfaces.api.v1.utils import paginate_dto_list, request_id_from, user_id_from


class MaterialRequestViewSet(GenericViewSet):
    """Expose material request services through REST endpoints."""

    permission_classes = [IsReadOnlyOrTechnicianOrAbove]

    @extend_schema(
        tags=[API_TAGS.material],
        responses=MaterialRequestResponseSerializer(many=True),
    )
    def list(self, request: Request) -> Response:
        """List material requests."""
        status_raw = request.query_params.get("status")
        mr_status = MaterialRequestStatus(status_raw) if status_raw else None
        items = deps.get_list_material_requests_service().execute(status=mr_status)
        return Response(MaterialRequestResponseSerializer(items, many=True).data)

    @extend_schema(
        tags=[API_TAGS.material], responses=MaterialRequestResponseSerializer
    )
    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsTransportSupervisorOrAbove],
    )
    def approve(self, request: Request, pk: str | None = None) -> Response:
        """Approve material request (compat: auto inventory availability)."""
        result = deps.get_approve_material_request_service().execute(
            MaterialRequestDecisionDTO(
                material_request_id=uuid.UUID(str(pk)),
                request_id=request_id_from(request),
                decided_by=user_id_from(request),
            )
        )
        return Response(MaterialRequestResponseSerializer(result).data)

    @extend_schema(
        tags=[API_TAGS.material],
        request=PartsAvailabilityDecisionSerializer,
        responses=MaterialRequestResponseSerializer,
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="availability-decision",
        permission_classes=[IsTransportSupervisorOrAbove],
    )
    def availability_decision(self, request: Request, pk: str | None = None) -> Response:
        """Transport decides stock vs purchase for each requested item."""
        serializer = PartsAvailabilityDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = deps.get_decide_parts_availability_service().execute(
            PartsAvailabilityDecisionDTO(
                material_request_id=uuid.UUID(str(pk)),
                items=tuple(
                    PartsItemDecisionDTO(
                        item_id=item["item_id"],
                        decision=MaterialItemDecision(item["decision"]),
                    )
                    for item in serializer.validated_data["items"]
                ),
                request_id=request_id_from(request),
                decided_by=user_id_from(request),
                note=serializer.validated_data.get("note", ""),
            )
        )
        return Response(MaterialRequestResponseSerializer(result).data)

    @extend_schema(
        tags=[API_TAGS.material], responses=MaterialRequestResponseSerializer
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="issue-purchased",
        permission_classes=[IsTransportSupervisorOrAbove],
    )
    def issue_purchased(self, request: Request, pk: str | None = None) -> Response:
        """After goods receipt, allocate purchased parts and send to workshop."""
        result = deps.get_issue_purchased_parts_service().execute(
            material_request_id=uuid.UUID(str(pk)),
            request_id=request_id_from(request),
            decided_by=user_id_from(request),
        )
        return Response(MaterialRequestResponseSerializer(result).data)

    @extend_schema(
        tags=[API_TAGS.material], responses=MaterialRequestResponseSerializer
    )
    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsWorkshopSupervisorOrAbove],
    )
    def receive(self, request: Request, pk: str | None = None) -> Response:
        """Workshop confirms physical receipt of parts."""
        result = deps.get_receive_material_request_service().execute(
            MaterialRequestDecisionDTO(
                material_request_id=uuid.UUID(str(pk)),
                request_id=request_id_from(request),
                decided_by=user_id_from(request),
            )
        )
        return Response(MaterialRequestResponseSerializer(result).data)


class CentralStockViewSet(GenericViewSet):
    """Expose SAP-synced central warehouse stock through read-only REST endpoints."""

    permission_classes = [IsReadOnlyOrTechnicianOrAbove]

    @extend_schema(
        tags=[API_TAGS.material],
        parameters=[
            OpenApiParameter(name="plant", required=False, type=str),
            OpenApiParameter(name="storage_location", required=False, type=str),
            OpenApiParameter(name="search", required=False, type=str),
        ],
        responses=CentralStockResponseSerializer(many=True),
    )
    def list(self, request: Request) -> Response:
        """List active central warehouse stock rows."""
        items = deps.get_list_central_stock_service().execute(
            plant=request.query_params.get("plant", "").strip(),
            storage_location=request.query_params.get("storage_location", "").strip(),
            search=request.query_params.get("search", "").strip(),
            request_id=request_id_from(request),
        )
        page = paginate_dto_list(self, items)
        serializer = CentralStockResponseSerializer(
            page if page is not None else items,
            many=True,
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)


class RepairOrderMaterialRequestMixin:
    """Mixin with repair-order scoped material request creation action."""

    @extend_schema(
        tags=[API_TAGS.material],
        request=MaterialRequestCreateSerializer,
        responses=MaterialRequestResponseSerializer,
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="material-requests",
        permission_classes=[IsWorkshopSupervisorOrAbove],
    )
    def material_requests(self, request: Request, pk: str | None = None) -> Response:
        """Create a material request for a repair order."""
        serializer = MaterialRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = deps.get_create_material_request_service().execute(
            CreateMaterialRequestDTO(
                repair_order_id=uuid.UUID(str(pk)),
                items=tuple(
                    CreateMaterialRequestItemDTO(
                        material_number=item["material_number"],
                        quantity=item["quantity"],
                        from_catalog=item.get("from_catalog", True),
                    )
                    for item in serializer.validated_data["items"]
                ),
                request_id=request_id_from(request),
                requested_by=user_id_from(request),
            )
        )
        return Response(
            MaterialRequestResponseSerializer(result).data,
            status=status.HTTP_201_CREATED,
        )
