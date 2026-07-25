"""Thin driver REST API view set."""

from __future__ import annotations

import uuid

from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.driver.application.dto.driver_dto import (
    DriverExitCenterDTO,
)
from apps.driver.application.services.get_driver_service import DriverAssignmentRole
from apps.driver.domain.entities import DriverStatus
from core.permissions import (
    IsReadOnlyOrDriverOrTechnicianOrAbove,
    IsReadOnlyOrTechnicianOrAbove,
)
from interfaces.api.v1 import deps
from interfaces.api.v1.driver import schema as driver_schema
from interfaces.api.v1.driver.serializers import (
    DriverExitCenterSerializer,
    DriverListQuerySerializer,
    DriverResponseSerializer,
    DriverSummarySerializer,
)
from interfaces.api.v1.utils import paginate_dto_list, request_id_from, user_id_from
from interfaces.api.v1.vehicle.serializers import (
    DateRangeFilterSerializer,
    VehicleDriverAssignmentHistoryResponseSerializer,
    VehicleResponseSerializer,
)


class DriverViewSet(GenericViewSet):
    """Expose driver application services through REST endpoints."""

    permission_classes = [IsReadOnlyOrTechnicianOrAbove]

    @driver_schema.retrieve
    def retrieve(self, request: Request, pk: str | None = None) -> Response:
        """Retrieve one driver."""
        result = deps.get_get_driver_service().execute(
            uuid.UUID(str(pk)), request_id_from(request)
        )
        return Response(DriverResponseSerializer(result).data)

    @driver_schema.list
    def list(self, request: Request) -> Response:
        """List drivers, optionally filtered by status and search text."""
        query = DriverListQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        filters = query.validated_data
        raw_status = filters.get("status")
        raw_role = filters.get("role")
        items = deps.get_list_drivers_service().execute(
            DriverStatus(raw_status) if raw_status else None,
            ordering=filters.get("ordering", ""),
            search=filters.get("search", ""),
            role=DriverAssignmentRole(raw_role) if raw_role else None,
            request_id=request_id_from(request),
        )
        page = paginate_dto_list(self, items)
        serializer = DriverResponseSerializer(
            page if page is not None else items, many=True
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @driver_schema.summary
    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request: Request) -> Response:
        """Return summary values for driver dashboard cards."""
        del request
        result = deps.get_get_driver_summary_service().execute()
        return Response(DriverSummarySerializer(result).data)

    @driver_schema.exit_center
    @action(
        detail=True,
        methods=["post"],
        url_path="exit-center",
        permission_classes=[IsReadOnlyOrDriverOrTechnicianOrAbove],
    )
    def exit_center(self, request: Request, pk: str | None = None) -> Response:
        """Mark the assigned vehicle as exited from the fleet center."""
        serializer = DriverExitCenterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        driver_id = uuid.UUID(str(pk))
        if getattr(request.user, "role", None) == "DRIVER":
            personnel = str(getattr(request.user, "personnel_number", "") or "").strip()
            linked = deps.get_driver_repository().find_by_personnel_number(personnel)
            if linked is None or linked.id != driver_id:
                from rest_framework.exceptions import PermissionDenied  # noqa: PLC0415

                raise PermissionDenied(
                    detail="Drivers may only exit for their own linked SAP identity."
                )
        result = deps.get_driver_exit_center_service().execute(
            DriverExitCenterDTO(
                driver_id=driver_id,
                vehicle_id=serializer.validated_data["vehicle_id"],
                inspection_id=serializer.validated_data["inspection_id"],
                request_id=request_id_from(request),
                requested_by_user_id=user_id_from(request),
            )
        )
        return Response(VehicleResponseSerializer(result).data)

    @driver_schema.vehicle_assignment_history
    @action(detail=True, methods=["get"], url_path="vehicle-assignment-history")
    def vehicle_assignment_history(
        self, request: Request, pk: str | None = None
    ) -> Response:
        """List SAP vehicle-assignment history for one driver."""
        filters = DateRangeFilterSerializer(data=request.query_params)
        filters.is_valid(raise_exception=True)
        result = deps.get_list_driver_vehicle_assignment_history_service().execute(
            uuid.UUID(str(pk)),
            from_date=filters.validated_data.get("from_date"),
            to_date=filters.validated_data.get("to_date"),
        )
        return Response(
            VehicleDriverAssignmentHistoryResponseSerializer(result, many=True).data
        )
