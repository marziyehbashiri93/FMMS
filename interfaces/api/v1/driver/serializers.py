"""Model-free serializers for driver API v1."""

from __future__ import annotations

from rest_framework import serializers

from apps.driver.domain.entities import DriverStatus


class DriverResponseSerializer(serializers.Serializer):
    """Serialize application driver response DTOs."""

    id = serializers.UUIDField()
    customer_number = serializers.CharField()
    name = serializers.CharField()
    status = serializers.ChoiceField(choices=[item.value for item in DriverStatus])
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    mobile = serializers.CharField(allow_null=True)
    personnel_number = serializers.CharField(allow_null=True)
    gender = serializers.CharField(allow_null=True)
    nilofar_code = serializers.CharField(allow_null=True)
