"""Model-free serializers for driver API v1."""

from __future__ import annotations

from rest_framework import serializers

from apps.driver.application.services.get_driver_service import DriverAssignmentRole
from apps.driver.domain.entities import DriverStatus

DRIVER_ORDERING_CHOICES = [
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
DRIVER_ROLE_CHOICES = [item.value for item in DriverAssignmentRole]
DRIVER_STATUS_CHOICES = [item.value for item in DriverStatus]


class DriverListQuerySerializer(serializers.Serializer):
    """Validate query parameters accepted by the driver list endpoint."""

    status = serializers.ChoiceField(
        choices=DRIVER_STATUS_CHOICES,
        required=False,
    )
    ordering = serializers.ChoiceField(
        choices=DRIVER_ORDERING_CHOICES,
        required=False,
        allow_blank=True,
    )
    search = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True)
    role = serializers.CharField(
        required=False,
        allow_blank=True,
        trim_whitespace=True,
    )

    def validate_role(self, value: str) -> str:
        """Normalize and validate the current assignment role filter."""
        normalized = value.upper()
        if normalized and normalized not in DRIVER_ROLE_CHOICES:
            raise serializers.ValidationError(
                "Unsupported role filter. Allowed values are DRIVER and ASSISTANT."
            )
        return normalized


class DriverAssignedVehicleSerializer(serializers.Serializer):
    """Serialize assigned vehicle details in driver responses."""

    id = serializers.UUIDField()
    vehicle_number = serializers.CharField()
    license_plate = serializers.CharField()


class DriverResponseSerializer(serializers.Serializer):
    """Serialize application driver response DTOs."""

    id = serializers.UUIDField()
    customer_number = serializers.CharField()
    name = serializers.CharField()
    status = serializers.ChoiceField(choices=DRIVER_STATUS_CHOICES)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    mobile = serializers.CharField(allow_null=True)
    personnel_number = serializers.CharField(allow_null=True)
    gender = serializers.CharField(allow_null=True)
    nilofar_code = serializers.CharField(allow_null=True)
    current_vehicle_as_driver = DriverAssignedVehicleSerializer(allow_null=True)
    current_vehicle_as_assistant = DriverAssignedVehicleSerializer(allow_null=True)


class DriverExitCenterSerializer(serializers.Serializer):
    """Validate driver vehicle-center exit request."""

    vehicle_id = serializers.UUIDField()
    inspection_id = serializers.UUIDField()


class DriverSummarySerializer(serializers.Serializer):
    """Serialize driver dashboard summary values."""

    active_count = serializers.IntegerField()
    decommissioned_count = serializers.IntegerField()
    with_vehicle_count = serializers.IntegerField()
    last_sap_sync_at = serializers.DateTimeField(allow_null=True)
