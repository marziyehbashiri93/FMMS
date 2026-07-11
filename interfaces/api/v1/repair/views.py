"""Thin repair REST API view set."""

from __future__ import annotations

import uuid

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.repair.application.dto.repair_dto import (
    AddRepairActivityDTO,
    AddRepairPartDTO,
    ApproveRepairOrderDTO,
    AssignRepairOrderDTO,
    AssignWorkshopDTO,
    CloseRepairOrderDTO,
    CompleteRepairOrderDTO,
    CreateRepairOrderDTO,
    SyncRepairToSAPDTO,
)
from apps.repair.domain.entities import RepairOrderStatus, WorkshopType
from core.permissions import (
    IsReadOnlyOrTechnicianOrAbove,
    IsSupervisorOrAbove,
    IsTechnicianOrAbove,
)
from interfaces.api.v1 import deps
from interfaces.api.v1.material.views import RepairOrderMaterialRequestMixin
from interfaces.api.v1.repair.external_invoice_views import (
    RepairOrderExternalInvoiceMixin,
)
from interfaces.api.v1.repair.serializers import (
    RepairActivityCreateSerializer,
    RepairAssignSerializer,
    RepairAssignWorkshopSerializer,
    RepairCompleteSerializer,
    RepairDecisionResponseSerializer,
    RepairOrderCreateSerializer,
    RepairOrderResponseSerializer,
    RepairOrderTimelineEventSerializer,
    RepairPartCreateSerializer,
    RepairSyncSAPSerializer,
)
from interfaces.api.v1.utils import paginate_dto_list, request_id_from, user_id_from


class RepairOrderViewSet(
    RepairOrderMaterialRequestMixin, RepairOrderExternalInvoiceMixin, GenericViewSet
):
    """Expose repair application services through REST endpoints."""

    permission_classes = [IsReadOnlyOrTechnicianOrAbove]

    @extend_schema(responses=RepairOrderResponseSerializer)
    def retrieve(self, request: Request, pk: str | None = None) -> Response:
        """Retrieve one repair order."""
        result = deps.get_get_repair_order_service().execute(
            uuid.UUID(str(pk)), request_id_from(request)
        )
        return Response(RepairOrderResponseSerializer(result).data)

    @extend_schema(responses=RepairOrderResponseSerializer(many=True))
    def list(self, request: Request) -> Response:
        """List repair orders for a vehicle."""
        vehicle_id_raw = request.query_params.get("vehicle_id")
        if not vehicle_id_raw:
            return Response(
                {"detail": "vehicle_id query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        status_raw = request.query_params.get("status")
        order_status = RepairOrderStatus(status_raw) if status_raw else None
        items = deps.get_list_repair_orders_service().execute(
            uuid.UUID(vehicle_id_raw),
            status=order_status,
            request_id=request_id_from(request),
        )
        page = paginate_dto_list(self, items)
        serializer = RepairOrderResponseSerializer(
            page if page is not None else items, many=True
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @extend_schema(
        request=RepairOrderCreateSerializer, responses=RepairOrderResponseSerializer
    )
    def create(self, request: Request) -> Response:
        """Create a repair order."""
        serializer = RepairOrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = deps.get_create_repair_order_service().execute(
            CreateRepairOrderDTO(
                vehicle_id=serializer.validated_data["vehicle_id"],
                fault_id=serializer.validated_data["fault_id"],
                request_id=request_id_from(request),
                created_by=user_id_from(request),
            )
        )
        return Response(
            RepairOrderResponseSerializer(result).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(request=None, responses=RepairDecisionResponseSerializer)
    @action(detail=True, methods=["post"], permission_classes=[IsSupervisorOrAbove])
    def approve(self, request: Request, pk: str | None = None) -> Response:
        """Transport supervisor approves continuing the repair process."""
        result = deps.get_approve_repair_order_service().execute(
            ApproveRepairOrderDTO(
                repair_order_id=uuid.UUID(str(pk)),
                request_id=request_id_from(request),
                approved_by=user_id_from(request),
            )
        )
        return Response(RepairDecisionResponseSerializer(result).data)

    @extend_schema(
        request=RepairAssignWorkshopSerializer,
        responses=RepairDecisionResponseSerializer,
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="assign-workshop",
        permission_classes=[IsSupervisorOrAbove],
    )
    def assign_workshop(self, request: Request, pk: str | None = None) -> Response:
        """Transport supervisor selects INTERNAL or EXTERNAL workshop."""
        serializer = RepairAssignWorkshopSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = deps.get_assign_workshop_service().execute(
            AssignWorkshopDTO(
                repair_order_id=uuid.UUID(str(pk)),
                workshop_type=WorkshopType(serializer.validated_data["workshop_type"]),
                workshop_id=serializer.validated_data.get("workshop_id") or None,
                request_id=request_id_from(request),
                assigned_by=user_id_from(request),
            )
        )
        return Response(RepairDecisionResponseSerializer(result).data)

    @extend_schema(request=None, responses=RepairDecisionResponseSerializer)
    @action(detail=True, methods=["post"], permission_classes=[IsTechnicianOrAbove])
    def accept(self, request: Request, pk: str | None = None) -> Response:
        """Internal workshop accepts the repair order."""
        result = deps.get_accept_repair_order_service().execute(
            repair_order_id=uuid.UUID(str(pk)),
            request_id=request_id_from(request),
            accepted_by=user_id_from(request),
        )
        return Response(RepairDecisionResponseSerializer(result).data)

    @extend_schema(request=None, responses=RepairDecisionResponseSerializer)
    @action(detail=True, methods=["post"], permission_classes=[IsTechnicianOrAbove])
    def reject(self, request: Request, pk: str | None = None) -> Response:
        """Internal workshop rejects the repair order."""
        result = deps.get_reject_repair_order_service().execute(
            repair_order_id=uuid.UUID(str(pk)),
            request_id=request_id_from(request),
            rejected_by=user_id_from(request),
        )
        return Response(RepairDecisionResponseSerializer(result).data)

    @extend_schema(
        request=RepairAssignSerializer, responses=RepairOrderResponseSerializer
    )
    @action(detail=True, methods=["post"])
    def assign(self, request: Request, pk: str | None = None) -> Response:
        """Assign a technician to a repair order."""
        serializer = RepairAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = deps.get_assign_repair_order_service().execute(
            AssignRepairOrderDTO(
                repair_order_id=uuid.UUID(str(pk)),
                technician_id=serializer.validated_data["technician_id"],
                request_id=request_id_from(request),
                assigned_by=user_id_from(request),
            )
        )
        return Response(RepairOrderResponseSerializer(result).data)

    @extend_schema(request=None, responses=RepairOrderResponseSerializer)
    @action(detail=True, methods=["post"])
    def start(self, request: Request, pk: str | None = None) -> Response:
        """Start work on an assigned repair order."""
        result = deps.get_start_repair_service().execute(
            uuid.UUID(str(pk)),
            request_id_from(request),
            started_by=user_id_from(request),
        )
        return Response(RepairOrderResponseSerializer(result).data)

    @extend_schema(responses=RepairOrderTimelineEventSerializer(many=True))
    @action(detail=True, methods=["get"], url_path="timeline")
    def timeline(self, request: Request, pk: str | None = None) -> Response:
        """Return chronological workflow events for a repair order."""
        events = deps.get_get_repair_order_timeline_service().execute(
            uuid.UUID(str(pk)),
            request_id_from(request),
        )
        return Response(RepairOrderTimelineEventSerializer(events, many=True).data)

    @extend_schema(
        request=RepairCompleteSerializer, responses=RepairOrderResponseSerializer
    )
    @action(detail=True, methods=["post"])
    def complete(self, request: Request, pk: str | None = None) -> Response:
        """Complete a repair order."""
        serializer = RepairCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = deps.get_complete_repair_order_service().execute(
            CompleteRepairOrderDTO(
                repair_order_id=uuid.UUID(str(pk)),
                completed_at=serializer.validated_data["completed_at"],
                request_id=request_id_from(request),
                completed_by=user_id_from(request),
            )
        )
        return Response(RepairOrderResponseSerializer(result).data)

    @extend_schema(request=None, responses=RepairOrderResponseSerializer)
    @action(detail=True, methods=["post"])
    def cancel(self, request: Request, pk: str | None = None) -> Response:
        """Cancel a repair order."""
        result = deps.get_cancel_repair_order_service().execute(
            CloseRepairOrderDTO(
                repair_order_id=uuid.UUID(str(pk)),
                request_id=request_id_from(request),
                requested_by=user_id_from(request),
            )
        )
        return Response(RepairOrderResponseSerializer(result).data)

    @extend_schema(
        request=RepairActivityCreateSerializer, responses=RepairOrderResponseSerializer
    )
    @action(detail=True, methods=["post"], url_path="activities")
    def activities(self, request: Request, pk: str | None = None) -> Response:
        """Add a repair activity."""
        serializer = RepairActivityCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = deps.get_add_repair_activity_service().execute(
            AddRepairActivityDTO(
                repair_order_id=uuid.UUID(str(pk)),
                request_id=request_id_from(request),
                **serializer.validated_data,
            )
        )
        return Response(RepairOrderResponseSerializer(result).data)

    @extend_schema(
        request=RepairPartCreateSerializer, responses=RepairOrderResponseSerializer
    )
    @action(detail=True, methods=["post"], url_path="parts")
    def parts(self, request: Request, pk: str | None = None) -> Response:
        """Add a repair part."""
        serializer = RepairPartCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = deps.get_add_repair_part_service().execute(
            AddRepairPartDTO(
                repair_order_id=uuid.UUID(str(pk)),
                request_id=request_id_from(request),
                **serializer.validated_data,
            )
        )
        return Response(RepairOrderResponseSerializer(result).data)

    @extend_schema(
        request=RepairSyncSAPSerializer, responses=RepairOrderResponseSerializer
    )
    @action(detail=True, methods=["post"], url_path="sync-sap")
    def sync_sap(self, request: Request, pk: str | None = None) -> Response:
        """Sync a repair order to SAP as a PM order."""
        serializer = RepairSyncSAPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = deps.get_sync_repair_to_sap_service().execute(
            SyncRepairToSAPDTO(
                repair_order_id=uuid.UUID(str(pk)),
                request_id=request_id_from(request),
                requested_by=user_id_from(request),
                **serializer.validated_data,
            )
        )
        return Response(RepairOrderResponseSerializer(result).data)
