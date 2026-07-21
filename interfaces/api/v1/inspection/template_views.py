"""Thin inspection-template REST API view set."""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from core.permissions import IsReadOnlyOrTechnicianOrAbove
from interfaces.api.v1 import deps
from interfaces.api.v1.inspection.template_serializers import (
    InspectionTemplateResponseSerializer,
    InspectionTemplateSyncResultSerializer,
)
from interfaces.api.v1.schema_tags import API_TAGS
from interfaces.api.v1.utils import paginate_dto_list, request_id_from


class InspectionTemplateViewSet(GenericViewSet):
    """Expose inspection checklist templates synced from SAP."""

    permission_classes = [IsReadOnlyOrTechnicianOrAbove]

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

    @extend_schema(
        tags=[API_TAGS.inspection],
        request=None,
        responses=InspectionTemplateSyncResultSerializer,
    )
    @action(detail=False, methods=["post"], url_path="sync-sap")
    def sync_sap(self, request: Request) -> Response:
        """Import/create/update checklist templates from SAP catalog."""
        result = deps.get_sync_inspection_templates_from_sap_service().execute(
            request_id_from(request)
        )
        return Response(InspectionTemplateSyncResultSerializer(result).data)
