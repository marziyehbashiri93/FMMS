"""Serializers for vehicle handover APIs."""

from __future__ import annotations

from rest_framework import serializers

from apps.handover.domain.entities import VehicleHandoverStatus


class VehicleHandoverConfirmSerializer(serializers.Serializer):
    """Validate handover confirmation payload."""

    accepted = serializers.BooleanField()
    comment = serializers.CharField(
        max_length=500, required=False, allow_null=True, allow_blank=True
    )


class VehicleHandoverResponseSerializer(serializers.Serializer):
    """Serialize handover response DTO."""

    id = serializers.UUIDField()
    repair_order_id = serializers.UUIDField()
    vehicle_id = serializers.UUIDField()
    status = serializers.ChoiceField(
        choices=[item.value for item in VehicleHandoverStatus]
    )
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    comment = serializers.CharField(allow_null=True)
    driver_id = serializers.UUIDField(allow_null=True, required=False)
    confirmed_at = serializers.DateTimeField(allow_null=True, required=False)
