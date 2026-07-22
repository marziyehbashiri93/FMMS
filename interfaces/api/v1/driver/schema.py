"""OpenAPI schema configuration for driver API v1."""

from __future__ import annotations

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema

from apps.driver.domain.entities import DriverStatus
from interfaces.api.v1.driver.serializers import (
    DriverExitCenterSerializer,
    DriverResponseSerializer,
    DriverSummarySerializer,
)
from interfaces.api.v1.schema_tags import API_TAGS
from interfaces.api.v1.vehicle.schema import date_range_parameters
from interfaces.api.v1.vehicle.serializers import (
    VehicleDriverAssignmentHistoryResponseSerializer,
    VehicleResponseSerializer,
)

_DRIVER_ORDERING_FIELDS = [
    "customer_number",
    "-customer_number",
    "name",
    "-name",
    "mobile",
    "-mobile",
    "personnel_number",
    "-personnel_number",
    "gender",
    "-gender",
    "nilofar_code",
    "-nilofar_code",
    "status",
    "-status",
    "created_at",
    "-created_at",
    "updated_at",
    "-updated_at",
]

driver_id_parameter = OpenApiParameter(
    name="id",
    location=OpenApiParameter.PATH,
    required=True,
    type=OpenApiTypes.UUID,
)

retrieve = extend_schema(
    tags=[API_TAGS.driver],
    parameters=[driver_id_parameter],
    responses=DriverResponseSerializer,
)

list = extend_schema(
    tags=[API_TAGS.driver],
    parameters=[
        OpenApiParameter(
            name="status",
            description="Filter drivers by lifecycle status. Omit to return all statuses.",
            required=False,
            type=str,
            enum=[item.value for item in DriverStatus],
        ),
        OpenApiParameter(
            name="ordering",
            description="Sort drivers by a supported field. Prefix with '-' for descending order.",
            required=False,
            type=str,
            enum=_DRIVER_ORDERING_FIELDS,
        ),
        OpenApiParameter(
            name="search",
            description="Case-insensitive contains filter on name or personnel_number.",
            required=False,
            type=str,
        ),
        OpenApiParameter(
            name="role",
            description="Filter by current vehicle assignment role.",
            required=False,
            type=str,
            enum=["DRIVER", "ASSISTANT"],
        ),
    ],
    responses=DriverResponseSerializer(many=True),
)

summary = extend_schema(
    tags=[API_TAGS.driver],
    responses=DriverSummarySerializer,
)

exit_center = extend_schema(
    tags=[API_TAGS.driver],
    parameters=[driver_id_parameter],
    request=DriverExitCenterSerializer,
    responses=VehicleResponseSerializer,
)

vehicle_assignment_history = extend_schema(
    tags=[API_TAGS.driver],
    parameters=[driver_id_parameter, *date_range_parameters],
    responses=VehicleDriverAssignmentHistoryResponseSerializer(many=True),
)
