"""
FMMS User Manager.

Custom manager for FMMSUser that provides create_user and
create_superuser helpers with role-aware defaults.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.contrib.auth.base_user import BaseUserManager

if TYPE_CHECKING:
    from apps.authentication.infrastructure.models import FMMSUser


class FMMSUserManager(BaseUserManager["FMMSUser"]):
    """
    Custom manager for the FMMSUser model.

    Replaces Django's default UserManager to enforce username-based login,
    contact email storage, and FMMS role assignment.
    """

    def create_user(
        self,
        username: str,
        email: str,
        full_name: str,
        password: str | None = None,
        **extra_fields: Any,
    ) -> FMMSUser:
        """
        Create and save a standard FMMS user.

        Args:
            username: The user's login identifier.
            email: The user's email address.
            full_name: The user's full display name.
            password: Plain-text password (hashed before storage).
            **extra_fields: Additional model fields (e.g. role, is_active).

        Returns:
            The newly created FMMSUser instance.

        Raises:
            ValueError: If email is not provided.
        """
        if not username:
            raise ValueError("Username is required for all FMMS users.")
        if not email:
            raise ValueError("Email address is required for all FMMS users.")

        username = self.model.normalize_username(username)
        email = self.normalize_email(email)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)

        user: FMMSUser = self.model(
            username=username,
            email=email,
            full_name=full_name,
            **extra_fields,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(
        self,
        username: str,
        email: str,
        full_name: str,
        password: str | None = None,
        **extra_fields: Any,
    ) -> FMMSUser:
        """
        Create and save a superuser with ADMIN role.

        Args:
            username: The user's login identifier.
            email: The user's email address.
            full_name: The user's full display name.
            password: Plain-text password.
            **extra_fields: Additional model fields.

        Returns:
            The newly created superuser FMMSUser instance.

        Raises:
            ValueError: If is_staff or is_superuser are explicitly set to False.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        from apps.authentication.infrastructure.models import FMMSUserRole

        extra_fields.setdefault("role", FMMSUserRole.ADMIN)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(username, email, full_name, password, **extra_fields)
