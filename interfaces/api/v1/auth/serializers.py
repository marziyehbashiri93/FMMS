"""Authentication serializers for API v1."""

from __future__ import annotations

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Obtain JWTs using FMMS's email username field."""

    username_field = "email"
