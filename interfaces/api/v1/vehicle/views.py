"""Thin vehicle REST API view set."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, time

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.vehicle.application.dto.vehicle_dto import (
    ChangeVehicleStatusDTO,
    RecordVehicleOdometerDTO,
)
from apps.vehicle.domain.entities import VehicleStatus
from core.permissions import IsReadOnlyOrTechnicianOrAbove, IsSupervisorOrAbove
from interfaces.api.v1 import deps
from interfaces.api.v1.inspection.serializers import InspectionResponseSerializer
from interfaces.api.v1.utils import paginate_dto_list, request_id_from, user_id_from
from interfaces.api.v1.vehicle import schema as vehicle_schema
from interfaces.api.v1.vehicle.serializers import (
    DateRangeFilterSerializer,
    VehicleDriverAssignmentSnapshotResponseSerializer,
    VehicleListQuerySerializer,
    VehicleOdometerRecordSerializer,
    VehicleOdometerResponseSerializer,
    VehicleResponseSerializer,
    VehicleStatusChangeSerializer,
    VehicleSummarySerializer,
)


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


class VehicleViewSet(GenericViewSet):
    """Expose vehicle application services through REST endpoints."""

    permission_classes = [IsReadOnlyOrTechnicianOrAbove]

    @vehicle_schema.retrieve
    def retrieve(self, request: Request, pk: str | None = None) -> Response:
        """Retrieve one vehicle."""
        result = deps.get_get_vehicle_service().execute(
            uuid.UUID(str(pk)), request_id_from(request)
        )
        return Response(VehicleResponseSerializer(result).data)

    @vehicle_schema.list
    def list(self, request: Request) -> Response:
        """List non-deleted vehicles, optionally filtered by status."""
        query_serializer = VehicleListQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        raw_status = query_serializer.validated_data.get("status")
        ordering = query_serializer.validated_data.get("ordering", "")
        search = query_serializer.validated_data.get("search", "").strip()
        vehicle_status = VehicleStatus(raw_status) if raw_status else None
        items = deps.get_list_vehicles_service().execute(
            vehicle_status,
            ordering=ordering,
            search=search,
            request_id=request_id_from(request),
        )
        page = paginate_dto_list(self, items)
        serializer = VehicleResponseSerializer(
            page if page is not None else items, many=True
        )
        return (
            self.get_paginated_response(serializer.data)
            if page is not None
            else Response(serializer.data)
        )

    @vehicle_schema.change_status
    @action(
        detail=True,
        methods=["post"],
        url_path="status",
        permission_classes=[IsSupervisorOrAbove],
    )
    def status(self, request: Request, pk: str | None = None) -> Response:
        """Change an FMMS-controlled vehicle status."""
        serializer = VehicleStatusChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = deps.get_change_vehicle_status_service().execute(
            ChangeVehicleStatusDTO(
                vehicle_id=uuid.UUID(str(pk)),
                status=VehicleStatus(serializer.validated_data["status"]),
                request_id=request_id_from(request),
                requested_by=user_id_from(request),
            )
        )
        return Response(VehicleResponseSerializer(result).data)

    @vehicle_schema.odometer_current
    @vehicle_schema.odometer_record
    @action(detail=True, methods=["get", "post"], url_path="odometer")
    def odometer(self, request: Request, pk: str | None = None) -> Response:
        """Retrieve current odometer, or create/update a daily reading."""
        if request.method == "GET":
            result = deps.get_get_vehicle_current_odometer_service().execute(
                uuid.UUID(str(pk)),
                request_id=request_id_from(request),
            )
            return Response(VehicleOdometerResponseSerializer(result).data)

        serializer = VehicleOdometerRecordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = deps.get_record_vehicle_odometer_service().execute(
            RecordVehicleOdometerDTO(
                vehicle_id=uuid.UUID(str(pk)),
                reading_date=serializer.validated_data["reading_date"],
                odometer_km=serializer.validated_data["odometer_km"],
                source=serializer.validated_data["source"],
                request_id=request_id_from(request),
                recorded_by=user_id_from(request),
            )
        )
        return Response(VehicleOdometerResponseSerializer(result).data)

    @vehicle_schema.odometer_history
    @action(detail=True, methods=["get"], url_path="odometer-history")
    def odometer_history(self, request: Request, pk: str | None = None) -> Response:
        """List vehicle odometer history with optional date filters."""
        filters = DateRangeFilterSerializer(data=request.query_params)
        filters.is_valid(raise_exception=True)
        result = deps.get_list_vehicle_odometer_history_service().execute(
            uuid.UUID(str(pk)),
            from_date=filters.validated_data.get("from_date"),
            to_date=filters.validated_data.get("to_date"),
            request_id=request_id_from(request),
        )
        return Response(VehicleOdometerResponseSerializer(result, many=True).data)

    @vehicle_schema.driver_assignment_history
    @action(detail=True, methods=["get"], url_path="driver-assignment-history")
    def driver_assignment_history(
        self, request: Request, pk: str | None = None
    ) -> Response:
        """List SAP driver-assignment history for one vehicle."""
        filters = DateRangeFilterSerializer(data=request.query_params)
        filters.is_valid(raise_exception=True)
        result = deps.get_list_vehicle_driver_assignment_history_service().execute(
            uuid.UUID(str(pk)),
            from_date=filters.validated_data.get("from_date"),
            to_date=filters.validated_data.get("to_date"),
        )
        return Response(
            VehicleDriverAssignmentSnapshotResponseSerializer(result, many=True).data
        )

    @vehicle_schema.checklist_history
    @action(detail=True, methods=["get"], url_path="checklists")
    def checklists(self, request: Request, pk: str | None = None) -> Response:
        """List registered checklist inspections for one vehicle."""
        vehicle_id = uuid.UUID(str(pk))
        deps.get_get_vehicle_service().execute(
            vehicle_id,
            request_id=request_id_from(request),
        )
        filters = DateRangeFilterSerializer(data=request.query_params)
        filters.is_valid(raise_exception=True)
        from_datetime, to_datetime = _date_range_to_datetimes(filters)
        result = deps.get_list_inspections_service().execute(
            vehicle_id,
            from_date=from_datetime,
            to_date=to_datetime,
            request_id=request_id_from(request),
        )
        page = paginate_dto_list(self, result)
        serializer = InspectionResponseSerializer(
            page if page is not None else result,
            many=True,
        )
        return (
            self.get_paginated_response(serializer.data)
            if page is not None
            else Response(serializer.data)
        )

    @vehicle_schema.checklist_detail
    @action(
        detail=True,
        methods=["get"],
        url_path=r"checklists/(?P<inspection_id>[^/.]+)",
    )
    def checklist_detail(
        self,
        request: Request,
        pk: str | None = None,
        inspection_id: str | None = None,
    ) -> Response:
        """Retrieve one registered checklist inspection for one vehicle."""
        vehicle_id = uuid.UUID(str(pk))
        result = deps.get_get_inspection_service().execute(
            uuid.UUID(str(inspection_id)),
            request_id=request_id_from(request),
        )
        if result.vehicle_id != vehicle_id:
            return Response(
                {"detail": "Checklist inspection was not found for this vehicle."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(InspectionResponseSerializer(result).data)

    @vehicle_schema.summary
    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request: Request) -> Response:
        """Return summary values for vehicle dashboard cards."""
        del request
        result = deps.get_get_vehicle_summary_service().execute()
        return Response(VehicleSummarySerializer(result).data)
