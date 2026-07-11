"""Serializers for material request APIs."""

from __future__ import annotations

from rest_framework import serializers

from apps.material.domain.entities import MaterialRequestStatus


class MaterialRequestItemCreateSerializer(serializers.Serializer):
    """Validate material request item payload."""

    material_number = serializers.CharField(max_length=18)
    quantity = serializers.DecimalField(max_digits=12, decimal_places=3)
    unit_of_measure = serializers.CharField(max_length=10)


class MaterialRequestCreateSerializer(serializers.Serializer):
    """Validate material request creation payload."""

    items = MaterialRequestItemCreateSerializer(many=True, min_length=1)


class MaterialRequestItemResponseSerializer(serializers.Serializer):
    """Serialize material request item DTO."""

    id = serializers.UUIDField()
    material_number = serializers.CharField()
    quantity = serializers.DecimalField(max_digits=12, decimal_places=3)
    unit_of_measure = serializers.CharField()


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
