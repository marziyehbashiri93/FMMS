"""Model-free serializers for inspection API v1."""

from __future__ import annotations

from rest_framework import serializers

from apps.inspection.domain.entities import InspectionStatus, InspectionType
from apps.inspection.domain.value_objects import (
    ChecklistResult,
    FailureSeverity,
    OdometerUnit,
)


class InspectionItemCreateSerializer(serializers.Serializer):
    """Validate checklist item creation input."""

    category = serializers.CharField(max_length=100)
    description = serializers.CharField(max_length=500)
    result = serializers.ChoiceField(choices=[item.value for item in ChecklistResult])
    notes = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    severity = serializers.ChoiceField(
        choices=[item.value for item in FailureSeverity],
        required=False,
        allow_null=True,
    )

    def validate(self, attrs: dict) -> dict:
        """Require severity on FAIL items; forbid it on PASS/NA items."""
        result = attrs.get("result")
        severity = attrs.get("severity")
        if result == ChecklistResult.FAIL.value:
            if not severity:
                raise serializers.ValidationError(
                    {"severity": "Severity is required when result is FAIL."}
                )
        elif severity:
            raise serializers.ValidationError(
                {"severity": "Severity may only be set when result is FAIL."}
            )
        return attrs


class InspectionCreateSerializer(serializers.Serializer):
    """Validate inspection creation input."""

    vehicle_id = serializers.UUIDField()
    inspection_type = serializers.ChoiceField(
        choices=[item.value for item in InspectionType]
    )
    odometer_value = serializers.IntegerField(min_value=0)
    odometer_unit = serializers.ChoiceField(
        choices=[item.value for item in OdometerUnit]
    )
    inspected_at = serializers.DateTimeField()
    driver_id = serializers.UUIDField(required=False, allow_null=True)
    items = InspectionItemCreateSerializer(many=True, required=False)


class InspectionDriverSummarySerializer(serializers.Serializer):
    """Serialize nested driver summary on inspection history."""

    id = serializers.UUIDField()
    name = serializers.CharField()


class InspectionItemResponseSerializer(serializers.Serializer):
    """Serialize inspection checklist item DTOs."""

    id = serializers.UUIDField()
    category = serializers.CharField()
    description = serializers.CharField()
    result = serializers.ChoiceField(choices=[item.value for item in ChecklistResult])
    notes = serializers.CharField(allow_null=True)
    severity = serializers.ChoiceField(
        choices=[item.value for item in FailureSeverity],
        allow_null=True,
        required=False,
    )


class InspectionResponseSerializer(serializers.Serializer):
    """Serialize application inspection response DTOs."""

    id = serializers.UUIDField()
    vehicle_id = serializers.UUIDField()
    inspection_type = serializers.ChoiceField(
        choices=[item.value for item in InspectionType]
    )
    odometer_value = serializers.IntegerField()
    odometer_unit = serializers.ChoiceField(
        choices=[item.value for item in OdometerUnit]
    )
    status = serializers.ChoiceField(choices=[item.value for item in InspectionStatus])
    inspected_at = serializers.DateTimeField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    items = InspectionItemResponseSerializer(many=True)
    driver_id = serializers.UUIDField(allow_null=True)
    reviewed_by_id = serializers.UUIDField(allow_null=True)
    review_notes = serializers.CharField(allow_null=True)
    has_failures = serializers.BooleanField()
    overall_result = serializers.CharField()
    related_fault_ids = serializers.ListField(child=serializers.UUIDField())
    driver = InspectionDriverSummarySerializer(allow_null=True, required=False)
