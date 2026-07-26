"""Thin inspection-template REST API view set."""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from core.permissions import IsReadOnlyOrDriverOrTechnicianOrAbove
from interfaces.api.v1 import deps
from interfaces.api.v1.inspection.template_serializers import (
    InspectionTemplateResponseSerializer,
)
from interfaces.api.v1.schema_tags import API_TAGS
from interfaces.api.v1.utils import paginate_dto_list, request_id_from


class InspectionTemplateViewSet(GenericViewSet):
    """Expose inspection checklist templates synced from SAP."""

    permission_classes = [IsReadOnlyOrDriverOrTechnicianOrAbove]

    @extend_schema(
        tags=[API_TAGS.inspection],
        responses=InspectionTemplateResponseSerializer(many=True),
    )
    def list(self, request: Request) -> Response:
        """List active inspection checklist templates."""
        items = deps.get_list_inspection_templates_service().execute(
            request_id_from(request)
        )
        page = paginate_dto_list(self, items)
        serializer = InspectionTemplateResponseSerializer(
            page if page is not None else items, many=True
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)
