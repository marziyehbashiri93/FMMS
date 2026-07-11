"""Repository interface for external repair invoices."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from apps.repair.domain.invoice_entities import ExternalRepairInvoice


class IExternalRepairInvoiceRepository(ABC):
    """Persistence port for external repair invoices."""

    @abstractmethod
    def get_by_id(self, invoice_id: uuid.UUID) -> ExternalRepairInvoice:
        """Get invoice by id."""

    @abstractmethod
    def list_all(self) -> list[ExternalRepairInvoice]:
        """List all invoices."""

    @abstractmethod
    def save(self, invoice: ExternalRepairInvoice) -> ExternalRepairInvoice:
        """Persist invoice aggregate."""
