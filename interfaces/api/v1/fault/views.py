"""Thin fault REST API view set."""

from __future__ import annotations

import uuid

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.fault.application.dto.fault_dto import (
    AssignFaultDTO,
    CloseFaultDTO,
    ReportFaultDTO,
)
from apps.fault.domain.value_objects import FaultSeverity
from core.permissions import IsReadOnlyOrTechnicianOrAbove
from interfaces.api.v1 import deps
from interfaces.api.v1.fault.serializers import (
    FaultAssignSerializer,
    FaultCreateSerializer,
    FaultResponseSerializer,
)
from interfaces.api.v1.schema_tags import API_TAGS
from interfaces.api.v1.utils import paginate_dto_list, request_id_from, user_id_from


class FaultViewSet(GenericViewSet):
    """Expose fault application services through REST endpoints."""

    permission_classes = [IsReadOnlyOrTechnicianOrAbove]

    @extend_schema(tags=[API_TAGS.fault], responses=FaultResponseSerializer)
    def retrieve(self, request: Request, pk: str | None = None) -> Response:
        """Retrieve one fault."""
        result = deps.get_get_fault_service().execute(
            uuid.UUID(str(pk)), request_id_from(request)
        )
        return Response(FaultResponseSerializer(result).data)

    @extend_schema(tags=[API_TAGS.fault], responses=FaultResponseSerializer(many=True))
    def list(self, request: Request) -> Response:
        """List faults filtered by vehicle or open severity."""
        vehicle_id_raw = request.query_params.get("vehicle_id")
        severity_raw = request.query_params.get("open_by_severity")
        vehicle_id = uuid.UUID(vehicle_id_raw) if vehicle_id_raw else None
        open_by_severity = FaultSeverity(severity_raw) if severity_raw else None
        items = deps.get_list_faults_service().execute(
            vehicle_id=vehicle_id,
            open_by_severity=open_by_severity,
            request_id=request_id_from(request),
        )
        page = paginate_dto_list(self, items)
        serializer = FaultResponseSerializer(
            page if page is not None else items, many=True
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @extend_schema(
        tags=[API_TAGS.fault],
        request=FaultCreateSerializer,
        responses=FaultResponseSerializer,
    )
    def create(self, request: Request) -> Response:
        """Report a new fault."""
        serializer = FaultCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        severity = FaultSeverity(data.pop("severity"))
        result = deps.get_report_fault_service().execute(
            ReportFaultDTO(
                **data,
                severity=severity,
                request_id=request_id_from(request),
                reported_by=user_id_from(request),
            )
        )
        return Response(
            FaultResponseSerializer(result).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        tags=[API_TAGS.fault],
        request=FaultAssignSerializer,
        responses=FaultResponseSerializer,
    )
    @action(detail=True, methods=["post"])
    def assign(self, request: Request, pk: str | None = None) -> Response:
        """Assign a fault to a technician."""
        serializer = FaultAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = deps.get_assign_fault_service().execute(
            AssignFaultDTO(
                fault_id=uuid.UUID(str(pk)),
                technician_id=serializer.validated_data["technician_id"],
                request_id=request_id_from(request),
                assigned_by=user_id_from(request),
            )
        )
        return Response(FaultResponseSerializer(result).data)

    @extend_schema(
        tags=[API_TAGS.fault], request=None, responses=FaultResponseSerializer
    )
    @action(detail=True, methods=["post"])
    def close(self, request: Request, pk: str | None = None) -> Response:
        """Close a fault."""
        result = deps.get_close_fault_service().execute(
            CloseFaultDTO(
                fault_id=uuid.UUID(str(pk)),
                request_id=request_id_from(request),
                closed_by=user_id_from(request),
            )
        )
        return Response(FaultResponseSerializer(result).data)
