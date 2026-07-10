"""Thin inspection REST API view set."""

from __future__ import annotations

import uuid
from datetime import datetime

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.inspection.application.dto.inspection_dto import (
    AddInspectionItemDTO,
    CreateInspectionDTO,
    CreateInspectionItemInputDTO,
    SubmitInspectionDTO,
)
from apps.inspection.domain.entities import InspectionType
from apps.inspection.domain.value_objects import ChecklistResult, FailureSeverity, OdometerUnit
from core.permissions import IsReadOnlyOrTechnicianOrAbove
from interfaces.api.v1 import deps
from interfaces.api.v1.inspection.serializers import (
    InspectionCreateSerializer,
    InspectionItemCreateSerializer,
    InspectionResponseSerializer,
)
from interfaces.api.v1.utils import paginate_dto_list, request_id_from, user_id_from


class InspectionViewSet(GenericViewSet):
    """Expose inspection application services through REST endpoints."""

    permission_classes = [IsReadOnlyOrTechnicianOrAbove]

    @extend_schema(responses=InspectionResponseSerializer)
    def retrieve(self, request: Request, pk: str | None = None) -> Response:
        """Retrieve one inspection."""
        result = deps.get_get_inspection_service().execute(
            uuid.UUID(str(pk)), request_id_from(request)
        )
        return Response(InspectionResponseSerializer(result).data)

    @extend_schema(responses=InspectionResponseSerializer(many=True))
    def list(self, request: Request) -> Response:
        """List inspections for a vehicle."""
        vehicle_id_raw = request.query_params.get("vehicle_id")
        if not vehicle_id_raw:
            return Response(
                {"detail": "vehicle_id query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from_date_raw = request.query_params.get("from_date")
        to_date_raw = request.query_params.get("to_date")
        from_date = datetime.fromisoformat(from_date_raw) if from_date_raw else None
        to_date = datetime.fromisoformat(to_date_raw) if to_date_raw else None
        items = deps.get_list_inspections_service().execute(
            uuid.UUID(vehicle_id_raw),
            from_date=from_date,
            to_date=to_date,
            request_id=request_id_from(request),
        )
        page = paginate_dto_list(self, items)
        serializer = InspectionResponseSerializer(
            page if page is not None else items, many=True
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @extend_schema(
        request=InspectionCreateSerializer, responses=InspectionResponseSerializer
    )
    def create(self, request: Request) -> Response:
        """Create a draft inspection."""
        serializer = InspectionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        inspection_type = InspectionType(data.pop("inspection_type"))
        odometer_unit = OdometerUnit(data.pop("odometer_unit"))
        raw_items = data.pop("items", []) or []
        items = [
            CreateInspectionItemInputDTO(
                category=item["category"],
                description=item["description"],
                result=ChecklistResult(item["result"]),
                notes=item.get("notes"),
                severity=FailureSeverity(item["severity"])
                if item.get("severity")
                else None,
            )
            for item in raw_items
        ]
        result = deps.get_create_inspection_service().execute(
            CreateInspectionDTO(
                **data,
                inspection_type=inspection_type,
                odometer_unit=odometer_unit,
                items=items,
                request_id=request_id_from(request),
                created_by=user_id_from(request),
            )
        )
        return Response(
            InspectionResponseSerializer(result).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        request=InspectionItemCreateSerializer, responses=InspectionResponseSerializer
    )
    @action(detail=True, methods=["post"], url_path="items")
    def items(self, request: Request, pk: str | None = None) -> Response:
        """Add a checklist item to a draft inspection."""
        serializer = InspectionItemCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        result_value = ChecklistResult(data.pop("result"))
        severity_raw = data.pop("severity", None)
        severity = FailureSeverity(severity_raw) if severity_raw else None
        result = deps.get_add_inspection_item_service().execute(
            AddInspectionItemDTO(
                inspection_id=uuid.UUID(str(pk)),
                **data,
                result=result_value,
                severity=severity,
                request_id=request_id_from(request),
            )
        )
        return Response(InspectionResponseSerializer(result).data)

    @extend_schema(request=None, responses=InspectionResponseSerializer)
    @action(detail=True, methods=["post"])
    def submit(self, request: Request, pk: str | None = None) -> Response:
        """Submit a draft inspection."""
        result = deps.get_submit_inspection_service().execute(
            SubmitInspectionDTO(
                inspection_id=uuid.UUID(str(pk)),
                request_id=request_id_from(request),
                submitted_by=user_id_from(request),
            )
        )
        return Response(InspectionResponseSerializer(result).data)
