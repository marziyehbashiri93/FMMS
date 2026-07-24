"""Thin inspection REST API view set."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, time

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.inspection.application.dto.inspection_dto import (
    AddInspectionItemDTO,
    CreateInspectionDTO,
    CreateInspectionItemInputDTO,
    ReportInspectionFaultDTO,
    SubmitInspectionDTO,
)
from apps.inspection.domain.entities import InspectionType
from apps.inspection.domain.value_objects import (
    ChecklistResult,
    FailureSeverity,
    OdometerUnit,
)
from core.permissions import IsReadOnlyOrTechnicianOrAbove
from interfaces.api.v1 import deps
from interfaces.api.v1.fault.serializers import FaultResponseSerializer
from interfaces.api.v1.inspection import schema as inspection_schema
from interfaces.api.v1.inspection.serializers import (
    InspectionCreateSerializer,
    InspectionItemCreateSerializer,
    InspectionResponseSerializer,
)
from interfaces.api.v1.utils import paginate_dto_list, request_id_from, user_id_from
from interfaces.api.v1.vehicle.serializers import DateRangeFilterSerializer


def _date_range_to_datetimes(
    filters: DateRangeFilterSerializer,
) -> tuple[datetime | None, datetime | None]:
    """Convert validated date filters to inclusive UTC datetime bounds."""
    from_date = filters.validated_data.get("from_date")
    to_date = filters.validated_data.get("to_date")
    from_datetime = (
        datetime.combine(from_date, time.min, tzinfo=UTC) if from_date else None
    )
    to_datetime = datetime.combine(to_date, time.max, tzinfo=UTC) if to_date else None
    return from_datetime, to_datetime


class InspectionViewSet(GenericViewSet):
    """Expose inspection application services through REST endpoints."""

    permission_classes = [IsReadOnlyOrTechnicianOrAbove]

    @inspection_schema.retrieve
    def retrieve(self, request: Request, pk: str | None = None) -> Response:
        """Retrieve one inspection."""
        result = deps.get_get_inspection_service().execute(
            uuid.UUID(str(pk)), request_id_from(request)
        )
        return Response(InspectionResponseSerializer(result).data)

    @inspection_schema.list
    def list(self, request: Request) -> Response:
        """List inspections; optionally filter by vehicle and date range."""
        vehicle_id_raw = request.query_params.get("vehicle_id")
        vehicle_id = uuid.UUID(vehicle_id_raw) if vehicle_id_raw else None
        filters = DateRangeFilterSerializer(data=request.query_params)
        filters.is_valid(raise_exception=True)
        from_datetime, to_datetime = _date_range_to_datetimes(filters)
        items = deps.get_list_inspections_service().execute(
            vehicle_id,
            from_date=from_datetime,
            to_date=to_datetime,
            request_id=request_id_from(request),
        )
        page = paginate_dto_list(self, items)
        serializer = InspectionResponseSerializer(
            page if page is not None else items, many=True
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @inspection_schema.create
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

    @inspection_schema.items
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

    @inspection_schema.submit
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

    @inspection_schema.report_fault
    @action(detail=True, methods=["post"], url_path="report-fault")
    def report_fault(self, request: Request, pk: str | None = None) -> Response:
        """Report failed checklist items as a fault."""
        result = deps.get_report_inspection_fault_service().execute(
            ReportInspectionFaultDTO(
                inspection_id=uuid.UUID(str(pk)),
                request_id=request_id_from(request),
                reported_by=user_id_from(request),
            )
        )
        return Response(
            FaultResponseSerializer(result).data,
            status=status.HTTP_201_CREATED,
        )
