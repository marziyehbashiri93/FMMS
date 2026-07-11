"""Model-free serializers for repair API v1."""

from __future__ import annotations

from rest_framework import serializers

from apps.repair.domain.entities import RepairOrderStatus, WorkshopType
from apps.repair.domain.invoice_entities import ExternalRepairInvoiceStatus


class RepairOrderCreateSerializer(serializers.Serializer):
    """Validate repair order creation input."""

    vehicle_id = serializers.UUIDField()
    fault_id = serializers.UUIDField()


class RepairAssignSerializer(serializers.Serializer):
    """Validate repair assignment input."""

    technician_id = serializers.UUIDField()


class RepairAssignWorkshopSerializer(serializers.Serializer):
    """Validate workshop type selection after transport approval."""

    workshop_type = serializers.ChoiceField(
        choices=[item.value for item in WorkshopType]
    )
    workshop_id = serializers.CharField(
        max_length=64, required=False, allow_null=True, allow_blank=True
    )


class RepairCompleteSerializer(serializers.Serializer):
    """Validate repair completion input."""

    completed_at = serializers.DateTimeField()


class RepairActivityCreateSerializer(serializers.Serializer):
    """Validate repair activity creation input."""

    description = serializers.CharField(max_length=500)
    labor_hours = serializers.DecimalField(max_digits=8, decimal_places=2)
    performed_by_id = serializers.UUIDField()
    performed_at = serializers.DateTimeField()
    notes = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class RepairPartCreateSerializer(serializers.Serializer):
    """Validate repair part creation input."""

    material_number = serializers.CharField(max_length=18)
    quantity = serializers.IntegerField(min_value=1)
    unit_of_measure = serializers.CharField(max_length=10)


class RepairSyncSAPSerializer(serializers.Serializer):
    """Validate repair-to-SAP sync input."""

    order_type = serializers.CharField(max_length=10)
    description = serializers.CharField(max_length=200)
    planned_start = serializers.DateTimeField()
    plant = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    work_center = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )


class RepairActivityResponseSerializer(serializers.Serializer):
    """Serialize repair activity DTOs."""

    id = serializers.UUIDField()
    description = serializers.CharField()
    labor_hours = serializers.DecimalField(max_digits=8, decimal_places=2)
    performed_by_id = serializers.UUIDField()
    performed_at = serializers.DateTimeField()
    notes = serializers.CharField(allow_null=True)


class RepairPartResponseSerializer(serializers.Serializer):
    """Serialize repair part DTOs."""

    id = serializers.UUIDField()
    material_number = serializers.CharField()
    quantity = serializers.IntegerField()
    unit_of_measure = serializers.CharField()
    goods_issue_id = serializers.UUIDField(allow_null=True)
    posted_at = serializers.DateTimeField(allow_null=True)


class RepairOrderTimelineEventSerializer(serializers.Serializer):
    """Serialize one repair-order timeline event."""

    event = serializers.CharField()
    description = serializers.CharField()
    created_at = serializers.DateTimeField()
    created_by_id = serializers.UUIDField(allow_null=True, required=False)


class RepairOrderResponseSerializer(serializers.Serializer):
    """Serialize application repair order response DTOs."""

    id = serializers.UUIDField()
    vehicle_id = serializers.UUIDField()
    fault_id = serializers.UUIDField()
    status = serializers.ChoiceField(choices=[item.value for item in RepairOrderStatus])
    created_by_id = serializers.UUIDField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    activities = RepairActivityResponseSerializer(many=True)
    parts = RepairPartResponseSerializer(many=True)
    technician_id = serializers.UUIDField(allow_null=True)
    assigned_at = serializers.DateTimeField(allow_null=True)
    sap_order_number = serializers.CharField(allow_null=True)
    workshop_type = serializers.ChoiceField(
        choices=[item.value for item in WorkshopType], allow_null=True
    )
    workshop_id = serializers.CharField(allow_null=True)
    completed_at = serializers.DateTimeField(allow_null=True)


class RepairDecisionResponseSerializer(serializers.Serializer):
    """Serialize transport approval / workshop assignment action responses."""

    id = serializers.UUIDField()
    status = serializers.ChoiceField(choices=[item.value for item in RepairOrderStatus])
    message = serializers.CharField()
    workshop_type = serializers.ChoiceField(
        choices=[item.value for item in WorkshopType],
        allow_null=True,
        required=False,
    )
    workshop_id = serializers.CharField(allow_null=True, required=False)


class ExternalInvoiceUploadSerializer(serializers.Serializer):
    """Validate external invoice upload payload."""

    amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    currency = serializers.CharField(max_length=3)
    vendor_id = serializers.CharField(
        max_length=64, required=False, allow_null=True, allow_blank=True
    )
    document = serializers.CharField(
        max_length=500, required=False, allow_null=True, allow_blank=True
    )


class ExternalInvoiceResponseSerializer(serializers.Serializer):
    """Serialize external invoice response DTO."""

    id = serializers.UUIDField()
    repair_order_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    currency = serializers.CharField()
    status = serializers.ChoiceField(
        choices=[item.value for item in ExternalRepairInvoiceStatus]
    )
    created_by_id = serializers.UUIDField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    vendor_id = serializers.CharField(allow_null=True, required=False)
    document = serializers.CharField(allow_null=True, required=False)
