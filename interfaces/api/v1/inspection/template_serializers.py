"""Serializers for inspection checklist template API v1."""

from __future__ import annotations

from rest_framework import serializers


class InspectionTemplateResponseSerializer(serializers.Serializer):
    """Serialize inspection checklist template DTOs."""

    id = serializers.UUIDField()
    code_group = serializers.CharField()
    code = serializers.CharField()
    group_text = serializers.CharField()
    code_text = serializers.CharField()
    is_active = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
