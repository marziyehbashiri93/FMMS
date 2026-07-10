"""Serializers for inspection checklist template API v1."""

from __future__ import annotations

from rest_framework import serializers


class InspectionTemplateResponseSerializer(serializers.Serializer):
    """Serialize inspection checklist template DTOs."""

    id = serializers.UUIDField()
    sap_code = serializers.CharField()
    code_group = serializers.CharField()
    category = serializers.CharField()
    description = serializers.CharField()
    catalog_type = serializers.CharField()
    is_active = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class InspectionTemplateSyncResultSerializer(serializers.Serializer):
    """Serialize bulk SAP inspection-template sync result counts."""

    total_received = serializers.IntegerField()
    created = serializers.IntegerField()
    updated = serializers.IntegerField()
    failed = serializers.IntegerField()
