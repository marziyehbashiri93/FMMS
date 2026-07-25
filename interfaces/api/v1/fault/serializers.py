"""Model-free serializers for fault API v1."""

from __future__ import annotations

from rest_framework import serializers

from apps.fault.domain.entities import FaultStatus
from apps.fault.domain.value_objects import FaultSeverity


class FaultItemCreateSerializer(serializers.Serializer):
    """Validate one child item inside a multi-defect fault report."""

    code = serializers.CharField(max_length=40)
    description = serializers.CharField(max_length=500)
    severity = serializers.ChoiceField(choices=[item.value for item in FaultSeverity])
    component = serializers.CharField(
        max_length=100, required=False, allow_blank=True, default=""
    )


class FaultCreateSerializer(serializers.Serializer):
    """Validate fault report input."""

    vehicle_id = serializers.UUIDField()
    code = serializers.CharField(max_length=20)
    description = serializers.CharField(max_length=500)
    severity = serializers.ChoiceField(choices=[item.value for item in FaultSeverity])
    inspection_id = serializers.UUIDField(required=False, allow_null=True)
    items = FaultItemCreateSerializer(many=True, required=False)


class FaultListQuerySerializer(serializers.Serializer):
    """Validate fault list filters."""

    vehicle_id = serializers.UUIDField(required=False)
    status = serializers.ChoiceField(
        choices=[item.value for item in FaultStatus],
        required=False,
    )
    open_by_severity = serializers.ChoiceField(
        choices=[item.value for item in FaultSeverity],
        required=False,
    )


class FaultAssignSerializer(serializers.Serializer):
    """Validate fault assignment input."""

    technician_id = serializers.UUIDField()


class FaultDistributionDecisionSerializer(serializers.Serializer):
    """Validate distribution unit decision note."""

    note = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        trim_whitespace=True,
    )


class UserProfileSummarySerializer(serializers.Serializer):
    """Serialize nested user profile summaries."""

    id = serializers.UUIDField()
    name = serializers.CharField()
    role = serializers.CharField()


class FaultItemResponseSerializer(serializers.Serializer):
    """Serialize fault item DTOs nested under a fault response."""

    id = serializers.UUIDField()
    component = serializers.CharField()
    description = serializers.CharField()
    severity = serializers.ChoiceField(choices=[item.value for item in FaultSeverity])
    inspection_item_id = serializers.UUIDField(allow_null=True)


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
    items = FaultItemResponseSerializer(many=True)
    created_by = UserProfileSummarySerializer(allow_null=True, required=False)


class FaultCatalogResponseSerializer(serializers.Serializer):
    """Serialize SAP-synced fault catalog rows."""

    id = serializers.UUIDField()
    code_group = serializers.CharField()
    code = serializers.CharField()
    group_text = serializers.CharField()
    code_text = serializers.CharField()
    defect_class = serializers.CharField()
    defect_class_text = serializers.CharField()
    is_active = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
