"""SAP Client abstraction layer.

Provides ``ISAPClient`` (the transport ABC) and concrete implementations:

- ``SAPODataClient``: Production OData HTTP client (real SAP, not yet connected).
- ``SAPBAPIClient``: Production RFC/BAPI client (real SAP, not yet connected).
- ``MockSAPClient``: Test/development client that simulates SAP responses.
"""

from infrastructure.sap.client.base import ISAPClient, SAPClientError

__all__ = ["ISAPClient", "SAPClientError"]
