"""Abstract repository interface for inspection checklist templates."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from apps.inspection.domain.template_entities import InspectionTemplate


class IInspectionTemplateRepository(ABC):
    """Port for persisting SAP-synced inspection checklist templates."""

    @abstractmethod
    def get_by_id(self, template_id: uuid.UUID) -> InspectionTemplate:
        """Retrieve a template by UUID.

        Args:
            template_id: Template identifier.

        Returns:
            Matching ``InspectionTemplate``.

        Raises:
            DomainNotFoundError: If the template does not exist.
        """

    @abstractmethod
    def get_by_sap_key(
        self, code: str, code_group: str, catalog_type: str
    ) -> InspectionTemplate | None:
        """Retrieve a template by its SAP natural key.

        Args:
            code: SAP ``Code``.
            code_group: SAP ``CodeGroup``.
            catalog_type: SAP catalog type.

        Returns:
            Matching template or ``None``.
        """

    @abstractmethod
    def list_active(self) -> list[InspectionTemplate]:
        """Return all active checklist templates.

        Returns:
            Ordered list of active templates.
        """

    @abstractmethod
    def save(self, template: InspectionTemplate) -> InspectionTemplate:
        """Persist a new or updated template.

        Args:
            template: Template aggregate to save.

        Returns:
            The saved template.
        """
