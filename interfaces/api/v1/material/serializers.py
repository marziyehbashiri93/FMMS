"""Serializers for material request APIs."""

from __future__ import annotations

from rest_framework import serializers

from apps.material.domain.entities import (
    MaterialItemDecision,
    MaterialItemStatus,
    MaterialRequestStatus,
)


class MaterialRequestItemCreateSerializer(serializers.Serializer):
    """Validate material request item payload."""

    material_number = serializers.CharField(max_length=18)
    quantity = serializers.DecimalField(max_digits=12, decimal_places=3)
    from_catalog = serializers.BooleanField(required=False, default=True)


class MaterialRequestCreateSerializer(serializers.Serializer):
    """Validate material request creation payload."""

    items = MaterialRequestItemCreateSerializer(many=True, min_length=1)


class PartsItemDecisionSerializer(serializers.Serializer):
    """Validate one per-item transport decision."""

    item_id = serializers.UUIDField()
    decision = serializers.ChoiceField(
        choices=[
            MaterialItemDecision.FROM_STOCK.value,
            MaterialItemDecision.PURCHASE.value,
        ]
    )


class PartsAvailabilityDecisionSerializer(serializers.Serializer):
    """Validate transport per-item availability decision payload."""

    items = PartsItemDecisionSerializer(many=True, min_length=1)
    note = serializers.CharField(
        max_length=500, required=False, allow_blank=True, default=""
    )


class MaterialRequestItemResponseSerializer(serializers.Serializer):
    """Serialize material request item DTO."""

    id = serializers.UUIDField()
    material_number = serializers.CharField()
    quantity = serializers.DecimalField(max_digits=12, decimal_places=3)
    from_catalog = serializers.BooleanField()
    decision = serializers.ChoiceField(
        choices=[item.value for item in MaterialItemDecision]
    )
    item_status = serializers.ChoiceField(
        choices=[item.value for item in MaterialItemStatus]
    )
    material_name = serializers.CharField(allow_blank=True)
    available_quantity = serializers.DecimalField(max_digits=18, decimal_places=3)
    in_catalog = serializers.BooleanField()
    available_quantity_snapshot = serializers.DecimalField(
        max_digits=18, decimal_places=3, allow_null=True, required=False
    )


class MaterialRequestResponseSerializer(serializers.Serializer):
    """Serialize material request response DTO."""

    id = serializers.UUIDField()
    repair_order_id = serializers.UUIDField()
    status = serializers.ChoiceField(
        choices=[item.value for item in MaterialRequestStatus]
    )
    created_by_id = serializers.UUIDField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    items = MaterialRequestItemResponseSerializer(many=True)


class CentralStockResponseSerializer(serializers.Serializer):
    """Serialize SAP-synced central warehouse stock rows."""

    id = serializers.UUIDField()
    material = serializers.CharField()
    plant = serializers.CharField()
    storage_location = serializers.CharField()
    inventory_stock_type = serializers.CharField()
    material_code = serializers.CharField()
    material_name = serializers.CharField(allow_blank=True)
    inventory_stock_type_text = serializers.CharField()
    quantity = serializers.DecimalField(max_digits=18, decimal_places=3)
    base_unit = serializers.CharField()
    stock_value = serializers.DecimalField(max_digits=18, decimal_places=2)
    display_currency = serializers.CharField()
    is_active = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
