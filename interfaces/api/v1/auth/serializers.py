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

from apps.authentication.infrastructure.models import FMMSUser

_TOKEN_TYPE = "Bearer"


def _expires_at(token: Token) -> str:
    """Return the JWT expiration timestamp as an ISO-8601 UTC string."""
    return datetime.fromtimestamp(int(token["exp"]), tz=UTC).isoformat()


class UsernameTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Obtain JWTs using FMMS username credentials."""

    username_field = "username"

    @classmethod
    def get_token(cls, user: FMMSUser) -> Any:
        """Add stable FMMS claims to issued JWTs."""
        token = super().get_token(user)
        token["username"] = user.username
        token["email"] = user.email
        token["full_name"] = user.full_name
        token["role"] = user.role
        return token

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

    def validate(self, attrs: dict[str, Any]) -> dict[str, str]:
        """Return a refreshed access token plus its expiration timestamp."""
        data = super().validate(attrs)
        data["token_type"] = _TOKEN_TYPE
        data["access_expires_at"] = _expires_at(AccessToken(data["access"]))
        return data


class TokenObtainPairResponseSerializer(serializers.Serializer):
    """Document token obtain response fields."""

    access = serializers.CharField()
    refresh = serializers.CharField()
    token_type = serializers.CharField()
    access_expires_at = serializers.DateTimeField()
    refresh_expires_at = serializers.DateTimeField()
    user = serializers.DictField()


class TokenRefreshResponseSerializer(serializers.Serializer):
    """Document token refresh response fields."""

    access = serializers.CharField()
    token_type = serializers.CharField()
    access_expires_at = serializers.DateTimeField()


class UserProfileSerializer(serializers.Serializer):
    """Serialize the authenticated FMMS user for frontend session state."""

    id = serializers.UUIDField(read_only=True)
    username = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    full_name = serializers.CharField(read_only=True)
    role = serializers.CharField(read_only=True)
    is_staff = serializers.BooleanField(read_only=True)
    is_superuser = serializers.BooleanField(read_only=True)
