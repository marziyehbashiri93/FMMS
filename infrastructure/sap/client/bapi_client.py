"""SAPBAPIClient — production-ready RFC/BAPI client stub.

This client handles real SAP BAPI/RFC communication via SAP's RFC protocol.
It requires the ``pyrfc`` library and a working SAP system with RFC access.

NOT connected to a real SAP system. The real RFC connection will be configured
when SAP environment details are provided.

When ``SAPConfig.use_mock`` is ``True`` (development/test), the
``MockSAPClient`` is used instead of this class.
"""

from __future__ import annotations

import logging
from typing import Any

from infrastructure.sap.client.base import ISAPClient, SAPClientError

logger = logging.getLogger(__name__)

# pyrfc is an optional dependency — it requires a native SAP NW RFC SDK.
# The import is guarded so that tests and development environments without
# the native library installed do not fail at import time.
try:
    import pyrfc  # type: ignore[import-untyped]

    _PYRFC_AVAILABLE = True
except ImportError:
    pyrfc = None  # type: ignore[assignment]
    _PYRFC_AVAILABLE = False


class SAPBAPIClient(ISAPClient):
    """RFC/BAPI client for SAP write integrations.

    Uses ``pyrfc`` to call SAP BAPI and RFC function modules. Requires the
    SAP NetWeaver RFC SDK to be installed on the host system.

    Args:
        ashost: SAP application server hostname or IP.
        sysnr: SAP system number (e.g. ``"00"``).
        client: SAP client/mandant code (e.g. ``"100"``).
        user: SAP technical user login.
        passwd: SAP technical user password.
        lang: SAP logon language (default ``"EN"``).
    """

    def __init__(
        self,
        ashost: str,
        sysnr: str,
        client: str,
        user: str,
        passwd: str,
        lang: str = "EN",
    ) -> None:
        if not _PYRFC_AVAILABLE:
            raise SAPClientError(
                "pyrfc is not installed. BAPI calls require the SAP NW RFC SDK "
                "and pyrfc. Set SAP_USE_MOCK=True in development."
            )
        self._conn_params = {
            "ashost": ashost,
            "sysnr": sysnr,
            "client": client,
            "user": user,
            "passwd": passwd,
            "lang": lang,
        }

    def odata_get(
        self,
        service: str,
        entity: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Not supported on BAPIClient.

        Raises:
            NotImplementedError: Always. Use ``SAPODataClient`` for OData reads.
        """
        raise NotImplementedError(
            "SAPBAPIClient does not support OData requests. Use SAPODataClient."
        )

    def odata_post(
        self,
        service: str,
        entity: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Not supported on BAPIClient.

        Raises:
            NotImplementedError: Always. Use ``SAPODataClient`` for OData writes.
        """
        raise NotImplementedError(
            "SAPBAPIClient does not support OData requests. Use SAPODataClient."
        )

    def odata_get_xml(
        self,
        service: str,
        entity: str = "",
        params: dict[str, Any] | None = None,
    ) -> str:
        """Not supported on BAPIClient."""
        raise NotImplementedError(
            "SAPBAPIClient does not support OData requests. Use SAPODataClient."
        )

    def bapi_call(
        self,
        function_module: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Invoke a SAP BAPI or RFC function module via pyrfc.

        Opens a connection per call (connection pooling deferred to production
        configuration). Always calls ``BAPI_TRANSACTION_COMMIT`` on success.

        Args:
            function_module: The BAPI/RFC function module name.
            params: Import and table parameters.

        Returns:
            Export and return parameters as a dictionary.

        Raises:
            SAPClientError: On pyrfc communication errors.
        """
        logger.debug(
            "SAP BAPI call",
            extra={"function_module": function_module},
        )
        try:
            with pyrfc.Connection(**self._conn_params) as conn:
                result: dict[str, Any] = conn.call(function_module, **params)
                conn.call("BAPI_TRANSACTION_COMMIT", WAIT="X")
                return result
        except pyrfc.CommunicationError as exc:
            raise SAPClientError(
                f"SAP RFC communication error calling {function_module}: {exc}"
            ) from exc
        except pyrfc.LogonError as exc:
            raise SAPClientError(
                f"SAP RFC logon failed calling {function_module}: {exc}"
            ) from exc
        except pyrfc.ABAPRuntimeError as exc:
            raise SAPClientError(
                f"SAP ABAP runtime error calling {function_module}: {exc}"
            ) from exc
