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
