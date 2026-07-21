"""Model-free serializers for integration API v1."""

from __future__ import annotations

from rest_framework import serializers

from apps.integration.domain.entities import SAPObjectType, SAPTransactionStatus


class SAPTransactionResponseSerializer(serializers.Serializer):
    """Serialize SAP transaction domain entities for read APIs."""

    id = serializers.UUIDField()
    object_type = serializers.ChoiceField(
        choices=[item.value for item in SAPObjectType]
    )
    object_id = serializers.UUIDField()
    idempotency_key = serializers.CharField()
    status = serializers.ChoiceField(
        choices=[item.value for item in SAPTransactionStatus]
    )
    retry_count = serializers.IntegerField()
    max_retries = serializers.IntegerField()
    request_payload = serializers.DictField()
    response_payload = serializers.DictField(allow_null=True)
    sap_document_number = serializers.CharField(allow_null=True)
    error_message = serializers.CharField(allow_null=True)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    completed_at = serializers.DateTimeField(allow_null=True)


class SAPSyncItemResultSerializer(serializers.Serializer):
    """Serialize the result of one SAP read-sync item."""

    name = serializers.CharField()
    status = serializers.ChoiceField(choices=["SUCCESS", "FAILED", "PARTIAL_SUCCESS"])
    started_at = serializers.DateTimeField()
    finished_at = serializers.DateTimeField()
    summary = serializers.DictField()
    error = serializers.CharField(allow_null=True)


class SAPSyncRunResponseSerializer(serializers.Serializer):
    """Serialize the global SAP read-sync run result."""

    id = serializers.CharField()
    trigger_source = serializers.ChoiceField(choices=["API", "CELERY", "JOB"])
    status = serializers.ChoiceField(choices=["SUCCESS", "FAILED", "PARTIAL_SUCCESS"])
    started_at = serializers.DateTimeField()
    finished_at = serializers.DateTimeField()
    items = SAPSyncItemResultSerializer(many=True)


class SAPSyncRunHistorySerializer(serializers.Serializer):
    """Serialize a persisted SAP read-sync run."""

    id = serializers.CharField()
    trigger_source = serializers.ChoiceField(choices=["API", "CELERY", "JOB"])
    status = serializers.ChoiceField(
        choices=["IN_PROGRESS", "SUCCESS", "FAILED", "PARTIAL_SUCCESS"]
    )
    request_id = serializers.CharField()
    triggered_by = serializers.CharField(allow_null=True)
    started_at = serializers.DateTimeField()
    finished_at = serializers.DateTimeField(allow_null=True)
    summary = serializers.DictField()
    error = serializers.CharField(allow_null=True)
    items = SAPSyncItemResultSerializer(many=True)
