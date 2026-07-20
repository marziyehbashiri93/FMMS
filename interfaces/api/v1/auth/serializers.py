"""Authentication serializers for API v1."""

from __future__ import annotations

from typing import Any

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.authentication.infrastructure.models import FMMSUser


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
        """Return tokens plus the authenticated user profile."""
        data = super().validate(attrs)
        data["user"] = UserProfileSerializer(self.user).data
        return data


class UserProfileSerializer(serializers.Serializer):
    """Serialize the authenticated FMMS user for frontend session state."""

    id = serializers.UUIDField(read_only=True)
    username = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    full_name = serializers.CharField(read_only=True)
    role = serializers.CharField(read_only=True)
    is_staff = serializers.BooleanField(read_only=True)
    is_superuser = serializers.BooleanField(read_only=True)
