"""OpenAPI schema configuration for driver API v1."""

from __future__ import annotations

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema

from apps.driver.domain.entities import DriverStatus
from interfaces.api.v1.driver.serializers import DriverResponseSerializer

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
    parameters=[driver_id_parameter],
    responses=DriverResponseSerializer,
)

list = extend_schema(
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
    ],
    responses=DriverResponseSerializer(many=True),
)
