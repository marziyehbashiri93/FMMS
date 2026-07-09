"""Model-free serializers for fault API v1."""

from __future__ import annotations

from rest_framework import serializers

from apps.fault.domain.entities import FaultStatus
from apps.fault.domain.value_objects import FaultSeverity


class FaultCreateSerializer(serializers.Serializer):
    """Validate fault report input."""

    vehicle_id = serializers.UUIDField()
    code = serializers.CharField(max_length=20)
    description = serializers.CharField(max_length=500)
    severity = serializers.ChoiceField(choices=[item.value for item in FaultSeverity])
    inspection_id = serializers.UUIDField(required=False, allow_null=True)


class FaultAssignSerializer(serializers.Serializer):
    """Validate fault assignment input."""

    technician_id = serializers.UUIDField()


class FaultResponseSerializer(serializers.Serializer):
    """Serialize application fault response DTOs."""

    id = serializers.UUIDField()
    vehicle_id = serializers.UUIDField()
    code = serializers.CharField()
    description = serializers.CharField()
    severity = serializers.ChoiceField(choices=[item.value for item in FaultSeverity])
    status = serializers.ChoiceField(choices=[item.value for item in FaultStatus])
    reported_by_id = serializers.UUIDField()
    reported_at = serializers.DateTimeField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    inspection_id = serializers.UUIDField(allow_null=True)
    assigned_to_id = serializers.UUIDField(allow_null=True)
    sap_notification_number = serializers.CharField(allow_null=True)
