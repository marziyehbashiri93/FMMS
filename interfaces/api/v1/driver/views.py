"""Thin driver REST API view set."""

from __future__ import annotations

import uuid

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.driver.domain.entities import DriverStatus
from core.permissions import IsReadOnlyOrTechnicianOrAbove
from interfaces.api.v1 import deps
from interfaces.api.v1.driver import schema as driver_schema
from interfaces.api.v1.driver.serializers import DriverResponseSerializer
from interfaces.api.v1.utils import paginate_dto_list, request_id_from


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
        """List drivers, optionally filtered by status."""
        raw_status = request.query_params.get("status")
        ordering = request.query_params.get("ordering", "")
        driver_status = DriverStatus(raw_status) if raw_status else None
        items = deps.get_list_drivers_service().execute(
            driver_status,
            ordering=ordering,
            request_id=request_id_from(request),
        )
        page = paginate_dto_list(self, items)
        serializer = DriverResponseSerializer(
            page if page is not None else items, many=True
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)
