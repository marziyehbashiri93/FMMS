"""Read-only port for resolving FMMS user profile summaries."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from apps.authentication.application.dto.user_profile_dto import UserProfileSummaryDTO


class IUserProfileReader(ABC):
    """Lookup user display metadata by UUID without leaking ORM types."""

    @abstractmethod
    def get_profile(self, user_id: uuid.UUID) -> UserProfileSummaryDTO | None:
        """Return profile summary for ``user_id``, or ``None`` if not found."""
