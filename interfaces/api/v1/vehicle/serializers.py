"""Model-free serializers for vehicle API v1."""

from __future__ import annotations

from rest_framework import serializers

from apps.vehicle.domain.entities import VehicleStatus


class VehicleUpdateSerializer(serializers.Serializer):
    """Validate FMMS-owned vehicle status changes."""

    status = serializers.ChoiceField(choices=[item.value for item in VehicleStatus])


class VehicleSAPSyncResultSerializer(serializers.Serializer):
    """Serialize bulk SAP vehicle sync result counts."""

    total_received = serializers.IntegerField()
    created = serializers.IntegerField()
    updated = serializers.IntegerField()
    decommissioned = serializers.IntegerField()
    failed = serializers.IntegerField()


class VehicleResponseSerializer(serializers.Serializer):
    """Serialize application vehicle response DTOs."""

    id = serializers.UUIDField()
    vehicle_number = serializers.CharField()
    license_plate = serializers.CharField()
    status = serializers.ChoiceField(choices=[item.value for item in VehicleStatus])
    status_label = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    commissioning_date = serializers.CharField(allow_null=True)
    driver1_customer_number = serializers.CharField(allow_null=True)
    driver2_customer_number = serializers.CharField(allow_null=True)


class VehicleOdometerRecordSerializer(serializers.Serializer):
    """Validate a daily odometer reading."""

    reading_date = serializers.DateField()
    odometer_km = serializers.IntegerField(min_value=0)
    source = serializers.CharField(max_length=30, required=False, default="DRIVER")


class VehicleOdometerResponseSerializer(serializers.Serializer):
    """Serialize vehicle odometer history entries."""

    id = serializers.UUIDField()
    vehicle_id = serializers.UUIDField()
    reading_date = serializers.DateField()
    odometer_km = serializers.IntegerField()
    source = serializers.CharField()
    recorded_by = serializers.UUIDField()
    recorded_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
