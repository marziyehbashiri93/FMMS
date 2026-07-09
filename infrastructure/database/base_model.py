"""
FMMS Abstract Base Model.

Every domain ORM model in FMMS must inherit from BaseModel.
This enforces the standard audit trail, soft-delete pattern,
and UUID primary key across the entire data layer.

Decision: ADR-006 — Soft Delete on All Business Records.
"""

import uuid

from django.conf import settings
from django.db import models


class BaseModel(models.Model):
    """
    Abstract base model providing audit fields for all FMMS domain models.

    Fields:
        id:         UUID primary key — decoupled from DB sequence.
        created_at: UTC timestamp set automatically on creation.
        created_by: FK to FMMSUser who created this record (nullable).
        updated_at: UTC timestamp updated automatically on every save.
        updated_by: FK to FMMSUser who last updated this record (nullable).
        is_deleted: Soft-delete flag — True means logically deleted.
        deleted_at: UTC timestamp of soft deletion (nullable).
        deleted_by: FK to FMMSUser who soft-deleted this record (nullable).

    Rules:
        - Never call .delete() directly — use a service that sets is_deleted=True.
        - All repository list queries must filter is_deleted=False by default.
        - Physical deletion is forbidden on all business records.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique record identifier (UUID4).",
    )

    # ── Creation audit ────────────────────────────────────────────────────────
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="UTC timestamp when this record was created.",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_created",
        help_text="User who created this record.",
    )

    # ── Update audit ──────────────────────────────────────────────────────────
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="UTC timestamp of the last update to this record.",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_updated",
        help_text="User who last updated this record.",
    )

    # ── Soft delete ───────────────────────────────────────────────────────────
    is_deleted = models.BooleanField(
        default=False,
        db_index=True,
        help_text="True if this record has been soft-deleted. Never physically remove records.",
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="UTC timestamp of soft deletion.",
    )
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_deleted",
        help_text="User who soft-deleted this record.",
    )

    class Meta:
        abstract = True

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.id!r})"
