"""Model-free serializers for driver API v1."""

from __future__ import annotations

from rest_framework import serializers

from apps.driver.domain.entities import DriverStatus


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
    status = serializers.ChoiceField(choices=[item.value for item in DriverStatus])
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
