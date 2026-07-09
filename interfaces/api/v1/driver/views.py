"""Thin driver REST API view set."""

from __future__ import annotations

import uuid

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.driver.application.dto.driver_dto import (
    AssignDriverToVehicleDTO,
    RegisterDriverDTO,
    SuspendDriverDTO,
)
from apps.driver.domain.entities import DriverStatus
from apps.driver.domain.value_objects import LicenseClass
from core.permissions import IsReadOnlyOrTechnicianOrAbove, IsSupervisorOrAbove
from interfaces.api.v1 import deps
from interfaces.api.v1.driver.serializers import (
    DriverAssignSerializer,
    DriverCreateSerializer,
    DriverResponseSerializer,
)
from interfaces.api.v1.utils import paginate_dto_list, request_id_from, user_id_from


class DriverViewSet(GenericViewSet):
    """Expose driver application services through REST endpoints."""

    permission_classes = [IsReadOnlyOrTechnicianOrAbove]

    @extend_schema(responses=DriverResponseSerializer)
    def retrieve(self, request: Request, pk: str | None = None) -> Response:
        """Retrieve one driver."""
        result = deps.get_get_driver_service().execute(
            uuid.UUID(str(pk)), request_id_from(request)
        )
        return Response(DriverResponseSerializer(result).data)

    @extend_schema(responses=DriverResponseSerializer(many=True))
    def list(self, request: Request) -> Response:
        """List drivers, optionally filtered by status."""
        raw_status = request.query_params.get("status")
        driver_status = DriverStatus(raw_status) if raw_status else DriverStatus.ACTIVE
        items = deps.get_list_drivers_service().execute(
            driver_status, request_id_from(request)
        )
        page = paginate_dto_list(self, items)
        serializer = DriverResponseSerializer(
            page if page is not None else items, many=True
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @extend_schema(request=DriverCreateSerializer, responses=DriverResponseSerializer)
    def create(self, request: Request) -> Response:
        """Register a driver through its application service."""
        serializer = DriverCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        license_class = LicenseClass(data.pop("license_class"))
        result = deps.get_register_driver_service().execute(
            RegisterDriverDTO(
                **data,
                license_class=license_class,
                request_id=request_id_from(request),
                created_by=user_id_from(request),
            )
        )
        return Response(
            DriverResponseSerializer(result).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(request=DriverAssignSerializer, responses=DriverResponseSerializer)
    @action(detail=True, methods=["post"])
    def assign(self, request: Request, pk: str | None = None) -> Response:
        """Assign a driver to a vehicle."""
        serializer = DriverAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = deps.get_assign_driver_to_vehicle_service().execute(
            AssignDriverToVehicleDTO(
                driver_id=uuid.UUID(str(pk)),
                vehicle_id=serializer.validated_data["vehicle_id"],
                request_id=request_id_from(request),
                assigned_by=user_id_from(request),
            )
        )
        return Response(DriverResponseSerializer(result).data)

    @extend_schema(request=None, responses=DriverResponseSerializer)
    @action(detail=True, methods=["post"], permission_classes=[IsSupervisorOrAbove])
    def suspend(self, request: Request, pk: str | None = None) -> Response:
        """Suspend a driver."""
        result = deps.get_suspend_driver_service().execute(
            SuspendDriverDTO(
                driver_id=uuid.UUID(str(pk)),
                request_id=request_id_from(request),
                requested_by=user_id_from(request),
            )
        )
        return Response(DriverResponseSerializer(result).data)
