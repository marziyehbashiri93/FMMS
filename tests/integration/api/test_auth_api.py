"""API integration tests for JWT authentication endpoints."""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from tests.factories.user_factory import FMMSUserFactory

pytestmark = pytest.mark.django_db


class TestAuthTokenAPI:
    """Cover token obtain and refresh flows."""

    def test_obtain_token_with_valid_credentials(self, api_client: APIClient) -> None:
        """Issue access and refresh tokens for a valid email/password."""
        user = FMMSUserFactory(role="ADMIN", password="testpass123!")
        response = api_client.post(
            "/api/v1/auth/token/",
            {"email": user.email, "password": "testpass123!"},
            format="json",
        )
        assert response.status_code == 200
        assert "access" in response.data
        assert "refresh" in response.data

    def test_obtain_token_rejects_invalid_credentials(
        self, api_client: APIClient
    ) -> None:
        """Reject invalid credentials with 401."""
        user = FMMSUserFactory(role="ADMIN", password="testpass123!")
        response = api_client.post(
            "/api/v1/auth/token/",
            {"email": user.email, "password": "wrong-password"},
            format="json",
        )
        assert response.status_code == 401

    def test_refresh_token(self, api_client: APIClient) -> None:
        """Refresh an access token from a valid refresh token."""
        user = FMMSUserFactory(role="ADMIN", password="testpass123!")
        obtain = api_client.post(
            "/api/v1/auth/token/",
            {"email": user.email, "password": "testpass123!"},
            format="json",
        )
        assert obtain.status_code == 200
        refresh = api_client.post(
            "/api/v1/auth/token/refresh/",
            {"refresh": obtain.data["refresh"]},
            format="json",
        )
        assert refresh.status_code == 200
        assert "access" in refresh.data
