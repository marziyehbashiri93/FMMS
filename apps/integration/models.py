"""Model shim — re-exports ORM models for Django auto-discovery."""

from apps.integration.infrastructure.models import SAPTransactionModel

__all__ = ["SAPTransactionModel"]
