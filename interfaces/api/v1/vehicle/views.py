"""Thin vehicle REST API view set."""

from __future__ import annotations

import uuid

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.vehicle.application.dto.vehicle_dto import (
    ActivateVehicleDTO,
    CreateVehicleDTO,
    DeactivateVehicleDTO,
    UpdateVehicleDTO,
)
from apps.vehicle.domain.entities import VehicleCategory, VehicleStatus
from core.permissions import IsReadOnlyOrTechnicianOrAbove, IsSupervisorOrAbove
from interfaces.api.v1 import deps
from interfaces.api.v1.utils import paginate_dto_list, request_id_from, user_id_from
from interfaces.api.v1.vehicle.serializers import (
    SAPEquipmentSyncSerializer,
    VehicleCreateSerializer,
    VehicleResponseSerializer,
    VehicleSAPSyncResultSerializer,
    VehicleUpdateSerializer,
)


class VehicleViewSet(GenericViewSet):
    """Expose vehicle application services through REST endpoints."""

    permission_classes = [IsReadOnlyOrTechnicianOrAbove]

    @extend_schema(responses=VehicleResponseSerializer)
    def retrieve(self, request: Request, pk: str | None = None) -> Response:
        """Retrieve one vehicle."""
        result = deps.get_get_vehicle_service().execute(
            uuid.UUID(str(pk)), request_id_from(request)
        )
        return Response(VehicleResponseSerializer(result).data)

    @extend_schema(responses=VehicleResponseSerializer(many=True))
    def list(self, request: Request) -> Response:
        """List non-deleted vehicles, optionally filtered by status."""
        raw_status = request.query_params.get("status")
        vehicle_status = VehicleStatus(raw_status) if raw_status else None
        items = deps.get_list_vehicles_service().execute(
            vehicle_status, request_id_from(request)
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

    @extend_schema(request=VehicleCreateSerializer, responses=VehicleResponseSerializer)
    def create(self, request: Request) -> Response:
        """Create a vehicle through its application service."""
        serializer = VehicleCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        category = VehicleCategory(data.pop("category"))
        result = deps.get_create_vehicle_service().execute(
            CreateVehicleDTO(
                **data,
                category=category,
                request_id=request_id_from(request),
                created_by=user_id_from(request),
            )
        )
        return Response(
            VehicleResponseSerializer(result).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(request=VehicleUpdateSerializer, responses=VehicleResponseSerializer)
    def partial_update(self, request: Request, pk: str | None = None) -> Response:
        """Update mutable vehicle properties."""
        serializer = VehicleUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        result = deps.get_update_vehicle_service().execute(
            UpdateVehicleDTO(
                vehicle_id=uuid.UUID(str(pk)),
                request_id=request_id_from(request),
                updated_by=user_id_from(request),
                category=(
                    VehicleCategory(values["category"])
                    if "category" in values
                    else None
                ),
                **{key: value for key, value in values.items() if key != "category"},
            )
        )
        return Response(VehicleResponseSerializer(result).data)

    @extend_schema(request=None, responses=VehicleResponseSerializer)
    @action(detail=True, methods=["post"], permission_classes=[IsSupervisorOrAbove])
    def deactivate(self, request: Request, pk: str | None = None) -> Response:
        """Deactivate a vehicle."""
        result = deps.get_deactivate_vehicle_service().execute(
            DeactivateVehicleDTO(
                uuid.UUID(str(pk)), request_id_from(request), user_id_from(request)
            )
        )
        return Response(VehicleResponseSerializer(result).data)

    @extend_schema(request=None, responses=VehicleResponseSerializer)
    @action(detail=True, methods=["post"], permission_classes=[IsSupervisorOrAbove])
    def activate(self, request: Request, pk: str | None = None) -> Response:
        """Re-activate a vehicle after maintenance when no open repairs remain."""
        result = deps.get_activate_vehicle_service().execute(
            ActivateVehicleDTO(
                vehicle_id=uuid.UUID(str(pk)),
                request_id=request_id_from(request),
                requested_by=user_id_from(request),
            )
        )
        return Response(VehicleResponseSerializer(result).data)

    @extend_schema(
        request=None,
        responses=VehicleSAPSyncResultSerializer,
    )
    @action(detail=False, methods=["post"], url_path="sync-sap")
    def sync_sap_bulk(self, request: Request) -> Response:
        """Import/create/update vehicles from SAP equipment master data."""
        result = deps.get_sync_vehicles_from_sap_service().execute(
            request_id_from(request)
        )
        return Response(VehicleSAPSyncResultSerializer(result).data)

    @extend_schema(
        request=SAPEquipmentSyncSerializer, responses=VehicleResponseSerializer
    )
    @action(detail=True, methods=["post"], url_path="sync-sap")
    def sync_sap(self, request: Request, pk: str | None = None) -> Response:
        """Synchronize a vehicle using its SAP equipment number."""
        serializer = SAPEquipmentSyncSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = deps.get_sync_sap_equipment_service().execute(
            serializer.validated_data["sap_equipment_number"], request_id_from(request)
        )
        return Response(VehicleResponseSerializer(result).data)
