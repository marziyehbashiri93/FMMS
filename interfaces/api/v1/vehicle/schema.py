"""OpenAPI schema configuration for vehicle API v1."""

from __future__ import annotations

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema

from apps.vehicle.domain.entities import VehicleStatus
from interfaces.api.v1.schema_tags import API_TAGS
from interfaces.api.v1.vehicle.serializers import (
    VehicleOdometerRecordSerializer,
    VehicleOdometerResponseSerializer,
    VehicleResponseSerializer,
    VehicleStatusChangeSerializer,
)

_VEHICLE_ORDERING_FIELDS = [
    "vehicle_number",
    "-vehicle_number",
    "license_plate",
    "-license_plate",
    "status",
    "-status",
    "created_at",
    "-created_at",
    "updated_at",
    "-updated_at",
    "commissioning_date",
    "-commissioning_date",
    "driver1_customer_number",
    "-driver1_customer_number",
    "driver2_customer_number",
    "-driver2_customer_number",
]

vehicle_id_parameter = OpenApiParameter(
    name="id",
    location=OpenApiParameter.PATH,
    required=True,
    type=OpenApiTypes.UUID,
)

retrieve = extend_schema(
    tags=[API_TAGS.vehicle],
    parameters=[vehicle_id_parameter],
    responses=VehicleResponseSerializer,
)

list = extend_schema(
    tags=[API_TAGS.vehicle],
    parameters=[
        OpenApiParameter(
            name="status",
            description="Filter vehicles by lifecycle status. Omit to return active vehicles.",
            required=False,
            type=str,
            enum=[item.value for item in VehicleStatus],
        ),
        OpenApiParameter(
            name="ordering",
            description="Sort vehicles by a supported field. Prefix with '-' for descending order.",
            required=False,
            type=str,
            enum=_VEHICLE_ORDERING_FIELDS,
        ),
    ],
    responses=VehicleResponseSerializer(many=True),
)

activate = extend_schema(
    tags=[API_TAGS.vehicle],
    parameters=[vehicle_id_parameter],
    request=None,
    responses=VehicleResponseSerializer,
)

deactivate = extend_schema(
    tags=[API_TAGS.vehicle],
    parameters=[vehicle_id_parameter],
    request=None,
    responses=VehicleResponseSerializer,
)

change_status = extend_schema(
    tags=[API_TAGS.vehicle],
    parameters=[vehicle_id_parameter],
    request=VehicleStatusChangeSerializer,
    responses=VehicleResponseSerializer,
)

odometer_list = extend_schema(
    tags=[API_TAGS.vehicle],
    methods=["GET"],
    parameters=[vehicle_id_parameter],
    responses=VehicleOdometerResponseSerializer(many=True),
)

odometer_record = extend_schema(
    tags=[API_TAGS.vehicle],
    methods=["POST"],
    parameters=[vehicle_id_parameter],
    request=VehicleOdometerRecordSerializer,
    responses=VehicleOdometerResponseSerializer,
)
