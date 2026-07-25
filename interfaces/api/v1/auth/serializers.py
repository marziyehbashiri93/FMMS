"""Authentication serializers for API v1."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from rest_framework import serializers
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
    TokenRefreshSerializer,
)
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken, Token

_TOKEN_TYPE = "Bearer"


def _expires_at(token: Token) -> str:
    """Return the JWT expiration timestamp as an ISO-8601 UTC string."""
    return datetime.fromtimestamp(int(token["exp"]), tz=UTC).isoformat()


class UsernameTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Obtain JWTs using FMMS username credentials."""

    username_field = "username"

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Return tokens, expiry metadata, and the authenticated user profile."""
        data = super().validate(attrs)
        data["token_type"] = _TOKEN_TYPE
        data["access_expires_at"] = _expires_at(AccessToken(data["access"]))
        data["refresh_expires_at"] = _expires_at(RefreshToken(data["refresh"]))
        data["user"] = UserProfileSerializer(self.user).data
        return data


class FMMSJWTTokenRefreshSerializer(TokenRefreshSerializer):
    """Refresh access tokens and return frontend-friendly expiry metadata."""

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Return a refreshed access token plus its expiration timestamp."""
        data = super().validate(attrs)
        data["token_type"] = _TOKEN_TYPE
        data["access_expires_at"] = _expires_at(AccessToken(data["access"]))
        return data


class LinkedDriverSerializer(serializers.Serializer):
    """SAP driver linked to the login user via personnel number."""

    id = serializers.UUIDField()
    customer_number = serializers.CharField()
    name = serializers.CharField()
    personnel_number = serializers.CharField(allow_blank=True)


class UserProfileSerializer(serializers.Serializer):
    """Serialize the authenticated FMMS user for frontend session state."""

    id = serializers.UUIDField(read_only=True)
    username = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    full_name = serializers.CharField(read_only=True)
    role = serializers.CharField(read_only=True)
    personnel_number = serializers.CharField(read_only=True, allow_blank=True)
    is_staff = serializers.BooleanField(read_only=True)
    is_superuser = serializers.BooleanField(read_only=True)
    linked_driver = LinkedDriverSerializer(read_only=True, allow_null=True, required=False)

    def to_representation(self, instance: Any) -> dict[str, Any]:
        """Include SAP driver link resolved by personnel_number when present."""
        data = super().to_representation(instance)
        personnel = str(getattr(instance, "personnel_number", "") or "").strip()
        data["personnel_number"] = personnel
        data["linked_driver"] = None
        if not personnel:
            return data
        try:
            from interfaces.api.v1 import deps  # noqa: PLC0415

            driver = deps.get_driver_repository().find_by_personnel_number(personnel)
        except Exception:  # noqa: BLE001 — profile must not fail if driver sync is down
            return data
        if driver is None:
            return data
        data["linked_driver"] = {
            "id": driver.id,
            "customer_number": driver.customer_number.value,
            "name": driver.name,
            "personnel_number": driver.personnel_number or "",
        }
        return data


class TokenObtainPairResponseSerializer(serializers.Serializer):
    """Document token obtain response fields."""

    access = serializers.CharField()
    refresh = serializers.CharField()
    token_type = serializers.CharField()
    access_expires_at = serializers.DateTimeField()
    refresh_expires_at = serializers.DateTimeField()
    user = UserProfileSerializer()


class TokenRefreshResponseSerializer(serializers.Serializer):
    """Document token refresh response fields."""

    access = serializers.CharField()
    token_type = serializers.CharField()
    access_expires_at = serializers.DateTimeField()
