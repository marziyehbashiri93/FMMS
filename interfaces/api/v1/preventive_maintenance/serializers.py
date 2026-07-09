"""Model-free serializers for preventive maintenance API v1."""

from __future__ import annotations

from rest_framework import serializers

from apps.preventive_maintenance.domain.entities import PMPlanStatus, PMWorkOrderStatus
from apps.preventive_maintenance.domain.value_objects import IntervalUnit, TriggerType


class PMPlanCreateSerializer(serializers.Serializer):
    """Validate PM plan creation input."""

    vehicle_id = serializers.UUIDField()
    name = serializers.CharField(max_length=200)
    description = serializers.CharField(max_length=1000)
    interval_value = serializers.IntegerField(min_value=1)
    interval_unit = serializers.ChoiceField(
        choices=[item.value for item in IntervalUnit]
    )
    trigger_type = serializers.ChoiceField(choices=[item.value for item in TriggerType])
    trigger_threshold = serializers.IntegerField(min_value=1)


class PMTriggerSerializer(serializers.Serializer):
    """Validate PM work-order trigger input."""

    scheduled_date = serializers.DateTimeField()
    create_sap_notification = serializers.BooleanField(required=False, default=False)
    defect_code = serializers.CharField(required=False, default="PM-TRIG")
    priority = serializers.CharField(required=False, default="3")
    notes = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class PMCompleteSerializer(serializers.Serializer):
    """Validate PM work-order completion input."""

    completed_at = serializers.DateTimeField()
    notes = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class PMPlanResponseSerializer(serializers.Serializer):
    """Serialize PM plan response DTOs."""

    id = serializers.UUIDField()
    vehicle_id = serializers.UUIDField()
    name = serializers.CharField()
    description = serializers.CharField()
    interval_value = serializers.IntegerField()
    interval_unit = serializers.ChoiceField(
        choices=[item.value for item in IntervalUnit]
    )
    trigger_type = serializers.ChoiceField(choices=[item.value for item in TriggerType])
    trigger_threshold = serializers.IntegerField()
    status = serializers.ChoiceField(choices=[item.value for item in PMPlanStatus])
    created_by_id = serializers.UUIDField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    last_triggered_at = serializers.DateTimeField(allow_null=True)
    next_due_at = serializers.DateTimeField(allow_null=True)


class PMWorkOrderResponseSerializer(serializers.Serializer):
    """Serialize PM work-order response DTOs."""

    id = serializers.UUIDField()
    plan_id = serializers.UUIDField()
    vehicle_id = serializers.UUIDField()
    status = serializers.ChoiceField(choices=[item.value for item in PMWorkOrderStatus])
    scheduled_date = serializers.DateTimeField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    triggered_at = serializers.DateTimeField(allow_null=True)
    completed_at = serializers.DateTimeField(allow_null=True)
    notes = serializers.CharField(allow_null=True)
    sap_order_number = serializers.CharField(allow_null=True)
    sap_notification_number = serializers.CharField(allow_null=True)
