"""Thin preventive maintenance REST API view sets."""

from __future__ import annotations

import uuid

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.preventive_maintenance.application.dto.pm_dto import (
    CompletePMWorkOrderDTO,
    CreatePMPlanDTO,
    TriggerPMWorkOrderDTO,
)
from apps.preventive_maintenance.domain.entities import PMPlanStatus, PMWorkOrderStatus
from apps.preventive_maintenance.domain.value_objects import IntervalUnit, TriggerType
from core.permissions import IsReadOnlyOrTechnicianOrAbove
from interfaces.api.v1 import deps
from interfaces.api.v1.preventive_maintenance.serializers import (
    PMCompleteSerializer,
    PMPlanCreateSerializer,
    PMPlanResponseSerializer,
    PMTriggerSerializer,
    PMWorkOrderResponseSerializer,
)
from interfaces.api.v1.schema_tags import API_TAGS
from interfaces.api.v1.utils import paginate_dto_list, request_id_from, user_id_from


class PMPlanViewSet(GenericViewSet):
    """Expose PM plan application services through REST endpoints."""

    permission_classes = [IsReadOnlyOrTechnicianOrAbove]

    @extend_schema(
        tags=[API_TAGS.preventive_maintenance],
        responses=PMPlanResponseSerializer,
    )
    def retrieve(self, request: Request, pk: str | None = None) -> Response:
        """Retrieve one PM plan."""
        result = deps.get_get_pm_plan_service().execute(
            uuid.UUID(str(pk)), request_id_from(request)
        )
        return Response(PMPlanResponseSerializer(result).data)

    @extend_schema(
        tags=[API_TAGS.preventive_maintenance],
        responses=PMPlanResponseSerializer(many=True),
    )
    def list(self, request: Request) -> Response:
        """List PM plans for a vehicle."""
        vehicle_id_raw = request.query_params.get("vehicle_id")
        if not vehicle_id_raw:
            return Response(
                {"detail": "vehicle_id query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        status_raw = request.query_params.get("status")
        plan_status = PMPlanStatus(status_raw) if status_raw else None
        items = deps.get_list_pm_plans_service().execute(
            uuid.UUID(vehicle_id_raw),
            status=plan_status,
            request_id=request_id_from(request),
        )
        page = paginate_dto_list(self, items)
        serializer = PMPlanResponseSerializer(
            page if page is not None else items, many=True
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @extend_schema(
        tags=[API_TAGS.preventive_maintenance],
        request=PMPlanCreateSerializer,
        responses=PMPlanResponseSerializer,
    )
    def create(self, request: Request) -> Response:
        """Create a PM plan."""
        serializer = PMPlanCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        interval_unit = IntervalUnit(data.pop("interval_unit"))
        trigger_type = TriggerType(data.pop("trigger_type"))
        result = deps.get_create_pm_plan_service().execute(
            CreatePMPlanDTO(
                **data,
                interval_unit=interval_unit,
                trigger_type=trigger_type,
                request_id=request_id_from(request),
                created_by=user_id_from(request),
            )
        )
        return Response(
            PMPlanResponseSerializer(result).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        tags=[API_TAGS.preventive_maintenance],
        request=PMTriggerSerializer,
        responses=PMWorkOrderResponseSerializer,
    )
    @action(detail=True, methods=["post"])
    def trigger(self, request: Request, pk: str | None = None) -> Response:
        """Trigger a PM work order from a plan."""
        serializer = PMTriggerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = deps.get_trigger_pm_work_order_service().execute(
            TriggerPMWorkOrderDTO(
                plan_id=uuid.UUID(str(pk)),
                request_id=request_id_from(request),
                triggered_by=user_id_from(request),
                **serializer.validated_data,
            )
        )
        return Response(
            PMWorkOrderResponseSerializer(result).data,
            status=status.HTTP_201_CREATED,
        )


class PMWorkOrderViewSet(GenericViewSet):
    """Expose PM work-order application services through REST endpoints."""

    permission_classes = [IsReadOnlyOrTechnicianOrAbove]

    @extend_schema(
        tags=[API_TAGS.preventive_maintenance],
        responses=PMWorkOrderResponseSerializer(many=True),
    )
    def list(self, request: Request) -> Response:
        """List PM work orders for a plan."""
        plan_id_raw = request.query_params.get("plan_id")
        if not plan_id_raw:
            return Response(
                {"detail": "plan_id query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        status_raw = request.query_params.get("status")
        wo_status = PMWorkOrderStatus(status_raw) if status_raw else None
        items = deps.get_list_pm_work_orders_service().execute(
            uuid.UUID(plan_id_raw),
            status=wo_status,
            request_id=request_id_from(request),
        )
        page = paginate_dto_list(self, items)
        serializer = PMWorkOrderResponseSerializer(
            page if page is not None else items, many=True
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @extend_schema(
        tags=[API_TAGS.preventive_maintenance],
        request=PMCompleteSerializer,
        responses=PMWorkOrderResponseSerializer,
    )
    @action(detail=True, methods=["post"])
    def complete(self, request: Request, pk: str | None = None) -> Response:
        """Complete a PM work order."""
        serializer = PMCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = deps.get_complete_pm_work_order_service().execute(
            CompletePMWorkOrderDTO(
                work_order_id=uuid.UUID(str(pk)),
                request_id=request_id_from(request),
                completed_by=user_id_from(request),
                **serializer.validated_data,
            )
        )
        return Response(PMWorkOrderResponseSerializer(result).data)
