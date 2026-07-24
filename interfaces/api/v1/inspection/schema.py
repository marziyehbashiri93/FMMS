"""OpenAPI schema configuration for inspection API v1."""

from __future__ import annotations

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema

from interfaces.api.v1.fault.serializers import FaultResponseSerializer
from interfaces.api.v1.inspection.serializers import (
    InspectionCreateSerializer,
    InspectionItemCreateSerializer,
    InspectionResponseSerializer,
)
from interfaces.api.v1.schema_tags import API_TAGS
from interfaces.api.v1.vehicle.schema import date_range_parameters

inspection_id_parameter = OpenApiParameter(
    name="id",
    location=OpenApiParameter.PATH,
    required=True,
    type=OpenApiTypes.UUID,
)

retrieve = extend_schema(
    tags=[API_TAGS.inspection],
    parameters=[inspection_id_parameter],
    responses=InspectionResponseSerializer,
)

list = extend_schema(
    tags=[API_TAGS.inspection],
    parameters=[
        OpenApiParameter(
            name="vehicle_id",
            description="Filter checklists by vehicle id.",
            required=False,
            type=OpenApiTypes.UUID,
        ),
        *date_range_parameters,
    ],
    responses=InspectionResponseSerializer(many=True),
)

create = extend_schema(
    tags=[API_TAGS.inspection],
    request=InspectionCreateSerializer,
    responses=InspectionResponseSerializer,
)

items = extend_schema(
    tags=[API_TAGS.inspection],
    parameters=[inspection_id_parameter],
    request=InspectionItemCreateSerializer,
    responses=InspectionResponseSerializer,
)

submit = extend_schema(
    tags=[API_TAGS.inspection],
    parameters=[inspection_id_parameter],
    request=None,
    responses=InspectionResponseSerializer,
)

report_fault = extend_schema(
    tags=[API_TAGS.inspection],
    parameters=[inspection_id_parameter],
    request=None,
    responses=FaultResponseSerializer,
)
