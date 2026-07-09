"""SAP Adapter implementations.

Each adapter:
- Implements one SAP port interface from ``core.sap.ports``.
- Receives an ``ISAPClient`` instance by constructor injection.
- Maps SAP raw responses to domain DTOs via a private ``_map_*`` method (ACL).
- Raises ``SAPIntegrationError`` (from ``apps.integration.domain.exceptions``)
  on all SAP-level errors; never exposes transport exceptions upward.
"""
