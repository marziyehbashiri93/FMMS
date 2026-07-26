"""Abstract repository interface for SAP-synced fault catalog rows."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from apps.fault.domain.catalog_entities import FaultCatalog


class IFaultCatalogRepository(ABC):
    """Port for persisting and reading fault catalog cache rows."""

    @abstractmethod
    def get_by_id(self, catalog_id: uuid.UUID) -> FaultCatalog:
        """Retrieve one catalog row by UUID."""

    @abstractmethod
    def get_by_sap_key(self, code: str, code_group: str) -> FaultCatalog | None:
        """Retrieve one catalog row by SAP ``Code`` and ``CodeGroup``."""

    @abstractmethod
    def list_active(
        self,
        *,
        code_group: str = "",
        defect_class: str = "",
        search: str = "",
    ) -> list[FaultCatalog]:
        """Return active catalog rows with optional filters."""

    @abstractmethod
    def save(self, catalog: FaultCatalog) -> FaultCatalog:
        """Persist a new or updated catalog row."""
