"""
FMMS Pytest Configuration and Shared Fixtures.

Provides reusable fixtures available across the entire test suite.
Domain tests (unit) should not use db-dependent fixtures.
Integration and API tests use the database fixtures.
"""

import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client() -> APIClient:
    """
    Return an unauthenticated DRF API test client.

    Use for testing endpoints that don't require authentication,
    or for testing 401 responses.
    """
    return APIClient()


@pytest.fixture
def admin_user(db: None) -> "FMMSUser":  # type: ignore[name-defined]  # noqa: F821
    """
    Return a persisted FMMSUser with ADMIN role.

    Requires database access (db fixture). Use only in integration tests.
    """
    from tests.factories.user_factory import FMMSUserFactory

    return FMMSUserFactory(role="ADMIN", is_staff=True, is_superuser=True)


@pytest.fixture
def supervisor_user(db: None) -> "FMMSUser":  # type: ignore[name-defined]  # noqa: F821
    """Return a persisted FMMSUser with SUPERVISOR role."""
    from tests.factories.user_factory import FMMSUserFactory

    return FMMSUserFactory(role="SUPERVISOR")


@pytest.fixture
def technician_user(db: None) -> "FMMSUser":  # type: ignore[name-defined]  # noqa: F821
    """Return a persisted FMMSUser with TECHNICIAN role."""
    from tests.factories.user_factory import FMMSUserFactory

    return FMMSUserFactory(role="TECHNICIAN")


@pytest.fixture
def viewer_user(db: None) -> "FMMSUser":  # type: ignore[name-defined]  # noqa: F821
    """Return a persisted FMMSUser with VIEWER role (read-only)."""
    from tests.factories.user_factory import FMMSUserFactory

    return FMMSUserFactory(role="VIEWER")


@pytest.fixture
def authenticated_client(api_client: APIClient, admin_user: "FMMSUser") -> APIClient:  # type: ignore[name-defined]  # noqa: F821
    """
    Return an API client authenticated as an admin user.

    Uses force_authenticate to bypass token/session setup in unit-style tests.
    """
    api_client.force_authenticate(user=admin_user)
    return api_client


@pytest.fixture
def supervisor_client(api_client: APIClient, supervisor_user: "FMMSUser") -> APIClient:  # type: ignore[name-defined]  # noqa: F821
    """Return an API client authenticated as a supervisor."""
    api_client.force_authenticate(user=supervisor_user)
    return api_client


@pytest.fixture
def technician_client(api_client: APIClient, technician_user: "FMMSUser") -> APIClient:  # type: ignore[name-defined]  # noqa: F821
    """Return an API client authenticated as a technician."""
    api_client.force_authenticate(user=technician_user)
    return api_client
