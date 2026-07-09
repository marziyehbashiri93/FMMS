"""SAP Transaction Manager package.

Provides ``SAPTransactionManager`` — the sole gateway for all SAP write operations.
Every write that must be tracked for idempotency, retry, and audit uses this manager.
"""

from infrastructure.sap.transaction.sap_transaction_manager import SAPTransactionManager

__all__ = ["SAPTransactionManager"]
