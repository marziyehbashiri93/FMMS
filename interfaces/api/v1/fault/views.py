"""Thin fault REST API view sets."""

from __future__ import annotations

import uuid

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.fault.application.dto.fault_dto import (
    AssignFaultDTO,
    CloseFaultDTO,
    DistributionFaultDecisionDTO,
    ReportFaultDTO,
    ReportFaultItemDTO,
)
from apps.fault.domain.entities import FaultStatus
from apps.fault.domain.value_objects import FaultSeverity
from core.permissions import (
    IsDistributionSupervisorOrAbove,
    IsReadOnlyOrTechnicianOrAbove,
)
from interfaces.api.v1 import deps
from interfaces.api.v1.fault.serializers import (
    FaultAssignSerializer,
    FaultCatalogResponseSerializer,
    FaultCreateSerializer,
    FaultDistributionDecisionSerializer,
    FaultDistributionRejectSerializer,
    FaultListQuerySerializer,
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
        query = FaultListQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        filters = query.validated_data
        raw_status = filters.get("status")
        raw_severity = filters.get("open_by_severity")
        items = deps.get_list_faults_service().execute(
            vehicle_id=filters.get("vehicle_id"),
            status=FaultStatus(raw_status) if raw_status else None,
            open_by_severity=FaultSeverity(raw_severity) if raw_severity else None,
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
        raw_items = data.pop("items", None) or []
        items = [
            ReportFaultItemDTO(
                code=item["code"],
                description=item["description"],
                severity=FaultSeverity(item["severity"]),
                component=item.get("component") or "",
            )
            for item in raw_items
        ]
        result = deps.get_report_fault_service().execute(
            ReportFaultDTO(
                **data,
                severity=severity,
                items=items,
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
        tags=[API_TAGS.fault],
        request=None,
        responses=FaultResponseSerializer,
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

    @extend_schema(
        tags=[API_TAGS.fault],
        request=FaultDistributionRejectSerializer,
        responses=FaultResponseSerializer,
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="distribution-usable",
        permission_classes=[IsDistributionSupervisorOrAbove],
    )
    def distribution_usable(self, request: Request, pk: str | None = None) -> Response:
        """Distribution rejected the fault: vehicle is usable."""
        serializer = FaultDistributionRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = deps.get_distribution_fault_decision_service().mark_usable(
            DistributionFaultDecisionDTO(
                fault_id=uuid.UUID(str(pk)),
                request_id=request_id_from(request),
                decided_by=user_id_from(request),
                note=serializer.validated_data.get("note", ""),
            )
        )
        return Response(FaultResponseSerializer(result).data)

    @extend_schema(
        tags=[API_TAGS.fault],
        request=FaultDistributionDecisionSerializer,
        responses=FaultResponseSerializer,
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="distribution-unusable",
        permission_classes=[IsDistributionSupervisorOrAbove],
    )
    def distribution_unusable(
        self, request: Request, pk: str | None = None
    ) -> Response:
        """Distribution confirmed the vehicle is unusable."""
        serializer = FaultDistributionDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = deps.get_distribution_fault_decision_service().mark_unusable(
            DistributionFaultDecisionDTO(
                fault_id=uuid.UUID(str(pk)),
                request_id=request_id_from(request),
                decided_by=user_id_from(request),
                note=serializer.validated_data.get("note", ""),
            )
        )
        return Response(FaultResponseSerializer(result).data)


class FaultCatalogViewSet(GenericViewSet):
    """Expose SAP-synced fault catalog rows through read-only REST endpoints."""

    permission_classes = [IsReadOnlyOrTechnicianOrAbove]

    @extend_schema(
        tags=[API_TAGS.fault],
        parameters=[
            OpenApiParameter(name="code_group", required=False, type=str),
            OpenApiParameter(name="defect_class", required=False, type=str),
            OpenApiParameter(name="search", required=False, type=str),
        ],
        responses=FaultCatalogResponseSerializer(many=True),
    )
    def list(self, request: Request) -> Response:
        """List active fault catalog rows."""
        items = deps.get_list_fault_catalog_service().execute(
            code_group=request.query_params.get("code_group", "").strip(),
            defect_class=request.query_params.get("defect_class", "").strip(),
            search=request.query_params.get("search", "").strip(),
            request_id=request_id_from(request),
        )
        page = paginate_dto_list(self, items)
        serializer = FaultCatalogResponseSerializer(
            page if page is not None else items,
            many=True,
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)
