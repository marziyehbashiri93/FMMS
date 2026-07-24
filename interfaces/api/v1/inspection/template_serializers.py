"""Serializers for inspection checklist template API v1."""

from __future__ import annotations

from rest_framework import serializers


class InspectionTemplateResponseSerializer(serializers.Serializer):
    """Serialize inspection checklist template DTOs."""

    id = serializers.UUIDField()
    CodeGroup = serializers.CharField(source="code_group")
    Code = serializers.CharField(source="code")
    GroupText = serializers.CharField(source="group_text")
    CodeText = serializers.CharField(source="code_text")
    is_active = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
