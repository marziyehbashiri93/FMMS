"""Model-free serializers for driver API v1."""

from __future__ import annotations

from rest_framework import serializers

from apps.driver.domain.entities import DriverStatus
from apps.driver.domain.value_objects import LicenseClass


class DriverCreateSerializer(serializers.Serializer):
    """Validate driver registration input."""

    full_name = serializers.CharField(max_length=200)
    license_number = serializers.CharField(max_length=20)
    license_class = serializers.ChoiceField(
        choices=[item.value for item in LicenseClass]
    )
    phone = serializers.CharField(max_length=20)
    email = serializers.EmailField(required=False, allow_null=True)


class DriverAssignSerializer(serializers.Serializer):
    """Validate driver-to-vehicle assignment input."""

    vehicle_id = serializers.UUIDField()


class DriverResponseSerializer(serializers.Serializer):
    """Serialize application driver response DTOs."""

    id = serializers.UUIDField()
    full_name = serializers.CharField()
    license_number = serializers.CharField()
    license_class = serializers.ChoiceField(
        choices=[item.value for item in LicenseClass]
    )
    status = serializers.ChoiceField(choices=[item.value for item in DriverStatus])
    phone = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    email = serializers.EmailField(allow_null=True)
    assigned_vehicle_id = serializers.UUIDField(allow_null=True)
