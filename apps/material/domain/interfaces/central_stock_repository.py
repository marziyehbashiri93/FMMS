"""Abstract repository interface for SAP-synced central warehouse stock."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from decimal import Decimal

from apps.material.domain.stock_entities import CentralStock


class ICentralStockRepository(ABC):
    """Port for persisting and reading central warehouse stock cache rows."""

    @abstractmethod
    def get_by_id(self, stock_id: uuid.UUID) -> CentralStock:
        """Retrieve one stock row by UUID."""

    @abstractmethod
    def get_by_sap_key(
        self,
        material: str,
        plant: str,
        storage_location: str,
        inventory_stock_type: str,
    ) -> CentralStock | None:
        """Retrieve one stock row by SAP natural key."""

    @abstractmethod
    def get_available_quantity(self, material_number: str) -> Decimal:
        """Return unrestricted quantity for a material across KH08 rows.

        Matching uses both padded ``material`` and short ``material_code``.
        """

    @abstractmethod
    def material_exists(self, material_number: str) -> bool:
        """Return whether any active KH08 stock row exists for the material."""

    @abstractmethod
    def get_material_name(self, material_number: str) -> str:
        """Return the first non-empty material name for the material, if any."""

    @abstractmethod
    def list_active(
        self,
        *,
        plant: str = "",
        storage_location: str = "",
        search: str = "",
    ) -> list[CentralStock]:
        """Return active stock rows with optional filters."""

    @abstractmethod
    def save(self, stock: CentralStock) -> CentralStock:
        """Persist a new or updated stock row."""
