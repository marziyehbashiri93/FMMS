"""Model-free serializers for vehicle API v1."""

from __future__ import annotations

from rest_framework import serializers

from apps.vehicle.domain.entities import VehicleCategory, VehicleStatus


class VehicleCreateSerializer(serializers.Serializer):
    """Validate vehicle creation input."""

    plate_number = serializers.CharField(max_length=32)
    vin = serializers.CharField(min_length=17, max_length=17)
    make = serializers.CharField(max_length=100)
    model = serializers.CharField(max_length=100)
    year = serializers.IntegerField(min_value=1886)
    category = serializers.ChoiceField(choices=[item.value for item in VehicleCategory])
    chassis_number = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    sap_equipment_number = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )


class VehicleUpdateSerializer(serializers.Serializer):
    """Validate mutable vehicle fields."""

    make = serializers.CharField(max_length=100, required=False)
    model = serializers.CharField(max_length=100, required=False)
    year = serializers.IntegerField(min_value=1886, required=False)
    category = serializers.ChoiceField(
        choices=[item.value for item in VehicleCategory], required=False
    )
    chassis_number = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    sap_equipment_number = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )


class SAPEquipmentSyncSerializer(serializers.Serializer):
    """Validate an SAP equipment synchronization request."""

    sap_equipment_number = serializers.CharField()


class VehicleSAPSyncResultSerializer(serializers.Serializer):
    """Serialize bulk SAP vehicle sync result counts."""

    total_received = serializers.IntegerField()
    created = serializers.IntegerField()
    updated = serializers.IntegerField()
    failed = serializers.IntegerField()


class VehicleResponseSerializer(serializers.Serializer):
    """Serialize application vehicle response DTOs."""

    id = serializers.UUIDField()
    plate_number = serializers.CharField()
    vin = serializers.CharField()
    make = serializers.CharField()
    model = serializers.CharField()
    year = serializers.IntegerField()
    category = serializers.ChoiceField(choices=[item.value for item in VehicleCategory])
    status = serializers.ChoiceField(choices=[item.value for item in VehicleStatus])
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    chassis_number = serializers.CharField(allow_null=True)
    sap_equipment_number = serializers.CharField(allow_null=True)
