"""Thin vehicle REST API view set."""

from __future__ import annotations

import uuid

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
from interfaces.api.v1.utils import paginate_dto_list, request_id_from, user_id_from
from interfaces.api.v1.vehicle import schema as vehicle_schema
from interfaces.api.v1.vehicle.serializers import (
    VehicleOdometerRecordSerializer,
    VehicleOdometerResponseSerializer,
    VehicleResponseSerializer,
    VehicleStatusChangeSerializer,
)


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
        raw_status = request.query_params.get("status")
        ordering = request.query_params.get("ordering", "")
        vehicle_status = VehicleStatus(raw_status) if raw_status else None
        items = deps.get_list_vehicles_service().execute(
            vehicle_status,
            ordering=ordering,
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

    @vehicle_schema.odometer_list
    @vehicle_schema.odometer_record
    @action(detail=True, methods=["get", "post"], url_path="odometer")
    def odometer(self, request: Request, pk: str | None = None) -> Response:
        """List, create, or update vehicle daily odometer readings."""
        if request.method == "GET":
            result = deps.get_list_vehicle_odometer_history_service().execute(
                uuid.UUID(str(pk)),
                request_id_from(request),
            )
            return Response(VehicleOdometerResponseSerializer(result, many=True).data)

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
