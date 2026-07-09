"""SAP Fault Catalog Port — abstract contract for defect code access.

SAP maintains the authoritative catalog of defect codes used when recording
faults against fleet vehicles. FMMS reads these codes to populate inspection
and fault reporting forms.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from core.sap.dtos.fault_catalog import SAPDefectCodeDTO


class ISAPFaultCatalogPort(ABC):
    """Business contract for reading defect codes from SAP's fault catalog.

    All transport and encoding details are the responsibility of the implementing
    adapter. This port exposes only business-meaningful operations.
    """

    @abstractmethod
    def list_defect_codes(
        self,
        catalog_profile: str | None = None,
    ) -> list[SAPDefectCodeDTO]:
        """Retrieve defect codes, optionally filtered by catalog profile.

        Args:
            catalog_profile: Optional SAP catalog profile identifier.
                When ``None``, all accessible defect codes are returned.

        Returns:
            A list of ``SAPDefectCodeDTO`` objects. May be empty.

        Raises:
            SAPIntegrationError: If SAP returns an error response.
        """

    @abstractmethod
    def get_defect_code(
        self,
        code: str,
        catalog_profile: str,
    ) -> SAPDefectCodeDTO:
        """Retrieve a single defect code from the SAP catalog.

        Args:
            code: The defect code identifier.
            catalog_profile: The SAP catalog profile the code belongs to.

        Returns:
            A populated ``SAPDefectCodeDTO``.

        Raises:
            SAPIntegrationError: If SAP returns an error or the code is not found.
        """
