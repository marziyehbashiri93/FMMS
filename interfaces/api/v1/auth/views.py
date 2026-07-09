"""JWT authentication endpoints."""

from __future__ import annotations

from typing import Any

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from interfaces.api.v1.auth.serializers import EmailTokenObtainPairSerializer


class FMMSJWTTokenObtainPairView(TokenObtainPairView):
    """Issue an access and refresh JWT pair."""

    serializer_class = EmailTokenObtainPairSerializer

    @extend_schema(tags=["auth"])
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Issue a JWT pair for valid email credentials."""
        return super().post(request, *args, **kwargs)


class FMMSJWTTokenRefreshView(TokenRefreshView):
    """Refresh an FMMS access token."""

    @extend_schema(tags=["auth"])
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Issue a new access token from a refresh token."""
        return super().post(request, *args, **kwargs)
