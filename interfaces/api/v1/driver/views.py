"""Thin driver REST API view set."""

from __future__ import annotations

import uuid

from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.driver.application.dto.driver_dto import (
    DriverExitCenterDTO,
    DriverResponseDTO,
)
from apps.driver.domain.entities import DriverStatus
from core.permissions import IsReadOnlyOrTechnicianOrAbove
from interfaces.api.v1 import deps
from interfaces.api.v1.driver import schema as driver_schema
from interfaces.api.v1.driver.serializers import (
    DriverExitCenterSerializer,
    DriverResponseSerializer,
    DriverSummarySerializer,
)
from interfaces.api.v1.utils import paginate_dto_list, request_id_from, user_id_from
from interfaces.api.v1.vehicle.serializers import (
    DateRangeFilterSerializer,
    VehicleDriverAssignmentHistoryResponseSerializer,
    VehicleResponseSerializer,
)

_DRIVER_ROLE_FILTERS = frozenset({"DRIVER", "ASSISTANT"})


def _filter_drivers_by_search(
    items: list[DriverResponseDTO],
    search: str,
) -> list[DriverResponseDTO]:
    """Filter driver DTOs by case-insensitive contains on searchable fields.

    Args:
        items: Driver response DTOs to filter.
        search: Free-text search term.

    Returns:
        Drivers whose name or personnel_number contain ``search``
        (case-insensitive).
    """
    needle = search.casefold()
    return [
        item
        for item in items
        if needle in item.name.casefold()
        or (item.personnel_number is not None and needle in item.personnel_number.casefold())
    ]


def _filter_drivers_by_role(
    items: list[DriverResponseDTO],
    role: str,
) -> list[DriverResponseDTO]:
    """Filter driver DTOs by their current vehicle assignment role."""
    if not role:
        return items
    if role not in _DRIVER_ROLE_FILTERS:
        raise serializers.ValidationError(
            {
                "role": (
                    "Unsupported role filter. Allowed values are DRIVER "
                    "and ASSISTANT."
                )
            }
        )
    if role == "DRIVER":
        return [item for item in items if item.current_vehicle_as_driver is not None]
    return [item for item in items if item.current_vehicle_as_assistant is not None]


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
        raw_status = request.query_params.get("status")
        ordering = request.query_params.get("ordering", "")
        search = request.query_params.get("search", "").strip()
        role = request.query_params.get("role", "").strip().upper()
        driver_status = DriverStatus(raw_status) if raw_status else None
        items = deps.get_list_drivers_service().execute(
            driver_status,
            ordering=ordering,
            request_id=request_id_from(request),
        )
        if search:
            items = _filter_drivers_by_search(items, search)
        items = _filter_drivers_by_role(items, role)
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
    @action(detail=True, methods=["post"], url_path="exit-center")
    def exit_center(self, request: Request, pk: str | None = None) -> Response:
        """Mark the assigned vehicle as exited from the fleet center."""
        serializer = DriverExitCenterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = deps.get_driver_exit_center_service().execute(
            DriverExitCenterDTO(
                driver_id=uuid.UUID(str(pk)),
                vehicle_id=serializer.validated_data["vehicle_id"],
                inspection_id=serializer.validated_data["inspection_id"],
                request_id=request_id_from(request),
                requested_by=user_id_from(request),
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
